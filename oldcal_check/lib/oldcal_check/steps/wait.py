"""step wait：等作业真的跑完（替代 gnl 的语义）。

判定顺序：
  1. bosslog 里有 "Application Manager Terminated successfully"  -> 成功
  2. 作业已经不在 hep_q 队列里，且 bosslog 存在但没有成功标记     -> 失败（立即，不等超时）
  3. 都没有                                                      -> 继续等
"""

import time

from ..batch import bosscondor
from ..context import Context


def _pending(ctx: Context, date: str):
    out = []
    for row in ctx.store.runs_of(date):
        if not ctx.force and not ctx.store.step_done(row["run"], "submit"):
            continue
        if not ctx.force and ctx.store.step_done(row["run"], "wait"):
            continue
        out.append(row["run"])
    return out


def run(ctx: Context, date: str) -> None:
    if ctx.dry:
        ctx.log.info("[dry-run] wait skipped")
        return

    poll = float(ctx.cfg.get("batch.poll_interval", 60))
    max_wait = float(ctx.cfg.get("batch.max_wait", 43200))
    deadline = time.time() + max_wait

    round_no = 0
    while True:
        pending = _pending(ctx, date)
        if not pending:
            break
        round_no += 1

        queue = bosscondor.queue_job_ids(ctx)
        still = []
        for run_no in pending:
            log_path = ctx.bosslog(date, run_no)
            if bosscondor.bosslog_finished(log_path):
                ctx.store.upsert_run(run_no, status="ran", bosslog_ok=1, error=None)
                ctx.store.set_step(run_no, "wait", "done")
                continue

            row = ctx.store.run_row(run_no)
            job_id = (row["job_id"] or "").strip() if row else ""
            finished_without_flag = (
                queue is not None
                and log_path.is_file()
                and (not job_id or job_id not in queue)
            )
            if finished_without_flag:
                err = bosscondor.bosslog_error(log_path) or "job ended without success mark"
                ctx.store.upsert_run(run_no, status="failed", error=err[:300])
                ctx.store.set_step(run_no, "wait", "failed", err[:200])
                continue

            still.append(run_no)

        ctx.log.info(
            "%s: round %d, done %d, waiting %d%s"
            % (date, round_no, len(pending) - len(still), len(still),
               "" if queue is not None else " (queue unavailable, bosslog only)")
        )
        if not still:
            break
        if time.time() >= deadline:
            for run_no in still:
                err = bosscondor.bosslog_error(ctx.bosslog(date, run_no)) or "timeout"
                ctx.store.upsert_run(run_no, status="failed", error=err[:300])
                ctx.store.set_step(run_no, "wait", "timeout", err[:200])
            ctx.log.warn("%s: %d run(s) timed out" % (date, len(still)))
            break
        time.sleep(poll)

    ok = sum(1 for r in ctx.store.runs_of(date) if r["bosslog_ok"])
    bad = sum(1 for r in ctx.store.runs_of(date) if r["status"] == "failed")
    ctx.log.info("%s: wait ok=%d fail=%d" % (date, ok, bad))
