"""步骤公共部分。"""


class StepError(RuntimeError):
    """某一步失败，流水线记下来继续跑别的日期。"""


__all__ = ["StepError"]
