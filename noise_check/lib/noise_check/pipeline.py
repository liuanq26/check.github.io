"""Orchestration: decide which phase each date needs."""
import shutil
import sys

from .batch import bosscondor
from .context import Context
from .steps import GLOBAL, MODULES
from .steps import verify
from .steps.base import StepError
from .steps.plan import discover_runs

SUBMIT_STEPS = ["plan", "meta", "genjob", "submit"]
RESULT_STEPS = ["collect", "check"]

ACTION = {
    "new": "submit",
    "running": "wait",
    "failed": "resubmit",
    "ready": "collect",
}


def _all_done(ctx, date, step):
    rows = ctx.store.runs_of(date)
    return bool(rows) and all(ctx.store.step_done(r["run"], step) for r in rows)


def count_runs(ctx, date):
    """Read-only count of runs for this date (used before submitting)."""
    try:
        _, found = discover_runs(ctx, date)
        return len(found)
    except StepError:
        return 0


def build_plan(ctx, dates, phase="auto"):
    plan = []
    for date in dates:
        state = verify.assess(ctx, date)
        action, jobs, runs = "skip", 0, 0

        if phase == "submit":
            if state in ("new", "failed"):
                action, jobs, runs = "submit", count_runs(ctx, date), 0
        elif phase == "result":
            if state == "ready":
                action, runs = "collect", len(ctx.store.runs_of(date))
        else:
            if state == "new":
                action, jobs, runs = "submit", count_runs(ctx, date), 0
            elif state == "failed":
                action, jobs = "resubmit", count_runs(ctx, date)
                runs = len(ctx.store.runs_of(date))
            elif state == "running":
                action, runs = "wait", len(ctx.store.runs_of(date))
            else:
                action, runs = "collect", len(ctx.store.runs_of(date))

        plan.append({"date": date, "state": state, "action": action,
                     "jobs": jobs, "runs": runs})
    return plan


def print_plan(ctx, plan, phase="auto"):
    cfg = ctx.cfg
    total_jobs = sum(p["jobs"] for p in plan)
    print()
    print("plan")
    print("  result  %s%s" % (cfg.result_dir, "" if cfg.is_shared_path() else "  (not shared)"))
    print("  range   %s..%s (%d day%s)"
          % (plan[0]["date"], plan[-1]["date"], len(plan), "" if len(plan) == 1 else "s"))
    print("  runs    %d" % sum(p["runs"] + p["jobs"] for p in plan))
    for p in plan:
        tail = "%d job(s)" % p["jobs"] if p["jobs"] else "%d run(s)" % p["runs"]
        print("          %s  %-8s -> %-8s %s"
              % (p["date"], p["state"], p["action"], tail))
    if total_jobs:
        print("  cmd     %s rec<run>.txt" % " ".join(cfg.submit_command()))
    print()
    sys.stdout.flush()


def ask_submit(total):
    try:
        answer = input("submit %d job(s)? [y/N] " % total).strip().lower()
    except EOFError:
        return False
    return answer in ("y", "yes")


def ask_resubmit(dates):
    try:
        answer = input("resubmit %s? (deletes those date folders first) [y/N] "
                       % " ".join(dates)).strip().lower()
    except EOFError:
        return False
    return answer in ("y", "yes")


def clean_date(ctx, date):
    """rm -rf the date folder, stale products and the db rows of that date."""
    runs = [r["run"] for r in ctx.store.runs_of(date)]
    if ctx.dry:
        ctx.log.info("[dry-run] would clean %s (%d run(s))" % (date, len(runs)))
        return
    shutil.rmtree(str(ctx.date_dir(date)), ignore_errors=True)
    for run in runs:
        for path in ctx.cfg.product_paths(run):
            try:
                path.unlink()
            except OSError:
                pass
    ctx.store.reset_date(date)
    ctx.log.info("%s: cleaned %d run(s), date folder removed" % (date, len(runs)))


def report_errors(ctx, date):
    for row in ctx.store.runs_of(date):
        ctx.log.error("%s run %d: %s"
                      % (date, row["run"], bosscondor.job_error(ctx, date, row["run"])))


