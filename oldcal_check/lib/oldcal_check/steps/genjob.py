"""step genjob：渲染 rec<run>.txt（替代 genJob_ip.sh 的 sed 拼装）。"""

import os
from datetime import datetime

from ..context import Context
from ..config import PKG_ROOT
from .base import StepError
from .plan import discover_runs

TEMPLATE = PKG_ROOT / "templates" / "rec.txt.j2"


def render(template: str, **tokens: str) -> str:
    text = template
    for key, value in tokens.items():
        text = text.replace(f"@{key}@", value)
    leftover = [t for t in ("@RUNNO@", "@INPUTS@", "@NTUPLEFILE@", "@HISTFILE@", "@DATE@", "@JOBDIR@", "@GENERATED@") if t in text]
    if leftover:
        raise StepError(f"unresolved template placeholders: {leftover}")
    return text


def run(ctx: Context, date: str) -> None:
    cfg = ctx.cfg
    if not TEMPLATE.is_file():
        raise StepError(f"template not found: {TEMPLATE}")

    raw_dir, found = discover_runs(ctx, date)
    jobs_dir = ctx.date_dir(date)
    jobs_dir.mkdir(parents=True, exist_ok=True)
    cfg.ntuple_dir.mkdir(parents=True, exist_ok=True)
    cfg.hist_dir.mkdir(parents=True, exist_ok=True)

    template = TEMPLATE.read_text(encoding="utf-8")
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    made = 0
    for run_no in sorted(found):
        if ctx.store.step_done(run_no, "genjob") and not ctx.force:
            continue
        inputs = "\n".join(f'  "{p}"' for p in sorted(found[run_no]))
        if not inputs:
            ctx.store.set_step(run_no, "genjob", "failed", "no raw input")
            continue

        ntuple = cfg.ntuple_dir / f"xtNtuple{run_no}.root"
        hist = cfg.hist_dir / f"hist{run_no}.root"
        text = render(
            template,
            RUNNO=str(run_no),
            INPUTS=inputs,
            NTUPLEFILE=str(ntuple),
            HISTFILE=str(hist),
            DATE=date,
            JOBDIR=str(jobs_dir),
            GENERATED=now,
        )
        target = ctx.job_script(date, run_no)
        if ctx.dry:
            ctx.log.info(f"[dry-run] write {target} ({len(found[run_no])} input)")
        else:
            target.write_text(text, encoding="utf-8")
            os.chmod(target, 0o755)
        ctx.store.set_step(run_no, "genjob", "done", f"{len(found[run_no])} inputs")
        made += 1

    ctx.log.info(f"{date}: {made} job file(s) -> {jobs_dir}")
