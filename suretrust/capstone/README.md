# 🐞 DebugAssist – Intelligent Bug Diagnosis & Resolution

An AI-powered software debugging assistance system that analyzes bug reports, stack traces, and error logs, retrieves similar historical defects using semantic similarity, and provides structured insights to help developers diagnose and resolve software issues.

---

## 📌 Overview

**DebugAssist** is designed to reduce the time and effort required for software debugging by using **Natural Language Processing, text embeddings, semantic similarity search, historical defect analysis, and a multi-agent architecture**.

The system accepts information such as:

* Bug descriptions
* Error messages
* Stack traces
* Error logs
* Related debugging information

It then processes the input, retrieves historically similar defects from a **Historical Defect Knowledge Base**, and passes the information through specialized analysis components to generate structured debugging insights.

### Key Capabilities

* 🔍 Bug triage and classification
* 📚 Historical defect retrieval
* 🔗 Semantic similarity search
* 🧩 Duplicate defect detection
* 🧠 Root-cause analysis assistance
* 🛠️ Remediation suggestions
* 📊 Structured debugging results

---

## 🏗️ System Architecture

```text
                         User
                           │
                           ▼
                ┌─────────────────────┐
                │   Bug Submission    │
                │      Module         │
                └──────────┬──────────┘
                           │
                           ▼
                ┌─────────────────────┐
                │ Text Preprocessing  │
                │ & Chunking          │
                └──────────┬──────────┘
                           │
                           ▼
                ┌─────────────────────┐
                │ Text Embeddings     │
                │ Sentence Transformer│
                └──────────┬──────────┘
                           │
                           ▼
                ┌─────────────────────┐
                │ Semantic Similarity │
                │ Search              │
                └──────────┬──────────┘
                           │
                           ▼
          ┌────────────────────────────────┐
          │ Historical Defect Knowledge    │
          │ Base                           │
          │ Mozilla | Apache | Eclipse     │
          └────────────────┬───────────────┘
                           │
                           ▼
                ┌─────────────────────┐
                │ Multi-Agent         │
                │ Analysis Pipeline   │
                └──────────┬──────────┘
                           │
        ┌──────────────────┼──────────────────┐
        ▼                  ▼                  ▼
   Triage Agent      Log Analysis       Root Cause
                        Agent              Agent
        │                  │                  │
        └──────────────────┼──────────────────┘
                           ▼
                ┌─────────────────────┐
                │ Duplicate Detection │
                │ Agent               │
                └──────────┬──────────┘
                           │
                           ▼
                ┌─────────────────────┐
                │ Remediation Agent   │
                └──────────┬──────────┘
                           │
                           ▼
                ┌─────────────────────┐
                │ Structured Findings │
                └─────────────────────┘
```

---

## ⚙️ How It Works

### 1. Bug Submission

The developer provides a bug report, error message, stack trace, or log information through the Streamlit interface.

### 2. Text Processing

The submitted information is cleaned and prepared for analysis. Larger textual inputs can be divided into manageable chunks.

### 3. Embedding Generation

The text is converted into numerical vector representations using:

**Sentence Transformers – `all-MiniLM-L6-v2`**

These embeddings capture the semantic meaning of the bug description rather than relying only on exact keyword matching.

### 4. Semantic Similarity Search

The new bug embedding is compared with embeddings of historical defects using **cosine similarity**.

The system retrieves historically similar defects that can provide useful debugging context.

### 5. Multi-Agent Analysis

The retrieved information and submitted bug are processed through specialized agents:

| Agent                         | Responsibility                               |
| ----------------------------- | -------------------------------------------- |
| **Triage Agent**              | Performs initial bug analysis                |
| **Log Analysis Agent**        | Examines logs, errors, and stack traces      |
| **Root Cause Agent**          | Identifies possible underlying causes        |
| **Duplicate Detection Agent** | Finds potentially related historical defects |
| **Remediation Agent**         | Suggests possible corrective approaches      |

### 6. Structured Output

The system presents the analysis as structured debugging findings to help developers investigate the issue more efficiently.

---

## 📚 Historical Defect Knowledge Base

DebugAssist uses publicly available historical software defect datasets associated with projects such as:

* **Mozilla**
* **Apache**
* **Eclipse**

The historical records are cleaned and transformed into textual representations before generating embeddings.

The knowledge base can contain information such as:

* Bug descriptions
* Error information
* Project information
* Defect categories
* Resolution information
* Related metadata

The historical embeddings are used as the retrieval source for semantic similarity search.

---

## 🧠 Retrieval Approach

The current implementation uses **embedding-based semantic retrieval**.

```text
New Bug
   │
   ▼
Embedding Model
   │
   ▼
Query Vector
   │
   ▼
Compare with Historical Vectors
   │
   ▼
Cosine Similarity
   │
   ▼
Top Similar Defects
```

### Why Semantic Similarity?

Traditional keyword search may fail when two bugs describe the same problem using different words.

For example:

```text
Bug A:
"Application crashes when the user uploads a large file."

Bug B:
"Program terminates unexpectedly while processing oversized uploads."
```

Although the wording differs, their meanings are closely related.

