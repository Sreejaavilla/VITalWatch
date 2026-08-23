"""Hybrid retrieval over the case corpus: BM25, concept expansion, fused with RRF.

Two retrievers that fail differently, and a fusion step that needs only their rankings.

**BM25** is the standard lexical ranker, implemented here rather than imported so the
parameters are visible: `k1` controls how quickly repeated terms stop helping, `b` how
hard a long document is penalised for its length. It is exact and unforgiving — it finds
"hepatic" only in documents containing "hepatic".

**Concept expansion** is the second retriever, and it is deliberately not a dense vector
model. Real dense retrieval means embedding the query at request time, which means
shipping a neural model; this build has no such model, and labelling a lexical retriever
"semantic" or "dense" would be exactly the overclaim this project refuses to make about
MedDRA. What it does instead is real and useful: it expands the query through the
curated vocabulary in `app/terms.csv`, so a query for "liver" reaches documents that
say "transaminase" because both map to the controlled term *Hepatic enzyme increased*.
That is a genuinely different signal from surface overlap — it retrieves documents with
no query word in them at all — and it is the same vocabulary the adverse-event coder
uses, so the retriever and the coder cannot disagree about what a term means.

**Reciprocal Rank Fusion** combines them: `score(d) = Σ 1/(k + rank_r(d))` over the
retrievers that returned `d`. It is the real algorithm, `k = 60` as in the original
paper. The property that matters here is that it consumes *ranks*, not scores — BM25's
scale and the concept retriever's scale never have to be reconciled, which is why a
fusion step is used at all rather than a weighted sum.

Swapping in an embedding model replaces `concept_search` and nothing else: `rrf` takes
ranked lists and does not care where they came from.
"""

from __future__ import annotations

import csv
import math
import re
from collections import defaultdict
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from . import pv

CORPUS_PATH = Path(__file__).resolve().parent / "corpus.csv"

#: BM25 term-frequency saturation. Above this, repeating a word stops adding much.
K1 = 1.5
#: BM25 length normalisation. 1.0 penalises long documents fully, 0.0 not at all.
B = 0.75
#: RRF smoothing constant, from Cormack et al. Large enough that the top of one list
#: cannot dominate the fusion on its own.
RRF_K = 60

#: Words carrying no retrieval signal. Short list on purpose — an aggressive stop list
#: silently removes terms that matter in a clinical corpus.
STOPWORDS = frozenset("""
a an the and or of in on at to for with without is are was were be been being by from
as that this these those it its not no any all each per than then which who whom
""".split())

_WORD = re.compile(r"[a-z0-9]+")


def tokenize(text: str) -> list[str]:
    return [t for t in _WORD.findall(text.lower()) if t not in STOPWORDS and len(t) > 1]


@dataclass(frozen=True)
class Document:
    id: str
    kind: str          # protocol | ayurveda | historical | publication | regulatory
    source: str
    title: str
    provenance: str
    text: str

    @property
    def tokens(self) -> list[str]:
        return tokenize(f"{self.title} {self.text}")


@dataclass(frozen=True)
class Hit:
    document: Document
    score: float
    rank: int
    #: The words that actually caused the match, for showing why a document was returned.
    matched: tuple[str, ...] = ()


@lru_cache(maxsize=1)
def load_corpus() -> tuple[Document, ...]:
    """Read the corpus once. Small enough that an index on disk would be ceremony."""
    with CORPUS_PATH.open(newline="", encoding="utf-8") as fh:
        return tuple(Document(**row) for row in csv.DictReader(fh))


# ----------------------------------------------------------------------- retriever 1


def bm25_search(query: str, limit: int = 8) -> list[Hit]:
    """Okapi BM25. Exact term overlap, length-normalised."""
    docs = load_corpus()
    q_terms = tokenize(query)
    if not q_terms:
        return []

    tokenised = {d.id: d.tokens for d in docs}
    lengths = {d_id: len(t) for d_id, t in tokenised.items()}
    avg_len = sum(lengths.values()) / len(lengths)

    # Document frequency per query term.
    df: dict[str, int] = defaultdict(int)
    for term in set(q_terms):
        for tokens in tokenised.values():
            if term in tokens:
                df[term] += 1

    n = len(docs)
    scored: list[tuple[float, Document, set[str]]] = []
    for doc in docs:
        tokens = tokenised[doc.id]
        score = 0.0
        matched: set[str] = set()
        for term in q_terms:
            tf = tokens.count(term)
            if tf == 0:
                continue
            matched.add(term)
            # Probabilistic IDF, floored at zero so a term in every document cannot
            # push a score negative.
            idf = max(0.0, math.log((n - df[term] + 0.5) / (df[term] + 0.5) + 1.0))
            norm = tf * (K1 + 1) / (tf + K1 * (1 - B + B * lengths[doc.id] / avg_len))
            score += idf * norm
        if score > 0:
            scored.append((score, doc, matched))

    scored.sort(key=lambda s: (-s[0], s[1].id))
    return [
        Hit(document=d, score=round(s, 3), rank=i, matched=tuple(sorted(m)))
        for i, (s, d, m) in enumerate(scored[:limit], start=1)
    ]


