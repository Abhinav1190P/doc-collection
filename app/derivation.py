from app.models import db, Requirement


def compute_implied(household):
    implied = {}

    implied[f"1040:{household.id}"] = {
        "kind": "FORM_1040",
        "person_id": None,
        "employment_period_id": None,
        "label": "Prior-year Form 1040 (household)",
    }

    for person in household.people:
        if person.role in ("taxpayer", "spouse"):
            implied[f"ID:{person.id}"] = {
                "kind": "GOVERNMENT_ID",
                "person_id": person.id,
                "employment_period_id": None,
                "label": f"Government ID — {person.full_name}",
            }

        current_periods = [p for p in person.employment_periods if p.tax_year == household.tax_year]

        if current_periods:
            for period in current_periods:
                employer = period.employer_name or "employer unknown"
                implied[f"W2:{person.id}:{period.id}"] = {
                    "kind": "W2",
                    "person_id": person.id,
                    "employment_period_id": period.id,
                    "label": f"W-2 — {person.full_name} ({employer})",
                }
        else:
            prior_periods = [
                p for p in person.employment_periods if p.tax_year == household.tax_year - 1
            ]
            for period in prior_periods:
                employer = period.employer_name or "employer unknown"
                implied[f"W2CARRY:{person.id}:{period.id}"] = {
                    "kind": "W2",
                    "person_id": person.id,
                    "employment_period_id": None,
                    "label": f"W-2 — {person.full_name} (expected, based on last year at {employer})",
                }

    return implied


def reconcile(household):
    implied = compute_implied(household)

    existing = {r.natural_key: r for r in household.requirements}

    created = 0
    retired = 0

    for key, details in implied.items():
        if key in existing:
            continue
        req = Requirement(
            household_id=household.id,
            natural_key=key,
            kind=details["kind"],
            person_id=details["person_id"],
            employment_period_id=details["employment_period_id"],
            label=details["label"],
            status="needed",
            source="system",
        )
        db.session.add(req)
        created += 1

    for key, req in existing.items():
        if req.source != "system":
            continue
        if key in implied:
            continue
        if req.status == "needed":
            req.status = "removed"
            req.note = (req.note + " " if req.note else "") + "(auto-retired: no longer implied by current data)"
            retired += 1

    db.session.commit()
    return {"created": created, "retired": retired}
