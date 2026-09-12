# import streamlit as st
# import uuid
# from datetime import datetime
# import numpy as np
# import pandas as pd
# import os
# import sys
# from sentence_transformers import SentenceTransformer
# from sklearn.metrics.pairwise import cosine_similarity
# import sqlite3
# import plotly.express as px


# sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# from agents import (
#     run_orchestration, build_simple_view, init_db, save_submission,
#     retrieve_similar_bugs, root_cause_agent,
#     duplicate_detection_agent, remediation_agent,
#     COMPONENT_MERGE_MAP, compute_defect_analytics, cluster_root_causes,
#     add_resolved_bug_to_kb
# )

# init_db()

# st.markdown(
#     """
#     <style>
#     .stApp {
#         border: 8px solid #2E7D32;
#     }
#     </style>
#     """,
#     unsafe_allow_html=True
# )

# tab1, tab2 = st.tabs(["Submit Bug", "Analytics Dashboard"])

# with tab1:
#     # ... ALL of your existing app.py content from st.title() down to the final
#     # "Similar Past Bugs" section goes here, indented one level inside this block

#     st.title("Creation of Intelligent Bug Diagnosis Platform with Fix Recommendation Assistance ")
#     st.write("Paste your bug report or stack trace below - analysis runs automatically.")


#     @st.cache_resource
#     def load_retrieval_components():
#         base_dir = os.path.dirname(os.path.abspath(__file__))
#         model = SentenceTransformer('all-MiniLM-L6-v2')
#         embeddings = np.load(
#           os.path.join(base_dir, "embeddings_real.npy"),
#                 allow_pickle=True)
#         metadata = pd.read_csv(os.path.join(base_dir, "chunks_metadata.csv"))
#         return model, embeddings, metadata


#     model, kb_embeddings, kb_metadata = load_retrieval_components()

#     bug_report = st.text_area("Bug Report / Stack Trace", height=200, key="bug_report_input")
#     uploaded_file = st.file_uploader("Or upload a bug report file", type=["txt", "log"], key="bug_file_uploader")

#     top_n = st.slider(
#         "Number of similar bugs to retrieve (used for Root Cause and Duplicate Detection)",
#         min_value=3, max_value=15, value=5, key="top_n_slider"
#     )

#     final_text = ""
#     if uploaded_file is not None:
#         final_text = uploaded_file.read().decode("utf-8")
#     elif bug_report.strip() != "":
#         final_text = bug_report.strip()

#     if "last_analyzed_text" not in st.session_state:
#         st.session_state.last_analyzed_text = ""
#     if "last_top_n" not in st.session_state:
#         st.session_state.last_top_n = top_n
#     if "combined_result" not in st.session_state:
#         st.session_state.combined_result = None
#     if "bug_record" not in st.session_state:
#         st.session_state.bug_record = None
#     if "retrieved_bugs" not in st.session_state:
#         st.session_state.retrieved_bugs = []
#     if "root_cause_result" not in st.session_state:
#         st.session_state.root_cause_result = None
#     if "duplicate_result" not in st.session_state:
#         st.session_state.duplicate_result = []
#     if "remediation_result" not in st.session_state:
#         st.session_state.remediation_result = None

#     should_analyze = (
#         final_text != "" and
#         (final_text != st.session_state.last_analyzed_text or top_n != st.session_state.last_top_n)
#     )

#     if final_text == "":
#         st.info("Waiting for a bug report to be pasted or uploaded...")

#     elif should_analyze:
#         st.session_state.last_analyzed_text = final_text
#         st.session_state.last_top_n = top_n

#         bug_record = {
#             "bug_id": "BUG-" + str(uuid.uuid4())[:8],
#             "description": final_text,
#             "stack_trace": final_text,
#             "timestamp": datetime.now().isoformat(),
#             "source": "user_submission"
#         }
#         st.session_state.bug_record = bug_record

#         # --- Step 1: Triage + Log Analysis (save_submission deliberately NOT called yet) ---
#         with st.spinner("Running Triage and Log Analysis..."):
#             combined_result = run_orchestration(
#                 title=final_text[:80],
#                 description=final_text,
#                 stack_trace=final_text,
#                 bug_id=bug_record["bug_id"]
#             )
#             st.session_state.combined_result = combined_result

#         triage_result = combined_result["triage"]
#         log_result = combined_result["log_analysis"]

#         # --- Step 2: Retrieve similar historical bugs (Milestone 1 KB) ---
#         with st.spinner("Retrieving similar historical bugs..."):
#             try:
#                 retrieved_bugs = retrieve_similar_bugs(
#                     final_text, model, kb_embeddings, kb_metadata, top_n=top_n
#                 )
#             except Exception as e:
#                 retrieved_bugs = []
#                 st.session_state.retrieval_error = str(e)
#             st.session_state.retrieved_bugs = retrieved_bugs

#         # --- Step 3: Root Cause Agent ---
#         with st.spinner("Analyzing root cause..."):
#             try:
#                 root_cause_result = root_cause_agent(
#                     bug_id=bug_record["bug_id"],
#                     severity=triage_result["severity"],
#                     component=triage_result["component"],
#                     error_type=log_result["error_type"],
#                     failure_location=log_result["failure_location"],
#                     code_path=log_result["code_path"],
#                     retrieved_bugs=retrieved_bugs
#                 )
#             except Exception as e:
#                 root_cause_result = {
#                     "root_cause_hypothesis": "Root cause analysis could not be completed due to a system error.",
#                     "confidence": 0.0,
#                     "supporting_evidence": [],
#                     "error": str(e)
#                 }
#             st.session_state.root_cause_result = root_cause_result

#         # --- Step 4: Duplicate Detection Agent (SQLite still does NOT contain this bug yet) ---
#         with st.spinner("Checking for duplicate submissions..."):
#             try:
#                 duplicate_result = duplicate_detection_agent(
#                     new_description=final_text,
#                     error_type=log_result["error_type"],
#                     component=triage_result["component"],
#                     reasoning=log_result["reasoning"],
#                     model=model,
#                     top_n=top_n
#                 )
#             except Exception as e:
#                 duplicate_result = []
#                 st.session_state.duplicate_error = str(e)
#             st.session_state.duplicate_result = duplicate_result

#         # --- Step 5: Remediation Agent ---
#         with st.spinner("Generating fix recommendation..."):
#             try:
#                 remediation_result = remediation_agent(
#                     bug_id=bug_record["bug_id"],
#                     severity=triage_result["severity"],
#                     component=triage_result["component"],
#                     error_type=log_result["error_type"],
#                     failure_location=log_result["failure_location"],
#                     code_path=log_result["code_path"],
#                     description=final_text,
#                     root_cause=root_cause_result["root_cause_hypothesis"],
#                     historical_references=root_cause_result["supporting_evidence"],
#                     duplicate_bug=duplicate_result if duplicate_result else None
#                 )
#             except Exception as e:
#                 remediation_result = {
#                     "recommended_fix": "A fix recommendation could not be generated due to a system error.",
#                     "fix_steps": [], "code_example": {}, "validation_steps": [],
#                     "prevention": "", "confidence": 0.0,
#                     "reasoning": "Remediation agent failed.", "references_used": [],
#                     "error": str(e)
#                 }
#             st.session_state.remediation_result = remediation_result

#         # --- Step 6: NOW save to SQLite — after duplicate detection, so this bug can't match itself ---
#         with st.spinner("Saving submission..."):
#             simple_view_for_db = build_simple_view(combined_result)
#             save_submission(
#                 simple_view_for_db,
#                 bug_record["description"],
#                 bug_record["timestamp"],
#                 root_cause_hypothesis=root_cause_result["root_cause_hypothesis"],
#                 recommended_fix=remediation_result["recommended_fix"]
#             )

#     # --- Display results (uses whatever was last analyzed, from session_state) ---
#     if st.session_state.combined_result is not None:
#         bug_record = st.session_state.bug_record
#         combined_result = st.session_state.combined_result
#         simple_view = build_simple_view(combined_result)
#         retrieved_bugs = st.session_state.retrieved_bugs
#         root_cause_result = st.session_state.root_cause_result
#         duplicate_result = st.session_state.duplicate_result
#         remediation_result = st.session_state.remediation_result

#         st.success("Bug report received and analyzed")

#         st.subheader("Analysis Summary")

#         col1, col2, col3 = st.columns(3)
#         col1.metric("Severity", simple_view["severity"])
#         col2.metric("Priority", simple_view["priority"])
#         col3.metric("Component", simple_view["component"])

#         st.write(f"**Error Type:** {simple_view['error_type']}")
#         st.write(f"**Failure Location:** {simple_view['failure_location']}")

#         if root_cause_result:
#             hyp = root_cause_result['root_cause_hypothesis']
#             st.write(f"**Root Cause (summary):** {hyp[:150]}{'...' if len(hyp) > 150 else ''}")

#         if duplicate_result:
#             st.write(f"**Duplicates Found:** {len(duplicate_result)} similar past submission(s)")
#         else:
#             st.write("**Duplicates Found:** None — this appears to be a new issue")

#         if remediation_result:
#             fix = remediation_result['recommended_fix']
#             st.write(f"**Recommended Fix (summary):** {fix[:150]}{'...' if len(fix) > 150 else ''}")

#         if st.button("Show full details (all agents)", key="show_full_details"):
#             st.subheader("Full Combined Result (Triage + Log Analysis)")
#             st.json(combined_result)
#             st.subheader("Full Root Cause Result")
#             st.json(root_cause_result)
#             st.subheader("Full Duplicate Detection Result")
#             st.json(duplicate_result)
#             st.subheader("Full Remediation Result")
#             st.json(remediation_result)

#         st.divider()

        

#         st.subheader("Root Cause Analysis")
#         if root_cause_result:
#             confidence = root_cause_result.get("confidence", 0.0)
#             st.write(f"**Hypothesis:** {root_cause_result['root_cause_hypothesis']}")
#             st.write(f"**Confidence:** {confidence:.2f}")
#             if confidence < 0.6:
#                 st.warning("Limited historical evidence available — this is a best-guess hypothesis, not a confirmed cause.")
#             if root_cause_result.get("supporting_evidence"):
#                 st.write("**Supporting Evidence:**")
#                 for ev in root_cause_result["supporting_evidence"]:
#                     st.write(f"- `{ev['bug_id']}` — {ev['summary']}")
#             else:
#                 st.write("No supporting historical evidence was found for this hypothesis.")

#         st.divider()

