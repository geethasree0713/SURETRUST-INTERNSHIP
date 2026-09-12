import os
import json
import time
from groq import Groq
from dotenv import load_dotenv
import sqlite3
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.cluster import AgglomerativeClustering
import pandas as pd
from sentence_transformers import SentenceTransformer


# Load API key and create client
_base_dir = os.path.dirname(os.path.abspath(__file__))
_env_path = os.path.join(_base_dir, "..", ".env")
load_dotenv(_env_path)
api_key = os.getenv("GROQ_API_KEY")
client = Groq(api_key=api_key)


def call_llm_with_retry(system_prompt, user_message, max_retries=3):
    for attempt in range(max_retries):
        try:
            response = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message}
                ],
                temperature=0.2
            )
            raw = response.choices[0].message.content.strip()

            if raw.startswith("```"):
                raw = raw.split("```")[1]
                if raw.startswith("json"):
                    raw = raw[4:]
                raw = raw.strip()

            return json.loads(raw)
        except Exception as e:
            if "rate_limit" in str(e).lower() or "429" in str(e):
                wait_time = (attempt + 1) * 3
                time.sleep(wait_time)
            else:
                print(f"Non-rate-limit error: {e}")
                break
    return None

system_prompt = """You are a bug triage assistant. You are given the title, description, and stack trace of a submitted bug, and you classify it by severity, priority, and affected component, with confidence scoring and reasoning.

IMPORTANT CALIBRATION: Most everyday bugs are Medium severity, not Critical or High. Reserve Critical/High for bugs that cause crashes, data loss, security issues, or completely block core functionality. Reserve Low for cosmetic issues, minor inconveniences, or feature requests. The MAJORITY of real-world bugs are routine Medium severity - do not over-classify ordinary bugs as urgent just because they mention words like "error" or "exception."

Examples for calibration:
- "App crashes on startup, no workaround" -> Critical
- "Login fails for all users" -> Critical  
- "Payment fails for some users but not others, blocking checkout for that group" -> High
- "File upload crashes for large files, though smaller files work fine" -> High
- "Button text is misaligned by 2px" -> Low
- "Feature request: add dark mode" -> Low
- "Export function occasionally produces incorrect date format" -> Medium
- "Search results are slow to load under heavy traffic" -> Medium

Reply ONLY in valid JSON, with this exact structure:
{"bug_id": "...", "severity": "Critical", "confidence": 0.85, "reasoning": "...", "priority": "...", "component": "Login"}

Field definitions:
- bug_id: if provided, use it; otherwise use "unknown"
- severity: must be exactly one of Critical, High, Medium, Low - no other words
- confidence: a score from 0 to 1 representing how confident you are in this classification
- reasoning: a brief explanation of why you classified it this way
- priority: how urgently this needs to be addressed - Immediate, High, Medium, or Low (related to but different from severity: severity is impact, priority is urgency)
- component: which part/module of the software seems affected, inferred from the content (e.g. "Login", "Database", "UI/Rendering") - do not restrict to a fixed list

If you encounter other severity-like words, map them using this table:
blocker/critical -> Critical, major -> High, normal/unknown -> Medium, minor/trivial -> Low
"""

