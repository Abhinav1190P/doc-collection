from datetime import datetime, timezone
import uuid

from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


def now():
    return datetime.now(timezone.utc)


class Household(db.Model):
    __tablename__ = "households"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    tax_year = db.Column(db.Integer, nullable=False)
    filing_status = db.Column(db.String(50), nullable=False, default="joint")
    created_at = db.Column(db.DateTime, default=now)

    people = db.relationship("Person", backref="household", cascade="all, delete-orphan")
    requirements = db.relationship("Requirement", backref="household", cascade="all, delete-orphan")
    documents = db.relationship("Document", backref="household", cascade="all, delete-orphan")


class Person(db.Model):
    __tablename__ = "people"

    id = db.Column(db.Integer, primary_key=True)
    household_id = db.Column(db.Integer, db.ForeignKey("households.id"), nullable=False)
    first_name = db.Column(db.String(100), nullable=False)
    last_name = db.Column(db.String(100), nullable=False)
    role = db.Column(db.String(20), nullable=False)  # taxpayer, spouse, dependent

    employment_periods = db.relationship(
        "EmploymentPeriod", backref="person", cascade="all, delete-orphan"
    )

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"


class EmploymentPeriod(db.Model):
    __tablename__ = "employment_periods"

    id = db.Column(db.Integer, primary_key=True)
    person_id = db.Column(db.Integer, db.ForeignKey("people.id"), nullable=False)
    tax_year = db.Column(db.Integer, nullable=False)
    employer_name = db.Column(db.String(200))
    date_range_note = db.Column(db.String(100))
    disclosed_at = db.Column(db.DateTime, default=now)


class Requirement(db.Model):
    __tablename__ = "requirements"

    id = db.Column(db.Integer, primary_key=True)
    household_id = db.Column(db.Integer, db.ForeignKey("households.id"), nullable=False)
    natural_key = db.Column(db.String(200), nullable=False)
    kind = db.Column(db.String(30), nullable=False)  # FORM_1040, GOVERNMENT_ID, W2
    person_id = db.Column(db.Integer, db.ForeignKey("people.id"), nullable=True)
    employment_period_id = db.Column(db.Integer, db.ForeignKey("employment_periods.id"), nullable=True)
    label = db.Column(db.String(200), nullable=False)
    status = db.Column(db.String(20), nullable=False, default="needed")
    source = db.Column(db.String(10), nullable=False, default="system")  # system, manual
    note = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=now)
    updated_at = db.Column(db.DateTime, default=now, onupdate=now)

    person = db.relationship("Person")

    __table_args__ = (db.UniqueConstraint("household_id", "natural_key", name="uq_requirement_key"),)


class Document(db.Model):
    __tablename__ = "documents"

    id = db.Column(db.Integer, primary_key=True)
    household_id = db.Column(db.Integer, db.ForeignKey("households.id"), nullable=False)
    original_filename = db.Column(db.String(300), nullable=False)
    stored_filename = db.Column(db.String(300), nullable=False)
    uploaded_at = db.Column(db.DateTime, default=now)

    guessed_kind = db.Column(db.String(30))
    guessed_tax_year = db.Column(db.Integer)
    guessed_person_id = db.Column(db.Integer, db.ForeignKey("people.id"), nullable=True)
    guessed_owner_raw = db.Column(db.String(200))
    guessed_employer_name = db.Column(db.String(200))
    confidence = db.Column(db.Float, nullable=False, default=0.0)
    extracted_snippet = db.Column(db.Text)

    status = db.Column(db.String(20), nullable=False, default="needs_review")
    matched_requirement_id = db.Column(db.Integer, db.ForeignKey("requirements.id"), nullable=True)
    review_note = db.Column(db.Text)

    guessed_person = db.relationship("Person", foreign_keys=[guessed_person_id])
    matched_requirement = db.relationship("Requirement", foreign_keys=[matched_requirement_id])

    @staticmethod
    def new_id():
        return uuid.uuid4().hex
