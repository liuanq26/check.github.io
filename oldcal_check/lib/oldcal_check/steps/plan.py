"""step plan：日期 -> run 列表（替代 run_range.sh + genJob 里的目录扫描）。"""

import re

from ..context import Context
from .base import StepError


def discover_runs(ctx: Context, date: str):
    """返回 (原始数据目录, {run: [文件...]})。"""
    raw_dir = ctx.cfg.p("data.raw_dir", date=date)
    if raw_dir is None or not raw_dir.is_dir():
        raise StepError(f"raw data dir not found: {raw_dir}")

    pattern = ctx.cfg.get("data.file_glob", "*")
    regex = re.compile(ctx.cfg.get("data.run_regex") or r"(\d{5})")

    found = {}
    for path in sorted(raw_dir.glob(pattern)):
        if not path.is_file():
            continue
        match = regex.search(path.name)
        if not match:
            continue
        run = int(match.group(1))
        found.setdefault(run, []).append(path)
    if not found:
        raise StepError(f"no file matching {pattern} in {raw_dir}")
    return raw_dir, found


def run(ctx: Context, date: str) -> None:
    raw_dir, found = discover_runs(ctx, date)
    runs = sorted(found)

    ctx.store.upsert_batch(date, status="planned", n_runs=len(runs))
    for run_no in runs:
        ctx.store.upsert_run(run_no, date)
        if ctx.store.step_done(run_no, "plan") and not ctx.force:
            continue
        ctx.store.set_step(run_no, "plan", "done", f"{len(found[run_no])} raw files")

    ctx.log.info(
        f"{date}: {len(runs)} run(s) in {raw_dir} ({runs[0]}..{runs[-1]})"
    )