#         st.subheader("Duplicate Bugs")
#         if duplicate_result:
#             for d in duplicate_result:
#                 st.write(f"**`{d['bug_id']}`** — {d['label'].upper()} match ({d['similarity']*100:.1f}% similar)")
#                 st.write(d["explanation"])
#                 st.write("---")
#         else:
#             st.info("No similar past submissions found — this appears to be a new issue.")

#         st.divider()

#         st.subheader("Recommended Fix")
#         if remediation_result:
#             st.write(f"**{remediation_result['recommended_fix']}**")
#             st.write(f"**Confidence:** {remediation_result.get('confidence', 0.0):.2f}")

#             if remediation_result.get("fix_steps"):
#                 st.write("**Fix Steps:**")
#                 for i, step in enumerate(remediation_result["fix_steps"], 1):
#                     st.write(f"{i}. {step}")

#             if remediation_result.get("code_example"):
#                 ce = remediation_result["code_example"]
#                 if ce.get("before") or ce.get("after"):
#                     col_before, col_after = st.columns(2)
#                     with col_before:
#                         st.write("**Before:**")
#                         st.code(ce.get("before", ""))
#                     with col_after:
#                         st.write("**After:**")
#                         st.code(ce.get("after", ""))

#             if remediation_result.get("validation_steps"):
#                 st.write("**Validation Steps:**")
#                 for step in remediation_result["validation_steps"]:
#                     st.write(f"- {step}")

#             if remediation_result.get("prevention"):
#                 st.write(f"**Prevention Tip:** {remediation_result['prevention']}")

#             if remediation_result.get("reasoning"):
#                 st.write(f"**Reasoning:** {remediation_result['reasoning']}")

#             if remediation_result.get("references_used"):
#                 st.write("**References Used:**")
#                 for ref in remediation_result["references_used"]:
#                     match_info = f" ({ref['match']}, {ref['similarity']*100:.0f}%)" if "match" in ref else ""
#                     st.write(f"- `{ref['bug_id']}`{match_info} — {ref.get('summary', '')}")
                
#             import streamlit as st
# import uuid
# from datetime import datetime
# import numpy as np
# import pandas as pd
# import os
# import sys
# from sentence_transformers import SentenceTransformer
# from sklearn.metrics.pairwise import cosine_similarity
# import sqlite3
# import plotly.express as px


# sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# from agents import (
#     run_orchestration, build_simple_view, init_db, save_submission,
#     retrieve_similar_bugs, root_cause_agent,
#     duplicate_detection_agent, remediation_agent,
#     COMPONENT_MERGE_MAP, compute_defect_analytics, cluster_root_causes,
#     add_resolved_bug_to_kb
# )

# init_db()

# st.markdown(
#     """
#     <style>
#     .stApp {
#         border: 8px solid #2E7D32;
#     }
#     </style>
#     """,
#     unsafe_allow_html=True
# )

# tab1, tab2 = st.tabs(["Submit Bug", "Analytics Dashboard"])

# with tab1:
#     # ... ALL of your existing app.py content from st.title() down to the final
#     # "Similar Past Bugs" section goes here, indented one level inside this block

#     st.title("Creation of Intelligent Bug Diagnosis Platform with Fix Recommendation Assistance ")
#     st.write("Paste your bug report or stack trace below - analysis runs automatically.")


#     @st.cache_resource
#     def load_retrieval_components():
#         base_dir = os.path.dirname(os.path.abspath(__file__))
#         model = SentenceTransformer('all-MiniLM-L6-v2')
#         embeddings = np.load(os.path.join(base_dir, "embeddings_real.npy"))
#         metadata = pd.read_csv(os.path.join(base_dir, "chunks_metadata.csv"))
#         return model, embeddings, metadata


#     model, kb_embeddings, kb_metadata = load_retrieval_components()

#     bug_report = st.text_area("Bug Report / Stack Trace", height=200, key="bug_report_input")
#     uploaded_file = st.file_uploader("Or upload a bug report file", type=["txt", "log"], key="bug_file_uploader")

#     top_n = st.slider(
#         "Number of similar bugs to retrieve (used for Root Cause and Duplicate Detection)",
#         min_value=3, max_value=15, value=5, key="top_n_slider"
#     )

#     final_text = ""
#     if uploaded_file is not None:
#         final_text = uploaded_file.read().decode("utf-8")
#     elif bug_report.strip() != "":
#         final_text = bug_report.strip()

#     if "last_analyzed_text" not in st.session_state:
#         st.session_state.last_analyzed_text = ""
#     if "last_top_n" not in st.session_state:
#         st.session_state.last_top_n = top_n
#     if "combined_result" not in st.session_state:
#         st.session_state.combined_result = None
#     if "bug_record" not in st.session_state:
#         st.session_state.bug_record = None
#     if "retrieved_bugs" not in st.session_state:
#         st.session_state.retrieved_bugs = []
#     if "root_cause_result" not in st.session_state:
#         st.session_state.root_cause_result = None
#     if "duplicate_result" not in st.session_state:
#         st.session_state.duplicate_result = []
#     if "remediation_result" not in st.session_state:
#         st.session_state.remediation_result = None

#     should_analyze = (
#         final_text != "" and
#         (final_text != st.session_state.last_analyzed_text or top_n != st.session_state.last_top_n)
#     )

#     if final_text == "":
#         st.info("Waiting for a bug report to be pasted or uploaded...")

#     elif should_analyze:
#         st.session_state.last_analyzed_text = final_text
#         st.session_state.last_top_n = top_n

#         bug_record = {
#             "bug_id": "BUG-" + str(uuid.uuid4())[:8],
#             "description": final_text,
#             "stack_trace": final_text,
#             "timestamp": datetime.now().isoformat(),
#             "source": "user_submission"
#         }
#         st.session_state.bug_record = bug_record

#         # --- Step 1: Triage + Log Analysis (save_submission deliberately NOT called yet) ---
#         with st.spinner("Running Triage and Log Analysis..."):
#             combined_result = run_orchestration(
#                 title=final_text[:80],
#                 description=final_text,
#                 stack_trace=final_text,
#                 bug_id=bug_record["bug_id"]
#             )
#             st.session_state.combined_result = combined_result

#         triage_result = combined_result["triage"]
#         log_result = combined_result["log_analysis"]

#         # --- Step 2: Retrieve similar historical bugs (Milestone 1 KB) ---
#         with st.spinner("Retrieving similar historical bugs..."):
#             try:
#                 retrieved_bugs = retrieve_similar_bugs(
#                     final_text, model, kb_embeddings, kb_metadata, top_n=top_n
#                 )
#             except Exception as e:
#                 retrieved_bugs = []
#                 st.session_state.retrieval_error = str(e)
#             st.session_state.retrieved_bugs = retrieved_bugs

#         # --- Step 3: Root Cause Agent ---
#         with st.spinner("Analyzing root cause..."):
#             try:
#                 root_cause_result = root_cause_agent(
#                     bug_id=bug_record["bug_id"],
#                     severity=triage_result["severity"],
#                     component=triage_result["component"],
#                     error_type=log_result["error_type"],
#                     failure_location=log_result["failure_location"],
#                     code_path=log_result["code_path"],
#                     retrieved_bugs=retrieved_bugs
#                 )
#             except Exception as e:
#                 root_cause_result = {
#                     "root_cause_hypothesis": "Root cause analysis could not be completed due to a system error.",
#                     "confidence": 0.0,
#                     "supporting_evidence": [],
#                     "error": str(e)
#                 }
#             st.session_state.root_cause_result = root_cause_result

#         # --- Step 4: Duplicate Detection Agent (SQLite still does NOT contain this bug yet) ---
#         with st.spinner("Checking for duplicate submissions..."):
#             try:
#                 duplicate_result = duplicate_detection_agent(
#                     new_description=final_text,
#                     error_type=log_result["error_type"],
#                     component=triage_result["component"],
#                     reasoning=log_result["reasoning"],
#                     model=model,
#                     top_n=top_n
#                 )
#             except Exception as e:
#                 duplicate_result = []
#                 st.session_state.duplicate_error = str(e)
#             st.session_state.duplicate_result = duplicate_result

#         # --- Step 5: Remediation Agent ---
#         with st.spinner("Generating fix recommendation..."):
#             try:
#                 remediation_result = remediation_agent(
#                     bug_id=bug_record["bug_id"],
#                     severity=triage_result["severity"],
#                     component=triage_result["component"],
#                     error_type=log_result["error_type"],
#                     failure_location=log_result["failure_location"],
#                     code_path=log_result["code_path"],
#                     description=final_text,
#                     root_cause=root_cause_result["root_cause_hypothesis"],
#                     historical_references=root_cause_result["supporting_evidence"],
#                     duplicate_bug=duplicate_result if duplicate_result else None
#                 )
#             except Exception as e:
#                 remediation_result = {
#                     "recommended_fix": "A fix recommendation could not be generated due to a system error.",
#                     "fix_steps": [], "code_example": {}, "validation_steps": [],
#                     "prevention": "", "confidence": 0.0,
#                     "reasoning": "Remediation agent failed.", "references_used": [],
#                     "error": str(e)
#                 }
#             st.session_state.remediation_result = remediation_result

#         # --- Step 6: NOW save to SQLite — after duplicate detection, so this bug can't match itself ---
#         with st.spinner("Saving submission..."):
#             simple_view_for_db = build_simple_view(combined_result)
#             save_submission(
#                 simple_view_for_db,
#                 bug_record["description"],
#                 bug_record["timestamp"],
#                 root_cause_hypothesis=root_cause_result["root_cause_hypothesis"],
#                 recommended_fix=remediation_result["recommended_fix"]
#             )

#     # --- Display results (uses whatever was last analyzed, from session_state) ---
#     if st.session_state.combined_result is not None:
#         bug_record = st.session_state.bug_record
#         combined_result = st.session_state.combined_result
#         simple_view = build_simple_view(combined_result)
#         retrieved_bugs = st.session_state.retrieved_bugs
#         root_cause_result = st.session_state.root_cause_result
#         duplicate_result = st.session_state.duplicate_result
#         remediation_result = st.session_state.remediation_result

#         st.success("Bug report received and analyzed")

#         st.subheader("Analysis Summary")

#         col1, col2, col3 = st.columns(3)
#         col1.metric("Severity", simple_view["severity"])
#         col2.metric("Priority", simple_view["priority"])
#         col3.metric("Component", simple_view["component"])

