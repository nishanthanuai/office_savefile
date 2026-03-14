import re
import os
import argparse
import tempfile
import requests
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    HRFlowable,
    Image,
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch


def sanitize_filename(name):
    return re.sub(r'[\\/*?:"<>|]', "_", name)


def extract_details(text):
    details = {}
    patterns = {
        "Project": r"Name of the Project\s*-\s*(.*)",
        "upc": r"Unique Project Code \(UPC\)\s*-\s*(.*)",
        "state": r"State\s*-\s*(.*)",
        "ro": r"Regional Office \(RO\)\s*-\s*(.*)",
        "piu": r"Project Implementation Unit \(PIU\)\s*-\s*(.*)",
    }
    for key, pattern in patterns.items():
        match = re.search(pattern, text)
        details[key] = match.group(1).strip() if match else "N/A"

    roads = {}
    sections = re.split(r"\n\s*\n", text)
    for section in sections[1:]:
        section = section.strip()
        if not section:
            continue
        road_match = re.search(r"([A-Za-z0-9\s.]+)\s*-\s*(\d+)(?:\s+signs)?", section)
        if road_match:
            road_name = road_match.group(1).strip()
            count = int(road_match.group(2).strip())
            header_lines = section.split("\n")
            original_header = header_lines[0].strip()
            sign_lines = [line.strip() for line in header_lines[1:] if line.strip()]
            signs = []
            for line in sign_lines:
                sign = extract_sign_detail(line)
                if sign:
                    signs.append(sign)
            roads[road_name] = {
                "count": count,
                "signs": signs,
                "original_header": original_header,
            }
    details["roads"] = roads
    return details


def extract_sign_detail(line):
    chainage_match = re.match(r"(\d+\+\d+)\s+(.*)", line)
    if not chainage_match:
        return None
    chainage = chainage_match.group(1)
    rest_of_line = chainage_match.group(2)
    parts = rest_of_line.rsplit(" ", 3)
    if len(parts) < 3:
        return None
    try:
        latitude = parts[-3]
        longitude = parts[-2]
        image_url = parts[-1]
        if not (
            re.match(r"^-?\d+\.\d+$", latitude) and re.match(r"^-?\d+\.\d+$", longitude)
        ):
            return None
    except Exception:
        return None
    rest = " ".join(parts[:-3])
    location_keywords = ["Avenue", "Median", "Overhead", "Left", "Right"]
    location = next((kw for kw in location_keywords if kw in rest), "Unknown")
    for keyword in location_keywords:
        rest = rest.replace(keyword, "").strip()
    tokens = rest.split()
    if not tokens:
        return None
    type_text = tokens[0]
    description = " ".join(tokens[1:]) if len(tokens) > 1 else "No description"
    return {
        "chainage": chainage,
        "type": type_text,
        "description": description,
        "location": location,
        "latitude": latitude,
        "longitude": longitude,
        "image": image_url,
    }


