
@'
from pathlib import Path
import csv
import json
import re
import os
import requests
from openpyxl import load_workbook
from sentence_transformers import SentenceTransformer

from answer import generate_answer
from retrieval import (
    load_sections, retrieve, MODEL_NAME,
    collection_fingerprint, INDEX_PATH, INDEX_METADATA_PATH
)
import faiss
from evaluate_master_150_confirmed_rewrite import (
    relevant_rank, parse_sections
)

ROOT = Path("data/evaluation")
DATASET = ROOT / "question_master_150_sections_confirmed.xlsx"
POLICY = ROOT / "step2_question_scoring_policy_v1.csv"
LIMIT = int(os.getenv("LEXASSIST_EXPERIMENT_LIMIT", "4"))
SUFFIX = "pilot_4" if LIMIT == 4 else f"run_{LIMIT}"
DETAIL = ROOT / f"five_system_experiment_{SUFFIX}.csv"
SUMMARY = ROOT / f"five_system_metrics_{SUFFIX}.csv"

OLLAMA = "http://localhost:11434"
REWRITE_MODEL = "qwen3:8b"
ANSWER_MODEL = "qwen3-guardrails-test"
TOP_K = 5
ABSTENTION_THRESHOLD = 0.575

for path in (DATASET, POLICY, INDEX_PATH, INDEX_METADATA_PATH):
    if not path.exists():
        raise FileNotFoundError(f"Required file missing: {path}")

for path in (DETAIL, SUMMARY):
    if path.exists():
        raise FileExistsError(
            f"Output already exists; refusing to overwrite: {path}"
        )

# Read benchmark.
wb = load_workbook(DATASET, read_only=True, data_only=True)
ws = wb.active
headers = [c.value for c in ws[1]]
questions = [dict(zip(headers, r)) for r in ws.iter_rows(
    min_row=2, values_only=True
)]
wb.close()

if len(questions) != 150:
    raise ValueError(f"Expected 150 benchmark questions, found {len(questions)}")

# Deterministic pilot: first answerable item per language plus one
# unanswerable item not already selected.
if LIMIT < 150:
    selected = []
    seen = set()
    for language in ("English", "Urdu", "Roman Urdu"):
        match = next(
            (r for r in questions
             if str(r.get("language", "")).strip().casefold() == language.casefold()
             and str(r.get("answerable", "")).strip().casefold() == "yes"),
            None
        )
        if match and match["question_id"] not in seen:
            selected.append(match)
            seen.add(match["question_id"])

    unanswerable = next(
        (r for r in questions
         if str(r.get("answerable", "")).strip().casefold() == "no"
         and r["question_id"] not in seen),
        None
    )
    if unanswerable:
        selected.append(unanswerable)
    questions = selected[:LIMIT]

if not questions:
    raise ValueError("No questions selected.")

# Attach scoring eligibility metadata.
with POLICY.open(encoding="utf-8-sig", newline="") as f:
    policy_rows = {
        r["question_id"]: r for r in csv.DictReader(f)
    }

# Validate existing index. Do not rebuild or write to it.
sections = load_sections()
with INDEX_METADATA_PATH.open(encoding="utf-8-sig") as f:
    metadata = json.load(f)

fingerprint = collection_fingerprint(sections)
if metadata.get("fingerprint") != fingerprint:
    raise RuntimeError(
        "FAISS index fingerprint does not match the configured corpus. "
        "No index was rebuilt. Resolve this before running experiments."
    )
if metadata.get("model_name") != MODEL_NAME:
    raise RuntimeError("Index embedding model does not match retrieval.py.")

index = faiss.read_index(str(INDEX_PATH))
if index.ntotal != len(sections):
    raise RuntimeError("FAISS index size does not match loaded sections.")

documents = [
    f"Act: {x['act_name']}\nSection: {x['section_number']}\n"
    f"Heading: {x['heading']}\nText: {x['text']}"
    for x in sections
]