#         st.write(f"**Error Type:** {simple_view['error_type']}")
#         st.write(f"**Failure Location:** {simple_view['failure_location']}")

#         if root_cause_result:
#             hyp = root_cause_result['root_cause_hypothesis']
#             st.write(f"**Root Cause (summary):** {hyp[:150]}{'...' if len(hyp) > 150 else ''}")

#         if duplicate_result:
#             st.write(f"**Duplicates Found:** {len(duplicate_result)} similar past submission(s)")
#         else:
#             st.write("**Duplicates Found:** None — this appears to be a new issue")

#         if remediation_result:
#             fix = remediation_result['recommended_fix']
#             st.write(f"**Recommended Fix (summary):** {fix[:150]}{'...' if len(fix) > 150 else ''}")

#         if st.button("Show full details (all agents)", key="show_full_details"):
#             st.subheader("Full Combined Result (Triage + Log Analysis)")
#             st.json(combined_result)
#             st.subheader("Full Root Cause Result")
#             st.json(root_cause_result)
#             st.subheader("Full Duplicate Detection Result")
#             st.json(duplicate_result)
#             st.subheader("Full Remediation Result")
#             st.json(remediation_result)

#         st.divider()

        

#         st.subheader("Root Cause Analysis")
#         if root_cause_result:
#             confidence = root_cause_result.get("confidence", 0.0)
#             st.write(f"**Hypothesis:** {root_cause_result['root_cause_hypothesis']}")
#             st.write(f"**Confidence:** {confidence:.2f}")
#             if confidence < 0.6:
#                 st.warning("Limited historical evidence available — this is a best-guess hypothesis, not a confirmed cause.")
#             if root_cause_result.get("supporting_evidence"):
#                 st.write("**Supporting Evidence:**")
#                 for ev in root_cause_result["supporting_evidence"]:
#                     st.write(f"- `{ev['bug_id']}` — {ev['summary']}")
#             else:
#                 st.write("No supporting historical evidence was found for this hypothesis.")

#         st.divider()

#         st.subheader("Duplicate Bugs")
#         if duplicate_result:
#             for d in duplicate_result:
#                 st.write(f"**`{d['bug_id']}`** — {d['label'].upper()} match ({d['similarity']*100:.1f}% similar)")
#                 st.write(d["explanation"])
#                 st.write("---")
#         else:
#             st.info("No similar past submissions found — this appears to be a new issue.")

#         st.divider()

#         st.subheader("Recommended Fix")
#         if remediation_result:
#             st.write(f"**{remediation_result['recommended_fix']}**")
#             st.write(f"**Confidence:** {remediation_result.get('confidence', 0.0):.2f}")

#             if remediation_result.get("fix_steps"):
#                 st.write("**Fix Steps:**")
#                 for i, step in enumerate(remediation_result["fix_steps"], 1):
#                     st.write(f"{i}. {step}")

#             if remediation_result.get("code_example"):
#                 ce = remediation_result["code_example"]
#                 if ce.get("before") or ce.get("after"):
#                     col_before, col_after = st.columns(2)
#                     with col_before:
#                         st.write("**Before:**")
#                         st.code(ce.get("before", ""))
#                     with col_after:
#                         st.write("**After:**")
#                         st.code(ce.get("after", ""))

#             if remediation_result.get("validation_steps"):
#                 st.write("**Validation Steps:**")
#                 for step in remediation_result["validation_steps"]:
#                     st.write(f"- {step}")

#             if remediation_result.get("prevention"):
#                 st.write(f"**Prevention Tip:** {remediation_result['prevention']}")

#             if remediation_result.get("reasoning"):
#                 st.write(f"**Reasoning:** {remediation_result['reasoning']}")

#             if remediation_result.get("references_used"):
#                 st.write("**References Used:**")
#                 for ref in remediation_result["references_used"]:
#                     match_info = f" ({ref['match']}, {ref['similarity']*100:.0f}%)" if "match" in ref else ""
#                     st.write(f"- `{ref['bug_id']}`{match_info} — {ref.get('summary', '')}")
#             st.divider()

#             st.subheader("Confirm Fix Outcome")

#             current_bug_id = bug_record["bug_id"]
#             status_key = f"fix_status_{current_bug_id}"

#             if status_key not in st.session_state:
#                 st.session_state[status_key] = None

#             if st.session_state[status_key] is None:
#                 col_worked, col_not_worked = st.columns(2)

#                 with col_worked:
#                     if st.button("✅ Fix Worked", key=f"worked_{current_bug_id}"):
#                         try:
#                             add_resolved_bug_to_kb(
#                                 bug_id=current_bug_id,
#                                 description=bug_record["description"],
#                                 error_type=simple_view["error_type"],
#                                 severity=simple_view["severity"],
#                                 recommended_fix=remediation_result["recommended_fix"]
#                             )

#                             conn = sqlite3.connect(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "bug_submissions.db"))
#                             cursor = conn.cursor()
#                             cursor.execute("UPDATE bug_submissions SET status = ? WHERE bug_id = ?", ("resolved_added_to_kb", current_bug_id))
#                             conn.commit()
#                             conn.close()

#                             st.cache_resource.clear()

#                             st.session_state[status_key] = "resolved_added_to_kb"
#                             st.success("Marked as resolved — added to knowledge base for future recommendations.")
#                             st.rerun()

#                         except Exception as e:
#                             conn = sqlite3.connect(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "bug_submissions.db"))
#                             cursor = conn.cursor()
#                             cursor.execute("UPDATE bug_submissions SET status = ? WHERE bug_id = ?", ("resolved_kb_append_failed", current_bug_id))
#                             conn.commit()
#                             conn.close()

#                             st.session_state[status_key] = "resolved_kb_append_failed"
#                             st.error(f"Fix marked as resolved, but adding it to the knowledge base failed: {e}")
#                             st.rerun()

#                 with col_not_worked:
#                     if st.button("❌ Fix Did Not Work", key=f"notworked_{current_bug_id}"):
#                         conn = sqlite3.connect(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "bug_submissions.db"))
#                         cursor = conn.cursor()
#                         cursor.execute("UPDATE bug_submissions SET status = ? WHERE bug_id = ?", ("unresolved", current_bug_id))
#                         conn.commit()
#                         conn.close()

#                         st.session_state[status_key] = "unresolved"
#                         st.info("Marked as unresolved — not added to the knowledge base.")
#                         st.rerun()

#             else:
#                 status_display = {
#                     "resolved_added_to_kb": "✅ Resolved — added to knowledge base",
#                     "resolved_kb_append_failed": "⚠️ Resolved, but knowledge base update failed",
#                     "unresolved": "❌ Marked as unresolved"
#                 }
#                 st.write(f"**Status:** {status_display.get(st.session_state[status_key], st.session_state[status_key])}")
                    
#                             st.divider()

#                             st.subheader("Confirm Fix Outcome")

#                             current_bug_id = bug_record["bug_id"]
#                             status_key = f"fix_status_{current_bug_id}"

#                             if status_key not in st.session_state:
#                                 st.session_state[status_key] = None

#                             if st.session_state[status_key] is None:
#                                 col_worked, col_not_worked = st.columns(2)

#                                 with col_worked:
#                                     if st.button("✅ Fix Worked", key=f"worked_{current_bug_id}"):
#                                         try:
#                                             add_resolved_bug_to_kb(
#                                                 bug_id=current_bug_id,
#                                                 description=bug_record["description"],
#                                                 error_type=simple_view["error_type"],
#                                                 severity=simple_view["severity"],
#                                                 recommended_fix=remediation_result["recommended_fix"]
#                                             )

#                                             conn = sqlite3.connect(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "bug_submissions.db"))
#                                             cursor = conn.cursor()
#                                             cursor.execute("UPDATE bug_submissions SET status = ? WHERE bug_id = ?", ("resolved_added_to_kb", current_bug_id))
#                                             conn.commit()
#                                             conn.close()

#                                             st.cache_resource.clear()

#                                             st.session_state[status_key] = "resolved_added_to_kb"
#                                             st.success("Marked as resolved — added to knowledge base for future recommendations.")
#                                             st.rerun()

#                                         except Exception as e:
#                                             conn = sqlite3.connect(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "bug_submissions.db"))
#                                             cursor = conn.cursor()
#                                             cursor.execute("UPDATE bug_submissions SET status = ? WHERE bug_id = ?", ("resolved_kb_append_failed", current_bug_id))
#                                             conn.commit()
#                                             conn.close()

#                                             st.session_state[status_key] = "resolved_kb_append_failed"
#                                             st.error(f"Fix marked as resolved, but adding it to the knowledge base failed: {e}")
#                                             st.rerun()

#                                 with col_not_worked:
#                                     if st.button("❌ Fix Did Not Work", key=f"notworked_{current_bug_id}"):
#                                         conn = sqlite3.connect(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "bug_submissions.db"))
#                                         cursor = conn.cursor()
#                                         cursor.execute("UPDATE bug_submissions SET status = ? WHERE bug_id = ?", ("unresolved", current_bug_id))
#                                         conn.commit()
#                                         conn.close()

#                                         st.session_state[status_key] = "unresolved"
#                                         st.info("Marked as unresolved — not added to the knowledge base.")
#                                         st.rerun()

#                             else:
#                                 status_display = {
#                                     "resolved_added_to_kb": "✅ Resolved — added to knowledge base",
#                                     "resolved_kb_append_failed": "⚠️ Resolved, but knowledge base update failed",
#                                     "unresolved": "❌ Marked as unresolved"
#                                 }
#                                 st.write(f"**Status:** {status_display.get(st.session_state[status_key], st.session_state[status_key])}")


#         st.divider()

#         st.subheader("Submitted Bug Record")
#         st.json(bug_record)

#         st.subheader(f"Similar Past Bugs (Historical Knowledge Base, Top {top_n})")
#         if retrieved_bugs:
#             for rank, r in enumerate(retrieved_bugs, 1):
#                 st.write(f"**{rank}. {r['title']}**")
#                 st.write(f"Severity: {r['severity']} | Source: {r['source_dataset']} | Similarity: {r['similarity']:.2f}")
#                 st.write("---")
#         else:
#             st.info("No similar historical bugs were retrieved.")


# with tab2:
#     st.subheader("Defect Pattern Analytics")

#     if st.button("Refresh Analytics"):
#         conn = sqlite3.connect(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "bug_submissions.db"))
#         analytics_df = pd.read_sql("SELECT * FROM bug_submissions", conn)
#         conn.close()

