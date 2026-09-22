# RepoRAG — Chat With a Git Repository

RepoRAG is a repository-aware RAG (Retrieval-Augmented Generation) system that allows developers to ask natural-language questions about a Git repository.

Instead of relying only on semantic vector search, RepoRAG combines **semantic retrieval, entity-aware retrieval, repository structure retrieval, version-aware retrieval, and LLM-based reranking** to improve answers to code-specific questions.

## Why RepoRAG?

Traditional RAG systems work well when the question is semantically similar to the indexed content.

However, software repositories contain additional information that semantic similarity alone may not capture:

* File and class names
* Repository structure
* Versioned implementations
* Relationships between classes
* Cross-file dependencies
* Implementation-specific details

For example, a question such as:

> "How does `TmcComponentManager` interact with `TmcBaseDevice`?"

may require retrieving two specific files even if semantic search does not rank both highly.

RepoRAG addresses these retrieval challenges with multiple retrieval strategies.

---

## Architecture

```text
                         User Question
                              │
                              ▼
                    ┌───────────────────┐
                    │   Query Analysis  │
                    └─────────┬─────────┘
                              │
             ┌────────────────┼────────────────┐
             │                │                │
             ▼                ▼                ▼
      Semantic Search   Entity Retrieval   Structure/
        ChromaDB        File/Class Names    Version Search
             │                │                │
             └────────────────┼────────────────┘
                              ▼
                    Candidate Chunks
                              │
                              ▼
                    Metadata-Aware Reranker
                              │
                              ▼
                       Top Relevant Chunks
                              │
                              ▼
                    Grounded LLM Generation
                              │
                              ▼
                    Answer + Source Citations
```

---

## Retrieval Pipeline

### 1. Repository ingestion

RepoRAG scans the repository and indexes supported source/documentation files.

Currently supported extensions include:

```text
.py
.md
.rst
.yaml
.yml
.toml
.json
```

Generated and irrelevant directories such as `.git`, virtual environments, caches, and `node_modules` are ignored.

---

### 2. Chunking

Repository files are divided into bounded chunks.

The current chunking configuration uses:

```text
Chunk size: 3000 characters
Overlap:    300 characters
```

Bounding chunks is important because very large source files can create extremely large embedding requests.

---

### 3. Embeddings

Each chunk is converted into an embedding using:

```text
text-embedding-3-small
```

The embeddings are stored in a persistent ChromaDB collection.

```text
Chroma collection:
repository_code
```

---

### 4. Semantic retrieval

The user's question is embedded and compared against repository chunks using vector similarity.

A distance threshold is applied to prevent obviously irrelevant chunks from entering the final context.

Current threshold:

```text
1.4
```

Semantic retrieval works particularly well for questions such as:

```text
How does this project communicate with Tango?

What is TmcComponentManager?

How does liveliness probing work?
```

---

## Why Semantic Search Alone Wasn't Enough

During development, several retrieval failure cases were discovered.

### Failure case 1 — Entity relationships

For example:

```text
How does TmcComponentManager interact with TmcBaseDevice?
```

Semantic retrieval initially found `TmcComponentManager` but failed to retrieve the relevant `TmcBaseDevice` implementation.

This demonstrated that semantic similarity alone is not always sufficient for code repositories.

### Solution

RepoRAG added lightweight **entity/file-name retrieval**.

The system identifies likely repository files from entities mentioned in the question and retrieves relevant chunks from those files.

---

## Entity-Aware Retrieval

RepoRAG can detect repository entities from questions.

For example:

```text
TmcComponentManager
TmcBaseDevice
```

can be mapped to files such as:

```text
tmc_component_manager.py
tmc_base_device.py
```

The relevant chunks from those files are then selected using the reranker rather than simply taking the first chunks.

This improved cross-file questions involving relationships between classes.

---

## Repository Structure Retrieval

Some questions are about the organization of a repository rather than a specific implementation.

For example:

```text
What is v1, v2 and v3 in this repository?
```

Semantic search may retrieve arbitrary code or tests.

RepoRAG therefore maintains a lightweight representation of the repository structure.

Example:

```text
src/ska_tmc_common/v1/
src/ska_tmc_common/v2/
src/ska_tmc_common/v3/
src/ska_tmc_common/v4/
```

This allows the system to answer structural questions using repository evidence.

---

## Version-Aware Retrieval

Version comparison questions exposed another retrieval problem.

For example:

```text
What is the difference between v1, v2, v3 and v4?
```

Semantic search could retrieve mostly v2/v4 code while missing other versions.

RepoRAG therefore detects explicitly mentioned versions:

```text
v1
v2
v3
v4
```

and retrieves implementation files belonging to those versioned directories.

For comparison questions, the retrieval pipeline attempts to ensure that each requested version contributes relevant context before final reranking.

---

## LLM Reranking

After retrieving candidates from the different retrieval strategies, RepoRAG uses an LLM-based reranker.

The reranker receives:

```text
Question
File path
Line range
Code chunk
```

and evaluates how useful each chunk is for answering the question.

The reranker considers:

* Whether the chunk contains the requested entity
* Whether it explains relationships between entities
* Whether it contains implementation details
* Whether it belongs to the relevant version
* Whether it is implementation code or unrelated test code

This helps reduce irrelevant context before generation.

---

## Metadata-Aware Retrieval

Repository metadata is preserved throughout the retrieval pipeline.

Each chunk contains information such as:

```text
File
Start line
End line
```

For example:

```text
File:
src/ska_tmc_common/tmc_component_manager.py

Lines:
337-422
```

This metadata is provided to the reranker and the generation model.

It also allows answers to provide traceable source references.

---

## Grounded Generation

