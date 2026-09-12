

import streamlit as st
import uuid
from datetime import datetime
import numpy as np
import pandas as pd
import os
import sys
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity

# Make sure agents.py (in the same folder) can be imported regardless of
# where Streamlit was launched from
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from agents import run_orchestration, build_simple_view, init_db, save_submission

init_db()

st.markdown(
    """
    <style>
    .stApp {
        border: 8px solid #2E7D32;
    }
    </style>
    """,
    unsafe_allow_html=True
)

st.title("AI Smart Bug Analyzer & Fix Advisor")
st.write("Paste your bug report or stack trace below - analysis runs automatically.")


@st.cache_resource
def load_retrieval_components():
    base_dir = os.path.dirname(os.path.abspath(__file__))

    model = SentenceTransformer('all-MiniLM-L6-v2')
    embeddings = np.load(os.path.join(base_dir, "embeddings_real.npy"))
    metadata = pd.read_csv(os.path.join(base_dir, "chunks_metadata.csv"))

    return model, embeddings, metadata


model, kb_embeddings, kb_metadata = load_retrieval_components()

bug_report = st.text_area("Bug Report / Stack Trace", height=200, key="bug_report_input")
uploaded_file = st.file_uploader("Or upload a bug report file", type=["txt", "log"], key="bug_file_uploader")

# --- Figure out what text (if any) is currently submitted ---
final_text = ""
if uploaded_file is not None:
    final_text = uploaded_file.read().decode("utf-8")
elif bug_report.strip() != "":
    final_text = bug_report.strip()

# --- Auto-submit: keep track of the last text we already analyzed ---
if "last_analyzed_text" not in st.session_state:
    st.session_state.last_analyzed_text = ""
if "combined_result" not in st.session_state:
    st.session_state.combined_result = None
if "bug_record" not in st.session_state:
    st.session_state.bug_record = None

should_analyze = (final_text != "" and final_text != st.session_state.last_analyzed_text)

if final_text == "":
    st.info("Waiting for a bug report to be pasted or uploaded...")

elif should_analyze:
    st.session_state.last_analyzed_text = final_text

    bug_record = {
        "bug_id": "BUG-" + str(uuid.uuid4())[:8],
        "description": final_text,
        "stack_trace": final_text,
        "timestamp": datetime.now().isoformat(),
        "source": "user_submission"
    }
    st.session_state.bug_record = bug_record

    with st.spinner("Analyzing bug report..."):
        # --- Run both agents (Task 3: orchestration) ---
        combined_result = run_orchestration(
            title=final_text[:80],
            description=final_text,
            stack_trace=final_text,
            bug_id=bug_record["bug_id"]
        )
        st.session_state.combined_result = combined_result
        simple_view_for_db = build_simple_view(combined_result)
        save_submission(simple_view_for_db, bug_record["description"], bug_record["timestamp"])

# --- Display results (uses whatever was last analyzed, from session_state) ---
if st.session_state.combined_result is not None:
    bug_record = st.session_state.bug_record
    combined_result = st.session_state.combined_result
    simple_view = build_simple_view(combined_result)

    st.success("Bug report received and analyzed")

    st.subheader("Analysis Summary")
    col1, col2, col3 = st.columns(3)
    col1.metric("Severity", simple_view["severity"])
    col2.metric("Priority", simple_view["priority"])
    col3.metric("Component", simple_view["component"])

    st.write(f"**Error Type:** {simple_view['error_type']}")
    st.write(f"**Failure Location:** {simple_view['failure_location']}")
    st.write(f"**Code Path:** {simple_view['code_path']}")
    st.write(f"**Confidence:** {simple_view['confidence']:.2f}")
    st.write(f"**Reasoning:** {simple_view['reasoning']}")

    # --- "Show full details" button - reveals both agents' complete raw output ---
    if st.button("Show full details (both agents)", key="show_full_details"):
        st.subheader("Full Combined Result")
        st.json(combined_result)

    st.divider()
    st.subheader("Submitted Bug Record")
    st.json(bug_record)

    # --- Retrieval: cosine similarity using real semantic embeddings ---
    query_vector = model.encode([bug_record["description"]], convert_to_numpy=True)
    similarities = cosine_similarity(query_vector, kb_embeddings)[0]

    top_indices = np.argsort(similarities)[::-1][:5]

    st.subheader("Similar Past Bugs")

    for rank, idx in enumerate(top_indices):
        row = kb_metadata.iloc[idx]
        st.write(f"**{rank+1}. {row['title']}**")
        st.write(f"Severity: {row['severity']} | Source: {row['source_dataset']} | Similarity: {similarities[idx]:.2f}")
        st.write("---")