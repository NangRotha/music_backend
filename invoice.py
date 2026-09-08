"""Printable PDF invoice (receipt) generator for paid ABA/KHQRcc orders.

Uses only Latin/ASCII text (base-14 PDF fonts) so it renders everywhere
without embedding custom fonts.
"""
from io import BytesIO

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


def _ascii(value) -> str:
    return "".join(ch if ord(ch) < 128 else "?" for ch in str(value or ""))


def _money(value) -> str:
    try:
        return f"${float(value):,.2f}"
    except (TypeError, ValueError):
        return "$0.00"


def _date_str(value) -> str:
    s = str(value or "")
    return s.replace("T", " ")[:16]


def make_invoice_pdf(data: dict) -> bytes:
    """Build a one-page A4 invoice PDF and return its bytes."""
    store = _ascii(data.get("store") or "KhmerBeats Music Store")
    reference = _ascii(data.get("reference") or "")
    transaction_id = _ascii(data.get("transaction_id") or "")
    date_str = _date_str(data.get("date"))
    customer = _ascii(data.get("customer") or "Guest Buyer")
    contact = _ascii(data.get("contact") or "")
    music = _ascii(data.get("music") or "")
    artist = _ascii(data.get("artist") or "")
    original = _money(data.get("original_price"))
    track_discount = _money(data.get("track_discount"))
    promo_code = _ascii(data.get("promo_code") or "")
    promo_discount = _money(data.get("promo_discount"))
    total = _money(data.get("total"))

    buf = BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=18 * mm, rightMargin=18 * mm,
                            topMargin=16 * mm, bottomMargin=16 * mm, title=f"Invoice {reference}")

    h1 = ParagraphStyle("h1", fontName="Helvetica-Bold", fontSize=19, leading=23, textColor=colors.HexColor("#111827"))
    paid = ParagraphStyle("paid", fontName="Helvetica-Bold", fontSize=13, leading=15, textColor=colors.HexColor("#059669"))
    small = ParagraphStyle("small", fontName="Helvetica", fontSize=8.5, leading=11, textColor=colors.HexColor("#6b7280"))
    label = ParagraphStyle("label", fontName="Helvetica-Bold", fontSize=8.5, leading=11, textColor=colors.HexColor("#9ca3af"))
    value = ParagraphStyle("value", fontName="Helvetica", fontSize=10, leading=13, textColor=colors.HexColor("#111827"))
    bold = ParagraphStyle("bold", fontName="Helvetica-Bold", fontSize=10.5, leading=14, textColor=colors.HexColor("#111827"))
    rule = ParagraphStyle("rule", fontName="Helvetica", fontSize=8, leading=10, textColor=colors.HexColor("#9ca3af"))
    story = []

    # ---- Header ----
    header = Table([[Paragraph(f"<b>{store}</b>", h1),
                     Paragraph('<font color="#059669"><b>PAID</b></font>', paid)]],
                   colWidths=[125 * mm, 49 * mm])
    header.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"),
                                ("ALIGN", (1, 0), (1, 0), "RIGHT"),
                                ("BOTTOMPADDING", (0, 0), (-1, -1), 4)]))
    story.append(header)
    story.append(Paragraph("Digital Music Receipt / Tax Invoice", small))
    story.append(Spacer(1, 5 * mm))

    # ---- Info block ----
    info_rows = [
        ["Invoice No.", f"#{reference}", "Payment", "ABA Pay / KHQR"],
        ["Transaction ID", transaction_id, "Status", "Paid"],
        ["Date", date_str, "Method", "QR auto-pay"],
    ]
    info = Table([[Paragraph(a, label), Paragraph(b, value), Paragraph(c, label), Paragraph(d, value)]
                  for a, b, c, d in info_rows],
                 colWidths=[26 * mm, 60 * mm, 26 * mm, 62 * mm])
    info.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#e5e7eb")),
        ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e5e7eb")),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f9fafb")),
        ("BACKGROUND", (2, 0), (3, -1), colors.HexColor("#f9fafb")),
        ("LEFTPADDING", (0, 0), (-1, -1), 6), ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3), ("TOPPADDING", (0, 0), (-1, -1), 3),
    ]))
    story.append(info)
    story.append(Spacer(1, 6 * mm))

    # ---- Bill to ----
    story.append(Paragraph("BILLED TO", label))
    story.append(Paragraph(customer, bold))
    if contact:
        story.append(Paragraph(contact, small))
    story.append(Spacer(1, 6 * mm))

    # ---- Items table ----
    head = ParagraphStyle("head", fontName="Helvetica-Bold", fontSize=9, leading=11, textColor=colors.HexColor("#374151"))
    item_rows = [
        [Paragraph("ITEM", head), Paragraph("", head), Paragraph("AMOUNT", head)],
        [Paragraph(f"<b>{music}</b>", value), Paragraph(artist, small), Paragraph(original, value)],
    ]
    if track_discount and track_discount != "$0.00":
        item_rows.append([Paragraph("Track discount", small), Paragraph("", small), Paragraph(f"-{track_discount}", value)])
    if promo_code:
        item_rows.append([Paragraph(f"Promo code {promo_code}", small), Paragraph("", small), Paragraph(f"-{promo_discount}", value)])
    item_rows.append([Paragraph("", small), Paragraph("", small), Paragraph("", small)])
    item_rows.append([Paragraph("<b>TOTAL PAID</b>", bold), Paragraph("", small), Paragraph(f"<b>{total}</b>", bold)])
    items = Table(item_rows, colWidths=[100 * mm, 32 * mm, 42 * mm])
    items.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ALIGN", (2, 0), (2, -1), "RIGHT"),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#111827")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("LINEBELOW", (0, -1), (-1, -1), 1.2, colors.HexColor("#111827")),
        ("LINEABOVE", (0, -2), (-1, -2), 0.5, colors.HexColor("#e5e7eb")),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4), ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING", (0, 0), (-1, -1), 4), ("RIGHTPADDING", (0, 0), (-1, -1), 4),
    ]))
    story.append(items)
    story.append(Spacer(1, 10 * mm))

    # ---- Footer ----
    story.append(Table(
        [[Paragraph("Thank you for your purchase!", small),
          Paragraph("Questions? Contact the store with your invoice number.", rule)]],
        colWidths=[87 * mm, 87 * mm]))

    doc.build(story)
    return buf.getvalue()