The final LLM receives only the retrieved repository context.

The generation prompt explicitly instructs the model:

```text
Do not invent information.

Use only the provided repository context.

If the context is insufficient, say so.

Cite repository sources.
```

Answers therefore include references such as:

```text
[Source 1]
[Source 2]
[Structure]
```

and provide a Sources section containing the relevant files and line ranges.

---

## No-Answer Handling

RepoRAG is designed not to hallucinate when the repository does not contain enough evidence.

For example, a question unrelated to the repository may produce:

```text
I don't have enough information in the retrieved
repository context to answer this.
```

This grounding behavior is an important part of the system.

---

## Example Questions

### General repository question

```text
What is TmcComponentManager?
```

### Cross-file relationship

```text
How does TmcComponentManager interact with TmcBaseDevice?
```

### Architecture

```text
How does this project communicate with Tango?
```

### Repository structure

```text
What is v1, v2 and v3 in this repository?
```

### Version comparison

```text
What is the difference between v1, v2, v3 and v4?
```

### Unsupported question

```text
Who is Akshay Sonawane?
```

The system should avoid answering questions when the repository context does not contain sufficient evidence.

---

## Project Structure

```text
repoRAG/
│
├── app/
│   ├── __init__.py
│   ├── ingest.py
│   ├── retrieve.py
│   ├── generate.py
│   ├── chunker.py
│   ├── vector_store.py
│   ├── reranker.py
│   ├── repository_structure.py
│   └── entity_search.py
│
├── data/
├── chroma_db/
├── .env
├── .gitignore
└── requirements.txt
```

### Main components

| Component                 | Responsibility                                 |
| ------------------------- | ---------------------------------------------- |
| `ingest.py`               | Repository ingestion                           |
| `chunker.py`              | Splits source files into chunks                |
| `vector_store.py`         | Creates embeddings and stores them in ChromaDB |
| `retrieve.py`             | Main hybrid retrieval pipeline                 |
| `entity_search.py`        | Entity/file-name retrieval                     |
| `repository_structure.py` | Repository structure and version retrieval     |
| `reranker.py`             | LLM-based candidate reranking                  |
| `generate.py`             | Grounded answer generation                     |

---

## Tech Stack

```text
Python
OpenAI Embeddings
OpenAI LLM
ChromaDB
python-dotenv
```

---

## Setup

Clone the project:

```bash
git clone <your-repository-url>
cd repoRAG
```

Create a virtual environment:

```bash
python3 -m venv venv
source venv/bin/activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Create `.env`:

```text
OPENAI_API_KEY=your_api_key
```

---

## Index a Repository

Configure the repository path in the ingestion configuration and run:

```bash
python app/ingest.py
```

The repository will be:

```text
Scanned
   ↓
Filtered
   ↓
Chunked
   ↓
Embedded
   ↓
Stored in ChromaDB
```

---

## Ask Questions

Run:

```bash
python app/retrieve.py
```

Then enter a repository question:

```text
Ask a question about the repository:
```

Example:

```text
How does TmcComponentManager interact with TmcBaseDevice?
```

---

## Design Decisions

### Why hybrid retrieval?

A repository contains several types of information.

Semantic similarity is useful for conceptual questions, but exact entities, filenames, repository structure, and version directories can be more important for other questions.

RepoRAG therefore combines multiple retrieval strategies instead of relying exclusively on vector search.

### Why reranking?

Initial retrieval produces candidates rather than guaranteed answers.

Reranking allows the system to evaluate the candidates against the actual question before sending them to the generation model.

### Why metadata-aware reranking?

Two chunks can have similar semantic content but very different importance depending on their file and location.

File paths and line ranges provide additional signals to the reranker.

### Why grounding?

Code assistants can easily hallucinate relationships or APIs that don't exist.

Restricting generation to retrieved repository context helps keep answers traceable to the actual codebase.

---

## What I Learned Building RepoRAG

One of the main lessons from the project was that **RAG quality is not determined only by the embedding model**.

During testing, retrieval failures led to progressively more targeted retrieval strategies:

```text
Semantic Retrieval
       ↓
Observed failure
       ↓
Entity Retrieval
       ↓
Observed failure
       ↓
Repository Structure Retrieval
       ↓
Observed failure
       ↓
Version-Aware Retrieval
       ↓
Metadata-Aware Reranking
```

This iterative approach helped identify where retrieval was failing instead of simply increasing the number of retrieved chunks.

---

## Current Limitations

RepoRAG is currently a learning/portfolio prototype rather than a production-ready repository assistant.

Current limitations include:

* LLM-based reranking adds latency and API cost.
* Version comparison depends on the repository's versioned directory structure.
* Repository entities are currently identified using lightweight filename matching.
* Complex relationships spanning many files may still require additional retrieval strategies.
* The system does not yet maintain a full dependency graph or AST-based code graph.
* Retrieval quality depends on the quality and granularity of chunking.

---

## Future Improvements

Possible future improvements include:

* AST-based code parsing
* Symbol/class/function indexing
* Import/dependency graph retrieval
* Dedicated cross-encoder reranking
* Query rewriting
* Hybrid lexical + vector search
* Better version comparison
* Git history-aware retrieval
* Repository-level dependency graphs
* FastAPI backend
* Web UI for interactive repository exploration
* Evaluation dataset with retrieval metrics such as Recall@K and MRR

---

## Key Takeaway

RepoRAG explores how RAG can be adapted specifically for **software repositories**, where questions are often structural, entity-specific, and cross-file rather than purely semantic.

The core idea is:

```text
Don't just retrieve what is semantically similar.

Retrieve what is relevant to the way
developers actually ask questions about code.
```
