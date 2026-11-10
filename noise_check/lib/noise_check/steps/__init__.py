"""Step registry."""

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

# These steps run once for the whole date range, not once per date.
GLOBAL = {"report"}

__all__ = ["ORDER", "MODULES", "GLOBAL"]
