"""Minimal PDF generator (Type1 Helvetica, ASCII), no third-party packages."""

from pathlib import Path


def _escape(text):
    return text.replace("\\", r"\\").replace("(", r"\(").replace(")", r"\)")


def _text_width(text, size):
    # Helvetica average character width is about 0.52 em.
    return len(text) * size * 0.52


def write_text_page(path, lines, page_w, page_h, font_size=26, margin=40):
    size = float(font_size)
    while size > 8 and max(_text_width(t, size) for t in lines) > page_w - 2 * margin:
        size -= 2

    leading = size * 1.45
    ops = []
    y = page_h - margin - size
    for line in lines:
        ops.append(
            "BT /F1 %.1f Tf %.1f %.1f Td (%s) Tj ET"
            % (size, margin, y, _escape(line))
        )
        y -= leading
    stream = "\n".join(ops).encode("latin-1", "replace")

    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        (
            "<< /Type /Page /Parent 2 0 R /MediaBox [0 0 %.2f %.2f] "
            "/Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>"
            % (page_w, page_h)
        ).encode("latin-1"),
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>",
        b"<< /Length " + str(len(stream)).encode("ascii") + b" >>\nstream\n" + stream + b"\nendstream",
    ]

    out = bytearray(b"%PDF-1.4\n")
    offsets = []
    for index, obj in enumerate(objects, 1):
        offsets.append(len(out))
        out += ("%d 0 obj\n" % index).encode("ascii") + obj + b"\nendobj\n"

    xref_pos = len(out)
    out += ("xref\n0 %d\n" % (len(objects) + 1)).encode("ascii")
    out += b"0000000000 65535 f \n"
    for offset in offsets:
        out += ("%010d 00000 n \n" % offset).encode("ascii")
    out += (
        "trailer\n<< /Size %d /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF\n"
        % (len(objects) + 1, xref_pos)
    ).encode("ascii")

    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(bytes(out))
    return target


def merge_pdfs(files, out, log_file=None, timeout=900):
    """Merge with gs (preferred) or pdfunite. Return (tool, error)."""
    from . import proc

    files = [str(f) for f in files]
    out = Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)

    if proc.run("which gs", timeout=10).rc == 0:
        cmd = ["gs", "-q", "-dNOPAUSE", "-dBATCH", "-dSAFER", "-sDEVICE=pdfwrite",
               "-dCompatibilityLevel=1.4", "-sOutputFile=%s" % out] + files
        tool = "gs"
    elif proc.run("which pdfunite", timeout=10).rc == 0:
        cmd = ["pdfunite"] + files + [str(out)]
        tool = "pdfunite"
    else:
        return None, "neither gs nor pdfunite found"

    res = proc.run(cmd, timeout=timeout, log_file=log_file)
    if not res.ok or not out.is_file():
        return None, res.tail(300)
    return tool, None
