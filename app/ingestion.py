import os
import uuid

from app.models import db, Document
from app.classifier import classify, find_match
from app.derivation import reconcile

UPLOAD_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "instance", "uploads")


def ensure_upload_dir():
    os.makedirs(UPLOAD_DIR, exist_ok=True)


def ingest_document(household, file_bytes, original_filename):
    ensure_upload_dir()
    reconcile(household)

    stored_filename = f"{uuid.uuid4().hex}_{original_filename}"
    stored_path = os.path.join(UPLOAD_DIR, stored_filename)
    with open(stored_path, "wb") as f:
        f.write(file_bytes)

    guess = classify(stored_path, household)
    requirement, reject_reason = find_match(guess, household)

    doc = Document(
        household_id=household.id,
        original_filename=original_filename,
        stored_filename=stored_filename,
        guessed_kind=guess["kind"],
        guessed_tax_year=guess["tax_year"],
        guessed_person_id=guess["person"].id if guess["person"] else None,
        guessed_owner_raw=guess["owner_raw"],
        guessed_employer_name=guess["employer_name"],
        confidence=guess["confidence"],
        extracted_snippet=guess["snippet"],
    )

    if requirement:
        doc.status = "matched"
        doc.matched_requirement_id = requirement.id
        requirement.status = "satisfied"
    else:
        doc.status = "needs_review"
        doc.review_note = reject_reason

    db.session.add(doc)
    db.session.commit()
    return doc


def resolve_review(document, requirement_id, dismiss=False, note=None):
    if dismiss:
        document.status = "rejected"
        document.review_note = note or document.review_note
        db.session.commit()
        return

    from app.models import Requirement

    requirement = db.session.get(Requirement, requirement_id)
    requirement.status = "satisfied"
    document.status = "matched"
    document.matched_requirement_id = requirement.id
    document.review_note = note or document.review_note
    db.session.commit()