#         analytics_df['component_normalized'] = analytics_df['component'].replace(COMPONENT_MERGE_MAP)

#         analytics_result = compute_defect_analytics(analytics_df)
#         st.session_state.analytics_result = analytics_result

#     if "analytics_result" in st.session_state:
#         result = st.session_state.analytics_result

#         # --- Top metrics ---
#         col1, col2, col3 = st.columns(3)
#         col1.metric("Total Submissions", result["total_submissions"])
#         col2.metric("Classified", result["classified_count"])
#         col3.metric("Unknown Rate", f"{result['unknown_rate']}%")
#         st.caption(
#             f"{result['classified_count']} of {result['total_submissions']} submissions were fully classified. "
#             f"{result['unknown_count']} had an unclassified component due to a pipeline/LLM extraction issue — "
#             f"excluded from component percentages, tracked here as a reliability metric."
#         )

#         st.divider()

#         # --- Severity pie chart ---
#         st.write("**Severity Breakdown**")
#         severity_df = pd.DataFrame(result["severity_breakdown"])
#         fig_severity = px.pie(severity_df, names="label", values="count", hover_data=["percent"])
#         st.plotly_chart(fig_severity, use_container_width=True)

#         st.divider()

#         # --- Component pie chart ---
#         st.write("**Component Breakdown** (classified submissions only)")
#         component_df = pd.DataFrame(result["component_breakdown"])
#         fig_component = px.pie(component_df, names="label", values="count", hover_data=["percent"])
#         st.plotly_chart(fig_component, use_container_width=True)

#         st.divider()

#         # --- Root cause clusters, expandable ---
#         st.write("**Root Cause Patterns** (semantic clustering)")
#         st.caption(
#     "Note: some entries may reflect compound submissions containing multiple distinct issues "
#     "in a single bug report (e.g. a test bug describing several unrelated errors at once), "
#     "rather than a true single-cause pattern."
#         )
#         for cluster in result["root_cause_breakdown"]:
#             with st.expander(f"{cluster['label']} — {cluster['count']} bugs ({cluster['percent']}%)"):
#                 if len(cluster["distinct_error_types"]) > 1:
#                     st.caption(f"Note: this cluster merges multiple error_type labels: {', '.join(cluster['distinct_error_types'])}")
#                 st.write("Bug IDs:", ", ".join(cluster["bug_ids"]))

#         st.divider()

#         # --- Submission activity ---
#         st.write("**Submission Activity**")
#         activity_df = pd.DataFrame(result["submission_activity"])
#         fig_activity = px.bar(activity_df, x="date", y="count")
#         st.plotly_chart(fig_activity, use_container_width=True)
#         st.caption(
#             "Reflects testing activity during development, not a real-world temporal defect pattern — "
#             "sample size and submission window are too small/compressed for genuine trend analysis."
#         )
#     else:
#         st.info("Click 'Refresh Analytics' to compute the current defect pattern analytics.")    
#         st.divider()

#         st.subheader("Submitted Bug Record")
#         st.json(bug_record)

#         st.subheader(f"Similar Past Bugs (Historical Knowledge Base, Top {top_n})")
#         if retrieved_bugs:
#             for rank, r in enumerate(retrieved_bugs, 1):
#                 st.write(f"**{rank}. {r['title']}**")
#                 st.write(f"Severity: {r['severity']} | Source: {r['source_dataset']} | Similarity: {r['similarity']:.2f}")
#                 st.write("---")
#         else:
#             st.info("No similar historical bugs were retrieved.")


# with tab2:
#     st.subheader("Defect Pattern Analytics")

#     if st.button("Refresh Analytics"):
#         conn = sqlite3.connect(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "bug_submissions.db"))
#         analytics_df = pd.read_sql("SELECT * FROM bug_submissions", conn)
#         conn.close()

#         analytics_df['component_normalized'] = analytics_df['component'].replace(COMPONENT_MERGE_MAP)

#         analytics_result = compute_defect_analytics(analytics_df)
#         st.session_state.analytics_result = analytics_result

#     if "analytics_result" in st.session_state:
#         result = st.session_state.analytics_result

#         # --- Top metrics ---
#         col1, col2, col3 = st.columns(3)
#         col1.metric("Total Submissions", result["total_submissions"])
#         col2.metric("Classified", result["classified_count"])
#         col3.metric("Unknown Rate", f"{result['unknown_rate']}%")
#         st.caption(
#             f"{result['classified_count']} of {result['total_submissions']} submissions were fully classified. "
#             f"{result['unknown_count']} had an unclassified component due to a pipeline/LLM extraction issue — "
#             f"excluded from component percentages, tracked here as a reliability metric."
#         )

#         st.divider()

#         # --- Severity pie chart ---
#         st.write("**Severity Breakdown**")
#         severity_df = pd.DataFrame(result["severity_breakdown"])
#         fig_severity = px.pie(severity_df, names="label", values="count", hover_data=["percent"])
#         st.plotly_chart(fig_severity, use_container_width=True)

#         st.divider()

#         # --- Component pie chart ---
#         st.write("**Component Breakdown** (classified submissions only)")
#         component_df = pd.DataFrame(result["component_breakdown"])
#         fig_component = px.pie(component_df, names="label", values="count", hover_data=["percent"])
#         st.plotly_chart(fig_component, use_container_width=True)

#         st.divider()

#         # --- Root cause clusters, expandable ---
#         st.write("**Root Cause Patterns** (semantic clustering)")
#         st.caption(
#     "Note: some entries may reflect compound submissions containing multiple distinct issues "
#     "in a single bug report (e.g. a test bug describing several unrelated errors at once), "
#     "rather than a true single-cause pattern."
#         )
#         for cluster in result["root_cause_breakdown"]:
#             with st.expander(f"{cluster['label']} — {cluster['count']} bugs ({cluster['percent']}%)"):
#                 if len(cluster["distinct_error_types"]) > 1:
#                     st.caption(f"Note: this cluster merges multiple error_type labels: {', '.join(cluster['distinct_error_types'])}")
#                 st.write("Bug IDs:", ", ".join(cluster["bug_ids"]))

#         st.divider()

#         # --- Submission activity ---
#         st.write("**Submission Activity**")
#         activity_df = pd.DataFrame(result["submission_activity"])
#         fig_activity = px.bar(activity_df, x="date", y="count")
#         st.plotly_chart(fig_activity, use_container_width=True)
#         st.caption(
#             "Reflects testing activity during development, not a real-world temporal defect pattern — "
#             "sample size and submission window are too small/compressed for genuine trend analysis."
#         )
#     else:
#         st.info("Click 'Refresh Analytics' to compute the current defect pattern analytics.")



import streamlit as st
import uuid
from datetime import datetime
import numpy as np
import pandas as pd
import os
import sys
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
import sqlite3
import plotly.express as px
from pathlib import Path

st.set_page_config(layout="wide")

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from agents import (
    run_orchestration, build_simple_view, init_db, save_submission,
    retrieve_similar_bugs, root_cause_agent,
    duplicate_detection_agent, remediation_agent,
    COMPONENT_MERGE_MAP, compute_defect_analytics, cluster_root_causes,
    add_resolved_bug_to_kb
)

from pathlib import Path

# Get the project root directory (one level up from src/)
PROJECT_ROOT = Path(__file__).resolve().parent.parent


init_db()

init_db()

# --- Developer Metadata Database Setup ---
DEV_DB_DIR = Path(__file__).resolve().parent / "data"
DEV_DB_DIR.mkdir(parents=True, exist_ok=True)
DEV_DB_PATH = DEV_DB_DIR / "Developer_Submission.db"

