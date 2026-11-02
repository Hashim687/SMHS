from io import BytesIO
from xml.sax.saxutils import escape

import arabic_reshaper
from bidi.algorithm import get_display
from django.conf import settings
from django.utils import timezone
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

FONT = settings.BASE_DIR / "assets" / "NotoNaskhArabic-Regular.ttf"
HAS_FONT = FONT.exists()
if HAS_FONT:
    pdfmetrics.registerFont(TTFont("Naskh", str(FONT)))

arabic = lambda s: any("\u0600" <= c <= "\u06ff" for c in s)


def P(s, size=9, bold=False, color=colors.black):
    s = str(s if s is not None else "")
    if arabic(s) and HAS_FONT:
        s, font = get_display(arabic_reshaper.reshape(s)), "Naskh"
    else:
        font = "Helvetica-Bold" if bold else "Helvetica"
        s = s.encode("latin-1", "replace").decode("latin-1") if not HAS_FONT else s
    return Paragraph(escape(s), ParagraphStyle("p", fontName=font, fontSize=size, leading=size + 4, textColor=color))


def local(obj, lang):
    return {"ur": obj.name_ur, "ks": obj.name_ks or obj.name_ur}.get(lang) or ""


def flag(item):
    t = item.test
    if item.value is None or (t.ref_low is None and t.ref_high is None):
        return ""
    if t.ref_low is not None and item.value < t.ref_low:
        return "L"
    if t.ref_high is not None and item.value > t.ref_high:
        return "H"
    return "N"


def ref_range(t):
    if t.ref_low is not None and t.ref_high is not None:
        return f"{float(t.ref_low):g} - {float(t.ref_high):g}"
    if t.ref_high is not None:
        return f"< {float(t.ref_high):g}"
    if t.ref_low is not None:
        return f"> {float(t.ref_low):g}"
    return ""


def build(order, doctor_view=False):
    items = [i for i in order.items.select_related("test").order_by("id") if i.status == "resulted"]
    t = order.ticket
    buf = BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=18 * mm, rightMargin=18 * mm, topMargin=16 * mm, bottomMargin=16 * mm,
                            title="Laboratory Report", author="SMHS Srinagar Hospital")
    red = colors.HexColor("#a4161a")
    rows = [[P(h, 9, True, colors.white) for h in ("Test", "Result", "Unit", "Reference", "Flag")]]
    abn = []
    for i in items:
        f = flag(i)
        res = f"{float(i.value):g}" if i.value is not None else i.text
        name = [P(i.test.name_en)] + ([P(local(i.test, t.language))] if local(i.test, t.language) else [])
        rows.append([name, P(res, 9, True), P(i.test.unit), P(ref_range(i.test)), P(f, 9, True, red if f in "LH" and f else colors.black)])
        if f in ("L", "H"):
            abn.append((i, f))
    tbl = Table(rows, colWidths=[62 * mm, 28 * mm, 20 * mm, 30 * mm, 14 * mm], repeatRows=1)
    tbl.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0b6e8a")), ("GRID", (0, 0), (-1, -1), 0.4, colors.grey),
                             ("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f1f6f9")])]))
    info = Table([[P("Patient", 8), P(t.name, 10, True), P("Patient ID", 8), P(t.patient.uid, 10, True)],
                  [P("Age / Sex", 8), P(f"{t.age} / {t.sex.upper()}"), P("Visit", 8), P(f"{timezone.localtime(t.created):%d %b %Y}")],
                  [P("Department", 8), P(t.department.name_en if t.department else "-"), P("Report ref", 8), P(order.ref.hex[:10].upper())]],
                 colWidths=[24 * mm, 62 * mm, 24 * mm, 44 * mm])
    info.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("BOTTOMPADDING", (0, 0), (-1, -1), 2)]))
    el = [P("SMHS Srinagar Hospital", 16, True, colors.HexColor("#0b6e8a")), P("Laboratory Report", 11), Spacer(1, 6 * mm),
          info, Spacer(1, 6 * mm), tbl, Spacer(1, 5 * mm)]
    if doctor_view:
        el.append(P("Clinical review summary", 11, True))
        el += [P(f"{i.test.name_en}: {float(i.value):g} {i.test.unit} ({'below' if f == 'L' else 'above'} reference {ref_range(i.test)})", 9, False, red) for i, f in abn] or [P("All numeric results are within the stored reference ranges.")]
        el.append(Spacer(1, 3 * mm))
        el.append(P("Reference ranges are generic adult values; interpret with age, sex and clinical context. Decision support only, not a diagnosis.", 8))
    else:
        el.append(P("Please show this report to your doctor. Values marked H or L are outside the usual range.", 9))
    el += [Spacer(1, 6 * mm), P(f"Generated {timezone.localtime():%d %b %Y %H:%M}", 8)]
    doc.build(el)
    return buf.getvalue()