log_analysis_system_prompt = """You are a Log Analysis Agent. Your job is to extract structured information from messy error text - stack traces, tracebacks, or compiler error messages, sometimes alongside the relevant code.

Extract:
- error_type: the SPECIFIC error/exception name as it would appear in real compiler/runtime output - NOT a generic category. For example, prefer "Template Mismatch" or "Dereferencing Void Pointer" over generic terms like "Compilation Error" or "Compilation Warning". Look for the specific technical term the error message itself uses, not a broad summary category.
- failure_location: the exact file/line/position where the error occurred, taken directly from the trace
- code_path: the chain of function/method calls leading to the failure. IMPORTANT: if the code being described contains double quote characters (e.g. from println!, print statements, or string literals), you MUST escape them as \\" so the JSON stays valid. Never include an unescaped " inside any field value.
- confidence: a score from 0 to 1 representing how certain you are that you extracted this correctly. Vary this realistically - very clear, unambiguous traces should score 0.95-0.99, while vague, truncated, or ambiguous input should score lower (0.5-0.8). Do not default to 0.99 for everything.
- reasoning: a brief, specific explanation of why the error occurred

Reply ONLY in valid JSON with this exact structure. Every field value must be a properly escaped JSON string - double quotes inside any value must be written as \\":
{"error_type": "...", "failure_location": "...", "code_path": "...", "confidence": 0.9, "reasoning": "..."}

Examples:

Input: Cell In[119], line 3
    return payload_2
    ^
IndentationError: unindent does not match any outer indentation level

Output: {"error_type": "IndentationError", "failure_location": "Cell In[119], line 3", "code_path": "return payload_2 executed directly within the current code block; indentation parsing failed before execution", "confidence": 0.99, "reasoning": "The 'return' statement has inconsistent indentation that does not align with the surrounding block, causing Python's parser to reject the code."}

Input: /workspace/service_2.js:3
console.log(session_2[5].id);
TypeError: Cannot read properties of undefined (reading 'id')
    at Object.<anonymous> (/workspace/service_2.js:3:15)

Output: {"error_type": "TypeError", "failure_location": "/workspace/service_2.js:3:15", "code_path": "Top-level execution -> console.log(session_2[5].id)", "confidence": 0.99, "reasoning": "The expression 'session_2[5]' evaluated to undefined, so accessing its 'id' property caused a TypeError."}

Input: parser_4.c: In function 'main':
parser_4.c:3:15: error: invalid initializer / incompatible types when initializing type 'int' using type 'char *'
    3 |     int val = str;

Output: {"error_type": "Invalid Initializer (Incompatible Types)", "failure_location": "parser_4.c:3:15", "code_path": "main() -> variable initialization: int val = str", "confidence": 0.85, "reasoning": "An integer variable was initialized using a character pointer, which is an incompatible type conversion in C."}

Input: session_2.cpp: In function 'int main()':
session_2.cpp:5:17: error: no matching member function for call to 'insert'
    5 |     ages.insert(10, "John");

Output: {"error_type": "No Matching Member Function", "failure_location": "session_2.cpp:5:17", "code_path": "main() -> std::map::insert(10, \\"John\\")", "confidence": 0.95, "reasoning": "The std::map::insert() function was called with arguments that do not match any valid overload."}

Input: Exception in thread "main" java.lang.NullPointerException: Cannot invoke "String.indexOf(String)" because "recordsList_2" is null
    at MetricsEngine_2.updateCache_2(Api_2.java:110)

Output: {"error_type": "NullPointerException", "failure_location": "Api_2.java:110", "code_path": "main thread -> MetricsEngine_2.updateCache_2() -> String.indexOf()", "confidence": 0.99, "reasoning": "The object 'recordsList_2' is null, so calling the 'indexOf()' method on it causes a NullPointerException."}

Input: CssSyntaxError: grid_2.css:20:1: Unclosed block
  18 |     background: #000;
  19 |     opacity: 0.9;
> 20 |
    | ^
  21 | .element-sibling_2 {

Output: {"error_type": "PostCSS Parser Error: Unclosed Block", "failure_location": "grid_2.css:20:1", "code_path": "CSS parser -> grid_2.css -> unclosed declaration block before '.element-sibling_2'", "confidence": 0.99, "reasoning": "A CSS block was not properly closed with '}', causing the parser to detect an unclosed block before the next selector."}

Input: Error: Stray end tag </span>.
From line 95, column 15; to line 95, column 22
item 1</p></span>\n</di

Output: {"error_type": "W3C Validator Error: Stray End Tag", "failure_location": "Line 95, columns 15-22", "code_path": "HTML parser -> closing tags -> unexpected </span>", "confidence": 0.99, "reasoning": "The closing </span> tag does not match any currently open <span> element, resulting in a stray end tag."}

Input: app_1.ts:63:1 - error TS2322: Type 'string' is not assignable to type 'number'.
63 weightsTensor_1 = "invalid_assign_1";
  ~~~~~~~~~~~~~~~

Output: {"error_type": "TypeScript Error: TS2322 (Type Assignment Error)", "failure_location": "app_1.ts:63:1", "code_path": "Top-level assignment -> weightsTensor_1 = \\"invalid_assign_1\\"", "confidence": 0.99, "reasoning": "A string value was assigned to a variable that is declared with the type 'number', violating TypeScript's type checking rules."}

Input: panic: runtime error: index out of range [7] with length 3
goroutine 1 [running]:
main.main()
    /go/src/app/main_2.go:96 +0x3d

Output: {"error_type": "Go Runtime Panic: Index Out of Range", "failure_location": "/go/src/app/main_2.go:96", "code_path": "main.main() -> slice/array index access", "confidence": 0.99, "reasoning": "The program attempted to access index 7 of a slice or array that contains only 3 elements, causing a runtime panic."}
"""


def triage_agent(title, description, stack_trace="Not available", bug_id="unknown"):
    user_message = f"Title: {title}\nDescription: {description}\nStack Trace: {stack_trace}"
    result = call_llm_with_retry(system_prompt, user_message)
    if result is None:
        result = {"severity": "Medium", "confidence": 0.0, "reasoning": "LLM call failed after retries", "priority": "Medium", "component": "Unknown"}
    result['bug_id'] = bug_id
    return result


def log_analysis_agent(error_text, code_context=""):
    if code_context:
        user_message = f"Code:\n{code_context}\n\nError:\n{error_text}"
    else:
        user_message = f"Error:\n{error_text}"
    result = call_llm_with_retry(log_analysis_system_prompt, user_message)
    if result is None:
        result = {
            "error_type": "Unknown",
            "failure_location": "Not determined",
            "code_path": "Not determined",
            "confidence": 0.0,
            "reasoning": "LLM call failed after retries"
        }
    return result


def run_orchestration(title, description, stack_trace, bug_id="unknown"):
    triage_result = triage_agent(title, description, stack_trace, bug_id=bug_id)
    log_result = log_analysis_agent(stack_trace)

    combined_result = {
        "bug_id": bug_id,
        "triage": triage_result,
        "log_analysis": log_result
    }

    return combined_result


def build_simple_view(combined_result):
    triage = combined_result["triage"]
    log = combined_result["log_analysis"]

    actual_result = {
        "bug_id": combined_result["bug_id"],
        "severity": triage["severity"],
        "priority": triage["priority"],
        "component": triage["component"],
        "error_type": log["error_type"],
        "failure_location": log["failure_location"],
        "code_path": log["code_path"],
        "confidence": log["confidence"],
        "reasoning": log["reasoning"]
    }

    return actual_result


def init_db():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    db_path = os.path.join(base_dir, "..", "data", "bug_submissions.db")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS bug_submissions (
            bug_id TEXT PRIMARY KEY,
            severity TEXT,
            priority TEXT,
            component TEXT,
            error_type TEXT,
            failure_location TEXT,
            code_path TEXT,
            confidence REAL,
            reasoning TEXT,
            description TEXT,
            timestamp TEXT
        )
    """)
    conn.commit()
    conn.close()


def save_submission(actual_result, description, timestamp, root_cause_hypothesis=None, recommended_fix=None):
    base_dir = os.path.dirname(os.path.abspath(__file__))
    db_path = os.path.join(base_dir, "..", "data", "bug_submissions.db")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT OR REPLACE INTO bug_submissions
        (bug_id, severity, priority, component, error_type, failure_location, code_path, confidence, reasoning, description, timestamp, root_cause_hypothesis, recommended_fix)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        actual_result["bug_id"], actual_result["severity"], actual_result["priority"],
        actual_result["component"], actual_result["error_type"], actual_result["failure_location"],
        actual_result["code_path"], actual_result["confidence"], actual_result["reasoning"],
        description, timestamp, root_cause_hypothesis, recommended_fix
    ))
    conn.commit()
    conn.close()

def retrieve_similar_bugs(query_text, model, kb_embeddings, kb_metadata, top_n=5):
    query_vector = model.encode([query_text], convert_to_numpy=True)
    similarities = cosine_similarity(query_vector, kb_embeddings)[0]
    top_indices = np.argsort(similarities)[::-1][:top_n]

    results = []
    for idx in top_indices:
        row = kb_metadata.iloc[idx]
        results.append({
            "bug_id": row["bug_id"],
            "title": row["title"],
            "severity": row["severity"],
            "resolution": row["resolution"],
            "source_dataset": row["source_dataset"],
            "similarity": float(similarities[idx])
        })

    return results

root_cause_prompt = """ You are job is to Retrieve Relevant Historical Bugs and Generate Root Cause Analysis

