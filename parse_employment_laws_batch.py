from pathlib import Path
import json
import re
import pymupdf

ROOT = Path("data/raw_laws")
OUT = Path("data/processed/corpus_audit_candidates")
OUT.mkdir(parents=True, exist_ok=True)

SOURCES = [
    {
        "file": "punjab_domestic_workers_act_2019.pdf",
        "slug": "punjab_domestic_workers_act_2019",
        "title": "Punjab Domestic Workers Act, 2019",
        "jurisdiction": "punjab",
        "official_url": "https://wdd.punjab.gov.pk/system/files/the-punjab-domestic-workers-act-2018-docx-pdf_2.pdf",
        "expected_first": 1,
        "expected_last": 38,
    },
    {
        "file": "protection_against_harassment_act_2010_updated_2022.pdf",
        "slug": "protection_against_harassment_act_2010",
        "title": "Protection Against Harassment of Women at the Workplace Act, 2010",
        "jurisdiction": "federal",
        "official_url": "https://pakistancode.gov.pk/pdffiles/administratorc22e81f4add9ea3dc023086953ca2b4f.pdf",
        "expected_first": 1,
        "expected_last": 13,
    },
    {
        "file": "punjab_shops_establishments_ordinance_1969_OFFICIAL.pdf",
        "slug": "punjab_shops_establishments_ordinance_1969",
        "title": "Punjab Shops and Establishments Ordinance, 1969",
        "jurisdiction": "punjab",
        "official_url": "https://www.punjablaws.gov.pk/lawspdf/230.pdf",
        "expected_first": 1,
        "expected_last": 34,
    },
]

# Match section headings at the start of a line, allowing OCR/PDF line breaks
# and common forms such as 10-A. Avoid treating subsections (1) as sections.
HEADING = re.compile(
    r"(?m)^[ \t]*(?:\d+\s*\[)?(\d{1,3}(?:-[A-Z])?)\.[ \t]*(?:\n[ \t]*)?([^\n]{2,180})"
)

def normalize_text(text):
    text = text.replace("\u00ad", "")
    text = text.replace("\r", "\n")
    text = re.sub(r"[ \t]+\n", "\n", text)
    text = re.sub(r"\n[ \t]*\n[ \t]*\n+", "\n\n", text)
    return text.strip()

def parse_source(source):
    pdf_path = ROOT / source["file"]
    if not pdf_path.exists():
        return {
            "source": source["file"],
            "error": f"PDF not found: {pdf_path}",
        }

    with pymupdf.open(pdf_path) as pdf:
        pages = [page.get_text("text") for page in pdf]

    # Exclude contents/front matter and the Shops Ordinance Schedule.
    if "domestic_workers" in source["slug"]:
        body_pages = pages[2:]
    elif "shops_establishments" in source["slug"]:
        # PDF pages 3-16 contain the Act body; later pages contain forms/schedules.
        body_pages = pages[2:16]
    else:
        body_pages = pages[1:]

    full_text = normalize_text("\n".join(body_pages))

    # Preserve the Harassment Act Schedule separately from numbered sections.
    schedule_text = ""
    if source["slug"] == "protection_against_harassment_act_2010":
        schedule_match = re.search(
            r"(?im)^\s*SCHEDULE\s*$",
            full_text
        )
        if schedule_match:
            schedule_text = full_text[schedule_match.end():].strip()
            full_text = full_text[:schedule_match.start()].strip()

    # Exclude the contents list by starting at the enactment text when possible.
    start_match = re.search(
        r"(?im)^\s*(?:Be it enacted|It is hereby enacted|NOW, THEREFORE|"
        r"Whereas\b.*)$",
        full_text,
    )
    if start_match:
        full_text = full_text[start_match.start():]

    matches = list(HEADING.finditer(full_text))
    sections = []

    for index, match in enumerate(matches):
        number = match.group(1).strip()
        heading = match.group(2).strip()

        # Reject likely contents entries and form/schedule numbered paragraphs.
        if len(heading) < 2:
            continue

        body_start = match.end()
        body_end = matches[index + 1].start() if index + 1 < len(matches) else len(full_text)
        body = full_text[body_start:body_end].strip()

        # Discard obvious non-section entries, especially numbered schedule fields.
        if re.match(r"(?i)^(name of the establishment|postal address|full name of)", heading):
            continue

        # Remove page headers/footers and excess whitespace, but retain legal text.
        body = re.sub(r"(?m)^\s*Page \d+ of \d+\s*$", "", body)
        body = re.sub(r"\n{3,}", "\n\n", body).strip()

        if not body:
            continue

        sections.append({
            "act_title": source["title"],
            "section_number": number,
            "section_heading": heading,
            "text": f"{number}. {heading}\n{body}",
            "jurisdiction": source["jurisdiction"],
            "source_url": source["official_url"],
            "source_file": source["file"],
            "verification_status": "pending_current_law_review",
            "extraction_status": "candidate_extracted",
        })

    # Save the Schedule as its own candidate record, not as Section 13 text.
    if schedule_text:
        sections.append({
            "act_title": source["title"],
            "section_number": "SCHEDULE",
            "section_heading": "Code of Conduct for Protection Against Harassment of Women at the Workplace",
            "text": "SCHEDULE\n" + schedule_text,
            "jurisdiction": source["jurisdiction"],
            "source_url": source["official_url"],
            "source_file": source["file"],
            "verification_status": "pending_current_law_review",
            "extraction_status": "candidate_schedule",
        })

    # Preserve evidence for manual validation.
    output_path = OUT / f"{source['slug']}_candidate.json"
    output_path.write_text(
        json.dumps(sections, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    numbers = [item["section_number"] for item in sections]
    duplicates = sorted({n for n in numbers if numbers.count(n) > 1})
    numeric_numbers = [
        int(n) for n in numbers if n.isdigit()
    ]

    return {
        "source": source["file"],
        "pages": len(pages),
        "candidate_sections": len(sections),
        "first_numbers": numbers[:8],
        "last_numbers": numbers[-8:],
        "duplicate_numbers": duplicates,
        "contains_expected_first": str(source["expected_first"]) in numbers,
        "contains_expected_last": str(source["expected_last"]) in numbers,
        "candidate_file": str(output_path),
        "warning": (
            "Candidate extraction only; inspect headings, gaps, schedules, "
            "amendments and source status before retrieval use."
        ),
    }

reports = [parse_source(source) for source in SOURCES]
report_path = OUT / "batch_extraction_report.json"
report_path.write_text(
    json.dumps(reports, ensure_ascii=False, indent=2),
    encoding="utf-8",
)

print(json.dumps(reports, ensure_ascii=False, indent=2))
print(f"\nReport saved to: {report_path}")
print("No existing retrieval JSON or retrieval.py file was changed.")
