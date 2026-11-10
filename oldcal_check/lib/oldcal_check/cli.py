"""Command line entry.

    ./oldcal_check.exe                    interactive panel
    ./oldcal_check.exe 260918             auto: submit, or collect when jobs are done
    ./oldcal_check.exe submit 260918      phase 1: plan meta genjob submit
    ./oldcal_check.exe collect 260918     phase 2: collect check report
    ./oldcal_check.exe status [260918]
    ./oldcal_check.exe selfcheck
"""
import argparse
import re
import sys
from datetime import datetime, timedelta

from . import __version__
from .config import Config
from .context import Context
from .pipeline import ask_submit, count_runs, run_range, run_smart
from .state import Store
from .steps import ORDER
from .utils.log import Logger

VERBS = set(ORDER) | {"status", "run", "all", "selfcheck", "collect", "result"}

_ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")


def _clean(text):
    return _ANSI_RE.sub("", text or "")


def _fmt(value, width, default="-"):
    if value is None or value == "":
        return default.rjust(width)
    return str(value).rjust(width)


def expand_dates(first, last):
    d0 = datetime.strptime(first, "%y%m%d")
    d1 = datetime.strptime(last, "%y%m%d") if last else d0
    if d0 > d1:
        d0, d1 = d1, d0
    out = []
    while d0 <= d1:
        out.append(d0.strftime("%y%m%d"))
        d0 += timedelta(days=1)
    return out


def print_status(store, dates=None):
    rows = []
    if dates:
        for date in dates:
            rows.extend(store.runs_of(date))
    else:
        rows = store.all_runs()
    if not rows:
        print("(no records yet)")
        return

    print("%-7s %6s %-10s %9s %7s %7s %2s %2s %3s  %s"
          % ("date", "run", "state", "events", "BPR", "BER", "NT", "H", "PDF", "note"))
    print("-" * 76)
    for r in rows:
        bpr = "%.4f" % r["bpr"] if r["bpr"] else None
        ber = "%.4f" % r["ber"] if r["ber"] else None
        print("%-7s %6s %-10s %s %s %s %2s %2s %3s  %s"
              % (r["date"] or "??????", r["run"], r["status"] or "",
                 _fmt(r["nevents"], 9), _fmt(bpr, 7), _fmt(ber, 7),
                 "Y" if r["ntuple"] else "", "Y" if r["hist"] else "",
                 "Y" if r["pdf"] else "", _clean(r["error"])[:52]))

    per_date = {}
    for r in rows:
        per_date.setdefault(r["date"] or "??????", []).append(r)
    print()
    for date, items in sorted(per_date.items()):
        ok = sum(1 for r in items if r["status"] in ("ok", "done"))
        bad = sum(1 for r in items if r["status"] == "failed")
        print("%s: %d run(s), ok %d, failed %d" % (date, len(items), ok, bad))


def selfcheck(cfg):
    import shutil
    import sqlite3 as _sqlite

    from .utils import proc

    rows = []

    def add(ok, name, detail=""):
        rows.append((ok, name, detail))

    add(sys.version_info >= (3, 6), "python", sys.version.split()[0])
    add(cfg.config_file.is_file(), "config", str(cfg.config_file))
    add(cfg.package.is_dir(), "package", str(cfg.package))

    try:
        probe = cfg.result_dir / ".probe"
        probe.parent.mkdir(parents=True, exist_ok=True)
        probe.write_text("x")
        probe.unlink()
        writable, why = True, ""
    except Exception as exc:  # noqa: BLE001
        writable, why = False, str(exc)
    add(writable, "result writable", str(cfg.result_dir) + ("" if writable else "  " + why))
    add(True, "result shared", "yes" if cfg.is_shared_path() else "no (worker nodes may fail to write)")
    add(cfg.state_dir.is_dir(), "state dir", str(cfg.state_dir))

    add(_sqlite.sqlite_version_info >= (3, 7, 0), "sqlite", _sqlite.sqlite_version)

    for label, path in (("ntuple dir", cfg.ntuple_dir), ("hist dir", cfg.hist_dir),
                        ("plot dir", cfg.plot_dir), ("reports dir", cfg.reports_dir)):
        add(path.is_dir(), label, str(path))

    raw_dir = cfg.p("data.raw_dir", date="260101")
    add(raw_dir is not None and raw_dir.parent.is_dir(), "raw data root",
        str(raw_dir.parent if raw_dir else ""))

    submit_cmd = str(cfg.get("batch.submit_cmd") or "boss.condor").split()[0]
    add(shutil.which(submit_cmd) is not None, submit_cmd, "source your BOSS env first")
    add(shutil.which("root-config") is not None, "root-config", "needed to compile the checker")
    add(shutil.which("g++") is not None, "g++", "")
    merger = "gs" if shutil.which("gs") else ("pdfunite" if shutil.which("pdfunite") else None)
    add(merger is not None, "pdf merge", merger or "need gs or pdfunite")
    add(shutil.which("mysql") is not None, "mysql", "")

    add(cfg.check_source.is_file(), "checker source", str(cfg.check_source))
    add(True, "checker", str(cfg.check_binary) if cfg.check_binary.is_file()
        else "not compiled yet, built on first check")

    params_file = cfg.package / "Parameter.txt"
    add(params_file.is_file(), "Parameter.txt", str(params_file))

    try:
        import reportlab
        cover = "reportlab " + str(getattr(reportlab, "Version", "?"))
    except Exception:
        cover = "not installed, built-in ascii cover"
    add(True, "cover page", cover)

    host = (cfg.get("db.hosts") or [""])[0]
    res = proc.run(["mysql", "--connect-timeout=%d" % int(cfg.get("db.timeout", 10)),
                    "-h", host, "-u", str(cfg.get("db.user", "guest")),
                    "-p%s" % cfg.get("db.password", ""), "-N", "-B", "-e", "select 1"],
                   timeout=30)
    add(res.ok, "run database", host if res.ok else (res.tail(120) or host))

    print("oldcal-check selfcheck  (package=%s)" % cfg.package)
    print("-" * 72)
    bad = 0
    for ok, name, detail in rows:
        if not ok:
            bad += 1
        print("[%s] %-16s %s" % ("OK  " if ok else "FAIL", name, detail))
    print("-" * 72)
    print("all ok" if bad == 0 else "%d issue(s)" % bad)
    return 0 if bad == 0 else 1