and identifies the most probable root cause of a submitted bug using RAG-based retrieval from the historical defect knowledge base. Output(Reply ONLY in valid JSON) - Root cause hypothesis, confidence score, and supporting historical evidence 

input will be the 

 { 

bug_id , severity , component , error_type ,failure_location , code_path , {plus the 5 retrieved similar historical bugs (with their resolutions)}       

}

You must reason about why this new bug likely happened, using patterns from those historical bugs as support.

Output:
{
  "root_cause_hypothesis": "...",   
  "confidence": 0.85,
  "supporting_evidence": [
    {"bug_id": "...", "summary": "..."},
    {"bug_id": "...", "summary": "..."}
  ]
}

 

 Root cause hypothesis - It is the explanation of why the bug happened — e.g., "The NullPointerException likely occurred because the recordsList object was never initialized before being accessed, similar to patterns seen in [historical bug].

confidence score - a score from 0 to 1 representing how certain you are that you extracted this correctly. Vary this realistically - very clear, unambiguous traces should score 0.95-0.99, while vague, truncated, or ambiguous input should score lower (0.5-0.8). Do not default to 0.99 for everything.

supporting historical evidence - evidence should include both a traceable bug_id AND a short 5-15 word summary ( this should be a list of small objects, not a single string.)



Example 1:
Input: {"error_type": "NullPointerException", "component": "Login", "failure_location": "Api_2.java:110", "code_path": "main thread -> updateCache_2() -> String.indexOf()", "retrieved_bugs": [{"bug_id": "GMF-RUNTIME-282380", "title": "DefaultProvider#getRelevantConnections may throw a NPE", "resolution": "fixed"}, {"bug_id": "JCR-71", "title": "WorkspaceConfig.init() throws NullPointerException if Search configuration is missing", "resolution": "Fixed"}]}

Output: {"root_cause_hypothesis": "The NullPointerException likely occurred because an object (recordsList) was accessed before being properly initialized, a pattern consistent with similar historical NPEs caused by missing configuration or setup steps.", "confidence": 0.82, "supporting_evidence": [{"bug_id": "GMF-RUNTIME-282380", "summary": "NPE from missing null check before method call"}, {"bug_id": "JCR-71", "summary": "NPE from missing required configuration on init"}]}

Example 2:
Input: {"error_type": "IndexError", "component": "Search/Filtering", "failure_location": "sort_handler.py:22", "code_path": "apply_filter() -> sort_results()", "retrieved_bugs": [{"bug_id": "PY-1002", "title": "List index out of range when filter returns empty results", "resolution": "fixed"}]}

Output: {"root_cause_hypothesis": "The IndexError likely occurred because the sorting function assumed the filtered list would always contain at least one item, but did not handle the case of an empty result set.", "confidence": 0.75, "supporting_evidence": [{"bug_id": "PY-1002", "summary": "Empty list not handled before indexing"}]}

Example 3:
Input: {"error_type": "ConnectionError", "component": "Database", "failure_location": "db_handler.py:8", "code_path": "startup() -> connect_db()", "retrieved_bugs": [{"bug_id": "APACHE-990", "title": "Database connection pool exhausted under load", "resolution": "fixed"}, {"bug_id": "APACHE-1103", "title": "Connection timeout not configured, hangs indefinitely", "resolution": "fixed"}, {"bug_id": "APACHE-1204", "title": "Retry logic missing on transient connection failures", "resolution": "wontfix"}]}

Output: {"root_cause_hypothesis": "The connection failure is likely caused by either exhausted connection pool capacity or a missing timeout/retry mechanism, both common causes of database connection failures under load in similar historical cases.", "confidence": 0.68, "supporting_evidence": [{"bug_id": "APACHE-990", "summary": "Connection pool exhausted under high load"}, {"bug_id": "APACHE-1103", "summary": "Missing timeout caused indefinite hang"}]}

Example 4:
Input: {"error_type": "TypeError", "component": "UI/Rendering", "failure_location": "render.js:15", "code_path": "renderComponent() -> formatDate()", "retrieved_bugs": []}

Output: {"root_cause_hypothesis": "No closely related historical bugs were found, but based on the error itself, this likely occurred because a date value was undefined or in an unexpected format when passed into the formatting function.", "confidence": 0.55, "supporting_evidence": []}

Example 5:
Input: {"error_type": "ValidationError", "component": "Payment Processing", "failure_location": "payment.py:44", "code_path": "checkout() -> validate_currency()", "retrieved_bugs": [{"bug_id": "TVT35-297", "title": "incorrect default placement of currency symbol", "resolution": "fixed"}]}

Output: {"root_cause_hypothesis": "This is likely a currency-code validation gap rather than the same issue as the retrieved bug, since that historical case involved display formatting, not validation logic - the connection is only loosely related.", "confidence": 0.6, "supporting_evidence": [{"bug_id": "TVT35-297", "summary": "Related currency-handling bug, but different root cause"}]}

