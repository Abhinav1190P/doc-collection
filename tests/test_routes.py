import io

from reportlab.pdfgen import canvas


def make_pdf_bytes(lines):
    buf = io.BytesIO()
    c = canvas.Canvas(buf)
    y = 750
    for line in lines:
        c.drawString(50, y, line)
        y -= 20
    c.save()
    buf.seek(0)
    return buf.read()


def test_household_page_shows_derived_checklist(client, rivera):
    res = client.get(f"/households/{rivera}")
    assert res.status_code == 200
    assert b"Ana Rivera" in res.data
    assert b"Outstanding" in res.data


def test_upload_matches_readable_document(client, rivera):
    pdf_bytes = make_pdf_bytes([
        "Form W-2 Wage and Tax Statement",
        "Tax Year 2025",
        "Employee: Ana Rivera",
        "Employer: Meridian Tech",
    ])

    res = client.post(
        f"/documents/upload/{rivera}",
        data={"file": (io.BytesIO(pdf_bytes), "ana_w2_2025.pdf")},
        content_type="multipart/form-data",
        follow_redirects=True,
    )

    assert res.status_code == 200
    assert b"matched automatically" in res.data


def test_upload_unreadable_document_lands_in_review_queue(client, rivera):
    buf = io.BytesIO()
    canvas.Canvas(buf).save()

    res = client.post(
        f"/documents/upload/{rivera}",
        data={"file": (io.BytesIO(buf.getvalue()), "mystery_scan.pdf")},
        content_type="multipart/form-data",
        follow_redirects=True,
    )

    assert res.status_code == 200
    assert b"needs a human look" in res.data
