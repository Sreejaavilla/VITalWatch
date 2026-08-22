"""STUB_MODE fixture loader. OWNER: Kavin.

Reads contracts/fixtures/*.json. Backend stubs and frontend/mocks/ load the SAME
files, so the two can never drift in shape. That is what stops integration dying
at hour 20.
"""


def load(name):
    """Load contracts/fixtures/{name}.json. Cached after first read."""
    raise NotImplementedError


def stubbed(name):
    """Decorator: when settings.stub_mode is true, short-circuit the handler and
    return the fixture instead of touching the database."""
    raise NotImplementedError
