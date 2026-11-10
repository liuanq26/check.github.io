"""step check: compile/run the checker, ingest per-run values, flag outliers.

plot_pdf.cpp writes noiseResults.txt (and graph.root, noise_<min>_<max>.pdf)
in the plot directory.  Thresholds come from Parameter.txt:
band = mean +/- n * sigma of the previous m runs.
"""
import json
import math
import time
from pathlib import Path
from shutil import which

from ..context import Context
from .. import params as paramfile
from ..utils import pdf as pdfutil
from ..utils import proc
from .base import StepError

# Page order inside noise_<min>_<max>.pdf produced by plot_pdf.cpp:
#   page 1 = T&Q matched occupancy, page 2 = T-channel occupancy
PAGE_MAP = {
    "occStp": 1, "nhitStp": 1, "occOut": 1, "nhitOut": 1,
    "occStp_T": 2, "nhitStp_T": 2, "occOut_T": 2, "nhitOut_T": 2,
}


def ensure_binary(ctx):
    cfg = ctx.cfg
    binary = cfg.check_binary
    source = cfg.check_source

    if not source.is_file():
        raise StepError("checker source not found: %s" % source)
    if binary.is_file() and binary.stat().st_mtime >= source.stat().st_mtime:
        return

    if ctx.dry:
        ctx.log.info("[dry-run] would compile %s" % source.name)
        return

    if which("root-config") is None:
        raise StepError("root-config not found, source your BOSS env first")

    cflags = proc.run("root-config --cflags", timeout=60)
    libs = proc.run("root-config --libs", timeout=60)
    if not (cflags.ok and libs.ok):
        raise StepError("root-config failed")

    binary.parent.mkdir(parents=True, exist_ok=True)
    cmd = (["g++"] + str(cfg.get("check.compile_flags", "")).split() + [source.name]
           + cflags.out.split() + libs.out.split())
    if cfg.get("check.lib_dir"):
        cmd += ["-L", str(cfg.get("check.lib_dir"))]
    cmd += str(cfg.get("check.link_libs", "")).split()
    cmd += ["-o", str(binary)]

    ctx.log.info("compiling %s -> %s" % (source.name, binary))
    res = proc.run(cmd, cwd=source.parent, timeout=1800,
                   log_file=cfg.state_dir / "logs" / "compile.log")
    if not res.ok:
        raise StepError("compile failed: %s" % res.tail(400))


def parse_noise_results(path):
    """noiseResults.txt -> {run: {quantity: value}}.

    Format written by plot_pdf.cpp:
        94207 OK 1000 nevents=1000 nhitStp=... occStp=...
    Lines starting with '#' are comments.
    """
    path = Path(path)
    if not path.is_file():
        return {}
    out = {}
    for line in path.read_text(errors="replace").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        toks = line.split()
        if len(toks) < 2:
            continue
        try:
            run = int(toks[0])
        except ValueError:
            continue
        rec = {}
        for tok in toks[2:]:
            if "=" not in tok:
                continue
            key, _, value = tok.partition("=")
            try:
                rec[key] = float(value)
            except ValueError:
                pass
        if rec:
            out[run] = rec
    return out


def ingest(ctx, date, rows):
    stored = 0
    for run, rec in rows.items():
        for quantity, value in rec.items():
            if quantity in ("run", "flag") or value is None:
                continue
            if isinstance(value, float) and (math.isnan(value) or math.isinf(value)):
                continue
            ctx.store.set_value(run, quantity, value, date)
            stored += 1
    return stored


def evaluate(ctx, date, params):
    anomalies = []
    runs = [r["run"] for r in ctx.store.runs_of(date)]
    min_runs = int(params.get("min_runs", 5))
    floor_frac = float(params.get("min_rel_band", 0.0))

    for quantity, spec in params["quantities"].items():
        if not spec["enabled"]:
            continue
        window = int(spec["m"])
        k = float(spec["n"])
        for run in runs:
            value = ctx.store.value(run, quantity)
            if value is None:
                continue
            history = ctx.store.recent_values(quantity, run, window)
            if len(history) < min_runs:
                continue
            mean = sum(history) / len(history)
            var = sum((x - mean) ** 2 for x in history) / max(len(history) - 1, 1)
            sigma = math.sqrt(var)
            low, high = mean - k * sigma, mean + k * sigma
            floor = abs(mean) * floor_frac
            if (high - low) < 2 * floor:
                low, high = mean - floor, mean + floor
            if value < low or value > high:
                anomalies.append({
                    "date": date, "run": run, "quantity": quantity,
                    "label": spec["label"], "value": value,
                    "mean": mean, "sigma": sigma, "low": low, "high": high,
                    "m": window, "n": k,
                })
    return anomalies


def _extract_pages(source, pages, outdir):
    out = []
    for page in sorted(set(pages)):
        target = outdir / ("p%d.pdf" % page)
        res = proc.run(["qpdf", "--empty", "--pages", str(source), str(page), "--", str(target)],
                       timeout=120)
        if res.ok and target.is_file():
            out.append(target)
    return out


