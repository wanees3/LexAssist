import json
import re
from pathlib import Path

INPUT_PATH = Path(
    "data/processed/punjab_consumer_protection_act_2005.txt"
)
OUTPUT_PATH = Path(
    "data/processed/punjab_consumer_protection_act_2005_sections.json"
)

text = INPUT_PATH.read_text(encoding="utf-8")

# Remove page markers, keeping the legal text across page breaks.
text = re.sub(r"--- PAGE \d+ ---", "\n", text)

lines = text.splitlines()

start = next(
    (i for i, line in enumerate(lines) if line.strip() == "TEXT"),
    None,
)

if start is None:
    raise ValueError(
        "Could not find the standalone TEXT marker."
    )

text = "\n".join(lines[start + 1:])
print("Found start of Act:", lines[start + 1].strip())

# Match numbered section headings, including section 23-A.
section_pattern = re.compile(
    r"(?m)^\s*(\d+[A-Z]?(?:-[A-Z])?)\.\s+"
    r"(.+?)\s*[.—–-]\s*"
)

matches = list(section_pattern.finditer(text))

if not matches:
    raise ValueError("No section headings were detected.")

sections = []

for i, match in enumerate(matches):
    section_number = match.group(1)
    heading = match.group(2).strip()

    end = (
        matches[i + 1].start()
        if i + 1 < len(matches)
        else len(text)
    )

    body = text[match.start():end].strip()
    # Remove page markers left inside a section.
    body = re.sub(r"(?m)^\s*--- PAGE \d+ ---\s*$", "", body)

    # Remove trailing spaces and collapse repeated blank lines.
    body = "\n".join(line.rstrip() for line in body.splitlines())
    body = re.sub(r"\n[ \t]*\n(?:[ \t]*\n)+", "\n\n", body)
    body = body.strip()

    # Ignore obvious contents-page entries if any remain.
    if len(body) < 30:
        continue

    sections.append({
        "section_number": section_number,
        "heading": heading,
        "text": body,
        "act_name": "Punjab Consumer Protection Act, 2005",
        "jurisdiction": "Punjab",
        "source_file": (
            "data/raw_laws/"
            "punjab_consumer_protection_act_2005.pdf"
        ),
        "source_url": "https://pccmdpunjab.gov.pk/static/acts/acts.pdf",
        "jurisdiction_source_url": "https://cpd.gop.pk/",
        "applicability_status": (
            "Provincial Act identified; verify current amendments "
            "and section-specific applicability"
        ),
        "verification_status": "pending_current_law_review",
    })

OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
OUTPUT_PATH.write_text(
    json.dumps(sections, ensure_ascii=False, indent=2),
    encoding="utf-8",
)

print("Sections extracted:", len(sections))
print("Saved to:", OUTPUT_PATH)
print("\nFirst five detected sections:")

for section in sections[:5]:
    print(
        f"{section['section_number']}: "
        f"{section['heading']} "
        f"({len(section['text'])} characters)"
    )
