"""步骤注册表。"""

from . import check, collect, genjob, meta, plan, report, submit, wait

ORDER = ["plan", "meta", "genjob", "submit", "wait", "collect", "check", "report"]

MODULES = {
    "plan": plan,
    "meta": meta,
    "genjob": genjob,
    "submit": submit,
    "wait": wait,
    "collect": collect,
    "check": check,
    "report": report,
}

# 这些步骤按整个日期区间跑一次，而不是每天各跑一次
GLOBAL = {"report"}

__all__ = ["ORDER", "MODULES", "GLOBAL"]
