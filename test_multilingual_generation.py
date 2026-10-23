import csv
from pathlib import Path

from retrieval import load_sections
from answer import generate_local_explanation

OUTPUT_PATH = Path(
    "data/evaluation/multilingual_generation_comparison.csv"
)

questions = [
    {
        "question_id": "P08-URDU",
        "language": "Urdu",
        "question": "غیر منقولہ جائیداد کی لیز کی تعریف کیا ہے؟",
    },
    {
        "question_id": "P08-ROMAN-URDU",
        "language": "Roman Urdu",
        "question": "Ghair manqoola jaidad ki lease ki tareef kya hai?",
    },
]

sections = load_sections()

evidence = next(
    (
        section for section in sections
        if "Transfer of Property Act, 1882" in section.get("act_name", "")
        and str(section.get("section_number", "")) == "105"
    ),
    None,
)

if evidence is None:
    raise RuntimeError(
        "Could not find section 105 of the Transfer of Property Act, 1882."
    )

rows = []

for item in questions:
    answer = generate_local_explanation(
        item["question"],
        [evidence],
    )

    rows.append({
        "question_id": item["question_id"],
        "language": item["language"],
        "question": item["question"],
        "evidence_act": evidence.get("act_name", ""),
        "evidence_section": evidence.get("section_number", ""),
        "generated_explanation": answer or "",
    })

    print(f'\n--- {item["language"]} ---')
    print(answer or "[No explanation returned]")

OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)

with OUTPUT_PATH.open("w", encoding="utf-8-sig", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=rows[0].keys())
    writer.writeheader()
    writer.writerows(rows)

print(f"\nSaved comparison to: {OUTPUT_PATH}")