# ----------------------------------------------------------------------- retriever 2


@lru_cache(maxsize=1)
def _concept_index() -> dict[str, set[str]]:
    """Every vocabulary synonym mapped to the controlled term it belongs to.

    Built from the same `app/terms.csv` the adverse-event coder uses, so a concept means
    the same thing to the retriever and to the coder.
    """
    index: dict[str, set[str]] = defaultdict(set)
    for term in pv.load_terms():
        for synonym in (*term.synonyms, term.term):
            for word in tokenize(synonym):
                index[word].add(term.code)
    return dict(index)


def concepts_in(text: str) -> set[str]:
    """The controlled-term codes a piece of text touches."""
    index = _concept_index()
    found: set[str] = set()
    for word in tokenize(text):
        found |= index.get(word, set())
    return found


def concept_search(query: str, limit: int = 8) -> list[Hit]:
    """Rank by shared controlled-term concepts rather than by shared words.

    This is what finds a document about "transaminase" for a query about "liver": both
    resolve to the same controlled term, and neither contains the other's wording. Score
    is the proportion of the query's concepts a document covers, which keeps a long
    document from winning simply by mentioning more things.
    """
    q_concepts = concepts_in(query)
    if not q_concepts:
        return []

    scored: list[tuple[float, Document, set[str]]] = []
    for doc in load_corpus():
        shared = q_concepts & concepts_in(f"{doc.title} {doc.text}")
        if not shared:
            continue
        scored.append((len(shared) / len(q_concepts), doc, shared))

    scored.sort(key=lambda s: (-s[0], s[1].id))
    by_code = {t.code: t.term for t in pv.load_terms()}
    return [
        Hit(
            document=d,
            score=round(s, 3),
            rank=i,
            matched=tuple(sorted(by_code.get(c, c) for c in m)),
        )
        for i, (s, d, m) in enumerate(scored[:limit], start=1)
    ]


# --------------------------------------------------------------------------- fusion


@dataclass(frozen=True)
class FusedHit:
    document: Document
    score: float
    rank: int
    #: Where each retriever placed this document, or None if it did not return it.
    bm25_rank: int | None
    concept_rank: int | None
    matched: tuple[str, ...]

    @property
    def found_by(self) -> str:
        if self.bm25_rank and self.concept_rank:
            return "both"
        return "lexical only" if self.bm25_rank else "concept only"


def rrf(rankings: dict[str, list[Hit]], k: int = RRF_K, limit: int = 6) -> list[FusedHit]:
    """Reciprocal Rank Fusion over any number of ranked lists.

    `score(d) = Σ 1/(k + rank)`. Ranks only — the retrievers' score scales never meet,
    which is the entire reason this is a fusion rather than a weighted sum.
    """
    positions: dict[str, dict[str, int]] = defaultdict(dict)
    documents: dict[str, Document] = {}
    matched: dict[str, set[str]] = defaultdict(set)

    for name, hits in rankings.items():
        for hit in hits:
            positions[hit.document.id][name] = hit.rank
            documents[hit.document.id] = hit.document
            matched[hit.document.id] |= set(hit.matched)

    scored = [
        (sum(1.0 / (k + rank) for rank in ranks.values()), doc_id, ranks)
        for doc_id, ranks in positions.items()
    ]
    scored.sort(key=lambda s: (-s[0], s[1]))

    return [
        FusedHit(
            document=documents[doc_id],
            score=round(score, 5),
            rank=i,
            bm25_rank=ranks.get("bm25"),
            concept_rank=ranks.get("concept"),
            matched=tuple(sorted(matched[doc_id])),
        )
        for i, (score, doc_id, ranks) in enumerate(scored[:limit], start=1)
    ]


def search(query: str, limit: int = 6) -> dict:
    """Run both retrievers and fuse. Returns all three rankings, for display.

    The intermediate rankings are returned rather than discarded because the point of
    showing a fusion step is being able to see what it changed.
    """
    lexical = bm25_search(query)
    conceptual = concept_search(query)
    fused = rrf({"bm25": lexical, "concept": conceptual}, limit=limit)
    return {
        "query": query,
        "bm25": lexical,
        "concept": conceptual,
        "fused": fused,
        "corpus_size": len(load_corpus()),
        "concepts": sorted(concepts_in(query)),
    }


if __name__ == "__main__":
    import sys

    q = " ".join(sys.argv[1:]) or "liver injury hepatic enzyme elevation"
    result = search(q)
    print(f"query: {q!r}   corpus: {result['corpus_size']} documents\n")
    for name in ("bm25", "concept"):
        print(f"{name}:")
        for hit in result[name]:
            print(f"  {hit.rank}. {hit.document.id}  {hit.score:>7}  {hit.document.title}")
        print()
    print("fused (RRF):")
    for hit in result["fused"]:
        print(
            f"  {hit.rank}. {hit.document.id}  {hit.score:.5f}  "
            f"[bm25 {hit.bm25_rank or '-'} | concept {hit.concept_rank or '-'}]  "
            f"{hit.document.title}"
        )