def create_pdf(details, output_filename):
    doc = SimpleDocTemplate(
        output_filename,
        pagesize=landscape(A4),
        rightMargin=10,
        leftMargin=10,
        topMargin=30,
        bottomMargin=30,
    )
    elements = []
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "Title",
        parent=styles["Heading1"],
        fontSize=20,
        alignment=1,
        textColor=colors.darkblue,
    )
    subtitle_style = ParagraphStyle(
        "Subtitle",
        parent=styles["Heading2"],
        fontSize=14,
        alignment=1,
        textColor=colors.darkblue,
    )
    section_title = ParagraphStyle(
        "SectionTitle",
        parent=styles["Heading3"],
        fontSize=13,
        spaceAfter=6,
        textColor=colors.darkred,
    )
    cell_style = ParagraphStyle(
        "CellContents", parent=styles["BodyText"], fontSize=9, alignment=1
    )
    header_style = ParagraphStyle(
        "HeaderCell",
        parent=styles["BodyText"],
        fontSize=9,
        alignment=1,
        textColor=colors.white,
        fontName="Helvetica-Bold",
    )

    elements.append(Paragraph("ROAD SIGN DAMAGE REPORT", title_style))
    elements.append(Paragraph(f"Project: {details['Project']}", subtitle_style))
    elements.append(Spacer(1, 0.2 * inch))
    total_signs = sum(rd["count"] for rd in details["roads"].values())
    project_fields = [
        ["UPC", details["upc"]],
        ["State", details["state"]],
        ["RO", details["ro"]],
        ["PIU", details["piu"]],
        ["Total Signs", str(total_signs)],
    ]
    info_table = Table(
        [
            [
                Paragraph("<b>Field</b>", header_style),
                Paragraph("<b>Value</b>", header_style),
            ]
        ]
        + [
            [Paragraph(f, cell_style), Paragraph(v, cell_style)]
            for f, v in project_fields
        ],
        colWidths=[220, 500],
    )
    info_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.lightblue),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.black),
                ("PADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    elements.append(Paragraph("PROJECT DETAILS", section_title))
    elements.append(info_table)
    elements.append(Spacer(1, 0.2 * inch))

    saved_image_base = "Saved_Images"
    os.makedirs(saved_image_base, exist_ok=True)
    temp_files = []

    for road_name in sorted(
        details["roads"], key=lambda x: ("MCW RHS" not in x, "MCW LHS" not in x, x)
    ):
        road_data = details["roads"][road_name]
        elements.append(
            Paragraph(road_data.get("original_header", road_name), section_title)
        )
        if not road_data["signs"]:
            elements.append(
                Paragraph("No detailed sign information available", cell_style)
            )
            continue
        sign_data = [
            [
                Paragraph("Chainage", header_style),
                Paragraph("Type", header_style),
                Paragraph("Description", header_style),
                Paragraph("Location", header_style),
                Paragraph("Latitude", header_style),
                Paragraph("Longitude", header_style),
                Paragraph("Image", header_style),
            ]
        ]
        road_folder = os.path.join(saved_image_base, sanitize_filename(road_name))
        os.makedirs(road_folder, exist_ok=True)

        for sign in road_data["signs"]:
            img_path = sign.get("image")
            image_obj = Paragraph("N/A", cell_style)
            if img_path and img_path.startswith("http"):
                try:
                    response = requests.get(img_path, stream=True, timeout=5)
                    if response.status_code == 200:
                        _, ext = os.path.splitext(img_path)
                        ext = (
                            ext if ext.lower() in [".jpg", ".jpeg", ".png"] else ".jpg"
                        )
                        filename = f"{sanitize_filename(sign['chainage'])}_{sanitize_filename(sign['type'])}_{sanitize_filename(sign['location'])}{ext}"
                        local_img_path = os.path.join(road_folder, filename)
                        with open(local_img_path, "wb") as out_file:
                            out_file.write(response.content)
                        image_obj = Image(local_img_path, width=110, height=60)
                    else:
                        image_obj = Paragraph("N/A", cell_style)
                except Exception:
                    image_obj = Paragraph("N/A", cell_style)
            elif img_path and os.path.exists(img_path):
                image_obj = Image(img_path, width=110, height=60)
            row = [
                Paragraph(sign["chainage"], cell_style),
                Paragraph(sign["type"], cell_style),
                Paragraph(sign["description"], cell_style),
                Paragraph(
                    "Center" if sign["location"] == "Unknown" else sign["location"],
                    cell_style,
                ),
                Paragraph(sign["latitude"], cell_style),
                Paragraph(sign["longitude"], cell_style),
                image_obj,
            ]
            sign_data.append(row)
        sign_table = Table(
            sign_data, colWidths=[60, 60, 140, 80, 60, 60, 140], repeatRows=1
        )
        sign_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.darkred),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.black),
                    ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("PADDING", (0, 0), (-1, -1), 6),
                ]
            )
        )
        elements.append(sign_table)
        elements.append(Spacer(1, 0.2 * inch))

    doc.build(elements)


def process_folder(folder_path, output_folder=None):
    if not os.path.exists(folder_path):
        print(f"Error: Folder '{folder_path}' does not exist.")
        return
    if output_folder:
        os.makedirs(output_folder, exist_ok=True)
    else:
        output_folder = folder_path
    txt_files = [f for f in os.listdir(folder_path) if f.endswith(".txt")]
    if not txt_files:
        print(f"No .txt files found in folder '{folder_path}'.")
        return
    for txt_file in txt_files:
        input_path = os.path.join(folder_path, txt_file)
        pdf_filename = f"{os.path.splitext(txt_file)[0]}.pdf"
        output_path = os.path.join(output_folder, pdf_filename)
        try:
            with open(input_path, "r") as f:
                text = f.read()
            details = extract_details(text)
            create_pdf(details, output_path)
            print(f"Processed '{txt_file}' -> '{pdf_filename}'")
        except Exception as e:
            print(f"Error processing '{txt_file}': {e}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=str, default=None)
    args = parser.parse_args()
    folder = "Report"
    process_folder(folder, args.output)


if __name__ == "__main__":
    main()
