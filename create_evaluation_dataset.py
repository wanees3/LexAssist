import csv
from pathlib import Path

OUTPUT = Path("data/evaluation/questions.csv")
OUTPUT.parent.mkdir(parents=True, exist_ok=True)

# expected_sections contains the manually assigned relevant section IDs.
# Review these labels before treating the results as final research findings.
questions = [
    {
        "question_id": "P01",
        "question": "How is a lease of immovable property defined?",
        "language": "English",
        "category": "property",
        "expected_act": "Transfer of Property Act, 1882",
        "expected_sections": "105",
        "answerable": "yes",
        "status": "ready_for_review",
    },
    {
        "question_id":"O02",
        "question":"What remedy is available for a defective consumer product?",
        "language":"English",
        "category":"consumer",
        "expected_act": "Punjab Consumer Protection Act, 2005",
        "expected_sections":"4|31",
        "answerable":"yes",
        "status":"ready_for_review"
    },
    {
        "question_id": "P03",
        "question": "What is a gift of property?",
        "language": "English",
        "category": "property",
        "expected_act": "Transfer of Property Act, 1882",
        "expected_sections": "122",
        "answerable": "yes",
        "status": "ready_for_review",
    },
    {
        "question_id": "P04",
        "question": "When does a lease of immovable property end?",
        "language": "English",
        "category": "property",
        "expected_act": "Transfer of Property Act, 1882",
        "expected_sections": "111",
        "answerable": "yes",
        "status": "ready_for_review",
    },
    {
        "question_id": "P05",
        "question": "What formalities apply to leases lasting more than one year?",
        "language": "English",
        "category": "property",
        "expected_act": "Transfer of Property Act, 1882",
        "expected_sections": "107",
        "answerable": "yes",
        "status": "ready_for_review",
    },
    {
        "question_id": "P06",
        "question": "How is lease duration determined when there is no contrary contract or local usage?",
        "language": "English",
        "category": "property",
        "expected_act": "Transfer of Property Act, 1882",
        "expected_sections": "106",
        "answerable": "yes",
        "status": "ready_for_review",
    },
    {
        "question_id": "P07",
        "question": "What does transfer of property mean under the Act?",
        "language": "English",
        "category": "property",
        "expected_act": "Transfer of Property Act, 1882",
        "expected_sections": "5",
        "answerable": "yes",
        "status": "ready_for_review",
    },
    {
        "question_id": "P08",
        "question": "غیر منقولہ جائیداد کی لیز کی تعریف کیا ہے؟",
        "language": "Urdu",
        "category": "property",
        "expected_act": "Transfer of Property Act, 1882",
        "expected_sections": "105",
        "answerable": "yes",
        "status": "exploratory_multilingual",
    },
    {
        "question_id": "P09",
        "question": "غیر منقولہ جائیداد کی فروخت کی تعریف کیا ہے؟",
        "language": "Urdu",
        "category": "property",
        "expected_act": "Transfer of Property Act, 1882",
        "expected_sections": "54",
        "answerable": "yes",
        "status": "exploratory_multilingual",
    },
    {
        "question_id": "P10",
        "question": "Lease ki definition kya hai?",
        "language": "Roman Urdu",
        "category": "property",
        "expected_act": "Transfer of Property Act, 1882",
        "expected_sections": "105",
        "answerable": "yes",
        "status": "exploratory_multilingual",
    },
    {
        "question_id": "P11",
        "question": "Property ki sale ke liye kaunsa section hai?",
        "language": "Roman Urdu",
        "category": "property",
        "expected_act": "Transfer of Property Act, 1882",
        "expected_sections": "54",
        "answerable": "yes",
        "status": "exploratory_multilingual",
    },
    {
        "question_id": "O01",
        "question": "What are the legal requirements for maternity leave in Punjab?",
        "language": "English",
        "category": "employment",
        "expected_act": "",
        "expected_sections": "",
        "answerable": "no",
        "status": "pending_employment_corpus",
    },
    {
        "question_id": "O03",
        "question": "What is the capital of France?",
        "language": "English",
        "category": "out_of_scope",
        "expected_act": "",
        "expected_sections": "",
        "answerable": "no",
        "status": "out_of_scope",
    },
]

fields = [
    "question_id",
    "question",
    "language",
    "category",
    "expected_act",
    "expected_sections",
    "answerable",
    "status",
]

with OUTPUT.open("w", newline="", encoding="utf-8-sig") as file:
    writer = csv.DictWriter(file, fieldnames=fields)
    writer.writeheader()
    writer.writerows(questions)

print(f"Created {len(questions)} evaluation questions: {OUTPUT}")
print("Answerable property questions:", sum(q["answerable"] == "yes" for q in questions))
print("Out-of-scope or pending-corpus questions:", sum(q["answerable"] == "no" for q in questions))
