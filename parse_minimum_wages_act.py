import json
import re
from datetime import date
from pathlib import Path

import pymupdf

PDF_PATH = Path("data/raw_laws/punjab_minimum_wages_act_2019_PROVISIONAL.pdf")
OUTPUT_PATH = Path(
    "data/processed/corpus_audit_candidates/"
    "punjab_minimum_wages_act_2019_candidate.json"
)
ACT_NAME = "Punjab Minimum Wages Act, 2019"
OFFICIAL_URL = "https://punjablaws.punjab.gov.pk/en/show_article/UWldYwUxBzM-"


def clean_text(text):
    text = text.replace("\u00ad", "").replace("\u200b", "")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def main():
    if not PDF_PATH.exists():
        raise FileNotFoundError(PDF_PATH)

    with pymupdf.open(PDF_PATH) as pdf:
        pages = [page.get_text("text") or "" for page in pdf]

    full_text = "\n".join(pages)
    start_marker = "Be it enacted by Provincial Assembly of the Punjab as follows:"
    start_pos = full_text.find(start_marker)
    if start_pos < 0:
        raise SystemExit("Could not find Act commencement marker; no records written.")

    body = full_text[start_pos + len(start_marker):]
    lines = body.splitlines()
    records = []
    current_number = None
    current_lines = []
    current_page = None
    page_offsets = []
    offset = 0
    for page_text in pages:
        page_offsets.append((offset, offset + len(page_text)))
        offset += len(page_text) + 1

    body_start = start_pos + len(start_marker)

    def page_for_line(line_index):
        char_pos = body_start + sum(len(x) + 1 for x in lines[:line_index])
        for page_num, (a, b) in enumerate(page_offsets, start=1):
            if a <= char_pos <= b:
                return page_num
        return None

    def save_section():
        nonlocal current_number, current_lines, current_page
        if current_number is None:
            return
        text = clean_text("\n".join(current_lines))
        if not text:
            return
        first_line = text.splitlines()[0]
        heading = re.sub(r"^\d{1,2}\.\s*", "", first_line).strip()
        heading = re.split(r"[–—-]\s*\(\d+\)", heading, maxsplit=1)[0].strip()
        records.append({
            "act_name": ACT_NAME,
            "section_number": current_number,
            "heading": heading,
            "text": text,
            "jurisdiction": "Punjab",
            "applicability": (
                "Candidate extraction from a provisional copy; verify against "
                "the official Act and current amendments."
            ),
            "source_file": str(PDF_PATH),
            "source_url": OFFICIAL_URL,
            "jurisdiction_source_url": OFFICIAL_URL,
            "retrieved_on": date.today().isoformat(),
            "pdf_start_page": current_page,
            "verification_status": "pending_official_scan_comparison",
            "extraction_status": "candidate",
        })

    i = 0
    while i < len(lines):
        line = lines[i].strip()
        match = re.fullmatch(r"(\d{1,2})\.", line)

        if match and 1 <= int(match.group(1)) <= 23:
            number = int(match.group(1))
            j = i + 1
            while j < len(lines) and not lines[j].strip():
                j += 1

            if j < len(lines):
                next_line = lines[j].strip()
                # Real section headings start with a capital letter or quote.
                if re.match(r'^[A-Z“"‘]', next_line):
                    save_section()
                    current_number = str(number)
                    current_lines = [f"{number}. {next_line}"]
                    current_page = page_for_line(i)
                    i = j + 1
                    continue

        if current_number is not None:
            current_lines.append(lines[i])
        i += 1

    save_section()

    numbers = [r["section_number"] for r in records]
    duplicates = sorted({n for n in numbers if numbers.count(n) > 1})
    missing = [str(n) for n in range(1, 24) if str(n) not in numbers]

    if duplicates or missing or len(records) != 23:
        print("Extraction validation failed.")
        print("Records:", len(records))
        print("Missing:", missing)
        print("Duplicates:", duplicates)
        raise SystemExit("Candidate output not overwritten with incomplete extraction.")

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(
        json.dumps(records, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print("Candidate extraction complete.")
    print("Records:", len(records))
    print("Sections:", ", ".join(numbers))
    print("Missing sections: none")
    print("Duplicate sections: none")
    print("Status: pending official scan comparison")
    print("Output:", OUTPUT_PATH)
    for r in records[:3]:
        print(f"\nSection {r['section_number']}: {r['heading']}")
        print("Text preview:", r["text"][:180].replace("\n", " "))


if __name__ == "__main__":
    main()
