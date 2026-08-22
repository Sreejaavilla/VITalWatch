"""Sentence Transformers + FAISS semantic coding. OWNER: Sreeja.

Embed the curated term list once (Colab, committed as embeddings.npy), embed the
incoming narrative at request time, return nearest neighbours with cosine scores.

Acceptance: `code("patient had a bad headache")` returns Headache as the top hit.
"""


class FaissCodingService:
    def __init__(self, embeddings_path, model_name):
        raise NotImplementedError

    def code(self, narrative, top_k=3):
        raise NotImplementedError

    def code_drug(self, drug_text, top_k=3):
        raise NotImplementedError


def build_index(terms_csv, out_path, model_name):
    """Run in Colab, commit the .npy. Not run at request time on the free tier."""
    raise NotImplementedError
