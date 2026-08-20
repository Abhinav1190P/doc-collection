from reportlab.pdfgen import canvas

from app.models import db, Household, Requirement
from app.classifier import classify, find_match
from app.derivation import reconcile


def make_pdf(path, lines):
    c = canvas.Canvas(str(path))
    y = 750
    for line in lines:
        c.drawString(50, y, line)
        y -= 20
    c.save()


def make_blank_pdf(path):
    c = canvas.Canvas(str(path))
    c.save()


def test_readable_w2_matches_open_requirement(app, rivera, tmp_path):
    with app.app_context():
        household = db.session.get(Household, rivera)
        reconcile(household)

        pdf_path = tmp_path / "w2.pdf"
        make_pdf(pdf_path, [
            "Form W-2 Wage and Tax Statement",
            "Tax Year 2025",
            "Employee: Ana Rivera",
            "Employer: Meridian Tech",
        ])

        guess = classify(str(pdf_path), household)
        assert guess["kind"] == "W2"
        assert guess["tax_year"] == 2025
        assert guess["person"].first_name == "Ana"
        assert guess["confidence"] >= 0.7

        requirement, reason = find_match(guess, household)
        assert requirement is not None
        assert reason is None
        assert requirement.kind == "W2"


def test_wrong_year_1040_is_not_matched(app, rivera, tmp_path):
    with app.app_context():
        household = db.session.get(Household, rivera)
        reconcile(household)

        pdf_path = tmp_path / "old_1040.pdf"
        make_pdf(pdf_path, [
            "Form 1040 U.S. Individual Income Tax Return",
            "Tax Year 2022",
            "Name: Ana Rivera",
        ])

        guess = classify(str(pdf_path), household)
        requirement, reason = find_match(guess, household)

        assert requirement is None
        assert "2022" in reason


def test_unreadable_scan_gets_zero_confidence(app, rivera, tmp_path):
    with app.app_context():
        household = db.session.get(Household, rivera)
        reconcile(household)

        pdf_path = tmp_path / "blank_scan.pdf"
        make_blank_pdf(pdf_path)

        guess = classify(str(pdf_path), household)
        assert guess["kind"] == "UNKNOWN"
        assert guess["confidence"] == 0.0

        requirement, reason = find_match(guess, household)
        assert requirement is None


def test_document_for_unrelated_person_is_flagged(app, rivera, tmp_path):
    with app.app_context():
        household = db.session.get(Household, rivera)
        reconcile(household)

        pdf_path = tmp_path / "stray_w2.pdf"
        make_pdf(pdf_path, [
            "Form W-2 Wage and Tax Statement",
            "Tax Year 2025",
            "Employee: Carlos Mendez",
            "Employer: Pinewood Retail",
        ])

        guess = classify(str(pdf_path), household)
        assert guess["person"] is None
        assert guess["owner_raw"] == "Carlos Mendez"

        requirement, reason = find_match(guess, household)
        assert requirement is None
        assert "Carlos Mendez" in reason
