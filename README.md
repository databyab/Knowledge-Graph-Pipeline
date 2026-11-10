# Entity Knowledge Graph Builder

## Setup

Use Python 3.11, create a virtual environment, and install `pip install -e .[eval]`.
Copy `.env.example` to `.env` and set `API_KEY`, provider API keys, and the provider model variable.
Set `NEO4J_PASSWORD` before `docker compose up -d`.

## Commands

`python scripts/build_graph.py --input examples/sample/source.txt`

`uvicorn ekg.api.main:app --reload`

`ruff check .`

`mypy --strict src`

`pytest`

`pip-audit`

## Assumptions

The configured provider is used for extraction and intermediate entity adjudication.
SQLite is the local run and snapshot store; Neo4j is optional for API startup.
The public viewer is addressed through a share identifier created after a completed build.