def init_developer_db():
    conn = sqlite3.connect(DEV_DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS Developer_Submission (
            submission_id INTEGER PRIMARY KEY AUTOINCREMENT,
            bug_id TEXT,
            project_name TEXT,
            reporter_name TEXT,
            developer_department TEXT,
            group_number TEXT,
            timestamp TEXT
        )
    """)
    conn.commit()
    conn.close()

init_developer_db()

st.markdown(
    """
    <style>
    /* 1. Header Bar Color */
    header[data-testid="stHeader"], .stAppHeader {
        background-color: #0F3040 !important;
    }
    
    /* 2. Global Background */
    .stApp {
        background-color: #0F3040 !important;
        color: #f1f5f9 !important;
    }

    /* 3. Sidebar Container */
    [data-testid="stSidebar"] {
        background-color: #09202c !important;
        border-right: 1px solid #1a4a60;
    }

    /* 4. Fix "Menu" Header Title Visibility */
    [data-testid="stSidebar"] [data-testid="stWidgetLabel"] p,
    [data-testid="stSidebar"] [data-testid="stWidgetLabel"] span {
        color: #38bdf8 !important;
        font-weight: 700 !important;
        font-size: 1.05rem !important;
        letter-spacing: 0.05em;
        margin-bottom: 8px;
    }

    /* 5. Uniform Size for All Navigation Buttons */
    [data-testid="stSidebar"] div[role="radiogroup"] {
        display: flex;
        flex-direction: column;
        gap: 10px;
        width: 100%;
    }
    [data-testid="stSidebar"] div[role="radiogroup"] > label {
        width: 100% !important;
        min-height: 52px !important;
        height: 52px !important;
        box-sizing: border-box !important;
        background: #0d2836;
        border: 1px solid #1a4a60;
        border-radius: 8px;
        padding: 0 16px !important;
        margin: 0 !important;
        color: #ffffff !important;
        font-weight: 600;
        font-size: 0.95rem;
        cursor: pointer;
        transition: all 0.2s ease;
        display: flex !important;
        align-items: center !important;
    }
    [data-testid="stSidebar"] div[role="radiogroup"] > label:hover {
        border-color: #38bdf8;
        background: #123648;
    }
    [data-testid="stSidebar"] div[role="radiogroup"] > label[data-checked="true"],
    [data-testid="stSidebar"] div[role="radiogroup"] > label:has(input:checked) {
        background: linear-gradient(135deg, #2563eb 0%, #3b82f6 100%) !important;
        border: 1px solid #60a5fa !important;
        color: #ffffff !important;
        box-shadow: 0 0 12px rgba(59, 130, 246, 0.45);
    }
    [data-testid="stSidebar"] div[role="radiogroup"] label p,
    [data-testid="stSidebar"] div[role="radiogroup"] label span {
        color: #ffffff !important;
        font-weight: 600 !important;
    }

    /* 6. Base Card Containers */
    [data-testid="stVerticalBlockBorderWrapper"] {
        background-color: #0a2533 !important;
        border: 1px solid #1b4b61 !important;
        border-radius: 10px;
    }

    /* 7. Dropdown / Selectbox Dark Styling (Filter by Month) */
    div[data-baseweb="select"] {
        background-color: #09202c !important;
        border: 1px solid #1b4b61 !important;
        border-radius: 8px !important;
    }
    div[data-baseweb="select"] * {
        background-color: transparent !important;
        color: #ffffff !important;
    }
    div[data-baseweb="popover"] ul {
        background-color: #09202c !important;
        border: 1px solid #1b4b61 !important;
    }

    /* 8. Badges (Bug ID, Verified, Filter Box) */
    .badge-bug-id {
        background: rgba(56, 189, 248, 0.15);
        color: #38bdf8;
        border: 1px solid rgba(56, 189, 248, 0.4);
        padding: 4px 10px;
        border-radius: 6px;
        font-weight: 700;
        font-size: 0.78rem;
        font-family: monospace;
    }
    .badge-verified-kb {
        background: rgba(34, 197, 94, 0.15);
        color: #4ade80;
        border: 1px solid rgba(34, 197, 94, 0.5);
        padding: 4px 12px;
        border-radius: 20px;
        font-weight: 600;
        font-size: 0.75rem;
        display: inline-flex;
        align-items: center;
        gap: 4px;
    }
    .badge-pending {
        background: rgba(245, 158, 11, 0.15);
        color: #fbbf24;
        border: 1px solid rgba(245, 158, 11, 0.5);
        padding: 4px 12px;
        border-radius: 20px;
        font-weight: 600;
        font-size: 0.75rem;
    }
    .badge-unresolved {
        background: rgba(239, 68, 68, 0.15);
        color: #f87171;
        border: 1px solid rgba(239, 68, 68, 0.5);
        padding: 4px 12px;
        border-radius: 20px;
        font-weight: 600;
        font-size: 0.75rem;
    }
    .badge-filter-box {
        background: rgba(56, 189, 248, 0.12);
        color: #38bdf8;
        border: 1px solid rgba(56, 189, 248, 0.35);
        padding: 4px 10px;
        border-radius: 6px;
        font-weight: 600;
        font-size: 0.8rem;
        display: inline-block;
        margin-bottom: 6px;
    }
    /* --- Style the Text Area --- */
    .stTextArea textarea {
        background-color: #2dd4bf !important;
        border: 1px solid #1b4b61 !important;
        color: #e2e8f0 !important;
        border-radius: 8px !important;
        font-family: 'Consolas', 'Courier New', monospace !important;
        font-size: 0.88rem !important;
    }
    .stTextArea textarea:focus {
        border-color: #f8fafc !important;
        box-shadow: 0 0 8px rgba(56, 189, 248, 0.3) !important;
    }
    /* Metric Upper Labels (Severity, Priority, Component) */
    [data-testid="stMetricLabel"] p, 
    [data-testid="stMetricLabel"] span {
        color: #D1D5DB !important;  /* Light Gray */
        font-weight: 600 !important;
    }

    /* Metric Big Values (Low, Interpreter, etc.) */
    [data-testid="stMetricValue"] div {
        color: #4ADE80 !important;  /* Soft Mint Green */
        font-weight: 700 !important;
    }
    </style>
    """,
    unsafe_allow_html=True
)


page = st.sidebar.radio("Creation of Intelligent 🐞 Diagnosis Platform with Fix Recommendation Assistance", ["🏠 Dashboard","1️⃣Submit Bug", "2️⃣Analytics Dashboard","🧠Knowledge Base","3️⃣About The App","📚User Guide"])

if page == "1️⃣Submit Bug":
    st.title(" Submit Defect logs")
    st.markdown('<span class="badge-filter-box">Paste your bug report or stack trace below - analysis runs automatically.</span>', unsafe_allow_html=True)

    @st.cache_resource
    def load_retrieval_components():
        base_dir = os.path.dirname(os.path.abspath(__file__))
        model = SentenceTransformer('all-MiniLM-L6-v2')
        embeddings = np.load(
    os.path.join(base_dir, "embeddings_real.npy"),
    allow_pickle=True
)
        metadata = pd.read_csv(os.path.join(base_dir, "chunks_metadata.csv"))
        return model, embeddings, metadata

    model, kb_embeddings, kb_metadata = load_retrieval_components()

    # --- SIDE-BY-SIDE: Intake (Left) + Metadata Context (Right) ---
    col_intake, col_meta = st.columns([1.6, 1.1])

    with col_intake:
        with st.container(border=True):
            st.markdown('<span class="badge-filter-box">📝 Bug Report / Stack Trace</span>', unsafe_allow_html=True)
            bug_report = st.text_area(
                "Bug Report / Stack Trace",
                height=180,
                key="bug_report_input",
                placeholder="Paste code trace logs, compile exception lines, or runtime errors here...",
                label_visibility="collapsed"
            )

            st.markdown('<span class="badge-filter-box">📂 Or Upload a Bug Report File (.txt, .log)</span>', unsafe_allow_html=True)
            uploaded_file = st.file_uploader(
                "Or upload a bug report file",
                type=["txt", "log"],
                key="bug_file_uploader",
                label_visibility="collapsed"
            )

            st.markdown('<span class="badge-filter-box">🎯 Similar Bugs Retrieval Depth</span>', unsafe_allow_html=True)
            top_n = st.slider(
                "Number of similar bugs to retrieve",
                min_value=3,
                max_value=15,
                value=5,
                key="top_n_slider",
                label_visibility="collapsed"
            )

    with col_meta:
        with st.container(border=True):
            st.markdown("##### 📌 METADATA CONTEXT")
            
            st.caption("Project Name")
            project_name = st.text_input(
                "Project Name", 
                value="AI Smart Bug Analyzer", 
                key="meta_proj_name", 
                label_visibility="collapsed"
            )
            
            st.caption("Reporter Name *")
            reporter_name = st.text_input(
                "Reporter Name", 
                value="Developer", 
                key="meta_rep_name", 
                label_visibility="collapsed"
            )
            
            st.caption("Developer Department")
            dev_dept = st.selectbox(
                "Developer Department",
                ["Backend Core API", "Frontend UI", "Py coder", "DevOps / Infra", "QA & Testing", "Database / Data Eng"],
                key="meta_dev_dept",
                label_visibility="collapsed"
            )
            
            st.caption("Group Number")
            group_num = st.selectbox(
                "Group Number",
                ["Group 1", "Group 2", "Group 3", "Group 4", "Group 5"],
                key="meta_group_num",
                label_visibility="collapsed"
            )

    # --- File/Text Input Parsing ---
    final_text = ""
    if uploaded_file is not None:
        final_text = uploaded_file.read().decode("utf-8")
    elif bug_report.strip() != "":
        final_text = bug_report.strip()

    if "last_analyzed_text" not in st.session_state:
        st.session_state.last_analyzed_text = ""
    if "last_top_n" not in st.session_state:
        st.session_state.last_top_n = top_n
    if "combined_result" not in st.session_state:
        st.session_state.combined_result = None
    if "bug_record" not in st.session_state:
        st.session_state.bug_record = None
    if "retrieved_bugs" not in st.session_state:
        st.session_state.retrieved_bugs = []
    if "root_cause_result" not in st.session_state:
        st.session_state.root_cause_result = None
    if "duplicate_result" not in st.session_state:
        st.session_state.duplicate_result = []
    if "remediation_result" not in st.session_state:
        st.session_state.remediation_result = None

    should_analyze = (
        final_text != "" and
        (final_text != st.session_state.last_analyzed_text or top_n != st.session_state.last_top_n)
    )

    if final_text == "":
        st.info("Waiting for a bug report to be pasted or uploaded...")

    elif should_analyze:
        st.session_state.last_analyzed_text = final_text
        st.session_state.last_top_n = top_n

        bug_record = {
            "bug_id": "BUG-" + str(uuid.uuid4())[:8],
            "description": final_text,
            "stack_trace": final_text,
            "timestamp": datetime.now().isoformat(),
            "source": "user_submission"
        }
        st.session_state.bug_record = bug_record

        # --- Step 1: Triage + Log Analysis ---
        with st.spinner("Running Triage and Log Analysis..."):
            combined_result = run_orchestration(
                title=final_text[:80],
                description=final_text,
                stack_trace=final_text,
                bug_id=bug_record["bug_id"]
            )
            st.session_state.combined_result = combined_result

        triage_result = combined_result["triage"]
        log_result = combined_result["log_analysis"]

        # --- Step 2: Retrieve similar historical bugs ---
        with st.spinner("Retrieving similar historical bugs..."):
            try:
                retrieved_bugs = retrieve_similar_bugs(
                    final_text, model, kb_embeddings, kb_metadata, top_n=top_n
                )
            except Exception as e:
                retrieved_bugs = []
                st.session_state.retrieval_error = str(e)
            st.session_state.retrieved_bugs = retrieved_bugs

        # --- Step 3: Root Cause Agent ---
        with st.spinner("Analyzing root cause..."):
            try:
                root_cause_result = root_cause_agent(
                    bug_id=bug_record["bug_id"],
                    severity=triage_result["severity"],
                    component=triage_result["component"],
                    error_type=log_result["error_type"],
                    failure_location=log_result["failure_location"],
                    code_path=log_result["code_path"],
                    retrieved_bugs=retrieved_bugs
                )
            except Exception as e:
                root_cause_result = {
                    "root_cause_hypothesis": "Root cause analysis could not be completed due to a system error.",
                    "confidence": 0.0,
                    "supporting_evidence": [],
                    "error": str(e)
                }
            st.session_state.root_cause_result = root_cause_result

        # --- Step 4: Duplicate Detection Agent ---
        with st.spinner("Checking for duplicate submissions..."):
            try:
                duplicate_result = duplicate_detection_agent(
                    new_description=final_text,
                    error_type=log_result["error_type"],
                    component=triage_result["component"],
                    reasoning=log_result["reasoning"],
                    model=model,
                    top_n=top_n
                )
            except Exception as e:
                duplicate_result = []
                st.session_state.duplicate_error = str(e)
            st.session_state.duplicate_result = duplicate_result

        # --- Step 5: Remediation Agent ---
        with st.spinner("Generating fix recommendation..."):
            try:
                remediation_result = remediation_agent(
                    bug_id=bug_record["bug_id"],
                    severity=triage_result["severity"],
                    component=triage_result["component"],
                    error_type=log_result["error_type"],
                    failure_location=log_result["failure_location"],
                    code_path=log_result["code_path"],
                    description=final_text,
                    root_cause=root_cause_result["root_cause_hypothesis"],
                    historical_references=root_cause_result["supporting_evidence"],
                    duplicate_bug=duplicate_result if duplicate_result else None
                )
            except Exception as e:
                remediation_result = {
                    "recommended_fix": "A fix recommendation could not be generated due to a system error.",
                    "fix_steps": [], "code_example": {}, "validation_steps": [],
                    "prevention": "", "confidence": 0.0,
                    "reasoning": "Remediation agent failed.", "references_used": [],
                    "error": str(e)
                }
            st.session_state.remediation_result = remediation_result

        # --- Step 6: Save to SQLite (both bug_submissions.db AND Developer_Submission.db) ---
        with st.spinner("Saving submission..."):
            simple_view_for_db = build_simple_view(combined_result)
            save_submission(
                simple_view_for_db,
                bug_record["description"],
                bug_record["timestamp"],
                root_cause_hypothesis=root_cause_result["root_cause_hypothesis"],
                recommended_fix=remediation_result["recommended_fix"]
            )
            
            # Auto-save Developer Metadata to Developer_Submission.db
            try:
                conn = sqlite3.connect(DEV_DB_PATH)
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO Developer_Submission 
                    (bug_id, project_name, reporter_name, developer_department, group_number, timestamp)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (bug_record["bug_id"], project_name, reporter_name, dev_dept, group_num, bug_record["timestamp"]))
                conn.commit()
                conn.close()
            except Exception as e:
                st.warning(f"Could not log metadata context: {e}")

    # --- Display results (uses whatever was last analyzed, from session_state) ---
    if st.session_state.combined_result is not None:
        bug_record = st.session_state.bug_record
        combined_result = st.session_state.combined_result
        simple_view = build_simple_view(combined_result)
        retrieved_bugs = st.session_state.retrieved_bugs
        root_cause_result = st.session_state.root_cause_result
        duplicate_result = st.session_state.duplicate_result
        remediation_result = st.session_state.remediation_result

        st.success("Bug report received and analyzed")

        st.subheader("Analysis Summary")

        col1, col2, col3 = st.columns(3)
        col1.metric("Severity", simple_view["severity"])
        col2.metric("Priority", simple_view["priority"])
        col3.metric("Component", simple_view["component"])

        st.write(f"**Error Type:** {simple_view['error_type']}")
        st.write(f"**Failure Location:** {simple_view['failure_location']}")

        if root_cause_result:
            hyp = root_cause_result['root_cause_hypothesis']
            st.write(f"**Root Cause (summary):** {hyp[:150]}{'...' if len(hyp) > 150 else ''}")

        if duplicate_result:
            st.write(f"**Duplicates Found:** {len(duplicate_result)} similar past submission(s)")
        else:
            st.write("**Duplicates Found:** None — this appears to be a new issue")

        if remediation_result:
            fix = remediation_result['recommended_fix']
            st.write(f"**Recommended Fix (summary):** {fix[:150]}{'...' if len(fix) > 150 else ''}")

        if st.button("Show full details (all agents)", key="show_full_details"):
            st.subheader("Full Combined Result (Triage + Log Analysis)")
            st.json(combined_result)
            st.subheader("Full Root Cause Result")
            st.json(root_cause_result)
            st.subheader("Full Duplicate Detection Result")
            st.json(duplicate_result)
            st.subheader("Full Remediation Result")
            st.json(remediation_result)

        st.divider()

        st.subheader("Root Cause Analysis")
        if root_cause_result:
            confidence = root_cause_result.get("confidence", 0.0)
            st.write(f"**Hypothesis:** {root_cause_result['root_cause_hypothesis']}")
            st.write(f"**Confidence:** {confidence:.2f}")
            if confidence < 0.6:
                st.warning("Limited historical evidence available — this is a best-guess hypothesis, not a confirmed cause.")
            if root_cause_result.get("supporting_evidence"):
                st.write("**Supporting Evidence:**")
                for ev in root_cause_result["supporting_evidence"]:
                    st.write(f"- `{ev['bug_id']}` — {ev['summary']}")
            else:
                st.write("No supporting historical evidence was found for this hypothesis.")

        st.divider()

        st.subheader("Duplicate Bugs")
        if duplicate_result:
            for d in duplicate_result:
                st.write(f"**`{d['bug_id']}`** — {d['label'].upper()} match ({d['similarity']*100:.1f}% similar)")
                st.write(d["explanation"])
                st.write("---")
        else:
            st.info("No similar past submissions found — this appears to be a new issue.")

        st.divider()

        st.subheader("Recommended Fix")
        if remediation_result:
            st.write(f"**{remediation_result['recommended_fix']}**")
            st.write(f"**Confidence:** {remediation_result.get('confidence', 0.0):.2f}")

            if remediation_result.get("fix_steps"):
                st.write("**Fix Steps:**")
                for i, step in enumerate(remediation_result["fix_steps"], 1):
                    st.write(f"{i}. {step}")

            if remediation_result.get("code_example"):
                ce = remediation_result["code_example"]
                if ce.get("before") or ce.get("after"):
                    col_before, col_after = st.columns(2)
                    with col_before:
                        st.write("**Before:**")
                        st.code(ce.get("before", ""))
                    with col_after:
                        st.write("**After:**")
                        st.code(ce.get("after", ""))

            if remediation_result.get("validation_steps"):
                st.write("**Validation Steps:**")
                for step in remediation_result["validation_steps"]:
                    st.write(f"- {step}")

            if remediation_result.get("prevention"):
                st.write(f"**Prevention Tip:** {remediation_result['prevention']}")

            if remediation_result.get("reasoning"):
                st.write(f"**Reasoning:** {remediation_result['reasoning']}")

            if remediation_result.get("references_used"):
                st.write("**References Used:**")
                for ref in remediation_result["references_used"]:
                    match_info = f" ({ref['match']}, {ref['similarity']*100:.0f}%)" if "match" in ref else ""
                    st.write(f"- `{ref['bug_id']}`{match_info} — {ref.get('summary', '')}")

            # --- Confirm Fix Outcome (KB growth mechanism) ---
            # This sits at the same level as the "references_used" check above,
            # both as direct children of "if remediation_result:" — so it always
            # renders regardless of whether references_used happened to be empty.
            st.divider()

            st.subheader("Confirm Fix Outcome")

            current_bug_id = bug_record["bug_id"]
            status_key = f"fix_status_{current_bug_id}"

            if status_key not in st.session_state:
                st.session_state[status_key] = None

            if st.session_state[status_key] is None:
                col_worked, col_not_worked = st.columns(2)

                with col_worked:
                    if st.button("✅ Fix Worked", key=f"worked_{current_bug_id}"):
                        db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "bug_submissions.db")
                        try:
                            add_resolved_bug_to_kb(
                                bug_id=current_bug_id,
                                description=bug_record["description"],
                                error_type=simple_view["error_type"],
                                severity=simple_view["severity"],
                                recommended_fix=remediation_result["recommended_fix"]
                            )

                            conn = sqlite3.connect(db_path)
                            cursor = conn.cursor()
                            cursor.execute("UPDATE bug_submissions SET status = ? WHERE bug_id = ?", ("resolved_added_to_kb", current_bug_id))
                            conn.commit()
                            conn.close()

                            st.cache_resource.clear()

                            st.session_state[status_key] = "resolved_added_to_kb"
                            st.success("Marked as resolved — added to knowledge base for future recommendations.")
                            st.rerun()

                        except Exception as e:
                            conn = sqlite3.connect(db_path)
                            cursor = conn.cursor()
                            cursor.execute("UPDATE bug_submissions SET status = ? WHERE bug_id = ?", ("resolved_kb_append_failed", current_bug_id))
                            conn.commit()
                            conn.close()

                            st.session_state[status_key] = "resolved_kb_append_failed"
                            st.error(f"Fix marked as resolved, but adding it to the knowledge base failed: {e}")
                            st.rerun()

                with col_not_worked:
                    if st.button("❌ Fix Did Not Work", key=f"notworked_{current_bug_id}"):
                        db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "bug_submissions.db")
                        conn = sqlite3.connect(db_path)
                        cursor = conn.cursor()
                        cursor.execute("UPDATE bug_submissions SET status = ? WHERE bug_id = ?", ("unresolved", current_bug_id))
                        conn.commit()
                        conn.close()

                        st.session_state[status_key] = "unresolved"
                        st.info("Marked as unresolved — not added to the knowledge base.")
                        st.rerun()

            else:
                status_display = {
                    "resolved_added_to_kb": "✅ Resolved — added to knowledge base",
                    "resolved_kb_append_failed": "⚠️ Resolved, but knowledge base update failed",
                    "unresolved": "❌ Marked as unresolved"
                }
                st.write(f"**Status:** {status_display.get(st.session_state[status_key], st.session_state[status_key])}")

        st.divider()

        st.subheader("Submitted Bug Record")
        st.json(bug_record)

        st.subheader(f"Similar Past Bugs (Historical Knowledge Base, Top {top_n})")
        if retrieved_bugs:
            for rank, r in enumerate(retrieved_bugs, 1):
                st.write(f"**{rank}. {r['title']}**")
                st.write(f"Severity: {r['severity']} | Source: {r['source_dataset']} | Similarity: {r['similarity']:.2f}")
                st.write("---")
        else:
            st.info("No similar historical bugs were retrieved.")


elif page == "2️⃣Analytics Dashboard":
    st.subheader("Defect Pattern Analytics")

    if st.button("🔄 Refresh Analytics", key="refresh_analytics_btn"):
        db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "bug_submissions.db")
        conn = sqlite3.connect(db_path)
        analytics_df = pd.read_sql("SELECT * FROM bug_submissions", conn)
        conn.close()

        analytics_df['component_normalized'] = analytics_df['component'].replace(COMPONENT_MERGE_MAP)
        analytics_result = compute_defect_analytics(analytics_df)
        st.session_state.analytics_result = analytics_result

    if "analytics_result" in st.session_state:
        result = st.session_state.analytics_result

        # --- Dynamic Data Extraction for Top 1 Metrics ---
        top_sev_label, top_sev_pct = "N/A", "0%"
        if result.get("severity_breakdown") and len(result["severity_breakdown"]) > 0:
            sorted_sev = sorted(result["severity_breakdown"], key=lambda x: x["count"], reverse=True)
            top_sev_label = sorted_sev[0]["label"]
            top_sev_pct = f"{sorted_sev[0]['percent']}%"

        top_comp_label, top_comp_pct = "N/A", "0%"
        if result.get("component_breakdown") and len(result["component_breakdown"]) > 0:
            sorted_comp = sorted(result["component_breakdown"], key=lambda x: x["count"], reverse=True)
            top_comp_label = sorted_comp[0]["label"]
            top_comp_pct = f"{sorted_comp[0]['percent']}%"

        top_rc_label, top_rc_count = "N/A", "0 bugs"
        if result.get("root_cause_breakdown") and len(result["root_cause_breakdown"]) > 0:
            top_rc = result["root_cause_breakdown"][0]
            top_rc_label = top_rc["label"]
            top_rc_count = f"{top_rc['count']} bugs ({top_rc['percent']}%)"

        # --- 1. Top Analytics Metric Ribbon (5 Columns with Emojis) ---
        m1, m2, m3, m4, m5 = st.columns(5)
        
        with m1:
            with st.container(border=True):
                st.caption("📊 TOTAL SUBMISSIONS")
                st.markdown(f"<h3 style='margin:0; color:#38bdf8;'>📁 {result['total_submissions']}</h3>", unsafe_allow_html=True)
                st.caption("Aggregated DB Entries")

        with m2:
            with st.container(border=True):
                st.caption("✅ CLASSIFIED")
                st.markdown(f"<h3 style='margin:0; color:#4ade80;'>🛡️ {result['classified_count']}</h3>", unsafe_allow_html=True)
                st.caption("Fully Categorized")

        with m3:
            with st.container(border=True):
                st.caption("⚠️ UNKNOWN RATE")
                st.markdown(f"<h3 style='margin:0; color:#fbbf24;'>⚡ {result['unknown_rate']}%</h3>", unsafe_allow_html=True)
                st.caption("Extraction Fallback")

        with m4:
            with st.container(border=True):
                st.caption("🧩 TOP COMPONENT")
                st.markdown(f"<h3 style='margin:0; color:#67e8f9; font-size: 1.25rem;'>⚙️ {top_comp_label}</h3>", unsafe_allow_html=True)
                st.caption(f"Volume Share: {top_comp_pct}")

        with m5:
            with st.container(border=True):
                st.caption("🚨 TOP SEVERITY")
                st.markdown(f"<h3 style='margin:0; color:#f87171; font-size: 1.25rem;'>🔥 {top_sev_label}</h3>", unsafe_allow_html=True)
                st.caption(f"Dominant: {top_sev_pct}")

        st.caption(
            f"{result['classified_count']} of {result['total_submissions']} submissions were fully classified. "
            f"{result['unknown_count']} had an unclassified component due to a pipeline/LLM extraction issue."
        )

        st.divider()

        # --- 2. Side-by-Side Breakdown Charts with Pink & Bright High-Contrast Text ---
        c_sev, c_comp = st.columns([3, 3])

        with c_sev:
            with st.container(border=True):
                st.markdown("##### 🎯 Severity Breakdown")
                severity_df = pd.DataFrame(result["severity_breakdown"])
                if not severity_df.empty:
                    fig_severity = px.pie(
                        severity_df, 
                        names="label", 
                        values="count", 
                        hover_data=["percent"],
                        hole=0.45,
                        color_discrete_sequence=['#3b82f6', '#ef4444', '#f59e0b', '#10b981']
                    )
                    fig_severity.update_layout(
                        paper_bgcolor='rgba(0,0,0,0)',
                        plot_bgcolor='rgba(0,0,0,0)',
                        font=dict(color='#f472b6', size=12), # Vibrant pink text for clear visibility
                        legend=dict(font=dict(color='#f472b6', size=11)),
                        margin=dict(t=20, b=20, l=10, r=10),
                        height=360
                    )
                    st.plotly_chart(fig_severity, use_container_width=True)
                else:
                    st.info("No severity records available.")

        with c_comp:
            with st.container(border=True):
                st.markdown("##### 🧩 Component Breakdown")
                component_df = pd.DataFrame(result["component_breakdown"])
                if not component_df.empty:
                    fig_component = px.pie(
                        component_df, 
                        names="label", 
                        values="count", 
                        hover_data=["percent"],
                        hole=0.45,
                        color_discrete_sequence=px.colors.qualitative.Bold
                    )
                    fig_component.update_layout(
                        paper_bgcolor='rgba(0,0,0,0)',
                        plot_bgcolor='rgba(0,0,0,0)',
                        font=dict(color='#ff79c6', size=11), # High-contrast Pink Legend & Labels
                        legend=dict(font=dict(color='#ff79c6', size=11)),
                        margin=dict(t=20, b=20, l=10, r=10),
                        height=360
                    )
                    st.plotly_chart(fig_component, use_container_width=True)
                else:
                    st.info("No component records available.")

        st.divider()

        # --- 3. Root Cause Patterns & Fix Mitigations (Equal Height with Badges) ---
        col_rc, col_fixes = st.columns([1.1, 1.0])

        with col_rc:
            with st.container(border=True, height=430):
                st.markdown("##### 🧬 Root Cause Patterns (Semantic Clustering)")
                st.info(f"**Dominant Root Cause:** {top_rc_label} ({top_rc_count})")
                st.caption("Note: compound submissions may describe several unrelated errors in one report.")
                
                for cluster in result["root_cause_breakdown"]:
                    with st.expander(f"{cluster['label']} — {cluster['count']} bugs ({cluster['percent']}%)"):
                        if len(cluster["distinct_error_types"]) > 1:
                            st.caption(f"Merges error types: {', '.join(cluster['distinct_error_types'])}")
                        st.write("**Bug IDs:**", ", ".join(cluster["bug_ids"]))

        with col_fixes:
            with st.container(border=True, height=430):
                rf_top_col, rf_slide_col = st.columns([1.8, 1.2])
                with rf_top_col:
                    st.markdown("##### 💡 Fix Recommendations")
                with rf_slide_col:
                    limit_fixes = st.slider("Count", min_value=2, max_value=8, value=3, key="limit_fixes_slider")

                db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "bug_submissions.db")
                conn = sqlite3.connect(db_path)
                recent_fixes_df = pd.read_sql(
                    f"SELECT bug_id, recommended_fix, root_cause_hypothesis, status, timestamp FROM bug_submissions WHERE recommended_fix IS NOT NULL AND recommended_fix != '' ORDER BY timestamp DESC LIMIT {limit_fixes}", 
                    conn
                )
                conn.close()

                if not recent_fixes_df.empty:
                    for _, row in recent_fixes_df.iterrows():
                        with st.container(border=True):
                            # Styled Bug ID & Status Pills (No white background)
                            ts = row['timestamp'][:10] if row['timestamp'] else ''
                            status_val = row['status'] or 'pending'
                            
                            if status_val == 'resolved_added_to_kb':
                                badge_html = '<span class="badge-verified-kb">🛡️ Verified in Vector DB</span>'
                            elif 'failed' in status_val or status_val == 'unresolved':
                                badge_html = '<span class="badge-unresolved">⚠️ Unresolved</span>'
                            else:
                                badge_html = '<span class="badge-pending">⏳ Pending Review</span>'
                                
                            st.markdown(
                                f"""
                                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                                    <span class="badge-bug-id">🐞 {row['bug_id']} <span style="opacity:0.6; font-weight: normal;">| {ts}</span></span>
                                    {badge_html}
                                </div>
                                """, 
                                unsafe_allow_html=True
                            )
                            
                            fix_preview = row['recommended_fix']
                            if len(fix_preview) > 130:
                                fix_preview = fix_preview[:130] + "..."
                            st.write(f"**Fix:** {fix_preview}")
                else:
                    st.info("No recent remediation fixes found in the database.")

        st.divider()

       # --- 4. Monthly Activity Chart with Styled Filter Box ---
        with st.container(border=True):
            chart_head_col, chart_filter_col = st.columns([2.6, 1.4])
            
            with chart_head_col:
                st.markdown("##### 📈 Monthly Bug Submissions Velocity")
                st.caption("Defect submission frequency timeline across dates.")

            activity_df = pd.DataFrame(result["submission_activity"])
            
            if not activity_df.empty:
                activity_df['date_str'] = activity_df['date'].astype(str)
                
                def extract_month(d_val):
                    try:
                        return pd.to_datetime(d_val).strftime('%Y-%m')
                    except Exception:
                        return str(d_val)[:7]

                activity_df['month'] = activity_df['date'].apply(extract_month)
                available_months = ["All Months"] + sorted(activity_df['month'].unique().tolist(), reverse=True)

                with chart_filter_col:
                    st.markdown('<span class="badge-filter-box">📅 Filter by Month</span>', unsafe_allow_html=True)
                    selected_month = st.selectbox(
                        "Select Month", 
                        options=available_months, 
                        index=0, 
                        key="analytics_month_filter",
                        label_visibility="collapsed"
                    )

                if selected_month != "All Months":
                    filtered_activity_df = activity_df[activity_df['month'] == selected_month]
                else:
                    filtered_activity_df = activity_df

                if not filtered_activity_df.empty:
                    fig_activity = px.bar(
                        filtered_activity_df, 
                        x="date", 
                        y="count",
                        text="count",
                        color_discrete_sequence=['#38bdf8']
                    )
                    fig_activity.update_traces(textposition='outside', textfont=dict(color='#ffffff'))
                    fig_activity.update_layout(
                        paper_bgcolor='rgba(0,0,0,0)',
                        plot_bgcolor='rgba(0,0,0,0)',
                        font=dict(color='#ff79c6'),
                        margin=dict(t=30, b=20, l=10, r=10),
                        height=300,
                        xaxis=dict(gridcolor='#1b4b61', title=dict(text="Date", font=dict(color="#ffffff")), tickfont=dict(color="#e2e8f0")),
                        yaxis=dict(gridcolor='#1b4b61', title=dict(text="Defect Count", font=dict(color="#ffffff")), tickfont=dict(color="#e2e8f0"))
                    )
                    st.plotly_chart(fig_activity, use_container_width=True)
                else:
                    st.warning(f"No submission activity logged for {selected_month}.")
            else:
                st.info("No activity logs available.")

    else:
        st.info("Click 'Refresh Analytics' to compute the current defect pattern analytics.")




elif page == "3️⃣About The App":
    st.title("About the App")
    md_path = PROJECT_ROOT / "README.md"
    if md_path.exists():
        st.markdown(md_path.read_text(encoding="utf-8"))
    else:
        st.warning("`README.md` not found in project root.")

elif page == "📚User Guide":
    st.title("📚 User Guide")
    md_path = PROJECT_ROOT / "docs" / "User_guide.md"
    if md_path.exists():
        st.markdown(md_path.read_text(encoding="utf-8"))
    else:
        st.warning("`docs/User_guide.md` not found.")

elif page == "🧠Knowledge Base":
    st.title("🧠 Knowledge Base Repository")
    st.caption("Aggregated vector repository and historical resolutions.")

    # =========================================================================
    # 🔴 PATH CONFIGURATION (Set your CSV & DB paths)
    # =========================================================================
    BASE_DIR = Path(__file__).resolve().parent.parent
    KB_CSV_PATH = BASE_DIR / "data"/"knowledge_base_with_severity.csv"
    # KB_CSV_PATH =Path(__file__).resolve().parent / "data" / "knowledge_base_with_severity.csv"
    BUG_DB_PATH = Path(__file__).resolve().parent / "data" / "bug_submissions.db"
    
    # Fallback to parent dir if DB is located in ../data/
    if not BUG_DB_PATH.exists():
        BUG_DB_PATH = Path(__file__).resolve().parent.parent / "data" / "bug_submissions.db"

    if os.path.exists(KB_CSV_PATH):
        kb_df = pd.read_csv(KB_CSV_PATH)

        # ---------------------------------------------------------
        # 1. Metric Calculations
        # ---------------------------------------------------------
        # Total Size of Initial KB
        total_kb_size = len(kb_df)

        # Count of New Fixed Rows Added Till Now (Queried from SQLite)
        total_fixed_till_now = 0
        if BUG_DB_PATH.exists():
            try:
                conn = sqlite3.connect(BUG_DB_PATH)
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM bug_submissions WHERE status = 'resolved_added_to_kb'")
                total_fixed_till_now = cursor.fetchone()[0]
                conn.close()
            except Exception as e:
                total_fixed_till_now = 0

        # Most Frequent Severity
        sev_col = next((c for c in kb_df.columns if "severity_mapped" in c.lower()), None)
        if sev_col and not kb_df[sev_col].dropna().empty:
            top_severity = kb_df[sev_col].mode().iloc[0]
            top_severity_count = int((kb_df[sev_col] == top_severity).sum())
        else:
            top_severity = "N/A"
            top_severity_count = 0

        # Most Frequent Component
        comp_col = next((c for c in kb_df.columns if any(k in c.lower() for k in ["component", "module", "service"])), None)
        if comp_col and not kb_df[comp_col].dropna().empty:
            top_component = kb_df[comp_col].mode().iloc[0]
            top_component_count = int((kb_df[comp_col] == top_component).sum())
        else:
            top_component = "N/A"
            top_component_count = 0

        # ---------------------------------------------------------
        # 2. Top 4 Metric Ribbon Cards
        # ---------------------------------------------------------
        k1, k2, k3, k4 = st.columns(4)

        with k1:
            with st.container(border=True):
                st.caption("📦 TOTAL KB SIZE")
                st.markdown(f"<h3 style='margin:0; color:#38bdf8;'>📚 {total_kb_size}</h3>", unsafe_allow_html=True)
                st.caption("Base Indexed Bugs")

        with k2:
            with st.container(border=True):
                st.caption("✅ FIXED ROWS ADDED TILL NOW")
                st.markdown(f"<h3 style='margin:0; color:#4ade80;'>🛡️ {total_fixed_till_now}</h3>", unsafe_allow_html=True)
                st.caption("Verified & Added to KB")

        with k3:
            with st.container(border=True):
                st.caption("🚨 DOMINANT SEVERITY")
                st.markdown(f"<h3 style='margin:0; color:#fbbf24; font-size: 1.15rem; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;'>🔥 {top_severity}</h3>", unsafe_allow_html=True)
                st.caption(f"Volume: {top_severity_count} entries")

        with k4:
            with st.container(border=True):
                st.caption("🧩 FREQUENT COMPONENT")
                st.markdown(f"<h3 style='margin:0; color:#f472b6; font-size: 1.15rem; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;'>⚙️ {top_component}</h3>", unsafe_allow_html=True)
                st.caption(f"Volume: {top_component_count} entries")

        st.divider()

        # ---------------------------------------------------------
        # 3. Interactive Search & Knowledge Base Table
        # ---------------------------------------------------------
        with st.container(border=True):
            tb_col1, tb_col2 = st.columns([2.5, 1.5])
            with tb_col1:
                st.markdown("##### 📋 Knowledge Base Records")
            with tb_col2:
                search_query = st.text_input("🔍 Search KB", placeholder="Filter by keyword, fix, or module...", label_visibility="collapsed")

            display_df = kb_df
            if search_query.strip():
                mask = display_df.astype(str).apply(lambda row: row.str.contains(search_query, case=False, na=False).any(), axis=1)
                display_df = display_df[mask]

            st.dataframe(display_df, use_container_width=True, height=450)
            st.caption(f"Showing {len(display_df)} base records + {total_fixed_till_now} dynamic verified fixes.")

    else:
        st.error(f"❌ File not found at: `{KB_CSV_PATH}`. Please check the path.")

elif page == "🏠 Dashboard":
    st.title("📊 Telemetry Dashboard")
    st.caption("Real-time telemetry of ingested defect tickets and resolution tracking.")

    # ---------------------------------------------------------
    # Database Paths
    # ---------------------------------------------------------
    BASE_DIR = Path(__file__).resolve().parent
    BUG_DB_PATH = BASE_DIR / "data" / "bug_submissions.db"
    DEV_DB_PATH = BASE_DIR / "data" / "Developer_Submission.db"

    # Fallback checks
    if not BUG_DB_PATH.exists():
        BUG_DB_PATH = BASE_DIR.parent / "data" / "bug_submissions.db"
    if not DEV_DB_PATH.exists():
        DEV_DB_PATH = BASE_DIR.parent / "data" / "Developer_Submission.db"

    # ---------------------------------------------------------
    # 1. Fetch Data & Calculate 4 Key Metrics
    # ---------------------------------------------------------
    total_bugs = 0
    total_critical = 0
    solved_critical = 0
    top_dev_name = "N/A"
    top_dev_count = 0
    submissions_df = pd.DataFrame()

    if BUG_DB_PATH.exists():
        try:
            conn = sqlite3.connect(BUG_DB_PATH)
            submissions_df = pd.read_sql("SELECT * FROM bug_submissions ORDER BY timestamp DESC", conn)
            conn.close()

            if not submissions_df.empty:
                total_bugs = len(submissions_df)
                
                # Critical bug calculations
                crit_mask = submissions_df['severity'].astype(str).str.lower() == 'critical'
                total_critical = int(crit_mask.sum())
                
                solved_crit_mask = crit_mask & (submissions_df['status'].astype(str) == 'resolved_added_to_kb')
                solved_critical = int(solved_crit_mask.sum())
        except Exception as e:
            st.error(f"Error reading bug database: {e}")

    # Query Developer Submissions for Top Reporter
    if DEV_DB_PATH.exists():
        try:
            conn_dev = sqlite3.connect(DEV_DB_PATH)
            dev_df = pd.read_sql("SELECT reporter_name, bug_id FROM Developer_Submission", conn_dev)
            conn_dev.close()

            if not dev_df.empty and 'reporter_name' in dev_df.columns:
                clean_devs = dev_df['reporter_name'].dropna().astype(str).str.strip()
                clean_devs = clean_devs[clean_devs != ""]
                if not clean_devs.empty:
                    top_dev_name = clean_devs.mode().iloc[0]
                    top_dev_count = int((clean_devs == top_dev_name).sum())
        except Exception as e:
            pass

    # ---------------------------------------------------------
    # 2. Top Metric Ribbon (4 SaaS Cards)
    # ---------------------------------------------------------
    m1, m2, m3, m4 = st.columns(4)

    with m1:
        with st.container(border=True):
            st.caption("📁 TOTAL SUBMITTED")
            st.markdown(f"<h3 style='margin:0; color:#38bdf8;'>🐞 {total_bugs}</h3>", unsafe_allow_html=True)
            st.caption("All Ingested Tickets")

    with m2:
        with st.container(border=True):
            st.caption("🚨 CRITICAL BUGS")
            st.markdown(f"<h3 style='margin:0; color:#f87171;'>🔥 {total_critical}</h3>", unsafe_allow_html=True)
            st.caption("Fatal & Blocker Defects")

    with m3:
        with m3:
            with st.container(border=True):
                st.caption("✅ SOLVED CRITICAL")
                st.markdown(f"<h3 style='margin:0; color:#4ade80;'>🛡️ {total_critical}</h3>", unsafe_allow_html=True)
                st.caption(f"Resolved of {total_critical} Critical")

    with m4:
        with st.container(border=True):
            st.caption("🏆 TOP CONTRIBUTOR")
            st.markdown(f"<h3 style='margin:0; color:#fbbf24; font-size:1.2rem; white-space:nowrap; overflow:hidden; text-overflow:ellipsis;'>👨‍💻 {top_dev_name}</h3>", unsafe_allow_html=True)
            st.caption(f"{top_dev_count} Submissions logged")

    st.divider()

    # ---------------------------------------------------------
    # 3. Live Defect Ticket Table (bug_submissions.db)
    # ---------------------------------------------------------
    with st.container(border=True):
        t_head, t_search = st.columns([2.6, 1.4])
        with t_head:
            st.markdown("##### 🗂️ Ingested Defect Tickets")
            st.caption("Direct telemetry feed from `bug_submissions.db`.")
        with t_search:
            db_search = st.text_input("Search Database", placeholder="Filter by ID, component, severity...", label_visibility="collapsed")

        if not submissions_df.empty:
            # Display relevant columns
            cols_to_show = [c for c in ['bug_id', 'severity', 'priority', 'component', 'error_type', 'status', 'timestamp', 'recommended_fix'] if c in submissions_df.columns]
            table_df = submissions_df[cols_to_show].copy()

            if db_search.strip():
                mask = table_df.astype(str).apply(lambda row: row.str.contains(db_search, case=False, na=False).any(), axis=1)
                table_df = table_df[mask]

            st.dataframe(table_df, use_container_width=True, height=450)
            st.caption(f"Displaying {len(table_df)} of {total_bugs} total records.")
        else:
            st.info("No bug records found in `bug_submissions.db`. Submit a bug to populate telemetry.")