def write_reports(ctx, date, anomalies, source_pdf, profile_name):
    cfg = ctx.cfg
    cfg.reports_dir.mkdir(parents=True, exist_ok=True)
    txt = cfg.reports_dir / ("anomaly_%s.txt" % date)

    lines = []
    for a in anomalies:
        lines.append(
            "%s  %6d  %-11s %9.6f  out of [%.6f, %.6f]  mean %.6f  n=%.1f  m=%d"
            % (a["date"], a["run"], a["quantity"], a["value"], a["low"], a["high"],
               a["mean"], a["n"], a["m"])
        )
    if lines:
        txt.write_text("\n".join(lines) + "\n", encoding="utf-8")
    elif txt.is_file():
        txt.unlink()

    if not anomalies:
        return txt, None

    cover = cfg.state_dir / "cover" / ("anomaly_%s.pdf" % date)
    head = ["noise-check anomalies", "date: %s" % date,
            "%d point(s) out of band" % len(anomalies)]
    for a in anomalies[:6]:
        head.append("%s %6d  %10.6f" % (a["quantity"], a["run"], a["value"]))
    if len(anomalies) > 6:
        head.append("... +%d more" % (len(anomalies) - 6))
    pdfutil.write_text_page(cover, head, 200 * 72 / 25.4, 127 * 72 / 25.4, font_size=18)

    parts = [cover]
    if source_pdf and Path(source_pdf).is_file() and profile_name == "noiseRun" and which("qpdf"):
        pages = [PAGE_MAP[a["quantity"]] for a in anomalies if a["quantity"] in PAGE_MAP]
        parts += _extract_pages(Path(source_pdf), pages, cfg.state_dir / "cover")

    out = cfg.reports_dir / ("anomaly_%s.pdf" % date)
    tool, err = pdfutil.merge_pdfs(parts, out, log_file=cfg.state_dir / "logs" / "anomaly.log")
    if err:
        ctx.log.warn("anomaly pdf failed: %s" % err)
        return txt, None
    return txt, out


def run(ctx: Context, date):
    cfg = ctx.cfg
    profiles = cfg.get("check.profiles") or {}
    if not profiles:
        ctx.log.warn("no check.profiles configured, skip")
        return

    runs = [r["run"] for r in ctx.store.runs_of(date) if r["hist"]]
    if not runs:
        ctx.store.upsert_batch(date, note="no hist product")
        ctx.log.warn("%s: no hist product, skip check" % date)
        return

    ensure_binary(ctx)
    binary = cfg.check_binary
    runmin, runmax = min(runs), max(runs)

    params_file = Path(cfg.package) / "Parameter.txt"
    params = paramfile.load(params_file, cfg.package)
    if params.get("error"):
        ctx.log.warn(params["error"])

    produced = {}
    parsed = {}
    default_results = str(cfg.get("check.results_file") or "noiseResults.txt")

    for name, profile in profiles.items():
        hist_dir = cfg.result_dir / str(profile.get("hist_dir") or "hist")
        cwd = cfg.result_dir / str(profile["cwd"])
        cwd.mkdir(parents=True, exist_ok=True)
        out_name = str(profile["output"]).format(runmin=runmin, runmax=runmax)
        out_path = cwd / out_name
        results_rel = str(profile.get("results_file") or default_results)
        results_path = cwd / results_rel

        if ctx.dry:
            ctx.log.info("[dry-run] (cd %s && %s %s %d %d)" % (cwd, binary, hist_dir, runmin, runmax))
            continue

        started = time.time()
        res = proc.run([str(binary), str(hist_dir), str(runmin), str(runmax)],
                       cwd=cwd, timeout=float(cfg.get("check.timeout", 7200)),
                       log_file=cfg.state_dir / "logs" / ("check_%s_%s.log" % (name, date)))
        if not res.ok or not out_path.is_file():
            ctx.log.warn("%s/%s: check failed rc=%d %s" % (date, name, res.rc, res.tail(200)))
            for run_no in runs:
                ctx.store.set_step(run_no, "check:%s" % name, "failed", res.tail(200))
            continue

        produced[name] = out_path
        ctx.log.info("%s: %s -> %s (%.0f KB, %.0fs)"
                     % (date, name, out_path.name, out_path.stat().st_size / 1024.0,
                        time.time() - started))

        rows = parse_noise_results(results_path)
        parsed[name] = rows
        if rows:
            stored = ingest(ctx, date, rows)
            ctx.log.info("%s: values %d from %d run(s) in %s"
                         % (date, stored, len(rows), results_path.name))
        else:
            ctx.log.warn("%s: no %s, numeric check skipped" % (date, results_path.name))

        for run_no in runs:
            row = ctx.store.run_row(run_no)
            checks = json.loads(row["checks"]) if row["checks"] else {}
            checks[name] = str(out_path)
            ctx.store.upsert_run(run_no, checks=json.dumps(checks, ensure_ascii=False))
            ctx.store.set_step(run_no, "check:%s" % name, "done")

    if ctx.dry or not produced:
        return

    first = list(profiles.keys())[0]
    if not parsed.get(first):
        ctx.log.warn("%s: no numeric results, anomaly check skipped" % date)
        return

    anomalies = evaluate(ctx, date, params)
    txt, pdf = write_reports(ctx, date, anomalies, produced.get(first), first)

    if anomalies:
        for a in anomalies:
            ctx.log.warn("%s run %d  %-11s %10.6f  out of [%.6f, %.6f]  mean %.6f n=%.1f m=%d"
                         % (a["date"], a["run"], a["quantity"], a["value"], a["low"],
                            a["high"], a["mean"], a["n"], a["m"]))
        ctx.log.warn("%s: %d anomaly(s) -> %s%s"
                     % (date, len(anomalies), txt, "" if pdf is None else " , %s" % pdf))
    else:
        ctx.log.info("%s: all enabled quantities within band (m=%d, n=%.1f)"
                     % (date, int(params.get("m", 200)), float(params.get("n", 1.0))))
