"""Common step definitions."""


class StepError(RuntimeError):
    """A step failed; the pipeline records it and continues with other dates."""


__all__ = ["StepError"]
