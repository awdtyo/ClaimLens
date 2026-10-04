"""Deterministic result comparison (Stage 6 stub).

Hard rule: the model never decides whether results match. Numbers are
extracted, normalized and compared in Python with explicit tolerances.
No model call is allowed in this module.
"""


def compare() -> None:
    """Compare a measured value to a reported value."""
    raise NotImplementedError
