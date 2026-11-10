# Entity Knowledge Graph Builder

This project converts unstructured text into an evidence-linked, ontology-validated entity graph and serves it through an API and browser viewer. It is domain-agnostic and uses the configured LLM provider for extraction and entity adjudication.

## Pipeline

chunk -> extract -> normalize -> resolve -> validate -> store -> serve

## Setup
Use Python 3.11 (`>=3.11,<3.12`), then create and activate a virtual environment:
`python3.11 -m venv venv && source venv/bin/activate && python -m pip install -e ".[eval]" && cp .env.example .env`

Set these variables in `.env`: `API_KEY`, `GROQ_API_KEY`, `GROQ_MODEL`, `GEMINI_API_KEY`, `GEMINI_MODEL`, and `NEO4J_PASSWORD`. `NEO4J_URI`, `NEO4J_USER`, and `CORS_ORIGINS` are optional; the provider is selected in `config/pipeline.yaml`.

Generate secrets with `python -c "import secrets; print(secrets.token_urlsafe(32))"` and put separate outputs in `API_KEY` and `NEO4J_PASSWORD`.

`docker compose up -d`

## Usage
`python scripts/build_graph.py --input examples/sample/source.txt`
`uvicorn ekg.api.main:app --reload`

Optional CLI arguments are `--entity-config FILE` and `--context STR`. Open the build page at `http://127.0.0.1:8000/`.

## API
- `POST /v1/graphs` — requires `X-API-Key`; queues a build and returns its ID.
- `GET /v1/graphs/{id}` — requires `X-API-Key`; returns status and the stored graph.
- `GET /g/{share_id}` — public; serves a completed graph viewer.
- `GET /v1/share/{share_id}` — public; returns the shared graph JSON.
- `GET /healthz` — public; returns the health status.

## Evaluation
Chunk export and gold-set validation commands are not implemented. The gold file is [eval/gold/gold_v1.jsonl](eval/gold/gold_v1.jsonl) and is currently empty.
`python eval/run_ablation.py`

This writes `eval/results/ablation.csv` and `eval/results/ablation.md` from `eval/ablations/baseline.yaml`.

## Results
Pending: run eval/run_ablation.py and paste the table here.

## Security
- Secrets are loaded from environment variables; API keys use constant-time comparison.
- Request bodies, input characters, and chunk counts are bounded by `config/pipeline.yaml`.
- Write requests have an in-memory per-IP rate limit and builds have a concurrency cap.
- Source text is delimited in LLM prompts; responses are parsed through Pydantic and ontology checks.
- Responses include CSP, `X-Content-Type-Options`, and `Referrer-Policy` headers.

## Limitations
- Extraction requires a configured Groq or Gemini model and API key; no local extraction model is provided.
- Neo4j must be running with the configured credentials for graph writes.
- Evaluation gold data and chunk-export/gold-validation tooling are not populated.

## Data and attribution
`examples/sample/source.txt` is a repository-authored sample text. The repository contains no external source citation or separate licence metadata for it.

<img width="1398" height="888" alt="image" src="https://github.com/user-attachments/assets/614641fe-8a0c-4305-b449-4f64f2370503" />
<img width="1328" height="747" alt="image" src="https://github.com/user-attachments/assets/67736d0c-3748-4be7-a033-24b098296a40" />

<img width="1398" height="750" alt="image" src="https://github.com/user-attachments/assets/b3587731-4ab3-4c13-bbcf-91f99fc1107e" />

