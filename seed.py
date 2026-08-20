import os

from app import create_app
from app.models import db, Household, Person, EmploymentPeriod
from app.derivation import reconcile
from app.ingestion import ingest_document

FIXTURES = os.path.join(os.path.dirname(__file__), "fixtures", "documents")


def upload(household, filename):
    path = os.path.join(FIXTURES, filename)
    with open(path, "rb") as f:
        data = f.read()
    doc = ingest_document(household, data, filename)
    print(f"  {filename:45s} -> {doc.status:12s} {doc.review_note or ''}")


def main():
    app = create_app()
    with app.app_context():
        db.drop_all()
        db.create_all()

        household = Household(name="Rivera household", tax_year=2025, filing_status="joint")
        db.session.add(household)
        db.session.flush()

        ana = Person(household_id=household.id, first_name="Ana", last_name="Rivera", role="taxpayer")
        luis = Person(household_id=household.id, first_name="Luis", last_name="Rivera", role="spouse")
        mateo = Person(household_id=household.id, first_name="Mateo", last_name="Rivera", role="dependent")
        db.session.add_all([ana, luis, mateo])
        db.session.flush()

        db.session.add_all([
            EmploymentPeriod(person_id=ana.id, tax_year=2024, employer_name="Meridian Tech"),
            EmploymentPeriod(person_id=ana.id, tax_year=2024, employer_name="Riverside Consulting"),
            EmploymentPeriod(person_id=luis.id, tax_year=2024, employer_name="Oakline Manufacturing"),
        ])
        db.session.commit()

        print("Deriving baseline checklist from last year's pattern...")
        reconcile(household)

        print("Documents arriving...")
        upload(household, "Rivera_1040_2024.pdf")
        upload(household, "Ana_ID.pdf")
        upload(household, "Luis_ID.pdf")
        upload(household, "Ana_W2_2025_MeridianTech.pdf")
        upload(household, "Ana_W2_2025_RiversideConsulting.pdf")
        upload(household, "Carlos_Mendez_W2_2025_unrelated.pdf")
        upload(household, "Ana_W2_2023_wrong_year.pdf")
        upload(household, "unreadable_scan.pdf")

        print("Luis's job change surfaces...")
        db.session.add_all([
            EmploymentPeriod(person_id=luis.id, tax_year=2025, employer_name="Oakline Manufacturing", date_range_note="Jan-May 2025"),
            EmploymentPeriod(person_id=luis.id, tax_year=2025, employer_name="Harborview Logistics", date_range_note="June-Dec 2025"),
        ])
        db.session.commit()
        result = reconcile(household)
        print(f"  checklist re-derived: {result['created']} added, {result['retired']} auto-retired")

        upload(household, "Luis_W2_2025_OaklineManufacturing.pdf")
        upload(household, "Luis_W2_2025_HarborviewLogistics.pdf")

        print(f"\nDone. Household id={household.id} — open it at /households/{household.id}")


if __name__ == "__main__":
    main()