Embedding-based retrieval can identify this semantic relationship.

---

## 🛠️ Technologies Used

| Category             | Technology                 |
| -------------------- | -------------------------- |
| Programming Language | Python                     |
| User Interface       | Streamlit                  |
| Embeddings           | Sentence Transformers      |
| Embedding Model      | `all-MiniLM-L6-v2`         |
| Similarity Search    | Cosine Similarity          |
| ML Library           | Scikit-learn               |
| Text Processing      | LangChain Text Splitters   |
| Data Processing      | pandas                     |
| Knowledge Base       | Historical Defect Datasets |
| Agent Architecture   | Custom Python Classes      |

> **Note:** ChromaDB was explored during development, but the current live implementation performs similarity search using saved embeddings and in-memory cosine similarity.

---

## 📂 Project Structure

```text
DebugAssist/
│
├── app/
│   ├── agents/
│   │   ├── triage_agent.py
│   │   ├── log_analysis_agent.py
│   │   ├── root_cause_agent.py
│   │   ├── duplicate_detection_agent.py
│   │   └── remediation_agent.py
│   │
│   ├── retrieval/
│   │   └── similarity_search.py
│   │
│   ├── preprocessing/
│   │   └── text_processing.py
│   │
│   └── ...
│
├── data/
│   └── historical_defects/
│
├── docs/
│   ├── 01_concepts.md
│   ├── 02_architecture.md
│   ├── 03_agents.md
│   └── 04_knowledge_base.md
│
├── embeddings/
│   └── saved_embeddings
│
├── app.py
├── requirements.txt
└── README.md
```

*The exact folder structure may vary depending on the current repository implementation.*

---

## 🚀 Getting Started

### 1. Clone the Repository

```bash
git clone <YOUR_GITHUB_REPOSITORY_URL>
cd <PROJECT_FOLDER>
```

### 2. Create a Virtual Environment

```bash
python -m venv venv
```

Activate it:

**Windows**

```bash
venv\Scripts\activate
```

**Linux/macOS**

```bash
source venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Run the Application

```bash
streamlit run app.py
```

The application will open in your browser.

---

## 💡 Example Workflow

```text
Input:
"NullPointerException occurs when opening the project configuration."

                    ↓

Text Processing

                    ↓

Embedding Generation
(all-MiniLM-L6-v2)

                    ↓

Semantic Similarity Search

                    ↓

Historical Defect Retrieval

                    ↓

Multi-Agent Analysis

                    ↓

┌──────────────────────────────┐
│ Possible Root Cause          │
│ Similar Historical Defects   │
│ Duplicate Probability        │
│ Suggested Remediation        │
└──────────────────────────────┘
```

---

## 👩‍💻 My Contributions

During the development of DebugAssist, I contributed to:

* Researching AI-assisted software debugging approaches
* Studying RAG and semantic retrieval concepts
* Preparing and exploring historical defect datasets
* Implementing text preprocessing
* Generating embeddings using Sentence Transformers
* Implementing cosine-similarity-based retrieval
* Designing the multi-agent analysis workflow
* Developing Streamlit application components
* Structuring the historical defect knowledge base
* Documenting system architecture and limitations
* Testing and evaluating retrieval behavior

---

## ⚠️ Known Limitations

* Retrieval quality depends on the coverage and quality of the historical defect datasets.
* Historical grounding may be weaker for programming languages that are underrepresented in the datasets.
* Multiple unrelated bugs submitted together may not always be separated correctly.
* The current implementation uses in-memory similarity search rather than a production vector database.
* Remediation suggestions should be reviewed and validated by developers.
* The system is intended as a **developer-assistance tool**, not a replacement for manual debugging, testing, or expert review.

---

## 🔮 Future Enhancements

Potential improvements include:

* Production-ready vector database integration
* Larger and continuously updated defect knowledge base
* Improved duplicate detection
* Support for additional programming languages
* Better root-cause analysis
* LLM-based remediation generation
* Automated code-fix recommendations
* GitHub issue integration
* Jira integration
* Developer feedback loops
* Advanced agent orchestration
* Evaluation metrics for retrieval and diagnosis quality

---

## 📖 Documentation

Detailed project documentation:

| Document                    | Description                                                       |
| --------------------------- | ----------------------------------------------------------------- |
| `docs/01_concepts.md`       | Defect analysis, RAG, semantic similarity, and debugging concepts |
| `docs/02_architecture.md`   | System architecture and data flow                                 |
| `docs/03_agents.md`         | Multi-agent responsibilities and workflow                         |
| `docs/04_knowledge_base.md` | Historical defect knowledge base                                  |

---

## 📌 Project Links

**GitHub Repository:**
`<YOUR_GITHUB_REPOSITORY_URL>`

**Project Report:**
`<YOUR_PROJECT_REPORT_URL>`

---

## 📜 License

This project is developed as part of the **SURE ProEd Generative AI Internship** for educational and project-development purposes.

---

## 🙏 Acknowledgments

Special thanks to **SURE ProEd (formerly SURE Trust)**, trainers, mentors, and peers for their guidance and support throughout the project.
