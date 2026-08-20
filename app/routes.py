from flask import Blueprint, render_template, request, redirect, url_for, flash, abort, send_from_directory

from app.models import db, Household, Person, EmploymentPeriod, Requirement, Document
from app.derivation import reconcile
from app.ingestion import ingest_document, resolve_review, UPLOAD_DIR

bp = Blueprint("main", __name__)


@bp.route("/")
def index():
    households = Household.query.order_by(Household.name).all()
    return render_template("index.html", households=households)


@bp.route("/households", methods=["POST"])
def create_household():
    name = request.form["name"].strip()
    tax_year = int(request.form["tax_year"])
    filing_status = request.form.get("filing_status", "joint")

    household = Household(name=name, tax_year=tax_year, filing_status=filing_status)
    db.session.add(household)
    db.session.commit()

    return redirect(url_for("main.view_household", household_id=household.id))


@bp.route("/households/<int:household_id>")
def view_household(household_id):
    household = Household.query.get_or_404(household_id)
    reconcile(household)
    db.session.refresh(household)

    requirements = (
        Requirement.query.filter_by(household_id=household.id)
        .order_by(Requirement.kind, Requirement.id)
        .all()
    )
    outstanding = [r for r in requirements if r.status == "needed"]
    satisfied = [r for r in requirements if r.status == "satisfied"]
    dismissed = [r for r in requirements if r.status in ("dismissed", "removed")]

    needs_review = (
        Document.query.filter_by(household_id=household.id, status="needs_review")
        .order_by(Document.uploaded_at.desc())
        .all()
    )
    matched_docs = (
        Document.query.filter_by(household_id=household.id, status="matched")
        .order_by(Document.uploaded_at.desc())
        .all()
    )

    return render_template(
        "household.html",
        household=household,
        outstanding=outstanding,
        satisfied=satisfied,
        dismissed=dismissed,
        needs_review=needs_review,
        matched_docs=matched_docs,
    )


@bp.route("/households/<int:household_id>/derive", methods=["POST"])
def derive(household_id):
    household = Household.query.get_or_404(household_id)
    result = reconcile(household)
    flash(f"Checklist re-derived: {result['created']} added, {result['retired']} auto-retired.")
    return redirect(url_for("main.view_household", household_id=household.id))


@bp.route("/households/<int:household_id>/people", methods=["POST"])
def add_person(household_id):
    household = Household.query.get_or_404(household_id)
    person = Person(
        household_id=household.id,
        first_name=request.form["first_name"].strip(),
        last_name=request.form["last_name"].strip(),
        role=request.form["role"],
    )
    db.session.add(person)
    db.session.commit()
    return redirect(url_for("main.view_household", household_id=household.id))


@bp.route("/households/<int:household_id>/employment", methods=["POST"])
def add_employment(household_id):
    household = Household.query.get_or_404(household_id)
    person_id = int(request.form["person_id"])
    person = Person.query.get_or_404(person_id)
    if person.household_id != household.id:
        abort(404)

    period = EmploymentPeriod(
        person_id=person.id,
        tax_year=int(request.form["tax_year"]),
        employer_name=request.form.get("employer_name", "").strip() or None,
        date_range_note=request.form.get("date_range_note", "").strip() or None,
    )
    db.session.add(period)
    db.session.commit()

    result = reconcile(household)
    flash(f"Employment added. Checklist re-derived: {result['created']} added, {result['retired']} auto-retired.")
    return redirect(url_for("main.view_household", household_id=household.id))


@bp.route("/households/<int:household_id>/requirements", methods=["POST"])
def add_manual_requirement(household_id):
    household = Household.query.get_or_404(household_id)
    person_id = request.form.get("person_id") or None

    req = Requirement(
        household_id=household.id,
        natural_key=f"manual:{Document.new_id()}",
        kind=request.form.get("kind", "OTHER"),
        person_id=int(person_id) if person_id else None,
        label=request.form["label"].strip(),
        status="needed",
        source="manual",
    )
    db.session.add(req)
    db.session.commit()
    return redirect(url_for("main.view_household", household_id=household.id))


@bp.route("/requirements/<int:requirement_id>/dismiss", methods=["POST"])
def dismiss_requirement(requirement_id):
    requirement = Requirement.query.get_or_404(requirement_id)
    requirement.status = "dismissed"
    requirement.note = request.form.get("note", "").strip() or requirement.note
    db.session.commit()
    return redirect(url_for("main.view_household", household_id=requirement.household_id))


@bp.route("/requirements/<int:requirement_id>/remove", methods=["POST"])
def remove_requirement(requirement_id):
    requirement = Requirement.query.get_or_404(requirement_id)
    requirement.status = "removed"
    requirement.note = "Marked incorrect by accountant."
    db.session.commit()
    return redirect(url_for("main.view_household", household_id=requirement.household_id))


@bp.route("/documents/upload/<int:household_id>", methods=["POST"])
def upload_document(household_id):
    household = Household.query.get_or_404(household_id)
    file = request.files.get("file")
    if not file or not file.filename:
        flash("Choose a file first.")
        return redirect(url_for("main.view_household", household_id=household.id))

    doc = ingest_document(household, file.read(), file.filename)

    if doc.status == "matched":
        flash(f"'{doc.original_filename}' matched automatically to: {doc.matched_requirement.label}")
    else:
        flash(f"'{doc.original_filename}' needs a human look: {doc.review_note}")

    return redirect(url_for("main.view_household", household_id=household.id))


@bp.route("/documents/<int:document_id>/review", methods=["GET"])
def review_document(document_id):
    document = Document.query.get_or_404(document_id)
    household = document.household
    open_requirements = [r for r in household.requirements if r.status == "needed"]
    return render_template("review.html", document=document, household=household, open_requirements=open_requirements)


@bp.route("/documents/<int:document_id>/review", methods=["POST"])
def submit_review(document_id):
    document = Document.query.get_or_404(document_id)

    if request.form.get("action") == "reject":
        resolve_review(document, None, dismiss=True, note=request.form.get("note"))
        flash(f"'{document.original_filename}' marked as not usable.")
    else:
        requirement_id = int(request.form["requirement_id"])
        resolve_review(document, requirement_id, note=request.form.get("note"))
        flash(f"'{document.original_filename}' linked to a requirement.")

    return redirect(url_for("main.view_household", household_id=document.household_id))


@bp.route("/uploads/<path:filename>")
def serve_upload(filename):
    return send_from_directory(UPLOAD_DIR, filename)
