# 🔍 CodeQuery API

**AI-Powered Code Intelligence** – Ingest GitHub repositories and ask natural-language questions about the code using Retrieval-Augmented Generation (RAG).

> COMP3011 – Web Services and Web Data | Sachin Sindhe

### 🎓 Submission Documents
- 📄 **API Documentation:** [`API_Documentation.pdf`](./api-docs.pdf) (Exported from Swagger UI, ensure to place in root before submission)
- 📝 **Technical Report:** [`main.tex`](./main.tex) (LaTeX Source)
- 📊 **Presentation Slides:** (Ensure to place `.pptx` in root before submission)

---

## 🏗️ Architecture

```
Client (Postman / Frontend)
    │  HTTP/JSON
    ▼
┌─────────────────────────┐
│  FastAPI (async)        │ ← API Layer
│  ├── /repositories      │
│  ├── /questions         │
│  └── /analysis          │
└────────┬────────────────┘
         │
  ┌──────▼──────┐    ┌──────────────┐
  │ PostgreSQL  │    │ Celery +     │
  │ + pgvector  │    │ Redis        │
  └─────────────┘    └──────┬───────┘
                            │
                     ┌──────▼───────┐
                     │  Ollama LLM  │
                     │  (Mistral)   │
                     └──────────────┘
```

## 🚀 Quick Start

### Prerequisites
- Docker & Docker Compose

### 1. Clone & Configure

```bash
git clone <your-repo-url>
cd codequery-api
cp .env.example .env   # Edit if needed
```

### 2. Start Services (Lightweight Mode by Default)

CodeQuery is configured to run in **Lightweight Mode** by default (< 20GB storage footprint). This runs only the API and PostgreSQL Database. Ingestion is handled natively within the API.

```bash
# Starts API + DB only
docker compose up --build -d
```

**⚠️ Warning on Storage Limits:** In `Lightweight Mode`, please start by testing ingestion on tiny repositories (e.g., https://github.com/octocat/Hello-World) to prevent memory blocks.

### 3. Optional Advanced Profiles
If you have sufficient RAM and storage, you can enable advanced services using Docker Compose profiles.

* **Async Mode (Celery + Redis):**
  Offloads ingestion to a background worker queue.
  ```bash
  docker compose --profile async up --build -d
  ```

* **LLM Mode (Local Ollama LLM):**
  Allows Q&A inference locally.
  ```bash
  docker compose --profile llm up --build -d
  
  # Pull the tiny model once after it's started:
  docker exec -it codequery-ollama ollama pull qwen2.5:0.5b
  ```

* **Full Mode (All Services):**
  ```bash
  docker compose --profile async --profile llm up --build -d
  ```

### 4. Explore the API

- **Swagger UI:** [http://localhost:8000/docs](http://localhost:8000/docs)
- **ReDoc:** [http://localhost:8000/redoc](http://localhost:8000/redoc)
- **Health Check:** [http://localhost:8000/api/v1/health](http://localhost:8000/api/v1/health)

---

## 📡 API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/v1/repositories` | Add a repository for analysis |
| `GET` | `/api/v1/repositories` | List all repositories |
| `GET` | `/api/v1/repositories/{id}` | Get repository details |
| `PUT` | `/api/v1/repositories/{id}` | Update / re-analyse |
| `DELETE` | `/api/v1/repositories/{id}` | Delete repository |
| `POST` | `/api/v1/repositories/{id}/questions` | Ask a question |
| `GET` | `/api/v1/repositories/{id}/questions` | Question history |
| `GET` | `/api/v1/questions/{id}` | Get single question |
| `DELETE` | `/api/v1/questions/{id}` | Delete question |
| `GET` | `/api/v1/repositories/{id}/analysis` | Analysis status |
| `GET` | `/api/v1/repositories/{id}/statistics` | Code statistics |
| `GET` | `/api/v1/health` | Health check |

### Example: Add a Repository

```bash
curl -X POST http://localhost:8000/api/v1/repositories \
  -H "Content-Type: application/json" \
  -d '{
    "repo_url": "https://github.com/pallets/flask",
    "branch": "main",
    "name": "Flask"
  }'
```

### Example: Ask a Question

```bash
curl -X POST http://localhost:8000/api/v1/repositories/1/questions \
  -H "Content-Type: application/json" \
  -d '{
    "question": "How is routing implemented?"
  }'
```

---

## 🗂️ Project Structure

```
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI entry point
│   ├── config.py            # Pydantic Settings
│   ├── database.py          # Async SQLAlchemy engine
│   ├── api/                 # REST endpoints
│   │   ├── repositories.py  # CRUD for repos
│   │   ├── questions.py     # Q&A endpoints
│   │   └── analysis.py      # Analysis status & stats
│   ├── models/              # SQLAlchemy ORM models
│   │   ├── repository.py
│   │   ├── code_chunk.py
│   │   ├── question.py
│   │   └── analysis_job.py
│   ├── schemas/             # Pydantic request/response
│   │   ├── repository.py
│   │   ├── question.py
│   │   └── analysis.py
│   ├── services/            # Business logic
│   │   ├── ingestion.py     # Git clone + file discovery
│   │   ├── chunking.py      # Code parsing & chunking
│   │   ├── embedding.py     # Vector embeddings (free model)
│   │   └── qa_engine.py     # RAG pipeline
│   └── tasks/               # Celery background tasks
│       └── analysis.py      # Full analysis pipeline
├── tests/
│   ├── test_api.py          # CRUD & Mocking tests
│   ├── test_services.py     # Chunk extraction tests
│   ├── test_qa_engine.py    # LLM prompt generation tests
│   ├── test_ingestion.py    # Git file discovery tests
│   └── conftest.py          # Pytest fixtures
├── alembic/                 # Database migrations
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
└── .env
```

---

## 🧪 Running Tests

```bash
# Run pytest in the API container:
docker compose exec api pytest -q

# Or locally with a virtual environment
pytest tests/ -v --cov=app
```

---

## 🔧 Database Migrations

```bash
# Generate a new migration
docker exec -it codequery-api alembic revision --autogenerate -m "description"

# Apply migrations
docker exec -it codequery-api alembic upgrade head
```

---

## 🤖 AI Models Used

| Component | Model | Cost | Dimension |
|-----------|-------|------|-----------|
| **Embeddings** | `all-MiniLM-L6-v2` (sentence-transformers) | Free | 384 |
| **LLM** | `qwen2.5:0.5b` via Ollama | Free (local) | – |

> To switch to OpenAI, set `OPENAI_API_KEY` in `.env`.

---

## 📄 License

MIT License – Built for COMP3011 coursework.
