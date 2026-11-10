"""Interactive panel: result dir, start/end date and a read-only preview."""
import json
import sys
from datetime import datetime, timedelta
from pathlib import Path
from types import SimpleNamespace

from .config import Config
from .context import Context
from .state import Store
from .utils.log import Logger


def _rule(char="-", width=64):
    print(char * width)


def _load_last(cfg):
    path = cfg.last_file()
    if path.is_file():
        try:
            return json.loads(path.read_text(encoding="utf-8")) or {}
        except Exception:
            return {}
    return {}


def _save_last(cfg, data):
    path = cfg.last_file()
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception as exc:  # noqa: BLE001
        print("(could not save last values: %r)" % (exc,))


def _today_yy():
    return datetime.now().strftime("%y%m%d")


def _valid_date(text):
    if len(text) != 6 or not text.isdigit():
        return False
    try:
        datetime.strptime(text, "%y%m%d")
        return True
    except ValueError:
        return False


def _ask(prompt, default, validate=None, hint=""):
    while True:
        try:
            raw = input("%-8s[%s] " % (prompt, default)).strip()
        except EOFError:
            return None
        if raw.lower() in ("q", "quit"):
            return None
        if not raw:
            return default
        if validate and not validate(raw):
            print("    %s" % (hint or "invalid input"))
            continue
        return raw


def _ask_result(cfg, default):
    while True:
        raw = _ask("result", default)
        if raw is None:
            return None
        path = Path(raw).expanduser()
        if not path.is_absolute():
            path = Path.cwd() / path
        path = path.resolve()
        try:
            path.mkdir(parents=True, exist_ok=True)
            probe = path / ".probe"
            probe.write_text("x")
            probe.unlink()
        except Exception as exc:  # noqa: BLE001
            print("    cannot write %s (%s)" % (path, exc))
            continue

        if not str(path).startswith(("/besfs", "/workfs", "/scratchfs", "/publicfs")):
            print("    warning: %s is not on a shared filesystem" % path)
            print("             worker nodes may fail to write hist")
            try:
                ok = input("    use it anyway? [y/N] ").strip().lower()
            except EOFError:
                ok = "n"
            if ok not in ("y", "yes"):
                continue
        return path


def _expand(first, last):
    d0 = datetime.strptime(first, "%y%m%d")
    d1 = datetime.strptime(last, "%y%m%d")
    if d0 > d1:
        d0, d1 = d1, d0
    out = []
    while d0 <= d1:
        out.append(d0.strftime("%y%m%d"))
        d0 += timedelta(days=1)
    return out


def preview(cfg, dates):
    """Read-only: runs per date + phase state. Returns (per_date, states, missing)."""
    from .steps.base import StepError
    from .steps.plan import discover_runs
    from .steps import verify

    fake = SimpleNamespace(cfg=cfg)
    per_date, missing = {}, []
    for date in dates:
        try:
            _, found = discover_runs(fake, date)
            per_date[date] = len(found)
        except StepError:
            per_date[date] = 0
            missing.append(date)

    states = {date: verify.NEW for date in dates}
    if cfg.state_db.is_file():
        store = Store(cfg.state_db)
        try:
            ctx = Context(cfg=cfg, store=store, log=Logger(quiet=True))
            for date in dates:
                states[date] = verify.assess(ctx, date)
        finally:
            store.close()
    return per_date, states, missing


def show_summary(cfg, start, end, dates):
    from .pipeline import ACTION

    per_date, states, missing = preview(cfg, dates)
    total = sum(per_date.values())
    jobs = sum(per_date[d] for d in dates
               if states[d] in ("new", "failed") and d not in missing)

    print()
    _rule("=")
    print("plan")
    print("  result  %s%s" % (cfg.result_dir, "" if cfg.is_shared_path() else "  (not shared)"))
    print("  range   %s..%s (%d day%s)" % (start, end, len(dates), "" if len(dates) == 1 else "s"))
    print("  runs    %d" % total)
    for date in dates:
        state = states[date]
        if date in missing:
            print("          %s  %3d  no data   -> skip" % (date, per_date[date]))
        else:
            print("          %s  %3d  %-8s  -> %s"
                  % (date, per_date[date], state, ACTION.get(state, "?")))
    print("  steps   submit: plan meta genjob submit | result: collect check report")
    _rule("=")
    return jobs


def run_panel():
    """Return an argv list, or None when the user quits."""
    cfg = Config()
    last = _load_last(cfg)
    default_result = last.get("result") or str(cfg.result_dir)
    default_start = last.get("end") or _today_yy()

    print()
    _rule("=")
    print("noise-check")
    print("  enter = default, q = quit")
    _rule()

    while True:
        result = _ask_result(cfg, default_result)
        if result is None:
            return None

        start = _ask("start", default_start, _valid_date, "expect YYMMDD")
        if start is None:
            return None
        end = _ask("end", start, _valid_date, "expect YYMMDD")
        if end is None:
            return None

        if end < start:
            print("    end < start, swapped")
            start, end = end, start

        cfg2 = Config(result=str(result))
        dates = _expand(start, end)
        jobs = show_summary(cfg2, start, end, dates)

        if jobs:
            question = "enter = submit %d job(s), n = edit, q = quit: " % jobs
        else:
            question = "enter = run, n = edit, q = quit: "
        try:
            answer = input(question).strip().lower()
        except EOFError:
            answer = "q"
        if answer in ("q", "quit"):
            return None
        if answer in ("n", "no"):
            continue

        _save_last(cfg, {
            "result": str(result),
            "start": start,
            "end": end,
            "saved_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        })
        return [start, end, "--result", str(result), "--yes"]