print(f"Loading embedding model: {MODEL_NAME}")
model = SentenceTransformer(MODEL_NAME)

def rewrite_query(question):
    prompt = (
        "Rewrite the following legal question into a concise, faithful "
        "English search query for finding Pakistani statutory provisions. "
        "The input may be English, Urdu script, or Roman Urdu. Preserve "
        "the meaning and specificity. Do not answer the question, add "
        "legal facts, or invent section numbers. Return only the query.\n\n"
        f"Question:\n{question}"
    )
    response = requests.post(
        f"{OLLAMA}/api/chat",
        json={
            "model": REWRITE_MODEL,
            "messages": [{"role": "user", "content": prompt}],
            "stream": False,
            "think": False,
            "options": {"temperature": 0, "num_predict": 128},
        },
        timeout=180,
    )
    response.raise_for_status()
    text = response.json().get("message", {}).get("content", "").strip()
    if not text:
        raise RuntimeError("Query rewrite returned empty text.")
    return text

def llm_only(question):
    prompt = (
        "Answer this question as a cautious Pakistani legal-information "
        "assistant. You have not been given statutory evidence or access "
        "to a legal database. Do not invent section numbers, citations, "
        "source links, or legal rules. If uncertain, say that you cannot "
        "verify the answer. Answer in the language and script of the "
        "question. Give general legal information, not legal advice.\n\n"
        f"Question:\n{question}"
    )
    response = requests.post(
        f"{OLLAMA}/api/chat",
        json={
            "model": ANSWER_MODEL,
            "stream": False,
            "think": False,
            "messages": [
                {"role": "user", "content": prompt}
            ],
            "options": {"temperature": 0.1, "num_predict": 220},
        },
        timeout=180,
    )
    response.raise_for_status()
    answer = response.json().get("message", {}).get("content", "").strip()
    if not answer:
        raise RuntimeError("LLM-only answer returned empty text.")
    return answer

def relevant_metrics(results, row):
    rank = relevant_rank(
        results,
        str(row.get("expected_act") or ""),
        parse_sections(str(row.get("expected_sections") or ""))
    )
    return {
        "expected_rank": rank or "",
        "recall_at_1": int(rank == 1),
        "recall_at_5": int(rank is not None and rank <= 5),
        "reciprocal_rank": 1 / rank if rank else 0.0,
    }

systems = [
    "LLM-only",
    "Basic RAG",
    "Full LexAssist",
    "No jurisdiction filter",
    "No query rewriting",
]

results_out = []

