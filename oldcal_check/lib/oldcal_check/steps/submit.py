"""step submit：把日期目录里的 rec<run>.txt 交给 boss.condor。"""

from ..batch import bosscondor
from ..context import Context


def run(ctx: Context, date: str) -> None:
    rows = ctx.store.runs_of(date)
    if not rows:
        if ctx.dry:
            scripts = sorted(p.name for p in ctx.date_dir(date).glob("rec*.txt"))
            if scripts:
                ctx.log.info("%s: %s rec<run>.txt (%d)"
                             % (date, " ".join(ctx.cfg.submit_command()), len(scripts)))
            for name in scripts:
                ctx.log.info("[dry-run] (cd %s && %s %s)"
                             % (ctx.date_dir(date), " ".join(ctx.cfg.submit_command()), name))
        else:
            ctx.log.warn("%s: no runs, skip submit" % date)
        return

    cmd_hint = " ".join(ctx.cfg.submit_command())
    ctx.log.info(f"{date}: {cmd_hint} rec<run>.txt ({len(rows)} runs)")

    n_ok = n_bad = 0
    for row in rows:
        run_no = row["run"]
        if ctx.store.step_done(run_no, "submit") and not ctx.force:
            n_ok += 1
            continue

        script = ctx.job_script(date, run_no)
        if not script.is_file():
            ctx.store.set_step(run_no, "submit", "failed", f"missing {script.name}")
            ctx.store.upsert_run(run_no, status="failed", error="job file not generated")
            n_bad += 1
            continue

        job_id, res = bosscondor.submit(ctx, date, run_no)
        if res is None:  # dry-run
            ctx.store.set_step(run_no, "submit", "skip", "dry-run")
            continue

        if res.ok:
            ctx.store.upsert_run(run_no, status="submitted", job_id=job_id or "")
            ctx.store.set_step(run_no, "submit", "done", f"job {job_id or '?'}")
            n_ok += 1
        else:
            note = res.tail(300)
            if res.rc == 127:
                note = "boss.condor not found, source your BOSS env first"
            ctx.store.upsert_run(run_no, status="failed", error=note)
            ctx.store.set_step(run_no, "submit", "failed", note)
            n_bad += 1

    ctx.log.info(f"{date}: submit ok={n_ok} fail={n_bad}")
