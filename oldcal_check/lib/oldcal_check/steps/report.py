"""step report：说明页 + 合并（替代 merge_pdf_to_ppt.py）。

说明页两条路：
  * 有 reportlab  -> 中文说明页
  * 没有 reportlab -> 内置最小 PDF 生成器，英文说明页（零依赖）
"""
import re
from pathlib import Path

from ..context import Context
from ..utils import pdf as minipdf
from ..utils import proc
from .base import StepError

MM = 72 / 25.4
_CJK_FONT = "MDCCJK"
_LATIN_FONT = "Helvetica"
_CJK_RE = re.compile("([\u3000-\u303f\u4e00-\u9fff\uff00-\uffef]+)")


def reportlab_available():
    try:
        import reportlab  # noqa: F401
        return True
    except Exception:
        return False


def _cjk_font(cfg):
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont

    path = cfg.get("report.cover_font")
    if path and Path(str(path)).is_file():
        if _CJK_FONT not in pdfmetrics.getRegisteredFontNames():
            pdfmetrics.registerFont(TTFont(_CJK_FONT, str(path)))
        return _CJK_FONT

    from reportlab.pdfbase.cidfonts import UnicodeCIDFont

    if "STSong-Light" not in pdfmetrics.getRegisteredFontNames():
        pdfmetrics.registerFont(UnicodeCIDFont("STSong-Light"))
    return "STSong-Light"


def _pieces(text):
    return [(part, bool(_CJK_RE.fullmatch(part))) for part in _CJK_RE.split(text) if part]


def _width(c, text, size, cjk):
    return sum(
        c.stringWidth(part, cjk if is_cjk else _LATIN_FONT, size)
        for part, is_cjk in _pieces(text)
    )


def _draw_line(c, x, y, text, size, cjk):
    for part, is_cjk in _pieces(text):
        font = cjk if is_cjk else _LATIN_FONT
        c.setFont(font, size)
        c.drawString(x, y, part)
        x += c.stringWidth(part, font, size)


def _make_cover_reportlab(target, lines, page_w, page_h, cfg):
    from reportlab.pdfgen import canvas

    cjk = _cjk_font(cfg)
    target.parent.mkdir(parents=True, exist_ok=True)
    c = canvas.Canvas(str(target), pagesize=(page_w, page_h))
    size = 34.0
    while size > 8 and max(_width(c, s, size, cjk) for s in lines) > page_w - 40:
        size -= 2
    y = page_h - 45
    for line in lines:
        _draw_line(c, 20, y, line, size, cjk)
        y -= size * 1.35
    c.showPage()
    c.save()
    return target


def make_cover(target, check_type, runmin, runmax, date, cfg):
    width_mm, height_mm = cfg.get("report.page_mm", [200, 127])
    page_w, page_h = float(width_mm) * MM, float(height_mm) * MM
    mode = str(cfg.get("report.cover_mode", "auto"))

    if mode in ("auto", "chinese") and reportlab_available():
        try:
            cn = [
                "Check type: %s" % check_type,
                "Runs: %d - %d" % (runmin, runmax),
                "Date: %s" % date,
            ]
            return _make_cover_reportlab(Path(target), cn, page_w, page_h, cfg)
        except Exception:
            pass

    en = [
        "Check : %s" % check_type,
        "Runs  : %d - %d" % (runmin, runmax),
        "Date  : %s" % date,
    ]
    return minipdf.write_text_page(Path(target), en, page_w, page_h)


def collect_pdfs(ctx):
    cfg = ctx.cfg
    items = []
    for name, profile in (cfg.get("check.profiles") or {}).items():
        folder = cfg.result_dir / str(profile["cwd"])
        if not folder.is_dir():
            continue
        for item in sorted(folder.glob("*.pdf")):
            match = re.search(r"(\d{4,})_(\d{4,})", item.stem)
            if not match:
                continue
            runmin, runmax = int(match.group(1)), int(match.group(2))
            date = ctx.store.date_of_run(runmin) or ""
            items.append((date, runmin, runmax, name, item))
    items.sort(key=lambda x: (x[0], x[1], x[3]))
    return items


def run(ctx: Context, dates):
    cfg = ctx.cfg
    items = collect_pdfs(ctx)
    if not items:
        ctx.log.warn("report: no section pdf found, run check first")
        return

    cover_dir = cfg.state_dir / "cover"
    cover_dir.mkdir(parents=True, exist_ok=True)

    sequence = []
    for date, runmin, runmax, name, item in items:
        if not ctx.dry:
            try:
                cover = make_cover(
                    cover_dir / ("%s_%s_%d_%d.pdf" % (name, date or "all", runmin, runmax)),
                    name, runmin, runmax, date, cfg,
                )
                sequence.append(cover)
            except Exception as exc:  # noqa: BLE001
                ctx.log.warn("cover page failed, skipped: %r" % (exc,))
        sequence.append(item)
        ctx.log.info("  + %-10s %s  %d-%d  %s" % (name, date or "????", runmin, runmax, item.name))

    first, last = items[0][0], items[-1][0]
    cfg.reports_dir.mkdir(parents=True, exist_ok=True)
    out = cfg.reports_dir / str(cfg.get("report.output")).format(
        **{"from": first or "all", "to": last or "all"}
    )

    if ctx.dry:
        ctx.log.info("[dry-run] merge %d file(s) -> %s" % (len(sequence), out))
        return

    tmp = out.with_suffix(".tmp.pdf")
    files = [str(p) for p in sequence]

    if proc.run("which gs", timeout=10).rc == 0:
        cmd = ["gs", "-q", "-dNOPAUSE", "-dBATCH", "-dSAFER", "-sDEVICE=pdfwrite",
               "-dCompatibilityLevel=1.4", "-sOutputFile=%s" % tmp] + files
        tool = "gs"
    elif proc.run("which pdfunite", timeout=10).rc == 0:
        cmd = ["pdfunite"] + files + [str(tmp)]
        tool = "pdfunite"
    else:
        raise StepError("neither gs nor pdfunite found")

    res = proc.run(cmd, timeout=900, log_file=cfg.state_dir / "logs" / "report.log")
    if not res.ok or not tmp.is_file():
        raise StepError("%s merge failed: %s" % (tool, res.tail(300)))
    tmp.replace(out)

    size_mb = out.stat().st_size / 1024.0 / 1024.0
    ctx.log.info("report: %s (%d sections, %.1f MB, %s)" % (out, len(sequence) // 2, size_mb, tool))

    for row in ctx.store.all_runs():
        if first and last and first <= (row["date"] or "") <= last:
            ctx.store.upsert_run(row["run"], pdf=str(out))
