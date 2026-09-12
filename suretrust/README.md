# MANYAM-GEETHA-SREE-g5-gen-ai
# 🐞 Intelligent Bug Diagnosis Platform with Fix Recommendation Assistance

An AI-powered software debugging platform that analyzes bug reports, defect logs, and stack traces to identify possible issues, determine root causes, detect similar/duplicate bugs, and provide fix recommendations.

---

## 📌 Project Overview

The **Intelligent Bug Diagnosis Platform with Fix Recommendation Assistance** is a Generative AI-based software debugging system designed to assist developers in diagnosing software defects more efficiently.

Traditional debugging often requires developers to manually inspect logs, stack traces, previous bug reports, documentation, and existing solutions. This process can be time-consuming, especially when dealing with large numbers of defects.

This project combines **Generative AI, AI agents, embeddings, semantic search, and a knowledge base** to automate several stages of the bug diagnosis process.

The platform accepts a bug report or stack trace from the user and processes it through specialized AI components to produce an understandable diagnosis and recommended remediation.

---

## 🎓 Internship Project

This project was developed as the **Final Project during a Generative AI Internship in SURETRUST**.

The project provided practical exposure to the application of Generative AI concepts such as:

* Large Language Models (LLMs)
* AI Agents
* Prompt Engineering
* Embeddings
* Semantic Search
* Retrieval-Augmented Generation (RAG)
* Knowledge Base Retrieval
* Automated Bug Analysis
* AI-assisted Root Cause Analysis
* Fix Recommendation

---

## 🎯 Objectives

The main objectives of the project are:

1. To automate the initial analysis of software bug reports.
2. To analyze stack traces and defect logs using AI.
3. To identify possible root causes of software defects.
4. To retrieve relevant information from an existing knowledge base.
5. To identify similar or duplicate bugs.
6. To generate useful fix/remediation recommendations.
7. To provide developers with an easy-to-use debugging interface.
8. To reduce the time required for manual bug investigation.

---

## 🏗️ System Architecture

The overall workflow of the platform is:

```text
                  ┌──────────────────────┐
                  │      User Input      │
                  │ Bug Report / Logs /  │
                  │    Stack Trace      │
                  └──────────┬───────────┘
                             │
                             ▼
                  ┌──────────────────────┐
                  │    Triage Agent     │
                  │ Classification and   │
                  │ Initial Analysis     │
                  └──────────┬───────────┘
                             │
                             ▼
                  ┌──────────────────────┐
                  │  Log Analysis Agent  │
                  │ Stack Trace / Log    │
                  │ Analysis             │
                  └──────────┬───────────┘
                             │
                             ▼
                  ┌──────────────────────┐
                  │ Knowledge Retrieval  │
                  │ Embeddings +         │
                  │ Semantic Search      │
                  └──────────┬───────────┘
                             │
                             ▼
                  ┌──────────────────────┐
                  │  Root Cause Agent    │
                  │ Possible Root Cause  │
                  └──────────┬───────────┘
                             │
                             ▼
                  ┌──────────────────────┐
                  │ Duplicate Detection  │
                  │ Similar Bug Analysis │
                  └──────────┬───────────┘
                             │
                             ▼
                  ┌──────────────────────┐
                  │ Remediation Agent    │
                  │ Fix Recommendation   │
                  └──────────┬───────────┘
                             │
                             ▼
                  ┌──────────────────────┐
                  │   Final Diagnosis    │
                  │ + Recommendations    │
                  └──────────────────────┘
```

---

## 🤖 AI Agents

The platform contains specialized AI components, with each component responsible for a specific debugging task.

### 1. Triage Agent

The Triage Agent performs the initial analysis of the submitted defect.

It helps identify important information such as:

* Bug category
* Severity
* Initial classification
* Relevant defect information

---

### 2. Log Analysis Agent

The Log Analysis Agent analyzes:

* Stack traces
* Error messages
* Logs
* Code-related error information

It identifies patterns and provides an interpretation of the observed error.

---

### 3. Root Cause Agent

The Root Cause Agent analyzes the available bug information and retrieved context to determine the likely underlying cause of the problem.

The objective is to move beyond simply identifying the error and determine **why the error occurred**.

---

### 4. Duplicate Detection Agent

The Duplicate Detection Agent compares the submitted issue with existing bug information.

It helps identify whether a similar or previously reported defect already exists.

This can reduce repeated investigation of the same problem.

---

### 5. Remediation Agent

The Remediation Agent uses the available diagnosis and context to generate possible solutions or remediation recommendations.

The recommendations are intended to assist developers during debugging and should be reviewed and verified before applying them to production systems.

---

## 🧠 Knowledge Base and Semantic Search

The platform uses a knowledge base containing software defect information.

The retrieval process can be represented as:

```text
Knowledge Base
      │
      ▼
Text Cleaning
      │
      ▼
Document Chunking
      │
      ▼
Embedding Generation
      │
      ▼
Vector Representations
      │
      ▼
Semantic Search
      │
      ▼
Relevant Knowledge
```

When a user submits a bug report, the query is converted into an embedding and compared with stored knowledge-base embeddings.

Relevant information is then retrieved and used as additional context during AI-based analysis.

---

## 🔢 Embeddings

The project uses the Sentence Transformers model:

```text
all-MiniLM-L6-v2
```

The model converts textual information into numerical vector representations.

For example:

```text
Bug Text
   ↓
Sentence Transformer
   ↓
Numerical Embedding
   ↓
Similarity Search
   ↓
Relevant Bug Information
```

The project stores pre-generated embeddings in:

```text
src/embeddings_real.npy
```

and associated metadata in:

```text
src/chunks_metadata.csv
```

---

## 🔎 Retrieval-Augmented Generation

