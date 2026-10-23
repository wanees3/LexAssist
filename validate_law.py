import json
from pathlib import Path

path = Path("data/processed/transfer_of_property_act_1882_sections.json")
sections = json.loads(path.read_text(encoding="utf-8"))

print(f"Total records: {len(sections)}")

numbers = [item["section_number"] for item in sections]

print(f"Unique section numbers: {len(set(numbers))}")

duplicates = sorted({
    number for number in numbers
    if numbers.count(number) > 1
})
print(f"Duplicate section numbers: {duplicates}")

print(
    "Missing required samples:",
    [
        number for number in ("1", "3", "54", "107", "114A", "123", "137")
        if number not in numbers
    ],
)

print("\nAll extracted section numbers:")
print(", ".join(item["section_number"] for item in sections))

print("\nRecords needing review:")
for item in sections:
    text = item["text"].strip()
    number = item["section_number"]

    issues = []

    # The first line should start with the record's section number.
    if not text.startswith(number + "."):
        issues.append("text does not start with its section number")

    # Flag suspiciously short provisions for manual review.
    if len(text) < 80:
        issues.append(f"short text ({len(text)} characters)")

    # Flag possible section-number duplication for the next parser revision.
    if text.count(number + ".") > 1:
        issues.append("section number appears more than once")

    if issues:
        print(
            f"\nSection {number} — {item['heading']}\n"
            f"Issues: {'; '.join(issues)}\n"
            f"Text: {text[:250]}"
        )

print("\nSample full records:")
for target in ("1", "3", "5", "54", "105", "114A", "122", "137"):
    matches = [
        item for item in sections
        if item["section_number"] == target
    ]

    if matches:
        item = matches[0]
        print(f"\n--- Section {target}: {item['heading']} ---")
        print(item["text"][:700])
    else:
        print(f"\nSection {target}: NOT FOUND")
