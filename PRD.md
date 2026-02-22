# RepoLens API (Repo Q&A and Intelligence)
PRD and Implementation Plan

## 1. Summary
RepoLens is a data driven REST API that ingests a Git repository, indexes its content, and lets users ask questions about the repository using retrieval augmented generation (RAG). It is designed to be demonstrable, well documented, and extendable into an MCP compatible service later.

This fits the coursework minimum requirements by:
- Implementing at least one SQL backed data model with full CRUD.  [oai_citation:0‡COMP3011_Coursework1_Brief__2025_2026 (1).pdf](sediment://file_00000000d5d07246bfd42520e4b496ea)
- Exposing at least four HTTP endpoints returning JSON.  [oai_citation:1‡COMP3011_Coursework1_Brief__2025_2026 (1).pdf](sediment://file_00000000d5d07246bfd42520e4b496ea)
- Using correct HTTP status and error codes.  [oai_citation:2‡COMP3011_Coursework1_Brief__2025_2026 (1).pdf](sediment://file_00000000d5d07246bfd42520e4b496ea)
- Being demonstrable via local execution and optionally hosted.  [oai_citation:3‡COMP3011_Coursework1_Brief__2025_2026 (1).pdf](sediment://file_00000000d5d07246bfd42520e4b496ea)
- Producing API documentation and a technical report as required deliverables. 

## 2. Problem Statement
When joining a new project or starting coursework, understanding an unfamiliar codebase is slow and frustrating. Developers need a way to ask high level questions like:
- Where is the authentication logic implemented
- How do requests flow through the API
- Which modules depend on this file
- What changed recently and why

RepoLens provides:
- Structured ingestion and indexing of a repo
- Question answering with citations back to specific files and line ranges
- Repeatable analysis jobs you can compare over time

## 3. Goals and Non Goals

### Goals
- Provide CRUD for repositories and analyses stored in SQL
- Ingest a Git repo at a chosen commit and index its files
- Provide repo scoped Q&A with citations
- Provide at least one additional analytic endpoint that is not just chat
- Provide clean OpenAPI docs, tests, and a demo flow for the oral exam

### Non Goals (for coursework scope)
- Perfect LLM answers or full static analysis coverage
- Full GitHub App installation, OAuth, or webhooks
- Huge repo scalability, multi tenant enterprise features
- UI frontend (optional only if time allows)

## 4. Target Users and Use Cases

### Personas
1. Student developer
- Wants to understand coursework starter repos quickly
- Wants a portfolio project that looks serious

2. Junior engineer
- Wants quick answers about module responsibilities
- Wants dependency and change summaries

### Key Use Cases
- Add a repo, run ingestion, ask questions about architecture
- Track findings and answers over time as the repo changes
- Generate a dependency summary for a file or folder

## 5. High Level Architecture

### Components
1. FastAPI server
- REST endpoints for CRUD, ingestion jobs, Q&A

2. SQL database (PostgreSQL recommended, SQLite allowed for local)
- Stores repositories, jobs, documents, questions, answers, findings

3. Ingestion pipeline
- Clones repo or pulls latest
- Walks files using allowlist and size limits
- Chunks files into document chunks with file_path and line ranges
- Generates embeddings for chunks and stores them

4. Retrieval and generation
- Embed the user question
- Retrieve top K chunks for that repo
- Send prompt to LLM with chunks and instructions to cite sources
- Persist question and answer, including citations JSON

### Data Flow
Repo created -> ingestion job created -> documents stored -> question created -> answer created

## 6. Technology Stack

### Backend
- Python 3.11+
- FastAPI
- SQLAlchemy ORM
- Alembic migrations
- PostgreSQL (primary) or SQLite (local mode)

### AI
- Embeddings: OpenAI embeddings or compatible provider (configurable)
- LLM: OpenAI chat model or compatible provider (configurable)
- Vector storage: store embedding vectors in SQL (simple approach) or pgvector if using Postgres

### Tooling
- pytest for tests
- ruff or black for formatting
- uvicorn for local run
- Docker for reproducible runs (optional but recommended)
- Swagger UI via FastAPI OpenAPI output for documentation

### Why this stack
FastAPI and SQL are explicitly permitted and align with the marking requirements for REST APIs with SQL and proper HTTP handling.  [oai_citation:4‡COMP3011_Coursework1_Brief__2025_2026 (1).pdf](sediment://file_00000000d5d07246bfd42520e4b496ea)

## 7. Data Model (SQL Schema)

### Repository
- id (uuid, pk)
- provider (string, enum: github, gitlab, local)
- url (string)
- default_branch (string, nullable)
- created_at (datetime)
- updated_at (datetime)

### IngestionJob
- id (uuid, pk)
- repo_id (uuid, fk)
- status (enum: queued, running, completed, failed)
- commit_sha (string, nullable)
- started_at (datetime, nullable)
- finished_at (datetime, nullable)
- error_message (text, nullable)
- stats_json (json, nullable)  # files_indexed, chunks, tokens_est, etc

### DocumentChunk
- id (uuid, pk)
- repo_id (uuid, fk)
- file_path (string)
- start_line (int)
- end_line (int)
- content (text)
- content_hash (string)
- embedding (vector or json array)  # depending on approach
- created_at (datetime)

### Question
- id (uuid, pk)
- repo_id (uuid, fk)
- question_text (text)
- asked_at (datetime)

### Answer
- id (uuid, pk)
- question_id (uuid, fk)
- answer_text (text)
- citations_json (json)  # list of {file_path, start_line, end_line, chunk_id}
- model_info_json (json) # model name, temperature, etc
- created_at (datetime)

### Finding (optional stretch but good for marks)
- id (uuid, pk)
- repo_id (uuid, fk)
- type (enum: security, quality, architecture)
- severity (enum: low, medium, high)
- title (string)
- description (text)
- evidence_json (json) # file and line refs
- created_at (datetime)

Minimum CRUD requirement can be satisfied fully with Repository alone, but we will implement CRUD for Repository and also support listing and reading other resources.  [oai_citation:5‡COMP3011_Coursework1_Brief__2025_2026 (1).pdf](sediment://file_00000000d5d07246bfd42520e4b496ea)

## 8. API Design

### Conventions
- Base URL: /api/v1
- JSON responses for success and error.  [oai_citation:6‡COMP3011_Coursework1_Brief__2025_2026 (1).pdf](sediment://file_00000000d5d07246bfd42520e4b496ea)
- Pagination: limit, offset for list endpoints
- Ids are UUIDs
- Use appropriate status codes.  [oai_citation:7‡COMP3011_Coursework1_Brief__2025_2026 (1).pdf](sediment://file_00000000d5d07246bfd42520e4b496ea)

### Error Response Format
{
  "error": {
    "code": "REPO_NOT_FOUND",
    "message": "Repository not found",
    "details": {}
  }
}

### Endpoints

#### 8.1 Repository CRUD (core marking requirement)
POST /api/v1/repos
- Body: { provider, url, default_branch? }
- 201 Created with repo object
- 422 Validation error

GET /api/v1/repos
- Query: limit, offset
- 200 OK with list

GET /api/v1/repos/{repo_id}
- 200 OK with repo
- 404 if missing

PATCH /api/v1/repos/{repo_id}
- Body: partial update
- 200 OK
- 404 if missing

DELETE /api/v1/repos/{repo_id}
- 204 No Content
- 404 if missing

#### 8.2 Ingestion jobs
POST /api/v1/repos/{repo_id}/ingestions
- Body: { commit_sha? , mode: "clone" | "pull" }
- 202 Accepted if queued, returns job
- 409 Conflict if a job is already running for repo

GET /api/v1/repos/{repo_id}/ingestions/{job_id}
- 200 OK, returns status and stats

GET /api/v1/repos/{repo_id}/documents
- Query: file_path_prefix?, limit, offset
- 200 OK, returns document chunk metadata (not full content by default)

GET /api/v1/repos/{repo_id}/files
- 200 OK, returns unique file paths and counts (analytics style endpoint)

#### 8.3 Q&A workflow (resource driven, still RESTful)
POST /api/v1/repos/{repo_id}/questions
- Body: { question_text }
- 201 Created with question
- Also triggers answer generation synchronously by default (simple for demo)
- Response may include embedded answer object for convenience

GET /api/v1/repos/{repo_id}/questions/{question_id}
- 200 OK

GET /api/v1/repos/{repo_id}/questions/{question_id}/answer
- 200 OK if ready
- 404 if missing
- 409 if still processing in async mode

#### 8.4 Findings (optional stretch)
POST /api/v1/repos/{repo_id}/findings
GET /api/v1/repos/{repo_id}/findings
GET /api/v1/repos/{repo_id}/findings/{finding_id}
PATCH /api/v1/repos/{repo_id}/findings/{finding_id}
DELETE /api/v1/repos/{repo_id}/findings/{finding_id}

This gives you many endpoints well beyond the minimum 4.  [oai_citation:8‡COMP3011_Coursework1_Brief__2025_2026 (1).pdf](sediment://file_00000000d5d07246bfd42520e4b496ea)

## 9. Ingestion and Indexing Details

### 9.1 Repo Acquisition
Supported modes:
- Clone by URL into a server side workspace directory
- Pull updates if already present

Constraints:
- Limit total indexed files (example: 2000)
- Skip binary files using extension allowlist
- Skip files above size threshold (example: 512 KB)
- Ignore directories: .git, node_modules, dist, build, .venv

### 9.2 Chunking Strategy
Goal: retrieve the right context with citations.
Chunk each text file into line based chunks:
- chunk_size_lines: 80
- overlap_lines: 20

Store:
- file_path, start_line, end_line, content

### 9.3 Embeddings
For each chunk:
- compute embedding
- store embedding alongside chunk (simple) or in a separate table

Retrieval:
- compute question embedding
- cosine similarity against chunks for that repo
- top_k: 6 to 10

If using PostgreSQL with pgvector, do similarity search in SQL.
If staying simple, do retrieval in Python using numpy, then fetch chunks by id.

### 9.4 Citation Policy
The assistant must cite file paths and line ranges.
The answer response includes citations_json so users can verify the evidence.

Example citations_json:
[
  { "file_path": "src/auth/jwt.py", "start_line": 10, "end_line": 55, "chunk_id": "..." },
  { "file_path": "src/api/routes.py", "start_line": 1, "end_line": 60, "chunk_id": "..." }
]

## 10. Prompting Design (LLM)

### System instruction
- You are a codebase assistant.
- Only answer using provided context chunks.
- If not enough evidence, say what is missing and suggest which files to inspect.
- Always include citations by referencing file_path and line ranges from the context chunks.

### User prompt template
Inputs:
- question_text
- retrieved_chunks list, each with (file_path, start_line, end_line, content)

Output schema:
- answer_text
- citations_json

## 11. Security and Abuse Controls

### Coursework safe baseline
- No secrets in logs or responses
- API keys stored in environment variables
- Request size limits
- Rate limiting for Q&A endpoint (simple in memory limiter)
- Input validation with Pydantic

### Optional auth
Authentication is not mandatory for pass, but it improves marks.
Implement API key auth for simplicity:
- Header: X-API-Key
- Store hashed keys in SQL or env var only for a single user mode

The brief expects authentication documented where applicable and encourages stronger solutions at higher bands. 

## 12. Testing Strategy

### Unit tests
- Repository CRUD happy paths and edge cases
- Validation failures
- Error code correctness

### Integration tests
- Create repo -> ingestion job -> verify documents exist
- Ask question -> answer created -> citations present

Use pytest with a temporary SQLite database for CI style runs.
Mock the LLM and embeddings to avoid external calls in automated tests.

Evidence of testing is a clear differentiator for higher bands.  [oai_citation:9‡COMP3011_Coursework1_Brief__2025_2026 (1).pdf](sediment://file_00000000d5d07246bfd42520e4b496ea)

## 13. Observability
- Structured logging (request_id, repo_id, job_id)
- Health endpoint: GET /api/v1/health returns { status: "ok" }
- Metrics optional: simple counters in logs

## 14. Documentation Requirements
You must include API documentation describing endpoints, parameters, and response formats, with examples and error codes.  [oai_citation:10‡COMP3011_Coursework1_Brief__2025_2026 (1).pdf](sediment://file_00000000d5d07246bfd42520e4b496ea)

Plan:
- Use FastAPI OpenAPI docs and export to PDF
- Also include a Markdown quickstart in README.md

## 15. Deployment Plan
The API must be demonstrable via local execution or hosting, and MCP server is explicitly acceptable.  [oai_citation:11‡COMP3011_Coursework1_Brief__2025_2026 (1).pdf](sediment://file_00000000d5d07246bfd42520e4b496ea)

Minimum:
- Local run with uvicorn and SQLite
Recommended:
- Docker compose with Postgres
Optional:
- Deploy to a simple platform (PythonAnywhere or similar) for easy demo

## 16. Repository Structure
/
  app/
    main.py
    api/
      routes/
      deps.py
    db/
      models.py
      session.py
      migrations/
    services/
      ingestion.py
      chunking.py
      embeddings.py
      retrieval.py
      qa.py
    schemas/
      repo.py
      ingestion.py
      qa.py
  tests/
  docs/
    api-docs.pdf
    implementation.md
  README.md
  technical-report.pdf (submitted via Minerva separately)
  slides.pptx or link in report

## 17. Milestones and Checklist

### Milestone 1: Project scaffolding
- Create FastAPI app with /health
- Setup SQLAlchemy and Alembic
- Create Repository model and CRUD endpoints
Deliverable: working CRUD with Swagger

### Milestone 2: Ingestion pipeline
- Clone and file walking
- Chunking and storing DocumentChunk
- Ingestion job lifecycle and status endpoint
Deliverable: ingestion creates chunks in DB

### Milestone 3: Retrieval and Q&A
- Embedding generation and storage
- Similarity retrieval
- Question and Answer endpoints with citations
Deliverable: users can ask about repo and see cited answers

### Milestone 4: Quality and assessment readiness
- Tests
- Error handling polish
- API docs with examples and PDF export
- README and demo script for viva
Deliverable: end to end demo rehearsed

### Milestone 5: Stretch goals
- Findings resource with vulnerability like heuristics
- MCP compatibility layer
- Hosted deployment

## 18. Oral Exam Demo Plan (5 minutes)
1. Show Swagger docs briefly and explain resources
2. Create repo (POST /repos)
3. Start ingestion (POST /repos/{id}/ingestions)
4. Poll status until completed
5. Ask a question (POST /repos/{id}/questions)
6. Show answer with citations and open the referenced file path in your editor
7. Show database tables quickly (or screenshots) to prove data driven design
8. Mention tests and deployment method

The oral exam is 5 minutes presentation plus Q&A, so keep the live flow tight.  [oai_citation:12‡COMP3011_Coursework1_Brief__2025_2026 (1).pdf](sediment://file_00000000d5d07246bfd42520e4b496ea)

## 19. GenAI Usage Declaration Notes
This coursework requires declaring AI tools used and including example conversation logs if used. 
Keep:
- A /genai-logs folder with exported prompts and outputs
- A short section in technical-report.pdf describing how AI helped you

## 20. Future Extensions (post coursework)
- Full GitHub OAuth and webhooks
- Multi user and role based auth
- Advanced static analysis with Semgrep rules
- Better graph queries: dependency graph and call graph endpoints
- MCP server wrapper exposing tools like:
  - list_repos
  - ingest_repo
  - ask_repo
  - list_findings