def _run_phase(ctx, date, steps):
    for step in steps:
        if ctx.force or not _all_done(ctx, date, step):
            ctx.log.info("%s: %s" % (date, step))
            MODULES[step].run(ctx, date)


def run_smart(ctx, dates, phase="auto", assume_yes=False):
    dates = list(dates)
    plan = build_plan(ctx, dates, phase)

    if not assume_yes:
        print_plan(ctx, plan, phase)

    # Failed dates: show errors, then ask once (it deletes folders).
    resubmit = [p for p in plan if p["action"] == "resubmit"]
    if resubmit and not assume_yes and not ctx.dry:
        print()
        print("previous run did not pass:")
        for p in resubmit:
            for row in ctx.store.runs_of(p["date"]):
                print("  %s run %d: %s"
                      % (p["date"], row["run"],
                         bosscondor.job_error(ctx, p["date"], row["run"])))
        for p in resubmit:
            p["errors_shown"] = True
        sys.stdout.flush()
        if not sys.stdin.isatty():
            ctx.log.error("refusing to resubmit without a terminal; add --yes")
            return 1
        if not ask_resubmit([p["date"] for p in resubmit]):
            for p in resubmit:
                p["action"] = "skip"
                p["declined"] = True
            ctx.log.info("resubmit declined")

    total_jobs = sum(p["jobs"] for p in plan if p["action"] in ("submit", "resubmit"))
    if total_jobs and not assume_yes and not ctx.dry:
        if not sys.stdin.isatty():
            ctx.log.error("refusing to submit %d job(s) without a terminal; add --yes"
                          % total_jobs)
            return 1
        if not ask_submit(total_jobs):
            ctx.log.info("not submitted")
            return 0

    failures = 0
    checked = []

    for p in plan:
        date, action = p["date"], p["action"]
        ctx.log.bind(date)
        ctx.store.upsert_batch(date)

        if action == "skip":
            if p.get("declined"):
                continue
            if p["state"] != "new":
                ctx.log.warn("%s: not ready (%s), skip" % (date, p["state"]))
            if p["state"] == "failed":
                report_errors(ctx, date)
            continue

        if action == "wait":
            ctx.log.info("%s: %d job(s) still in queue, come back later"
                         % (date, p["runs"] or count_runs(ctx, date)))
            continue

        if action == "resubmit":
            ctx.log.warn("%s: previous run did not pass -> clean and resubmit" % date)
            if not p.get("errors_shown"):
                report_errors(ctx, date)
            clean_date(ctx, date)
            action = "submit"

        if action == "submit":
            try:
                _run_phase(ctx, date, SUBMIT_STEPS)
            except StepError as exc:
                failures += 1
                ctx.log.error("%s/submit: %s" % (date, exc))
            continue

        # collect
        try:
            _run_phase(ctx, date, RESULT_STEPS)
            checked.append(date)
        except StepError as exc:
            failures += 1
            ctx.log.error("%s/result: %s" % (date, exc))

    if checked and "report" in MODULES:
        try:
            MODULES["report"].run(ctx, checked)
        except StepError as exc:
            failures += 1
            ctx.log.error("report: %s" % exc)

    return failures


def run_range(ctx: Context, dates, steps):
    """Explicit step list (from --steps or a single step name)."""
    dates = list(dates)
    failures = 0
    per_date = [s for s in steps if s not in GLOBAL]

    for date in dates:
        ctx.log.bind(date)
        ctx.store.upsert_batch(date)
        for step in per_date:
            if not ctx.force and _all_done(ctx, date, step):
                ctx.log.info("%s: %s already done, skip" % (date, step))
                continue
            try:
                MODULES[step].run(ctx, date)
            except StepError as exc:
                failures += 1
                ctx.log.error("%s/%s: %s" % (date, step, exc))
                break

    for step in [s for s in steps if s in GLOBAL]:
        try:
            MODULES[step].run(ctx, dates)
        except StepError as exc:
            failures += 1
            ctx.log.error("%s: %s" % (step, exc))

    return failures
