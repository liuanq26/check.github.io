"""step collect：核对 xtNtuple / hist 是否落到 NTuple/ 和 hist/（替代两个 process_*.sh）。

模板里已经直接写绝对路径，正常情况这里只是核对；
若产物落在日期目录里，会顺手搬过去。
"""

import shutil

from ..context import Context


def _ensure(target, name: str, search_dirs) -> bool:
    if target.is_file():
        return True
    for d in search_dirs:
        candidate = d / name
        if candidate.is_file():
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(candidate), str(target))
            return True
    return False


def run(ctx: Context, date: str) -> None:
    cfg = ctx.cfg
    if ctx.dry:
        ctx.log.info("[dry-run] collect skipped")
        return
    cfg.ntuple_dir.mkdir(parents=True, exist_ok=True)
    cfg.hist_dir.mkdir(parents=True, exist_ok=True)
    jobs_dir = ctx.date_dir(date)

    ok = bad = 0
    for row in ctx.store.runs_of(date):
        run_no = row["run"]
        if ctx.store.step_done(run_no, "collect") and not ctx.force:
            ok += 1
            continue
        if not row["bosslog_ok"]:
            ctx.store.set_step(run_no, "collect", "skip", "job did not finish ok")
            continue

        ntuple = cfg.ntuple_dir / f"xtNtuple{run_no}.root"
        hist = cfg.hist_dir / f"hist{run_no}.root"

        got_ntuple = _ensure(ntuple, ntuple.name, [jobs_dir])
        got_hist = _ensure(hist, hist.name, [jobs_dir])

        if got_ntuple and got_hist:
            ctx.store.upsert_run(
                run_no, ntuple=str(ntuple), hist=str(hist), status="ok", error=None
            )
            ctx.store.set_step(run_no, "collect", "done")
            ok += 1
        else:
            missing = []
            if not got_ntuple:
                missing.append("xtNtuple")
            if not got_hist:
                missing.append("hist")
            msg = "missing " + "/".join(missing)
            ctx.store.upsert_run(run_no, status="failed", error=msg)
            ctx.store.set_step(run_no, "collect", "failed", msg)
            bad += 1

    ctx.log.info(f"{date}: collect ok={ok} missing={bad}")
