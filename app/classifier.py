import re
from collections import Counter

from pypdf import PdfReader

W2_HINTS = ["w-2", "w2", "wage and tax statement"]
FORM_1040_HINTS = ["1040", "individual income tax return"]
GOV_ID_HINTS = ["driver license", "driver's license", "identification card", "passport", "state id"]

YEAR_PATTERN = re.compile(r"\b(20[12]\d)\b")
EMPLOYER_PATTERN = re.compile(r"employer\s*:\s*([A-Za-z0-9&,.\- ]+)", re.IGNORECASE)
NAME_PATTERN = re.compile(r"(?:employee|name|owner)\s*:\s*([A-Za-z .'\-]+)", re.IGNORECASE)

REVIEW_THRESHOLD = 0.7


def extract_text(file_path):
    try:
        reader = PdfReader(file_path)
        text = "\n".join(page.extract_text() or "" for page in reader.pages)
        return text.strip()
    except Exception:
        return ""


def guess_kind(text_lower):
    if any(h in text_lower for h in W2_HINTS):
        return "W2"
    if any(h in text_lower for h in FORM_1040_HINTS):
        return "FORM_1040"
    if any(h in text_lower for h in GOV_ID_HINTS):
        return "GOVERNMENT_ID"
    return "UNKNOWN"


def guess_tax_year(text):
    years = YEAR_PATTERN.findall(text)
    if not years:
        return None
    return int(Counter(years).most_common(1)[0][0])


def guess_employer(text):
    match = EMPLOYER_PATTERN.search(text)
    if not match:
        return None
    return match.group(1).strip().splitlines()[0][:200]


def guess_person(text, household):
    match = NAME_PATTERN.search(text)
    raw_name = match.group(1).strip().splitlines()[0][:200] if match else None

    text_lower = text.lower()
    matches = [p for p in household.people if p.full_name.lower() in text_lower]
    if len(matches) == 1:
        return matches[0], raw_name or matches[0].full_name
    return None, raw_name


def classify(file_path, household):
    text = extract_text(file_path)

    if len(text) < 20:
        return {
            "kind": "UNKNOWN",
            "tax_year": None,
            "person": None,
            "owner_raw": None,
            "employer_name": None,
            "confidence": 0.0,
            "snippet": text[:300],
        }

    text_lower = text.lower()
    kind = guess_kind(text_lower)
    tax_year = guess_tax_year(text)
    person, owner_raw = guess_person(text, household)
    employer_name = guess_employer(text) if kind == "W2" else None

    confidence = 0.0
    if kind != "UNKNOWN":
        confidence += 0.5
    if tax_year is not None:
        confidence += 0.2
    if person is not None:
        confidence += 0.25
    if kind == "W2" and employer_name:
        confidence += 0.05

    return {
        "kind": kind,
        "tax_year": tax_year,
        "person": person,
        "owner_raw": owner_raw,
        "employer_name": employer_name,
        "confidence": round(min(confidence, 1.0), 2),
        "snippet": text[:300],
    }


def find_match(guess, household):
    if guess["confidence"] < REVIEW_THRESHOLD:
        return None, "Low-confidence guess — needs a human look before it's acted on."

    kind = guess["kind"]

    if kind == "UNKNOWN":
        return None, "Could not tell what kind of document this is."

    if kind == "FORM_1040":
        expected_year = household.tax_year - 1
        if guess["tax_year"] != expected_year:
            return None, f"This looks like a Form 1040, but for tax year {guess['tax_year']}, not the expected {expected_year}."
        candidates = [r for r in household.requirements if r.kind == "FORM_1040" and r.status == "needed"]
        return (candidates[0], None) if candidates else (None, "No outstanding Form 1040 requirement for this household.")

    if kind == "GOVERNMENT_ID":
        if guess["person"] is None:
            reason = "Could not tell which household member this ID belongs to."
            if guess["owner_raw"]:
                reason = f"Found the name '{guess['owner_raw']}', which doesn't match anyone in this household."
            return None, reason
        candidates = [
            r for r in household.requirements
            if r.kind == "GOVERNMENT_ID" and r.person_id == guess["person"].id and r.status == "needed"
        ]
        return (candidates[0], None) if candidates else (None, "No outstanding ID requirement for this person.")

    if kind == "W2":
        if guess["tax_year"] != household.tax_year:
            return None, f"This W-2 is for tax year {guess['tax_year']}, not this client's tax year {household.tax_year}."
        if guess["person"] is None:
            reason = "Could not tell which household member this W-2 belongs to."
            if guess["owner_raw"]:
                reason = f"Found the name '{guess['owner_raw']}', which doesn't match anyone in this household."
            return None, reason
        candidates = [
            r for r in household.requirements
            if r.kind == "W2" and r.person_id == guess["person"].id and r.status == "needed"
        ]
        if not candidates:
            return None, f"No outstanding W-2 requirement for {guess['person'].full_name}."
        if guess["employer_name"]:
            for r in candidates:
                if guess["employer_name"].lower() in (r.label or "").lower():
                    return r, None
        return candidates[0], None

    return None, "Unrecognized document type."
