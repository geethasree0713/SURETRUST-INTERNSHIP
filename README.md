![Planting](https://raw.githubusercontent.com/geethasree0713/SURETRUST-INTERNSHIP/main/suretrust/community-services/planting.png)
# SURE ProEd (formerly SURE Trust)

## Skill Upgradation for Rural youth Empowerment Trust

---

## Student Details

**Name:** Manyam Geetha Sree

**Email ID:** geethamsree9@gmail.om

**College Name:** Nitte Meenakshi Institute of Technology, Bengaluru

**Branch/Specialization:** Information Science Engineering


---

## Course Details

**Course Opted:** Generative AI

**Instructor Name:** Prujith Radhakrishnan

**Duration:** 6 months

---

## Trainer Details

**Trainer Name:** Radha Kumari Challa

**Trainer Email ID:** radha@sureproed.in


---



## Overall Learning

During my SURE ProEd Generative AI internship, I developed a practical understanding of Generative AI, Retrieval-Augmented Generation (RAG), embeddings, semantic search, AI agents, and AI-assisted software development.

The internship provided me with hands-on experience in understanding real-world problems, researching suitable AI techniques, designing system architectures, working with datasets, implementing retrieval pipelines, and documenting technical solutions.

As part of the internship, I worked on **DebugAssist: Intelligent Bug Diagnosis & Resolution**, an AI-powered system designed to assist developers in analyzing software bugs, identifying similar historical defects, determining possible root causes, detecting duplicate issues, and suggesting possible resolutions.

Through this project, I strengthened my skills in:

- Generative AI
- Retrieval-Augmented Generation (RAG)
- Text embeddings
- Semantic similarity search
- Historical defect analysis
- Multi-agent system design
- Python
- Streamlit
- Data preprocessing
- Software debugging concepts
- Technical documentation
- Problem-solving
- System design

---

## Project Completed

**[Project : DebugAssist – Intelligent Bug Diagnosis & Resolution](#project1)**

---

## Project Introduction

### Project: DebugAssist – Intelligent Bug Diagnosis & Resolution

**DebugAssist: Intelligent Bug Diagnosis & Resolution** is an AI-powered software debugging assistance system designed to help developers analyze software defects more efficiently.

The system accepts bug reports, stack traces, error logs, or related debugging information and processes the submitted information to identify important characteristics of the defect.

The project combines:

- Natural Language Processing
- Text embeddings
- Semantic similarity
- Retrieval-Augmented Generation concepts
- Historical defect analysis
- Multi-agent architecture

The system uses a **Historical Defect Knowledge Base** created using publicly available software defect datasets from projects such as Mozilla, Apache, and Eclipse through Kaggle.

Historical defect records are processed and converted into embeddings. When a new bug is submitted, its textual information is also converted into an embedding and compared with historical defects using semantic similarity.

The retrieved historical defects provide additional context that can support bug analysis, duplicate detection, root-cause identification, and possible resolution recommendations.

---

## How the System Works

The overall workflow of DebugAssist is:

```text
                         User
                           |
                           v
              Bug Submission Module
                           |
                           v
        Bug Report / Stack Trace / Error Log
                           |
                           v
              Text Processing & Chunking
                           |
                           v
                    Text Embeddings
                           |
                           v
             Semantic Similarity Search
                           |
                           v
        Historical Defect Knowledge Base
                           |
                           v
                 Multi-Agent Pipeline
                           |
        +------------------+------------------+
        |                  |                  |
        v                  v                  v
   Triage Agent      Log Analysis Agent   Root Cause Agent
        |                  |                  |
        +------------------+------------------+
                           |
                           v
                 Duplicate Detection
                       Agent
                           |
                           v
                  Remediation Agent
                           |
                           v
              Structured Findings
                           |
                           v
                 Resolution Display
```

---

## Historical Defect Knowledge Base

A major component of DebugAssist is the **Historical Defect Knowledge Base**.

The knowledge base contains historical software defects collected from publicly available datasets associated with projects such as:

- Mozilla
- Apache
- Eclipse

The historical bug records are cleaned and processed before being used for retrieval.

The available defect information can include:

- Bug descriptions
- Error information
- Project information
- Defect categories
- Historical resolution information
- Related metadata

The processed textual information is converted into vector representations using an embedding model.

When a new bug is submitted, its textual representation is converted into an embedding and compared with the stored historical defect embeddings.

The system uses **cosine similarity** to identify historically similar defects.

---

## Multi-Agent Pipeline

DebugAssist is designed using multiple specialized agents, where each agent is responsible for a particular stage of the analysis process.

### 1. Triage Agent

The Triage Agent performs the initial analysis of the submitted bug.

Its responsibilities include:

- Understanding the reported issue
- Extracting important information
- Identifying the general nature of the problem
- Preparing the bug information for further analysis

### 2. Log Analysis Agent

The Log Analysis Agent focuses on error messages, logs, and stack traces.

It helps identify:

- Important error messages
- Exception information
- Stack-trace details
- Potential failure points
- Relevant technical keywords

### 3. Root Cause Agent

The Root Cause Agent focuses on determining the likely reason behind the reported failure.

It considers:

- Bug description
- Error information
- Stack traces
- Retrieved historical defects
- Similarity results

The objective is to provide a structured explanation of the possible underlying cause.

### 4. Duplicate Detection Agent

The Duplicate Detection Agent compares the submitted bug with historical defects.

It uses semantic similarity to identify previously reported issues that may describe the same or a closely related problem.

This can help developers identify defects that may already exist in the historical knowledge base.

### 5. Remediation Agent

The Remediation Agent focuses on possible corrective actions.

It uses the available bug information and historical context to identify possible approaches for resolving the reported issue.

The remediation component can be further enhanced with LLM-based generation and confirmed fixes in future versions.

---

## Technologies Used

### Programming Language

- Python

### User Interface

- Streamlit

Streamlit is used to create the interactive interface for submitting bug information and displaying the analysis results.

### Embedding Model

- Sentence Transformers
- `all-MiniLM-L6-v2`

The embedding model converts textual bug information into numerical vector representations.

### Vector Similarity Search

- Scikit-learn
- Cosine Similarity
- Saved embeddings
- In-memory similarity search

The current implementation performs similarity search using saved embeddings and cosine similarity.

**ChromaDB** was installed and tested during development, but the current live application uses in-memory similarity search.

### Text Processing

- LangChain Text Splitters

LangChain text splitters are used to divide larger textual information into manageable chunks.

### Data Processing

- pandas

Pandas is used for loading, cleaning, transforming, and exploring historical defect datasets.

### Agent Orchestration

- Python custom classes

Custom Python classes are used to organize the responsibilities and workflow of the different agents in the current milestone.

---

## Project Architecture

The project follows a modular architecture:

```text
DebugAssist
│
├── User Interface
│   └── Streamlit Application
│
├── Input Processing
│   ├── Bug Report
│   ├── Stack Trace
│   └── Error Logs
│
├── Data Processing
│   ├── Cleaning
│   ├── Chunking
│   └── Preprocessing
│
├── Embedding Layer
│   └── Sentence Transformers
│
├── Retrieval Layer
│   ├── Saved Embeddings
│   └── Cosine Similarity
│
├── Historical Knowledge Base
│   ├── Mozilla Defects
│   ├── Apache Defects
│   └── Eclipse Defects
│
├── Multi-Agent Pipeline
│   ├── Triage Agent
│   ├── Log Analysis Agent
│   ├── Root Cause Agent
│   ├── Duplicate Detection Agent
│   └── Remediation Agent
│
└── Output
    └── Structured Bug Analysis
```

---

## Technologies Used

| Category | Technology |
|---|---|
| Programming Language | Python |
| UI | Streamlit |
| Embeddings | Sentence Transformers |
| Embedding Model | all-MiniLM-L6-v2 |
| Similarity Search | Cosine Similarity |
| Machine Learning Library | Scikit-learn |
| Text Splitting | LangChain |
| Data Processing | pandas |
| Knowledge Base | Historical Defect Datasets |
| Agent Architecture | Custom Python Classes |

---

## Roles and Responsibilities

During the development of DebugAssist, I worked on the following areas:

### Research and Requirement Analysis

- Studied software defect analysis and debugging workflows.
- Studied the structure of bug reports and stack traces.
- Researched Retrieval-Augmented Generation and semantic search.
- Analyzed how historical defects can support bug diagnosis.

### Dataset Preparation

- Worked with publicly available historical defect datasets.
- Explored and cleaned defect records.
- Prepared textual information for embedding and retrieval.
- Studied the structure and quality of historical defect information.

### Embeddings and Semantic Search

- Implemented text embedding using Sentence Transformers.
- Used `all-MiniLM-L6-v2` for generating text embeddings.
- Used cosine similarity for identifying related historical defects.
- Designed the historical defect retrieval workflow.

### Multi-Agent Architecture

- Designed the responsibilities of specialized agents.
- Created custom Python-based agent components.
- Defined the expected input, processing, and output of each agent.
- Designed the flow between different analysis stages.

### Application Development

- Worked with Streamlit for the project interface.
- Integrated the bug submission and analysis workflow.
- Organized the project into modular components.

### Documentation

- Prepared technical documentation.
- Documented system architecture and data flow.
- Documented agent responsibilities.
- Documented the Historical Defect Knowledge Base.
- Recorded project limitations and future improvements.

---



### Project Repository

[**→ View GitHub Repository**]([[PUT_YOUR_GITHUB_REPOSITORY_LINK_HERE](https://github.com/geethasree0713/SURETRUST-INTERNSHIP/tree/main/suretrust/capstone)](https://github.com/sure-trust/MANYAM-GEETHA-SREE-g5-gen-ai/tree/main/Creation-of-Intelligent-Bug-Diagnosis-Platform-with-Fix-Recommendation-Assistance-Group-1-main))

### Project Report

[**→ View Full Project Report**]([[PUT_YOUR_PROJECT_REPORT_LINK_HERE](https://github.com/geethasree0713/SURETRUST-INTERNSHIP/blob/main/suretrust/capstone/REPORT-sureTrust.pdf)](https://github.com/sure-trust/MANYAM-GEETHA-SREE-g5-gen-ai/blob/main/Creation-of-Intelligent-Bug-Diagnosis-Platform-with-Fix-Recommendation-Assistance-Group-1-main/REPORT-sureTrust.pdf))

---

## Known Limitations

- Historical grounding can be weaker for programming languages that are less represented in the original historical datasets, such as Rust, Go, and TypeScript.
- Compound submissions containing multiple unrelated issues may result in a combined error classification instead of separating each issue independently.
- Retrieval quality depends on the coverage and quality of the historical defect knowledge base.
- The current live application uses in-memory cosine similarity over saved embeddings rather than a production vector database.
- LLM-based remediation generation can be affected by the API provider's usage limits and availability.
- The system is designed to assist developers and does not replace manual debugging, testing, or expert review.

---

## Future Enhancements

The project can be extended with:

- Integration of a production-ready vector database.
- Addition of more historical defect datasets.
- Continuous updating of the knowledge base using confirmed fixes.
- Improved duplicate bug detection.
- Support for additional programming languages.
- Stronger LLM-based remediation generation.
- Automated code-fix recommendations.
- Integration with GitHub and Jira issue tracking systems.
- Developer feedback mechanisms for improving future recommendations.
- Advanced multi-agent orchestration using suitable frameworks.

---


## Learnings from LST and SST

The LST and SST sessions provided me with valuable learning beyond the technical aspects of the internship.

These sessions helped me improve my:

- Communication skills
- Presentation skills
- Teamwork
- Problem-solving approach
- Professional communication
- Time management
- Confidence in presenting technical work

The sessions also helped me understand how to communicate technical concepts clearly, participate effectively in discussions, and work collaboratively with peers and mentors.

---

## Community Services

As part of the SURE ProEd internship program, I participated in community-oriented activities that helped me understand the importance of social responsibility and contributing to society.

### Activities Involved

- **Food Distribution** – Participated in a food distribution activity and contributed towards supporting members of the community.

- **Tree Plantation Drive** – Participated in a tree plantation activity and contributed towards environmental awareness and sustainability.

### Impact / Contribution

- Contributed actively to the successful completion of the community activities.
- Supported initiatives focused on community welfare and environmental responsibility.
- Developed better communication and coordination skills through participation.
- Gained a greater understanding of social responsibility and community involvement.
- Improved teamwork, empathy, and interpersonal skills.

### Photos

![Community Service - Food Distribution]([https://github.com/sure-trust/MANYAM-GEETHA-SREE-g5-gen-ai/blob/main/community-services/food.png?raw=true](https://github.com/geethasree0713/SURETRUST-INTERNSHIP/blob/main/suretrust/community-services/food.png))

![Community Service - Tree Plantation]([https://github.com/sure-trust/MANYAM-GEETHA-SREE-g5-gen-ai/blob/main/community-services/planting.png?raw=true](https://github.com/geethasree0713/SURETRUST-INTERNSHIP/blob/main/suretrust/community-services/planting.png))

---

## Certificate

The internship certificate serves as an official acknowledgment of my successful participation and completion of the SURE ProEd internship program.

The internship provided me with practical exposure to Generative AI concepts, project development, research, documentation, and professional skills.

The certificate represents my participation in the program and the knowledge and experience gained throughout the internship.

### Internship Certificate

![SURE ProEd Internship Certificate](PUT_YOUR_CERTIFICATE_IMAGE_LINK_HERE)
