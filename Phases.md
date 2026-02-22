Your end goal is a demonstrable, database-backed REST API that:
	1.	stores repositories in SQL with full CRUD
	2.	ingests a small Git repo into SQL as “code chunks” with file path + line ranges
	3.	lets users ask questions about that repo and returns answers with citations (file + line ranges)
	4.	is easy to run and demo (Docker), documented (Swagger + README + PDF docs), and tested (pytest)
	5.	has a clear 5-page report + a smooth 5-minute demo for the viva  ￼

That is enough for a “very good” grade if it’s clean, reliable, well-justified, and well-presented.  ￼

⸻

Full process broken into small tasks (do in this order)

Phase 0: Lock the scope (30 mins)

Goal: prevent overbuilding.
	•	Decide “lightweight mode” as your submission baseline:
	•	Docker runs api + db only
	•	ingestion runs synchronously
	•	Q&A works even if LLM is not configured (graceful fallback)
	•	Write this in README as “Baseline mode”.

Deliverable: README section “Baseline mode vs optional extensions”.

⸻

Phase 1: Make the base API rock solid (must not fail in viva)

Goal: pass requirements early and make everything stable.

Tasks
	1.	Run docker compose up --build -d (api + db only)
	2.	Confirm Swagger at /docs
	3.	Confirm GET /health returns JSON
	4.	Confirm Repository CRUD works with correct status codes:
	•	POST 201, GET 200, PATCH/PUT 200, DELETE 204
	•	404 on missing id, 422 on invalid body
	5.	Add consistent error format across endpoints

Deliverables:
	•	Working CRUD demo script (copy-paste curl commands)
	•	Screenshot of Swagger showing endpoints (useful for report)

⸻

Phase 2: Database and migrations (small but high impact)

Goal: show good engineering practice.

Tasks
	1.	Ensure Alembic migrations run cleanly
	2.	Create initial migration for all current models
	3.	Document how to run migrations in README

Deliverables:
	•	alembic upgrade head works inside container
	•	short “DB schema overview” section for your report

⸻

Phase 3: Ingestion pipeline (repo → chunks in DB)

Goal: prove it is data-driven beyond just CRUD.

Tasks
	1.	Add endpoint: POST /repositories/{id}/ingest
	•	input: optional branch/commit, optional include/exclude patterns
	2.	Implement clone/pull into a workspace folder
	3.	File filtering rules (important for robustness):
	•	skip .git, node_modules, dist, build, .venv
	•	skip files > e.g. 512KB
	•	allowlist common text extensions
	4.	Chunking:
	•	line-based chunking: 80 lines, 20 overlap
	•	store file_path, start_line, end_line, content
	5.	Store ingestion stats:
	•	files scanned, files indexed, chunks created
	6.	Add read endpoint to verify ingestion:
	•	GET /repositories/{id}/files
	•	GET /repositories/{id}/chunks?limit=...

Deliverables:
	•	Ingestion works on octocat/Hello-World quickly (safe storage)
	•	DB contains CodeChunk rows
	•	Endpoint returns stats JSON

⸻

Phase 4: Retrieval (the “intelligence” part without heavy AI)

Goal: make Q&A grounded, not random.

Tasks
	1.	Choose simplest embedding approach:
	•	If you already have sentence-transformers working: keep it
	•	Otherwise, implement a very lightweight baseline:
	•	keyword scoring (TF-IDF) or simple cosine similarity on embeddings stored as JSON
	2.	Implement retrieve_top_k(repo_id, question) returning chunks + scores
	3.	Add endpoint to inspect retrieval:
	•	POST /repositories/{id}/retrieve returns top chunks and citations only

Deliverables:
	•	You can prove retrieval works even before the LLM
	•	This is strong for viva: “here’s the evidence I pass to the model”

⸻

Phase 5: Q&A endpoint with citations (the standout)

Goal: answer questions and always cite evidence.

Tasks
	1.	Add POST /repositories/{id}/questions
	•	stores Question row
	2.	Use retrieval to fetch top chunks
	3.	Generate answer:
	•	If LLM configured: call it with strict prompt
	•	If not configured: return a “retrieval-only answer” (summary + top citations) and 503 if you want to be strict
	4.	Store Answer row with:
	•	answer_text
	•	sources_json containing file path + line ranges
	5.	Add GET /repositories/{id}/questions/{qid} and GET /.../answer

Deliverables:
	•	Answers always include citations
	•	No crashes if LLM is missing (graceful fallback)

⸻

Phase 6: Testing (easy marks if done well)

Goal: show reliability and good practice.

Tasks
	1.	API tests:
	•	health
	•	repo CRUD happy path + 404/422
	2.	Service tests:
	•	chunking produces correct line ranges
	•	ingestion file filtering works
	3.	If LLM calls exist, mock them

Deliverables:
	•	pytest -q passes inside container
	•	mention testing strategy in report

⸻

Phase 7: Documentation (what examiners care about)

Goal: make it runnable and understandable quickly.

Tasks
	1.	README:
	•	one command to run
	•	environment variables
	•	curl examples for CRUD + ingest + ask
	•	storage warning: use tiny repos
	2.	API docs:
	•	Swagger already exists
	•	export OpenAPI or add a docs/api.md with examples and error codes
	3.	Add a “Demo Script” section: exact steps you’ll do in the viva

Deliverables:
	•	Anyone can run it in 5 minutes
	•	You can demo without improvising

⸻

Phase 8: Viva prep (5-minute demo that never fails)

Goal: a smooth live demo plus good answers.

Your demo sequence
	1.	docker compose up --build -d
	2.	open /docs
	3.	POST repo (tiny repo)
	4.	POST ingest and show stats
	5.	POST question and show answer + citations
	6.	Show DB tables or a quick GET /files endpoint
	7.	Mention tests + design choices

Prepare 2 backup plans:
	•	If ingestion fails: demo CRUD + show code + explain pipeline
	•	If LLM fails: demo retrieval endpoint + citations (still impressive)

⸻

Phase 9: Technical report (max 5 pages, high scoring structure)

Goal: hit marking criteria cleanly.  ￼

Suggested structure:
	1.	Problem + goals (1/2 page)
	2.	API design + resources + endpoints (1 page)
	3.	DB schema + why SQL + migrations (1 page)
	4.	Ingestion + retrieval + grounding (1 page)
	5.	Testing + limitations + future work (1 page)
	6.	GenAI usage declaration (short section)

⸻

Optional “very good” add-ons (only if baseline is done)

Pick one, not all:
	•	Profiles in Docker Compose (baseline vs llm vs async)
	•	Simple auth (API key header)
	•	Findings endpoint (basic security heuristics like “hardcoded secrets” patterns)
	•	Async ingestion (Celery) only if you’re confident

⸻

Quick success checklist (your end state)

You’re done when:
	•	docker compose up --build -d starts without pulling huge images
	•	/docs works
	•	Repository CRUD works with correct status codes
	•	Ingesting a tiny repo creates chunks in DB
	•	Asking a question returns an answer with citations (or retrieval-only fallback)
	•	pytest passes
	•	README + docs + report + slides are ready
