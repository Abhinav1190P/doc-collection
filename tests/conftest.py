import pytest

from app import create_app
from app.models import db, Household, Person, EmploymentPeriod


@pytest.fixture
def app():
    app = create_app({
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
        "WTF_CSRF_ENABLED": False,
    })
    yield app


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def rivera(app):
    with app.app_context():
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

        yield household.id