for i, row in enumerate(questions, start=1):
    qid = str(row["question_id"])
    question = str(row["question"]).strip()
    answerable = str(row.get("answerable", "")).strip().casefold() == "yes"
    jurisdiction = str(row.get("retrieval_jurisdiction") or "").strip()
    if jurisdiction.casefold() in {"", "all (no filter)"}:
        jurisdiction = None

    print(f"\nQuestion {i}/{len(questions)}: {qid}")

    # Reuse one rewrite for the two configurations that require it.
    rewritten = rewrite_query(question)
    print(f"  Rewrite: {rewritten[:120]}")

    configurations = [
        ("Basic RAG", question, None),
        ("Full LexAssist", rewritten, jurisdiction),
        ("No jurisdiction filter", rewritten, None),
        ("No query rewriting", question, jurisdiction),
    ]

    # LLM-only: no retrieval, no supplied statutory evidence.
    answer = llm_only(question)
    results_out.append({
        "question_id": qid,
        "language": row.get("language", ""),
        "answerable": "yes" if answerable else "no",
        "system": "LLM-only",
        "search_query": "",
        "jurisdiction_filter": "not applicable",
        "expected_act": row.get("expected_act", ""),
        "expected_sections": row.get("expected_sections", ""),
        "expected_rank": "",
        "recall_at_1": "",
        "recall_at_5": "",
        "reciprocal_rank": "",
        "top_score": "",
        "abstention_proxy": "",
        "top_5_acts_and_sections": "",
        "generated_answer": answer,
        "primary_scoring_policy": policy_rows.get(qid, {}).get(
            "primary_scoring_policy", ""
        ),
        "correctness_score_0_2": "",
        "groundedness_score_0_2": "",
        "citation_accuracy_score_0_2": "",
        "language_quality_score_0_2": "",
        "abstention_appropriate": "",
        "reviewer_notes": "",
    })

    for system, search_query, filter_jurisdiction in configurations:
        retrieved = retrieve(
            search_query, sections, model, index, documents,
            top_k=TOP_K, jurisdiction=filter_jurisdiction
        )
        metrics = relevant_metrics(retrieved, row) if answerable else {
            "expected_rank": "",
            "recall_at_1": "",
            "recall_at_5": "",
            "reciprocal_rank": "",
        }

        generated = generate_answer(question, retrieved)
        top_score = retrieved[0]["score"] if retrieved else None
        top5 = " | ".join(
            f"{x.get('act_name', '')} Section {x.get('section_number', '')}"
            for x in retrieved
        )

        results_out.append({
            "question_id": qid,
            "language": row.get("language", ""),
            "answerable": "yes" if answerable else "no",
            "system": system,
            "search_query": search_query,
            "jurisdiction_filter": filter_jurisdiction or "none",
            "expected_act": row.get("expected_act", ""),
            "expected_sections": row.get("expected_sections", ""),
            **metrics,
            "top_score": top_score if top_score is not None else "",
            "abstention_proxy": (
                int(top_score is None or top_score < ABSTENTION_THRESHOLD)
                if top_score is not None or not retrieved else 1
            ),
            "top_5_acts_and_sections": top5,
            "generated_answer": generated,
            "primary_scoring_policy": policy_rows.get(qid, {}).get(
                "primary_scoring_policy", ""
            ),
            "correctness_score_0_2": "",
            "groundedness_score_0_2": "",
            "citation_accuracy_score_0_2": "",
            "language_quality_score_0_2": "",
            "abstention_appropriate": "",
            "reviewer_notes": "",
        })
        print(f"  {system}: retrieved {len(retrieved)} sections; answer generated.")

# Save detailed results.
with DETAIL.open("w", encoding="utf-8-sig", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=list(results_out[0].keys()))
    writer.writeheader()
    writer.writerows(results_out)

# Summarize retrieval metrics. LLM-only retrieval metrics are N/A.
summary = []
for system in systems:
    subset = [r for r in results_out if r["system"] == system]
    answerable_rows = [
        r for r in subset
        if r["answerable"] == "yes" and r["reciprocal_rank"] != ""
    ]
    unanswerable_rows = [r for r in subset if r["answerable"] == "no"]
    summary.append({
        "system": system,
        "questions": len(subset),
        "answerable_questions": sum(r["answerable"] == "yes" for r in subset),
        "unanswerable_questions": len(unanswerable_rows),
        "recall_at_1": (
            round(sum(r["recall_at_1"] for r in answerable_rows) /
                  len(answerable_rows), 4) if answerable_rows else ""
        ),
        "recall_at_5": (
            round(sum(r["recall_at_5"] for r in answerable_rows) /
                  len(answerable_rows), 4) if answerable_rows else ""
        ),
        "mrr": (
            round(sum(r["reciprocal_rank"] for r in answerable_rows) /
                  len(answerable_rows), 4) if answerable_rows else ""
        ),
        "note": (
            "No retrieval; metrics not applicable."
            if system == "LLM-only"
            else "Pilot only; run all 150 questions for final metrics."
        ),
    })

with SUMMARY.open("w", encoding="utf-8-sig", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=list(summary[0].keys()))
    writer.writeheader()
    writer.writerows(summary)

print("\nPilot complete.")
print(f"Detailed results: {DETAIL}")
print(f"Metrics summary: {SUMMARY}")
print("Generated-answer review columns are intentionally blank.")
print("No production code, corpus, or FAISS index was modified.")
'@ | .\.venv\Scripts\python.exe -