def build_parser():
    ap = argparse.ArgumentParser(
        prog="oldcal_check.exe",
        description="BESIII MDC calibration check",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    ap.add_argument("args", nargs="*", help="YYMMDD [YYMMDD], or a verb")
    ap.add_argument("--result", help="result dir (default: ../result next to the package)")
    ap.add_argument("--config", help="config file")
    ap.add_argument("--group", help='boss.condor -g value, "" to omit')
    ap.add_argument("--steps", help="run only these steps, comma separated")
    ap.add_argument("--resume", dest="resume", action="store_true", default=True)
    ap.add_argument("--no-resume", dest="resume", action="store_false")
    ap.add_argument("--force", action="store_true", help="redo everything")
    ap.add_argument("--max-wait", type=int, default=None, help="wait timeout in seconds")
    ap.add_argument("--dry-run", action="store_true", help="print commands only")
    ap.add_argument("--no-ask", action="store_true", help="never show the panel")
    ap.add_argument("-y", "--yes", action="store_true",
                    help="skip the submit confirmation (for scripts)")
    ap.add_argument("-q", "--quiet", action="store_true")
    ap.add_argument("-V", "--version", action="version", version="oldcal-check %s" % __version__)
    return ap


def main(argv=None):
    if argv is None:
        argv = sys.argv[1:]
    argv = list(argv)

    if not argv and sys.stdin.isatty():
        from .prompt import run_panel

        argv = run_panel()
        if argv is None:
            print("cancelled")
            return 0
        if not argv:
            return 0

    return _run(argv)


def _run(argv):
    parser = build_parser()
    a = parser.parse_args(argv)

    tokens = list(a.args)
    verb = None
    if tokens and tokens[0] in VERBS:
        verb = tokens.pop(0)

    bad = [t for t in tokens if not re.fullmatch(r"\d{6}", t)]
    if bad:
        parser.error("unknown argument(s): %s (dates are YYMMDD)" % " ".join(bad))

    overrides = {}
    batch_over = {}
    if a.group is not None:
        batch_over["group"] = a.group
    if a.max_wait is not None:
        batch_over["max_wait"] = int(a.max_wait)
    if batch_over:
        overrides["batch"] = batch_over

    cfg = Config(result=a.result, config_file=a.config, overrides=overrides)
    cfg.ensure_dirs()

    if verb == "selfcheck":
        return selfcheck(cfg)

    if verb == "status":
        dates = expand_dates(tokens[0], tokens[1] if len(tokens) > 1 else None) if tokens else None
        store = Store(cfg.state_db)
        print_status(store, dates)
        store.close()
        return 0

    if not tokens:
        parser.print_help()
        return 2

    dates = expand_dates(tokens[0], tokens[1] if len(tokens) > 1 else None)

    phase = "auto"
    if verb == "submit":
        phase = "submit"
    elif verb in ("collect", "result"):
        phase = "result"

    steps = None
    if a.steps:
        steps = [s.strip() for s in a.steps.split(",") if s.strip()]
        unknown = [s for s in steps if s not in ORDER]
        if unknown:
            parser.error("unknown step(s): %s" % unknown)
    elif phase == "auto" and verb in ORDER:
        steps = [verb]

    store = Store(cfg.state_db)
    store.dry = a.dry_run
    log = Logger(cfg.state_dir / "logs" / "run.log", quiet=a.quiet)

    log.info("oldcal-check %s  package=%s" % (__version__, cfg.package))
    log.info("result %s" % cfg.result_dir)
    log.info("dates %s..%s (%d)" % (dates[0], dates[-1], len(dates)))
    log.info("submit command: %s rec<run>.txt" % " ".join(cfg.submit_command()))

    ctx = Context(cfg=cfg, store=store, log=log, dry=a.dry_run, force=a.force)

    try:
        if steps is not None:
            if "submit" in steps and not a.yes and not a.dry_run:
                total = sum(count_runs(ctx, d) for d in dates)
                if total:
                    if not sys.stdin.isatty():
                        log.error("refusing to submit %d job(s) without a terminal; add --yes" % total)
                        return 1
                    if not ask_submit(total):
                        log.info("not submitted")
                        return 0
            failures = run_range(ctx, dates, steps)
        else:
            failures = run_smart(ctx, dates, phase, assume_yes=a.yes)
    except KeyboardInterrupt:
        log.warn("interrupted; finished steps are recorded")
        failures = 130

    print()
    print_status(store, dates)
    store.close()
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
