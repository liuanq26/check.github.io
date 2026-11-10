"""Assess one date: has it been submitted, did it pass, is it still running?"""
from ..batch import bosscondor

NEW = "new"
RUNNING = "running"
FAILED = "failed"
READY = "ready"


def assess(ctx, date):
    rows = ctx.store.runs_of(date)
    if not rows or not ctx.date_dir(date).is_dir():
        return NEW

    if not all(ctx.store.step_done(r["run"], "submit") for r in rows):
        return NEW

    logs = [ctx.bosslog(date, r["run"]) for r in rows]
    if all(bosscondor.bosslog_finished(p) for p in logs):
        return READY

    queue = bosscondor.queue_job_ids(ctx)
    if queue is None:
        return RUNNING
    ids = set(str(r["job_id"]) for r in rows if r["job_id"])
    return RUNNING if (ids & queue) else FAILED