The system applies the idea of Retrieval-Augmented Generation (RAG) by combining retrieved knowledge with AI-based analysis.

The general process is:

```text
User Bug Report
      ↓
Create Query Embedding
      ↓
Search Knowledge Base
      ↓
Retrieve Relevant Information
      ↓
Provide Context to AI
      ↓
Generate Diagnosis
      ↓
Generate Recommendation
```

This allows the AI system to use information from the project's knowledge base instead of relying only on its internal model knowledge.

---

## 📊 Dataset and Data Processing

The project contains multiple datasets related to software defects, bug reports, and stack traces.

Important data resources include:

```text
data/
├── knowledge_base_cleaned.csv
├── knowledge_base_with_severity.csv
├── knowledge_basic_combined.csv
├── chunks_df.csv
├── stack_trace_combined.csv
└── stack_traces/
```

The stack-trace dataset contains examples from multiple programming languages, including:

* C
* C++
* CSS
* Go
* HTML
* Java
* JavaScript
* PHP
* Python
* Rust
* TypeScript

The data is processed and prepared for AI-based analysis and evaluation.

---

## 🖥️ Application Features

The Streamlit application provides multiple sections.

### 🏠 Dashboard

Provides an overview of the application.

### 🐞 Submit Bug

Users can submit:

* Bug descriptions
* Defect logs
* Stack traces
* Text files
* Log files

The submitted information is then processed for diagnosis.

### 📊 Analytics Dashboard

Provides analysis and evaluation-related information.

### 🧠 Knowledge Base

Allows users to explore the knowledge base used by the application.

### ℹ️ About the App

Provides information about the platform.

### 📚 User Guide

Provides instructions for using the application.

---

## 🛠️ Technologies Used

### Programming Language

* Python

### AI / GenAI

* Generative AI
* Large Language Models
* AI Agents
* Prompt Engineering
* Sentence Transformers
* Embeddings
* Semantic Search
* Retrieval-Augmented Generation

### Data Processing

* Pandas
* NumPy

### Application

* Streamlit

### Data Storage / Artifacts

* CSV
* NumPy `.npy`
* Pickle-based model/vectorizer artifacts

---

## 📁 Project Structure

```text
Creation-of-Intelligent-Bug-Diagnosis-Platform-with-Fix-Recommendation-Assistance-Group-1-main/
│
├── data/
│   ├── knowledge_base_cleaned.csv
│   ├── knowledge_base_with_severity.csv
│   ├── chunks_df.csv
│   ├── stack_trace_combined.csv
│   └── stack_traces/
│
├── docs/
│   ├── 01_concepts.md
│   ├── 02_architecture.md
│   ├── 03_agents.md
│   ├── 04_knowledge_base.md
│   ├── Test_Report.md
│   ├── User_guide.md
│   └── project_report.md
│
├── notebooks/
│   ├── 01_dataset_collection.ipynb
│   ├── 02_triage_agent.ipynb
│   ├── 03_analytics_and_testing.ipynb
│   └── agents.py
│
├── src/
│   ├── app.py
│   ├── agents.py
│   ├── chunks_metadata.csv
│   ├── embeddings_real.npy
│   └── vectorizer.pkl
│
├── requirements.txt
└── README.md
```

---

## ⚙️ Installation

### 1. Clone the repository

```bash
git clone <repository-url>
```

### 2. Navigate to the project

```bash
cd Creation-of-Intelligent-Bug-Diagnosis-Platform-with-Fix-Recommendation-Assistance-Group-1-main
```

### 3. Install dependencies

```bash
python -m pip install -r requirements.txt
```

### 4. Run the Streamlit application

Navigate to the `src` directory:

```bash
cd src
```

Then run:

```bash
python -m streamlit run app.py
```

The application will open in the browser.

---

## 🔐 Environment Configuration

If the project requires API-based AI services, configure the required API keys through environment variables or the project's environment configuration.

Do not commit real API keys or credentials to GitHub.

Example:

```text
.env
```

should be kept private and should be included in `.gitignore`.

---

## 🚀 How the System Works

### Step 1 — Submit a Bug

The developer provides a bug description, error log, or stack trace.

### Step 2 — Initial Triage

The Triage Agent analyzes the issue and determines its initial classification.

### Step 3 — Log Analysis

The Log Analysis Agent examines the stack trace and error information.

### Step 4 — Knowledge Retrieval

The system searches the knowledge base using semantic similarity.

### Step 5 — Root Cause Analysis

The Root Cause Agent uses the bug information and retrieved context to identify the likely cause.

### Step 6 — Duplicate Detection

The system checks for similar existing defects.

### Step 7 — Fix Recommendation

The Remediation Agent generates possible solutions.

### Step 8 — Final Result

The platform presents the diagnosis and recommendations through the Streamlit interface.

---

## 📈 Benefits

The proposed platform can help:

* Reduce manual debugging effort
* Speed up initial bug investigation
* Organize defect analysis
* Identify similar issues
* Retrieve relevant historical information
* Provide AI-assisted root cause analysis
* Generate actionable remediation suggestions

---

## ⚠️ Limitations

AI-generated diagnoses and recommendations should not be treated as guaranteed solutions.

The quality of the output depends on:

* Input quality
* Knowledge-base quality
* Retrieved context
* Model capabilities
* Complexity of the software defect

Developers should validate generated recommendations before applying them to real systems.

---

## 🔮 Future Enhancements

Possible future improvements include:

* Automatic code patch generation
* Integration with GitHub and Jira
* Improved code-aware debugging
* Larger and continuously updated knowledge bases
* Advanced RAG techniques
* Better agent orchestration
* Automated regression testing of generated fixes
* Continuous learning from resolved defects
* Integration with CI/CD pipelines

---
