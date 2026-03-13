# 🔍 CodeQuery API

**AI-Powered Code Intelligence** – Ingest GitHub repositories and ask natural-language questions about the code using Retrieval-Augmented Generation (RAG).

> COMP3011 – Web Services and Web Data | Sachin Sindhe

### 🎓 Submission Documents
- 📄 **API Documentation:** [`api-docs.pdf`](./api-docs.pdf) (Exported from Swagger UI)
- 📝 **Technical Report:** [`technical-report.pdf`](./technical-report.pdf) (Compiled report)
- 🤖 **GenAI Logs:** [`genai-conversation-logs.pdf`](./genai-conversation-logs.pdf) (Appendix)
- 📊 **Presentation Slides:** [`slides.pptx`](./slides.pptx)


---

## 🏗️ Architecture

```
Client (Postman / Frontend / Swagger)
    │  HTTP/JSON
    ▼
┌─────────────────────────┐
│  FastAPI (async)        │ ← API Layer
│  ├── /api/v1/repositories
│  ├── /api/v1/questions
│  └── /api/v1/analysis   │
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
- Git
- Internet connection (to download Docker images and clone Git repositories)

### 1. Clone & Configure
```bash
git clone <repository-url>
cd <repository-directory>
cp .env.example .env
```
*(The defaults in `.env` are sufficient for local testing).*

### 2. Start Services (Lightweight Mode)
CodeQuery defaults to **Lightweight Mode** (< 20GB storage footprint), which runs only the FastAPI server and PostgreSQL Database. Ingestion happens natively within the API process.

```bash
# Starts the "api" and "db" services in the background
docker compose up --build -d
```

### 3. Verify Health and Database
Ensure the application is running:
- **Health Check:** `curl http://localhost:8000/api/v1/health`
- **Swagger UI:** [http://localhost:8000/docs](http://localhost:8000/docs)

*Note: The API automatically creates database tables on startup (via SQLAlchemy `Base.metadata.create_all`). If you need to manually apply Alembic migrations, use `docker compose exec`:*
```bash
docker compose exec api alembic upgrade head
```

---

## 🎯 Manual Demo Steps 

Follow these steps via Swagger UI ([http://localhost:8000/docs](http://localhost:8000/docs)) to demo the full RAG pipeline:

1. **Create Repository**
   - Click `POST /api/v1/repositories`
   - Paste the following tiny test repo:
     ```json
     {
       "repo_url": "https://github.com/octocat/Hello-World",
       "branch": "master",
       "name": "Octocat HelloWorld"
     }
     ```
   - **Expected Status:** `202 Accepted`

2. **Check Analysis Status**
   - Click `GET /api/v1/repositories/{repo_id}/analysis`
   - Enter `repo_id`: `1`
   - Click Execute until `"status": "completed"`
   - **Expected Status:** `200 OK`

3. **Ask a Question**
   - Click `POST /api/v1/repositories/{repo_id}/questions`
   - Enter `repo_id`: `1`
   - Paste the JSON payload:
     ```json
     {
       "question": "What does the README say?"
     }
     ```
   - **Expected Status:** `200 OK` (Or `503 Service Unavailable` if the local LLM is disabled, which confirms the lightweight fallback mechanism works).

*Note: See full list of status codes including `204 No Content`, `404 Not Found`, and `422 Unprocessable Entity` in the `/docs` UI for edge cases.*

---

## 📡 API Endpoints List

All endpoints are prefixed with `/api/v1`.

| Method   | Endpoint                                   | Description                               |
|----------|--------------------------------------------|-------------------------------------------|
| `POST`   | `/repositories`                            | Add a new repository and queue analysis   |
| `GET`    | `/repositories`                            | List all repositories                     |
| `GET`    | `/repositories/{repo_id}`                  | Get repository details                    |
| `PUT`    | `/repositories/{repo_id}`                  | Update / re-analyse a repository          |
| `DELETE` | `/repositories/{repo_id}`                  | Delete a repository and associated data   |
| `POST`   | `/repositories/{repo_id}/questions`        | Ask a question about a repository         |
| `GET`    | `/repositories/{repo_id}/questions`        | Get question history for a repository     |
| `GET`    | `/questions/{question_id}`                 | Get a single question with full answer    |
| `DELETE` | `/questions/{question_id}`                 | Delete a question                         |
| `GET`    | `/repositories/{repo_id}/analysis`         | Get analysis job status                   |
| `GET`    | `/repositories/{repo_id}/statistics`       | Get code statistics (functions, classes)  |
| `GET`    | `/health`                                  | Service health check                      |

*(No auth headers are required for local testing, though `API_KEY` authentication setup is supported in `config.py`)*

---

## ⚙️ Optional Advanced Modes

If you have sufficient system resources (RAM and storage), you can enable advanced capabilities via Docker Compose profiles.

### Async Mode
Offloads ingestion to a background Celery worker queue, powered by Redis.
```bash
docker compose --profile async up --build -d
```

### LLM Mode (Local Inference)
Enables the local Ollama container to answer questions.
```bash
# 1. Start the LLM profile
docker compose --profile llm up --build -d

# 2. Pull the model (mistral) inside the ollama container
docker compose exec ollama ollama pull mistral
```
*(The exact model used in `app/config.py` is `mistral`. If the Ollama service is unavailable, questions will return a clean `503` error with the retrieved source snippets, confirming the RAG retrieval still functions.)*

---

## 🧪 Testing

The test suite covers Git ingestion, RAG prompt generation, code chunking, and mock API tests.

To run the full suite using `pytest`:
```bash
# Execute within the running `api` container:
docker compose exec api pytest tests/ -v
```

---

## ⚠️ Important Notes

- **Storage Warning:** Ingestion stores cloned repositories locally in `/tmp/codequery_repos` and text embeddings in the PostgreSQL database. **Please use tiny repositories (like `octocat/Hello-World`) to prevent disk usage spikes.**
- **Version Guarantee:** The current commit branch `main` corresponds strictly to the final runnable viva version.
