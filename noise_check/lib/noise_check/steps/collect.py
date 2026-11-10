"""step collect: verify hist<run>.root and optionally nt<run>.root.

The job template already writes absolute paths, so normally this is just a
check.  If a product landed in the date folder (older job options), move it.
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
    require_ntuple = bool(cfg.get("collect.require_ntuple", False))

    ok = bad = 0
    for row in ctx.store.runs_of(date):
        run_no = row["run"]
        if ctx.store.step_done(run_no, "collect") and not ctx.force:
            ok += 1
            continue
        if not row["bosslog_ok"]:
            ctx.store.set_step(run_no, "collect", "skip", "job did not finish ok")
            continue

        fields = {}
        missing = []

        hist = cfg.hist_dir / f"hist{run_no}.root"
        if _ensure(hist, hist.name, [jobs_dir]):
            fields["hist"] = str(hist)
        else:
            missing.append("hist")

        ntuple_name = cfg.ntuple_name(run_no)
        if ntuple_name:
            ntuple = cfg.ntuple_dir / ntuple_name
            if _ensure(ntuple, ntuple.name, [jobs_dir]):
                fields["ntuple"] = str(ntuple)
            elif require_ntuple:
                missing.append("ntuple")

        if not missing:
            fields["status"] = "ok"
            fields["error"] = None
            ctx.store.upsert_run(run_no, **fields)
            ctx.store.set_step(run_no, "collect", "done")
            ok += 1
        else:
            msg = "missing " + "/".join(missing)
            ctx.store.upsert_run(run_no, status="failed", error=msg)
            ctx.store.set_step(run_no, "collect", "failed", msg)
            bad += 1

    ctx.log.info(f"{date}: collect ok={ok} missing={bad}")