Example 6:
Input: {"error_type": "MemoryError", "component": "File Upload", "failure_location": "upload_handler.js:67", "code_path": "uploadFile() -> allocateBuffer()", "retrieved_bugs": [{"bug_id": "AXIS-1741", "title": "LogHandler can only work in GlobalConfiguration", "resolution": "fixed"}]}

Output: {"root_cause_hypothesis": "No strongly related historical bug was found; the retrieved bug shares only superficial similarity (both are configuration-related) but does not explain a memory allocation failure on large file uploads.", "confidence": 0.5, "supporting_evidence": [{"bug_id": "AXIS-1741", "summary": "Unrelated configuration bug, weak match only"}]}

Example 7:
Input: {"error_type": "SyntaxError", "component": "Build System", "failure_location": "config.css:20", "code_path": "CSS parser -> block parsing", "retrieved_bugs": [{"bug_id": "CSS-501", "title": "Unclosed declaration block causes parser failure", "resolution": "fixed"}, {"bug_id": "CSS-512", "title": "Missing semicolon triggers cascading syntax errors", "resolution": "fixed"}]}

Output: {"root_cause_hypothesis": "The syntax error is almost certainly caused by an unclosed block or missing terminator in the CSS source, a very common and well-documented pattern matching both retrieved historical bugs closely.", "confidence": 0.93, "supporting_evidence": [{"bug_id": "CSS-501", "summary": "Unclosed block caused identical parser failure"}, {"bug_id": "CSS-512", "summary": "Missing semicolon caused cascading syntax error"}]}



"""

def root_cause_agent(bug_id, severity, component, error_type, failure_location, code_path, retrieved_bugs):
    input_data = {
        "bug_id": bug_id,
        "severity": severity,
        "component": component,
        "error_type": error_type,
        "failure_location": failure_location,
        "code_path": code_path,
        "retrieved_bugs": retrieved_bugs
    }

    user_message = json.dumps(input_data)

    result = call_llm_with_retry(root_cause_prompt, user_message)

    if result is None:
        result = {
            "root_cause_hypothesis": "Unable to determine root cause due to a processing error.",
            "confidence": 0.0,
            "supporting_evidence": []
        }

    return result

duplicate_detection_agent_prompt = """You are given a new bug report and a previously submitted bug that has already been mathematically determined to be a likely duplicate, along with its similarity label ("same" or "similar").

Your only job is to write one short, clear sentence (15-25 words) explaining why these two bugs likely describe the same underlying issue, based on their description, error_type, and component.

Do not assign or change the similarity score or label - those are already fixed and provided to you. Do not question or override the label.

Reply ONLY in valid JSON with this exact structure:
{"explanation": "..."}

Example:
Input: {"new_bug": {"description": "App crashes on login with NullPointerException", "error_type": "NullPointerException", "component": "Login"}, "matched_bug": {"description": "Login fails, NullPointerException thrown", "error_type": "NullPointerException", "component": "Login"}, "label": "similar", "similarity": 0.87}

Output: {"explanation": "Both reports describe a NullPointerException occurring during login, indicating the same underlying failure in the Login component."}
"""

def find_duplicate_candidates(new_description, model, top_n=5):
    base_dir = os.path.dirname(os.path.abspath(__file__))
    db_path = os.path.join(base_dir, "..", "data", "bug_submissions.db")

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT bug_id, description, error_type, component, reasoning FROM bug_submissions")
    rows = cursor.fetchall()
    conn.close()

    if not rows:
        return []

    stored_descriptions = [row[1] for row in rows]

    new_vector = model.encode([new_description], convert_to_numpy=True)
    stored_vectors = model.encode(stored_descriptions, convert_to_numpy=True)

    similarities = cosine_similarity(new_vector, stored_vectors)[0]

    candidates = []
    for i, sim in enumerate(similarities):
        if sim >= 0.75:
            label = "same" if sim >= 0.90 else "similar"
            candidates.append({
                "bug_id": rows[i][0],
                "description": rows[i][1],
                "error_type": rows[i][2],
                "similarity": float(sim),
                "label": label
            })

    candidates.sort(key=lambda x: x["similarity"], reverse=True)
    return candidates[:top_n]


def duplicate_detection_agent(new_description, error_type, component, reasoning, model, top_n=5):
    candidates = find_duplicate_candidates(new_description, model, top_n=top_n)

    results = []
    for c in candidates:
        input_data = {
            "new_bug": {"description": new_description, "error_type": error_type, "component": component},
            "matched_bug": {"description": c["description"], "error_type": c["error_type"]},
            "label": c["label"],
            "similarity": c["similarity"]
        }
        user_message = json.dumps(input_data)
        explanation_result = call_llm_with_retry(duplicate_detection_agent_prompt, user_message)

        results.append({
            "bug_id": c["bug_id"],
            "similarity": c["similarity"],
            "label": c["label"],
            "explanation": explanation_result["explanation"] if explanation_result else "No explanation available."
        })

    return results


remediation_agent_prompt = """ You are an agent  and you job is  to generates specific fix recommendations grounded in historical resolutions, root cause findings, and best practice guidelines and Reply ONLY in valid JSON.

input you will get are : bug_id, severity , component , error_type ,failure_location , code_path ,  description , root_cause , historical_references , duplicate_bug

