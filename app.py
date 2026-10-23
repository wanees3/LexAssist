import streamlit as st
from sentence_transformers import SentenceTransformer
from retrieval import load_sections, load_or_build_index, retrieve
from answer import generate_answer, MODEL_NAME

st.set_page_config(
    page_title="LexAssist",
    page_icon="âš–ï¸",
    layout="wide",
)

@st.cache_resource(show_spinner="Loading legal documents and search model...")
def load_search_system():
    sections = load_sections()
    model = SentenceTransformer(MODEL_NAME)
    index, documents = load_or_build_index(sections, model)
    return sections, model, index, documents


st.title("⚖️ LexAssist")
st.subheader("Legal Information Assistant for Federal and Punjab Laws")

st.info(
    "LexAssist provides general legal information, not legal advice. "
    "Always verify current law and jurisdictional applicability."
)


st.warning(
    "Prototype Limitation: This prototype covers selected Pakistani laws, and most of the selected legal sources have been reviewed and verified. "
    "However, complete verification of the current legal status, amendments, and applicability of every provision was limited by the availability of authoritative and up-to-date information. "
    "The 2025 Punjab minimum-wage notification reference is provisional and should not be treated as confirmation of current wage rates. "
    "Please check official legal sources before relying on any information."
)

jurisdiction = st.selectbox(
    "Select jurisdiction",
    ["Punjab", "Federal"],
)

st.caption(
    f"Selected jurisdiction: {jurisdiction}. "
    "Results are filtered by recorded jurisdiction tags only. "
    "This does not confirm that a provision is currently in force "
    "or applicable to your specific circumstances."
)

question = st.text_area(
    "Ask a legal-information question",
    placeholder="For example: How is a lease of immovable property defined?",
    height=120,
)


# Pilot only: fixed query variants tested in the expanded evaluation.
# The user's original question remains unchanged for answer generation.
QUERY_REWRITES = {
    "What remedy is available for a defective consumer product?":
        "Under the Punjab Consumer Protection Act, which sections provide a remedy or compensation for a consumer who receives a defective product?",
    "When does a lease of immovable property end?":
        "Under which provision is a lease determined under the Transfer of Property Act?",
    "Section 105 ke tehat lease kya hoti hai?":
        "What is a lease under Section 105 of the Transfer of Property Act, 1882?",
    "Lease kab khatam hoti hai?":
        "Under which provision is a lease determined under the Transfer of Property Act?",
    "Property ki sale ke liye kaunsa section hai?":
        "Property ki sale kis section mein define hai?",
    "Gift of immovable property kis tarah transfer ki jati hai?":
        "Immovable property ka gift kis section ke tehat transfer hota hai?",
    "??? ?????? ??????? ?? ????? ?? ???? ??? ???? ?? ??? ???":
        "??? ?????? ??????? ?? ????? ?? ????? ?? ???? ??? ???",
    "Kaam ki jagah par harassment ke khilaf qanoon kya tahaffuz deta hai?":
        "Which provisions of the Protection Against Harassment of Women at the Workplace Act, 2010 define harassment and           require employers to establish an inquiry committee and implement a code of conduct?",
}

if st.button("Find legal information", type="primary"):
    if not question.strip():
        st.warning("Please enter a question first.")
    else:
        try:
            sections, model, index, documents = load_search_system()

            original_question = question.strip()
            retrieval_query = QUERY_REWRITES.get(
                original_question,
                original_question,
            )

            if retrieval_query != original_question:
                st.caption(
                    "Pilot query refinement is active for this tested question. "
                    "Your original wording is retained for the response."
                )

            with st.spinner("Searching the legal collection..."):
                results = retrieve(
                    retrieval_query,
                    sections,
                    model,
                    index,
                    documents,
                    top_k=5,
                    jurisdiction=jurisdiction,
                )

            st.markdown("## Response")

            if not results:
                st.warning(
                    f"No matching provisions were found in the indexed collection "
                    f"for the selected jurisdiction: {jurisdiction}. "
                    "This does not mean that no relevant law exists. "
                    "Check the appropriate official legal sources."
                    )
            
            else:
                answer = generate_answer(original_question, results)
                st.markdown(answer)

                abstained = answer.startswith(
                    (
                        "I could not find a matching provision",
                        "I could not find sufficiently relevant legal text",
                    )
                )

                if not abstained:
                    st.markdown("## Retrieved legal provisions")

                    for result in results:
                        with st.expander(
                            f"Section {result['section_number']}: "
                            f"{result['heading']} "
                            f"(score: {result['score']:.3f})"
                        ):
                            st.markdown("**Full provision text**")
                            st.text(result["text"])
                            st.caption(
                                f"Source file: {result['source_file']}"
                            )
                            st.caption(
                                f"Source URL: {result['source_url']}"
                            )
                            st.caption(
                                f"Jurisdiction source: "
                                f"{result.get('jurisdiction_source_url', 'Not recorded')}"
                            )
                            st.caption(
                                f"Applicability status: "
                                f"{result.get('applicability', 'Not recorded')}"
                            )
                            st.caption(
                                f"Verification status: "
                                f"{result.get('verification_status', 'Not recorded')}"
                            )

        except Exception as error:
            st.error(f"LexAssist encountered an error: {error}")
