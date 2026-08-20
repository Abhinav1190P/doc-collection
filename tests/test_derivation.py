from app.models import db, Household, Requirement, EmploymentPeriod, Person
from app.derivation import reconcile


def requirements_for(household_id):
    return Requirement.query.filter_by(household_id=household_id).all()


def test_baseline_checklist_carries_forward_last_years_job_count(app, rivera):
    with app.app_context():
        household = db.session.get(Household, rivera)
        reconcile(household)

        reqs = requirements_for(rivera)
        kinds = [r.kind for r in reqs]

        assert kinds.count("FORM_1040") == 1
        assert kinds.count("GOVERNMENT_ID") == 2
        assert kinds.count("W2") == 3

        luis = Person.query.filter_by(first_name="Luis").first()
        luis_w2s = [r for r in reqs if r.kind == "W2" and r.person_id == luis.id]
        assert len(luis_w2s) == 1
        assert all(r.status == "needed" for r in reqs)


def test_dependent_does_not_get_id_requirement(app, rivera):
    with app.app_context():
        household = db.session.get(Household, rivera)
        reconcile(household)

        mateo = Person.query.filter_by(first_name="Mateo").first()
        mateo_reqs = [r for r in requirements_for(rivera) if r.person_id == mateo.id]
        assert mateo_reqs == []


def test_disclosed_job_change_overrides_carry_forward_without_touching_others(app, rivera):
    with app.app_context():
        household = db.session.get(Household, rivera)
        reconcile(household)

        luis = Person.query.filter_by(first_name="Luis").first()
        ana = Person.query.filter_by(first_name="Ana").first()

        db.session.add_all([
            EmploymentPeriod(person_id=luis.id, tax_year=2025, employer_name="Harborview Logistics"),
            EmploymentPeriod(person_id=luis.id, tax_year=2025, employer_name="Crestline Retail"),
        ])
        db.session.commit()

        reconcile(household)

        reqs = requirements_for(rivera)
        luis_w2s = [r for r in reqs if r.kind == "W2" and r.person_id == luis.id]
        ana_w2s = [r for r in reqs if r.kind == "W2" and r.person_id == ana.id]

        assert len([r for r in luis_w2s if r.status == "needed"]) == 2
        assert len([r for r in luis_w2s if r.status == "removed"]) == 1
        assert len(ana_w2s) == 2
        assert all(r.status == "needed" for r in ana_w2s)


def test_dismissed_requirement_is_not_resurrected(app, rivera):
    with app.app_context():
        household = db.session.get(Household, rivera)
        reconcile(household)

        target = [r for r in requirements_for(rivera) if r.kind == "GOVERNMENT_ID"][0]
        target.status = "dismissed"
        db.session.commit()

        reconcile(household)

        refreshed = db.session.get(Requirement, target.id)
        assert refreshed.status == "dismissed"

        id_reqs = [r for r in requirements_for(rivera) if r.kind == "GOVERNMENT_ID"]
        assert len(id_reqs) == 2


def test_manual_requirement_survives_reconciliation(app, rivera):
    with app.app_context():
        household = db.session.get(Household, rivera)
        reconcile(household)

        manual = Requirement(
            household_id=household.id,
            natural_key="manual:abc123",
            kind="OTHER",
            label="1099-NEC — Ana Rivera",
            status="needed",
            source="manual",
        )
        db.session.add(manual)
        db.session.commit()

        reconcile(household)

        refreshed = db.session.get(Requirement, manual.id)
        assert refreshed.status == "needed"


def test_satisfied_requirement_is_never_auto_retired(app, rivera):
    with app.app_context():
        household = db.session.get(Household, rivera)
        reconcile(household)

        luis = Person.query.filter_by(first_name="Luis").first()
        luis_w2 = [r for r in requirements_for(rivera) if r.kind == "W2" and r.person_id == luis.id][0]
        luis_w2.status = "satisfied"
        db.session.commit()

        db.session.add_all([
            EmploymentPeriod(person_id=luis.id, tax_year=2025, employer_name="Harborview Logistics"),
            EmploymentPeriod(person_id=luis.id, tax_year=2025, employer_name="Crestline Retail"),
        ])
        db.session.commit()

        reconcile(household)

        refreshed = db.session.get(Requirement, luis_w2.id)
        assert refreshed.status == "satisfied"