bug_id → to identify which bug it's fixing.
severity → to decide how urgent or cautious the fix should be.
component → to understand which module or subsystem is affected.
error_type → to know the category of error (e.g., NameError, NullPointerException).
failure_location → to know where the bug occurred.
code_path → to understand the execution path leading to the error.
description → a concise explanation of what failed (this can come from the Log Analysis Agent's reasoning).
root_cause → the Root Cause Agent's hypothesis about why the bug occurred.
historical_references → previous similar bugs or fixes to ground the recommendation.
duplicate_bug → if a duplicate exists, the Remediation Agent may simply recommend the existing fix instead of generating a new one.
match: Indicates how closely the historical bug matches the current bug (e.g., "same" for nearly identical, "similar" for related but not identical).
similarity: A numeric score (0 to 1) representing how similar the current bug is to the historical bug, where 1.0 means an almost identical match and 0.0 means completely different.


IMPORTANT: The "before" and "after" values inside code_example must be single, valid JSON string values. If example code spans multiple lines, join those lines using the two-character escape sequence \n (a backslash followed by the letter n) — never include an actual line break inside any field value. The entire JSON response must be valid on parse, with no raw newline or control characters inside any string.



output : 
bug_id	: A unique ID used to identify this specific bug.
recommended_fix : 	The main solution that should be applied to fix the bug.
fix_steps : 	A list of simple steps the developer should follow to fix the problem.
code_example : 	Shows the incorrect code ("before") and the corrected code ("after") as an example.
validation_steps : 	Steps to check whether the bug has been fixed successfully after applying the solution.
prevention : 	A best practice or tip to help prevent the same type of bug in the future.
confidence : 	A score showing how confident the agent is that the suggested fix is the correct one.
reasoning : 	A short explanation of why the agent chose this particular fix based on the available information.
references_used : 	The historical bugs, documentation, or best-practice sources that helped the agent decide on the fix.
Field : 	Simple Explanation
type : 	The kind of source used, such as a historical bug or documentation.
bug_id : 	The ID of the similar historical bug that was used as a reference.
summary : 	A short description of what that historical bug was about.





example :


example 1:


input :
{
  "bug_id": "BUG-30550c39",
  "severity": "Medium",
  "component": "Cache Management",
  "error_type": "NameError",
  "failure_location": "Cell In[92], line 2",
  "code_path": "update_cache_4() -> return statement: config_4_missing + 10",
  "description": "The variable 'config_4_missing' is referenced in the return statement but has not been defined, resulting in a NameError.",
  "root_cause": "The NameError likely occurred because a variable was referenced before being defined, possibly due to a missing import or incorrect variable naming.",
  "historical_references": [
    {
      "bug_id": "IVY-108",
      "summary": "Cache fileset issue with empty configuration"
    },
    {
      "bug_id": "COCOON-1698",
      "summary": "Caching attribute issue with global use"
    }
  ],
  "duplicate_bug": [
  {
    "bug_id": "IVY-108",
    "similarity": 0.91,
    "label": "same",
    "explanation": "Both reports involve cache configuration code where an undefined or missing configuration value causes execution to fail. The affected component and root cause are highly consistent."
  },
  {
    "bug_id": "COCOON-1698",
    "similarity": 0.78,
    "label": "similar",
    "explanation": "Both reports are related to cache management and configuration handling. Although the exact exception differs, both stem from configuration-related issues affecting cache behavior."
  }
]
}


ouptut:
{
  "bug_id": "BUG-30550c39",
  "recommended_fix": "Define the variable 'config_4_missing' before it is referenced, or replace it with the correct configuration variable if the current name is a typo.",
  "fix_steps": [
    "Locate the 'update_cache_4()' function and identify where 'config_4_missing' is referenced.",
    "Check whether 'config_4_missing' was intended to be another existing configuration variable.",
    "If the variable is missing, initialize it with a valid value before the return statement.",
    "If the value should come from another module or configuration file, import or retrieve it correctly.",
    "Run the function again to confirm that the NameError no longer occurs."
  ],
  "code_example": {
    "before": "return config_4_missing + 10",
    "after": "config_4_missing = 5\nreturn config_4_missing + 10"
  },
  "validation_steps": [
    "Execute update_cache_4() after applying the fix.",
    "Verify that no NameError is raised.",
    "Run all cache management unit tests.",
    "Test cache initialization using different configuration values.",
    "Confirm that no new errors are introduced in dependent modules."
  ],
  "prevention": "Use static analysis tools such as pylint or pyright to detect undefined variables before execution, and adopt consistent variable naming conventions for configuration values.",
  "confidence": 0.97,
  "reasoning": "The Log Analysis identified a NameError caused by an undefined variable, while the Root Cause analysis indicates that the variable was likely referenced before being defined or imported. Duplicate detection found a highly similar historical bug (IVY-108) involving cache configuration issues, whose successful resolution supports defining or correcting the missing configuration variable as the appropriate remediation.",
  "references_used": [
    {
      "type": "historical_bug",
      "bug_id": "IVY-108",
      "summary": "Cache fileset issue with empty configuration",
      "match": "same",
      "similarity": 0.91
    },
    {
      "type": "historical_bug",
      "bug_id": "COCOON-1698",
      "summary": "Caching attribute issue with global use",
      "match": "similar",
      "similarity": 0.78
    }
  ]
}



example 2:

Input: {"bug_id": "BUG-f5b5592a", "severity": "High", "component": "Payment Processing", "error_type": "ValidationError", "failure_location": "payment.py:44", "code_path": "checkout() -> validate_currency()", "description": "Payment processing occasionally fails for international transactions due to a currency validation error.", "root_cause": "Likely a validation gap in currency-code handling for non-default locales, based on similar historical payment validation bugs.", "historical_references": [{"bug_id": "TVT35-297", "summary": "Incorrect default placement of currency symbol"}], "duplicate_bug": [{"bug_id": "BUG-b216f3db", "similarity": 1.0, "label": "same", "explanation": "Both reports describe identical international payment validation failures with the same error type and component."}]}

Output: {"bug_id": "BUG-f5b5592a", "recommended_fix": "This is a duplicate of BUG-b216f3db, already identified. Apply the same fix: extend currency validation to explicitly support all supported international currency codes, not just default-locale ones.", "fix_steps": ["Confirm this matches the already-tracked issue BUG-b216f3db.", "Review the currency validation function for locale-specific assumptions.", "Add explicit handling for international currency codes.", "Apply the same fix already scoped for BUG-b216f3db rather than duplicating engineering effort."], "code_example": {"before": "if currency == 'USD': validate(amount)", "after": "if currency in SUPPORTED_CURRENCIES: validate(amount, currency)"}, "validation_steps": ["Re-test with multiple international currency codes.", "Confirm checkout succeeds for previously failing locales.", "Verify no regression for USD/default-locale transactions."], "prevention": "Add international currency test cases to the payment validation test suite to catch locale-specific gaps earlier.", "confidence": 0.95, "reasoning": "An exact duplicate (BUG-b216f3db) was already found and resolved-in-progress. Reusing the existing fix avoids redundant engineering effort, consistent with the project's goal of not re-solving already-identified issues.", "references_used": [{"type": "duplicate_bug", "bug_id": "BUG-b216f3db", "summary": "Identical international payment validation failure", "match": "same", "similarity": 1.0}, {"type": "historical_bug", "bug_id": "TVT35-297", "summary": "Currency symbol placement bug, loosely related"}]}



example 3:

Input: {"bug_id": "BUG-f25343c8", "severity": "Critical", "component": "Database", "error_type": "ConnectionError", "failure_location": "db_handler.py:8", "code_path": "startup() -> connect_db()", "description": "Database connection fails on every request, entirely blocking core functionality.", "root_cause": "Likely caused by exhausted connection pool capacity or a missing timeout/retry mechanism, based on similar historical database connection bugs.", "historical_references": [{"bug_id": "APACHE-990", "summary": "Database connection pool exhausted under load"}, {"bug_id": "APACHE-1103", "summary": "Connection timeout not configured, hangs indefinitely"}], "duplicate_bug": null}

Output: {"bug_id": "BUG-f25343c8", "recommended_fix": "Add connection pool size limits and a configured timeout with retry logic to the database connection handler.", "fix_steps": ["Review current connection pool configuration for missing size limits.", "Add an explicit timeout value to the connection setup.", "Implement retry-with-backoff logic for transient connection failures.", "Add logging to distinguish pool-exhaustion failures from timeout failures."], "code_example": {"before": "conn = db.connect(host, user, password)", "after": "conn = db.connect(host, user, password, timeout=10, pool_size=20)"}, "validation_steps": ["Simulate high concurrent load and confirm connections succeed within pool limits.", "Verify timeout triggers a clean retry instead of an indefinite hang.", "Confirm no regression under normal single-user load."], "prevention": "Set up monitoring/alerting on connection pool utilization to catch exhaustion trends before they cause outages.", "confidence": 0.72, "reasoning": "No exact duplicate was found, but two historical bugs from the same knowledge base describe closely related connection-pool and timeout issues. Since it's unclear which specific cause applies here, the fix addresses both plausible causes rather than assuming one.", "references_used": [{"type": "historical_bug", "bug_id": "APACHE-990", "summary": "Connection pool exhausted under high load"}, {"type": "historical_bug", "bug_id": "APACHE-1103", "summary": "Missing timeout caused indefinite hang"}]}



example 4:

Input: {"bug_id": "BUG-fabe5064", "severity": "Medium", "component": "Search/Filtering", "error_type": "Incorrect Sort Order", "failure_location": "sort_handler.py:31", "code_path": "apply_filter() -> sort_results()", "description": "Search results occasionally show incorrect sort order when multiple filters are applied together.", "root_cause": "Possibly a sort-stability issue when multiple filter criteria are combined, though the exact trigger condition is unclear.", "historical_references": [{"bug_id": "PY-1002", "summary": "List index out of range when filter returns empty results"}], "duplicate_bug": null}

Output: {"bug_id": "BUG-fabe5064", "recommended_fix": "Review the sort function for stability when multiple filter criteria are combined, and add a deterministic secondary sort key.", "fix_steps": ["Reproduce the issue with a specific combination of filters.", "Check whether the sort function is stable across repeated calls.", "Add a secondary sort key (e.g. by ID) to guarantee deterministic ordering.", "Add regression tests covering multi-filter combinations."], "code_example": {"before": "results.sort(key=lambda x: x.relevance)", "after": "results.sort(key=lambda x: (x.relevance, x.id))"}, "validation_steps": ["Apply multiple filters together and verify consistent ordering across repeated runs.", "Test edge cases with tied relevance scores.", "Confirm single-filter searches remain unaffected."], "prevention": "Always use a deterministic tiebreaker key when sorting by a non-unique field like relevance score.", "confidence": 0.58, "reasoning": "The only historical reference found (PY-1002) is only loosely related - it concerns empty filter results, not sort ordering. Without a closely matching precedent, this recommendation is based on a common general pattern (unstable sort without a tiebreaker) rather than strong historical evidence.", "references_used": [{"type": "historical_bug", "bug_id": "PY-1002", "summary": "Related to filtering, but different root issue"}]}



example 5:

Input: {"bug_id": "BUG-173ed07b", "severity": "Low", "component": "UI/Rendering", "error_type": "Cosmetic Typo", "failure_location": "checkout_form.html:52", "code_path": "renderCheckoutForm() -> button label", "description": "Button label says 'Sumbit' instead of 'Submit' on the checkout form.", "root_cause": "Simple text typo in the static UI label, unrelated to any logic or data-handling issue.", "historical_references": [], "duplicate_bug": null}

Output: {"bug_id": "BUG-173ed07b", "recommended_fix": "Correct the button label text from 'Sumbit' to 'Submit'.", "fix_steps": ["Locate the button label string in checkout_form.html.", "Correct the spelling.", "Verify the change renders correctly on the page."], "code_example": {"before": "<button>Sumbit</button>", "after": "<button>Submit</button>"}, "validation_steps": ["Visually confirm the corrected label on the checkout page.", "Check for the same typo elsewhere in the codebase."], "prevention": "Run a spell-checker or linting tool over UI text strings as part of the review process.", "confidence": 0.99, "reasoning": "This is an unambiguous, single-word spelling correction with no logic involved - no historical grounding is needed for a fix this simple and certain.", "references_used": []}



example 6:

Input: {"bug_id": "BUG-9931aa02", "severity": "High", "component": "Backend/Runtime", "error_type": "Go Runtime Panic: Index Out of Range", "failure_location": "/go/src/app/main_2.go:96", "code_path": "main.main() -> slice/array index access", "description": "Program panics with index out of range when accessing a slice element.", "root_cause": "The program attempted to access an index beyond the slice's actual length, likely due to an assumption that the slice always has a minimum number of elements.", "historical_references": [], "duplicate_bug": null}

Output: {"bug_id": "BUG-9931aa02", "recommended_fix": "Add a bounds check before accessing the slice index, and handle the case where the slice has fewer elements than expected.", "fix_steps": ["Identify the slice being accessed at main_2.go:96.", "Add a length check before the index access.", "Decide on safe fallback behavior when the slice is shorter than expected.", "Add a test case with an undersized slice."], "code_example": {"before": "value := items[7]", "after": "if len(items) > 7 {\n    value := items[7]\n}"}, "validation_steps": ["Run with a deliberately short slice and confirm no panic occurs.", "Confirm normal-length inputs still behave correctly."], "prevention": "Always validate slice/array length before fixed-index access, especially when the length is not guaranteed by an earlier step.", "confidence": 0.65, "reasoning": "No historical bug or duplicate was found for this specific case; the recommendation is based on general best practice for Go slice-bounds errors rather than a specific precedent, so confidence is moderate rather than high.", "references_used": []}



example 7:



Input: {"bug_id": "BUG-77aa10ff", "severity": "Medium", "component": "Notifications", "error_type": "Timeout", "failure_location": "notify_service.py:19", "code_path": "sendNotification() -> external_api_call()", "description": "Notification delivery occasionally times out with no clear pattern.", "root_cause": "Unclear - could be an intermittent external API issue, a network condition, or a misconfigured timeout value; no strong signal points to one specific cause.", "historical_references": [], "duplicate_bug": null}

Output: {"bug_id": "BUG-77aa10ff", "recommended_fix": "Add retry-with-backoff around the external API call, and add structured logging to capture timing details for future diagnosis.", "fix_steps": ["Add a retry mechanism with exponential backoff around the external call.", "Log request duration and failure details on every timeout.", "Set an explicit, documented timeout value rather than relying on a default.", "Monitor logs over the next several occurrences to identify a pattern."], "code_example": {"before": "response = external_api_call(payload)", "after": "response = retry_with_backoff(lambda: external_api_call(payload, timeout=5), max_retries=3)"}, "validation_steps": ["Confirm retries trigger correctly on simulated timeout.", "Review logs after deployment to check for a recurring pattern.", "Confirm normal notification delivery is unaffected."], "prevention": "Add alerting on notification timeout rate so intermittent issues are caught early rather than discovered only when reported.", "confidence": 0.5, "reasoning": "No historical bug, duplicate, or clear pattern was found. Given the intermittent, unclear nature of the issue, this recommendation focuses on resilience (retries, logging) to both mitigate the symptom and gather better evidence, rather than claiming to know the exact root cause.", "references_used": []}



example 8 :

Input: {"bug_id": "BUG-c81f9e02", "severity": "High", "component": "File Upload", "error_type": "MemoryError", "failure_location": "upload_handler.js:67", "code_path": "uploadFile() -> allocateBuffer()", "description": "Large file uploads occasionally fail with a memory allocation error.", "root_cause": "Likely caused by allocating a fixed-size buffer without checking available memory for large files.", "historical_references": [{"bug_id": "AXIS-1741", "summary": "LogHandler can only work in GlobalConfiguration"}], "duplicate_bug": null}

Output: {"bug_id": "BUG-c81f9e02", "recommended_fix": "Stream the file upload in chunks instead of allocating one large buffer, and add a file-size check before upload begins.", "fix_steps": ["Identify the fixed-size buffer allocation in uploadFile().", "Replace it with chunked/streaming upload handling.", "Add a maximum file-size validation before processing begins.", "Add a clear error message when a file exceeds the allowed size."], "code_example": {"before": "const buffer = allocateBuffer(file.size);", "after": "const stream = createUploadStream(file, { chunkSize: 1024 * 1024 });"}, "validation_steps": ["Test uploads with very large files and confirm no memory error occurs.", "Confirm normal-size uploads still work unchanged.", "Verify the size-limit error message displays correctly for oversized files."], "prevention": "Always stream large file uploads rather than loading them fully into memory, and enforce explicit size limits at the API boundary.", "confidence": 0.68, "reasoning": "No directly matching precedent was found - the only historical reference (AXIS-1741) is only superficially related (a configuration bug, not a memory issue). This recommendation is based on the general best practice for handling large file uploads, not a specific proven fix from history, so confidence is moderate rather than high.", "references_used": [{"type": "historical_bug", "bug_id": "AXIS-1741", "summary": "Unrelated configuration bug, weak match only"}]}



example 9 :

Input: {"bug_id": "BUG-e410a7c5", "severity": "Medium", "component": "Authentication", "error_type": "TokenExpiredError", "failure_location": "auth_middleware.py:29", "code_path": "verifyRequest() -> checkToken()", "description": "Users are occasionally logged out mid-session with a token expired error, even during active use.", "root_cause": "Unclear - could be an overly short token expiry window, a clock synchronization issue between services, or a token refresh mechanism failing silently.", "historical_references": [], "duplicate_bug": null}

Output: {"bug_id": "BUG-e410a7c5", "recommended_fix": "Add a silent token-refresh mechanism before expiry, and add logging to capture expiry timing versus actual session activity.", "fix_steps": ["Review the current token expiry duration and refresh logic.", "Implement a background refresh that triggers before the token actually expires.", "Add logging around token issuance, refresh attempts, and expiry checks.", "Monitor logs to identify whether this is a timing, clock-sync, or refresh-logic issue."], "code_example": {"before": "if token.expired: raise TokenExpiredError()", "after": "if token.expires_soon(): token = refresh_token(token)"}, "validation_steps": ["Simulate an active session spanning the token's expiry window and confirm no forced logout occurs.", "Review captured logs after deployment to identify the actual failure pattern.", "Confirm normal token expiry still logs out genuinely inactive sessions."], "prevention": "Always implement proactive token refresh for active sessions rather than relying solely on hard expiry checks.", "confidence": 0.55, "reasoning": "No historical bug or duplicate was found for this issue, and the root cause itself is genuinely uncertain among several plausible explanations. This recommendation focuses on a generally safe mitigation (proactive refresh + logging) rather than claiming to know the exact cause, so confidence is kept low and honest.", "references_used": []}




"""
def remediation_agent(bug_id, severity, component, error_type, failure_location, code_path, description, root_cause, historical_references, duplicate_bug):
    input_data = {
        "bug_id": bug_id,
        "severity": severity,
        "component": component,
        "error_type": error_type,
        "failure_location": failure_location,
        "code_path": code_path,
        "description": description,
        "root_cause": root_cause,
        "historical_references": historical_references,
        "duplicate_bug": duplicate_bug
    }

    user_message = json.dumps(input_data)

    result = call_llm_with_retry(remediation_agent_prompt, user_message)

    if result is None:
        result = {
            "bug_id": bug_id,
            "recommended_fix": "Unable to generate a recommendation due to a processing error.",
            "fix_steps": [],
            "code_example": {},
            "validation_steps": [],
            "prevention": "",
            "confidence": 0.0,
            "reasoning": "LLM call failed after retries",
            "references_used": []
        }

    return result
COMPONENT_MERGE_MAP = {
    "Startup/Initialization": "Initialization",
}


def cluster_root_causes(df, distance_threshold=0.35):
    reasoning_texts = df['reasoning'].fillna("").tolist()

    model = SentenceTransformer('all-MiniLM-L6-v2')
    reasoning_embeddings = model.encode(reasoning_texts, convert_to_numpy=True)

    clustering = AgglomerativeClustering(
        n_clusters=None,
        distance_threshold=distance_threshold,
        metric='cosine',
        linkage='average'
    )
    cluster_labels = clustering.fit_predict(reasoning_embeddings)

    df_temp = df.copy()
    df_temp['cluster_id'] = cluster_labels

    total = len(df_temp)
    root_cause_breakdown = []

    for cluster_id in sorted(df_temp['cluster_id'].unique()):
        cluster_rows = df_temp[df_temp['cluster_id'] == cluster_id]
        count = len(cluster_rows)

        error_type_counts = cluster_rows['error_type'].value_counts()
        top_label = error_type_counts.idxmax()
        distinct_error_types = error_type_counts.index.tolist()

        if top_label == "Unknown":
            top_label = "Unclassified (Log Analysis extraction failed)"

        root_cause_breakdown.append({
            "label": top_label,
            "count": int(count),
            "percent": round((count / total) * 100, 1),
            "bug_ids": cluster_rows['bug_id'].tolist(),
            "distinct_error_types": distinct_error_types
        })

    root_cause_breakdown.sort(key=lambda x: x["count"], reverse=True)

    return root_cause_breakdown


def compute_defect_analytics(df, distance_threshold=0.35):
    total = len(df)

    unknown_mask = df['component'] == 'Unknown'
    unknown_count = int(unknown_mask.sum())
    classified_count = total - unknown_count
    unknown_rate = round((unknown_count / total) * 100, 1) if total > 0 else 0.0

    severity_counts = df['severity'].value_counts()
    severity_breakdown = [
        {"label": label, "count": int(count), "percent": round((count / total) * 100, 1)}
        for label, count in severity_counts.items()
    ]

    classified_df = df[~unknown_mask]
    component_counts = classified_df['component_normalized'].value_counts()
    component_breakdown = [
        {
            "label": label,
            "count": int(count),
            "percent": round((count / classified_count) * 100, 1) if classified_count > 0 else 0.0
        }
        for label, count in component_counts.items()
    ]

    df_dates = pd.to_datetime(df['timestamp']).dt.date
    activity_counts = df_dates.value_counts().sort_index()
    submission_activity = [
        {"date": str(date), "count": int(count)}
        for date, count in activity_counts.items()
    ]

    root_cause_breakdown = cluster_root_causes(df, distance_threshold=distance_threshold)

    return {
        "total_submissions": total,
        "classified_count": classified_count,
        "unknown_count": unknown_count,
        "unknown_rate": unknown_rate,
        "severity_breakdown": severity_breakdown,
        "component_breakdown": component_breakdown,
        "root_cause_breakdown": root_cause_breakdown,
        "submission_activity": submission_activity
    }
def add_resolved_bug_to_kb(bug_id, description, error_type, severity, recommended_fix, source_dataset="live_submissions"):
    base_dir = os.path.dirname(os.path.abspath(__file__))
    embeddings_path = os.path.join(base_dir, "embeddings_real.npy")
    metadata_path = os.path.join(base_dir, "chunks_metadata.csv")

    # Build text the same way the original KB was built: title-equivalent + ". " + description
    # error_type stands in for "title" here, since your bugs don't have a separate title field
    full_text = f"{error_type}. {description}"

    model = SentenceTransformer('all-MiniLM-L6-v2')
    new_embedding = model.encode([full_text], convert_to_numpy=True)

    # Load existing KB
    existing_embeddings = np.load(embeddings_path)
    existing_metadata = pd.read_csv(metadata_path)

    # Append new vector
    updated_embeddings = np.vstack([existing_embeddings, new_embedding])

    # Append new metadata row, same columns as the existing KB
    new_row = pd.DataFrame([{
        "bug_id": bug_id,
        "title": error_type,
        "severity": severity,
        "resolution": recommended_fix,
        "status": "resolved",
        "source_dataset": source_dataset
    }])
    updated_metadata = pd.concat([existing_metadata, new_row], ignore_index=True)

    # Save both back to disk
    np.save(embeddings_path, updated_embeddings)
    updated_metadata.to_csv(metadata_path, index=False)

    return {
        "success": True,
        "new_kb_size": len(updated_metadata)
    }