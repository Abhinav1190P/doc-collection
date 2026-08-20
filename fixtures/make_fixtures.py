import os

from PIL import Image, ImageDraw
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

OUT_DIR = os.path.join(os.path.dirname(__file__), "documents")


def box(c, x, y, w, h, label, value=""):
    c.rect(x, y, w, h)
    c.setFont("Helvetica", 6)
    c.drawString(x + 3, y + h - 8, label)
    c.setFont("Helvetica", 10)
    c.drawString(x + 3, y + 4, value)


def make_w2(path, tax_year, employee, ssn, employer, wages):
    c = canvas.Canvas(path, pagesize=letter)
    c.setFont("Helvetica-Bold", 14)
    c.drawString(50, 740, "Form W-2  Wage and Tax Statement")
    c.setFont("Helvetica", 10)
    c.drawString(50, 722, f"Tax Year {tax_year}")

    box(c, 50, 660, 250, 45, "b Employer identification number, Employer", f"Employer: {employer}")
    box(c, 310, 660, 240, 45, "a Employee's SSN", f"SSN: {ssn}")
    box(c, 50, 610, 250, 45, "e Employee's name / c  Employee", f"Employee: {employee}")
    box(c, 310, 610, 240, 45, "1 Wages, tips, other compensation", f"${wages:,.2f}")
    box(c, 310, 560, 240, 45, "2 Federal income tax withheld", f"${wages * 0.15:,.2f}")

    c.setFont("Helvetica", 7)
    c.drawString(50, 540, "Copy B - To Be Filed With Employee's FEDERAL Tax Return")
    c.save()


def make_1040(path, tax_year, name1, name2, ssn1, ssn2):
    c = canvas.Canvas(path, pagesize=letter)
    c.setFont("Helvetica-Bold", 14)
    c.drawString(50, 740, "Form 1040  U.S. Individual Income Tax Return")
    c.setFont("Helvetica", 10)
    c.drawString(50, 722, f"Tax Year {tax_year}")

    box(c, 50, 660, 500, 45, "Filing status: Married filing jointly", f"Name: {name1}   Name: {name2}")
    box(c, 50, 610, 240, 40, "Your social security number", ssn1)
    box(c, 310, 610, 240, 40, "Spouse's social security number", ssn2)

    c.setFont("Helvetica", 7)
    c.drawString(50, 580, "For Disclosure, Privacy Act, and Paperwork Reduction Act Notice, see separate instructions.")
    c.save()


def make_id(path, name, dob, id_number):
    c = canvas.Canvas(path, pagesize=(340, 216))
    c.setFillColorRGB(0.09, 0.14, 0.24)
    c.rect(0, 0, 340, 216, fill=1)
    c.setFillColorRGB(1, 1, 1)
    c.setFont("Helvetica-Bold", 12)
    c.drawString(16, 190, "STATE IDENTIFICATION CARD")
    c.setFont("Helvetica", 9)
    c.drawString(16, 165, f"Name: {name}")
    c.drawString(16, 148, f"DOB: {dob}")
    c.drawString(16, 131, f"ID Number: {id_number}")
    c.drawString(16, 20, "SPECIMEN - NOT A REAL DOCUMENT")
    c.save()


def make_unreadable(path):
    img = Image.new("L", (1700, 2200), color=235)
    draw = ImageDraw.Draw(img)
    for y in range(300, 2000, 55):
        smudge = 200 - (y % 40)
        draw.line([(120, y), (1550, y - 15)], fill=smudge, width=6)
    draw.rectangle([80, 80, 1620, 2120], outline=190, width=3)

    png_path = path.replace(".pdf", ".png")
    img.save(png_path)

    c = canvas.Canvas(path, pagesize=letter)
    c.drawImage(png_path, 0, 0, width=612, height=792)
    c.save()
    os.remove(png_path)


def main():
    os.makedirs(OUT_DIR, exist_ok=True)

    make_1040(
        os.path.join(OUT_DIR, "Rivera_1040_2024.pdf"),
        2024, "Ana Rivera", "Luis Rivera", "XXX-XX-1111", "XXX-XX-2222",
    )
    make_id(os.path.join(OUT_DIR, "Ana_ID.pdf"), "Ana Rivera", "1985-04-12", "CA-9834021")
    make_id(os.path.join(OUT_DIR, "Luis_ID.pdf"), "Luis Rivera", "1983-11-02", "CA-9834022")

    make_w2(
        os.path.join(OUT_DIR, "Ana_W2_2025_MeridianTech.pdf"),
        2025, "Ana Rivera", "XXX-XX-1111", "Meridian Tech", 78500,
    )
    make_w2(
        os.path.join(OUT_DIR, "Ana_W2_2025_RiversideConsulting.pdf"),
        2025, "Ana Rivera", "XXX-XX-1111", "Riverside Consulting", 22100,
    )
    make_w2(
        os.path.join(OUT_DIR, "Luis_W2_2025_OaklineManufacturing.pdf"),
        2025, "Luis Rivera", "XXX-XX-2222", "Oakline Manufacturing", 31200,
    )
    make_w2(
        os.path.join(OUT_DIR, "Luis_W2_2025_HarborviewLogistics.pdf"),
        2025, "Luis Rivera", "XXX-XX-2222", "Harborview Logistics", 29800,
    )

    make_w2(
        os.path.join(OUT_DIR, "Ana_W2_2023_wrong_year.pdf"),
        2023, "Ana Rivera", "XXX-XX-1111", "Meridian Tech", 71000,
    )
    make_w2(
        os.path.join(OUT_DIR, "Carlos_Mendez_W2_2025_unrelated.pdf"),
        2025, "Carlos Mendez", "XXX-XX-9999", "Pinewood Retail", 41000,
    )

    make_unreadable(os.path.join(OUT_DIR, "unreadable_scan.pdf"))

    print("fixtures written to", OUT_DIR)


if __name__ == "__main__":
    main()
