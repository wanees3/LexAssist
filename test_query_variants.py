
from sentence_transformers import SentenceTransformer
from retrieval import load_sections, load_or_build_index, retrieve, MODEL_NAME


TESTS = [
    {
        "id": "P04",
        "expected_act": "Transfer of Property Act, 1882",
        "expected_section": "111",
        "variants": [
            "When does a lease of immovable property end?",
            "What are the ways a lease is determined under the Transfer of Property Act?",
            "Under which section does a lease determine or terminate?",
        ],
    },
    {
        "id": "P11",
        "expected_act": "Transfer of Property Act, 1882",
        "expected_section": "54",
        "variants": [
            "Property ki sale ke liye kaunsa section hai?",
            "Property ki sale kis section mein define hai?",
            "Immovable property ki sale ki definition kis section mein hai?",
            "Which section defines the sale of immovable property?",
        ],
    },
]


def main():
    sections = load_sections()

    print(f"Loading embedding model: {MODEL_NAME}")
    model = SentenceTransformer(MODEL_NAME)

    print("Loading search index...")
    index, documents = load_or_build_index(sections, model)

    for test in TESTS:
        print(f"\n{'=' * 65}")
        print(f"Test {test['id']}: expected Section {test['expected_section']}")

        for query in test["variants"]:
            results = retrieve(
                query,
                sections,
                model,
                index,
                documents,
                top_k=5,
                jurisdiction="Punjab",
            )

            expected_act = test["expected_act"].casefold()
            expected_section = test["expected_section"]

            expected_rank = next(
                (
                    rank
                    for rank, item in enumerate(results, start=1)
                    if item["act_name"].casefold() == expected_act
                    and str(item["section_number"]) == expected_section
                ),
                None,
            )

            print(f"\nQuery: {query}")
            print(f"Expected section rank: {expected_rank or 'Not in top 5'}")

            for rank, item in enumerate(results, start=1):
                print(
                    f"  {rank}. Section {item['section_number']}: "
                    f"{item['heading']} | score={item['score']:.4f}"
                )


if __name__ == "__main__":
    main()
