import csv
from pathlib import Path

from sentence_transformers import SentenceTransformer
from retrieval import load_sections, load_or_build_index, retrieve, MODEL_NAME

DATASET_PATH = Path("data/evaluation/questions.csv")
RESULTS_PATH = Path("data/evaluation/retrieval_results.csv")
TOP_K = 5
JURISDICTION = "Punjab"


def parse_expected_sections(value):
    return {
        section.strip()
        for section in value.split("|")
        if section.strip()
    }


def main():
    if not DATASET_PATH.exists():
        raise FileNotFoundError(
            f"Dataset not found: {DATASET_PATH}. "
            "Run create_evaluation_dataset.py first."
        )

    with DATASET_PATH.open(
        "r", newline="", encoding="utf-8-sig"
    ) as file:
        questions = list(csv.DictReader(file))

    print("Loading legal collection...")
    sections = load_sections()

    print("Loading embedding model...")
    model = SentenceTransformer(MODEL_NAME)

    print("Loading or building FAISS index...")
    index, documents = load_or_build_index(sections, model)

    rows = []
    answerable_ranks = []
    answerable_recall_1 = []
    answerable_recall_5 = []

    for number, item in enumerate(questions, start=1):
        question = item["question"].strip()
        expected = parse_expected_sections(item["expected_sections"])
        is_answerable = item["answerable"].strip().lower() == "yes"

        print(f"[{number}/{len(questions)}] {item['question_id']}: {question}")

        results = retrieve(
            question,
            sections,
            model,
            index,
            documents,
            top_k=TOP_K,
            jurisdiction=JURISDICTION,
        )

        ranked_sections = [str(result["section_number"]) for result in results]
        top_score = results[0]["score"] if results else 0.0
        abstained = top_score < 0.575

        expected_act = item.get("expected_act", "").strip().casefold()

        # A result is relevant only when both the Act and section match.
        relevant_flags = [
            (
                result.get("act_name", "").strip().casefold()
                == expected_act
                and str(result["section_number"]) in expected
            )
            for result in results
        ]

        # Rank is the position of the first matching Act + section, starting at 1.
        first_relevant_rank = next(
            (
                rank
                for rank, is_relevant in enumerate(relevant_flags, start=1)
                if is_relevant
            ),
            None,
        )

        if is_answerable and expected:
            hit_1 = int(any(relevant_flags[:1]))
            hit_5 = int(any(relevant_flags[:5]))
            reciprocal_rank = (
                1.0 / first_relevant_rank
                if first_relevant_rank is not None
                else 0.0
            )

            answerable_recall_1.append(hit_1)
            answerable_recall_5.append(hit_5)
            answerable_ranks.append(reciprocal_rank)
        else:
            hit_1 = ""
            hit_5 = ""
            reciprocal_rank = ""

        rows.append({
            "question_id": item["question_id"],
            "question": question,
            "language": item["language"],
            "category": item["category"],
            "expected_act": item.get("expected_act", ""),
            "expected_sections": "|".join(sorted(expected)),
            "answerable": item["answerable"],
            "status": item["status"],
            "top_5_sections": "|".join(ranked_sections),
            "top_5_scores": "|".join(
                f"{result['score']:.4f}" for result in results
            ),
            "first_relevant_rank": first_relevant_rank or "",
            "recall_at_1": hit_1,
            "recall_at_5": hit_5,
            "reciprocal_rank": (
                f"{reciprocal_rank:.4f}"
                if reciprocal_rank != ""
                else ""
            ),
            "top_score": f"{top_score:.4f}",
            "abstained_at_0575": abstained,
        })

    RESULTS_PATH.parent.mkdir(parents=True, exist_ok=True)

    with RESULTS_PATH.open(
        "w", newline="", encoding="utf-8-sig"
    ) as file:
        writer = csv.DictWriter(file, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)

    count = len(answerable_ranks)

    print("\n=== RETRIEVAL EVALUATION ===")
    print(f"Total questions: {len(questions)}")
    print(f"Included in retrieval metrics: {count}")

    if count:
        recall_1 = sum(answerable_recall_1) / count
        recall_5 = sum(answerable_recall_5) / count
        mrr = sum(answerable_ranks) / count

        print(f"Recall@1: {recall_1:.4f} ({recall_1 * 100:.2f}%)")
        print(f"Recall@5: {recall_5:.4f} ({recall_5 * 100:.2f}%)")
        print(f"MRR:      {mrr:.4f}")
    else:
        print("No answerable questions with labels were available.")

    print("\nOut-of-scope/pending-corpus questions are excluded")
    print("from these retrieval metrics.")
    print(f"Per-question results saved to: {RESULTS_PATH}")


if __name__ == "__main__":
    main()
