# Tandem Backend

FastAPI API and processing worker for the recruitment demo. It uses SQLite for application data and private local storage for original resumes. Hosted AI calls use Hugging Face Inference Providers; the Mac does not download model weights or need a GPU.

## Recommended Demo Models

- Resume/JD extraction: [Qwen3-14B](https://huggingface.co/Qwen/Qwen3-14B), selected with the `:cheapest` provider policy.
- Embeddings: [Qwen3-Embedding-0.6B](https://huggingface.co/Qwen/Qwen3-Embedding-0.6B).

The Hugging Face model cards list Apache-2.0 licenses. Hugging Face’s current model/provider pages list Qwen3-14B for chat and Qwen3-Embedding-0.6B for feature extraction through hosted providers. Provider availability, price, latency, license terms, and data handling can change; confirm them before use with real resumes. Requests send resume text to the selected inference provider only after the candidate grants AI-processing consent.

## What You Need

1. A Mac with Python 3.12+ and Node.js 20.19+ or 22.12+ for the non-Docker setup, or Docker Desktop for the container setup.
2. A Hugging Face account with a fine-grained token permitted to **Make calls to Inference Providers**. Usage may be billed under Hugging Face/provider terms; check your account credits and current pricing.
3. A locally generated `ACCESS_TOKEN_SECRET` (at least 32 characters).
4. A local admin email and password for initial organization verification.

Do **not** send tokens, passwords, or signing secrets in chat. Put them directly in the ignored `backend/.env` file on your Mac.

## Run Natively on macOS

The checked-in/root `.venv` on Windows is not portable. Create a fresh Mac environment from the repository root:

```bash
python3 -m venv .venv
source .venv/bin/activate
cd backend
pip install -e '.[dev]'
cp .env.example .env
```

Generate a local signing secret:

```bash
python3 -c 'import secrets; print(secrets.token_urlsafe(48))'
```

Edit `backend/.env` and set:

```dotenv
ACCESS_TOKEN_SECRET=<paste the locally generated value here>
INFERENCE_ENABLED=true
INFERENCE_PROVIDER=auto
INFERENCE_API_KEY=<your Hugging Face token>
INFERENCE_CHAT_MODEL=Qwen/Qwen3-14B:cheapest
INFERENCE_EMBEDDING_MODEL=Qwen/Qwen3-Embedding-0.6B
```

After the first `alembic upgrade head`, create the initial admin using locally entered environment values. This command creates no public admin-registration route:

```bash
export BOOTSTRAP_ADMIN_EMAIL='admin@your-company.example'
read -s BOOTSTRAP_ADMIN_PASSWORD
export BOOTSTRAP_ADMIN_PASSWORD
python -m app.bootstrap_admin
unset BOOTSTRAP_ADMIN_EMAIL BOOTSTRAP_ADMIN_PASSWORD
```

Use the admin login in `/docs` to verify the recruiter's organization before publishing a job.

Run the API and worker in separate Terminal tabs, both from `backend/` with the venv active:

```bash
alembic upgrade head
uvicorn app.main:app --reload
```

```bash
python -m app.worker
```

Open API docs at `http://127.0.0.1:8000/docs`. In the docs, register a candidate and a recruiter; create the first admin with the bootstrap steps below. Upload a text-based PDF/DOCX, grant AI-processing consent, process it with the worker, review the extracted JSON, and grant recruiter-search consent before matching.

To run the current frontend demo separately, use another terminal:

```bash
cd frontend
npm ci
npm run dev
```

The React screens are **not connected to the backend yet**; the frontend remains a clearly labeled sample UI. Use `/docs` to demonstrate the real API flow. Do not set `VITE_USE_MOCKS=false` expecting live screens until frontend services/forms are wired to the actual routes in [API_CONTRACT.md](API_CONTRACT.md).

## Docker Desktop Demo

1. Copy `backend/.env.example` to `backend/.env` and fill in the signing secret and Hugging Face token/model settings above.
2. Before starting Compose for the first time, also fill `BOOTSTRAP_ADMIN_EMAIL` and `BOOTSTRAP_ADMIN_PASSWORD` in the ignored `backend/.env`.
3. From the repository root, run:

```bash
docker compose up --build -d
```

4. Create the first admin, then remove the two bootstrap values from `backend/.env` and recreate the containers:

```bash
docker compose exec api python -m app.bootstrap_admin
docker compose up -d --force-recreate api worker
```

5. Open the sample UI at `http://localhost:8080` and API docs at `http://localhost:8000/docs`.

Compose stores the SQLite database and private resumes in named volumes. Do not run multiple API replicas against this SQLite file. The exposed API port binds to localhost for a development demo; put TLS and a reviewed production reverse proxy in front before remote use.

## Backups

The SQLite online-backup helper creates a consistent backup and runs `PRAGMA integrity_check`:

```bash
cd backend
python scripts/backup_sqlite.py ./backups
```

Protect backups like resume files: they contain personal data. Store copies encrypted and off-machine according to your retention policy. Test restoration before relying on backups.

## Checks

From `backend/` with the venv active:

```bash
ruff check app tests migrations
pytest -q
alembic upgrade head
alembic check
```

## Current Limitations

This is a local/staging demonstration, not production-ready recruitment software. It lacks OCR for scanned resumes, malware scanning, email verification/password recovery, login rate limiting, automated retention/deletion, and encrypted file storage at the application layer. SQLite is intended for one host and modest write concurrency. The frontend is not integrated. Matching currently uses consent-filtered FTS5 plus optional hosted embeddings and returns evidence; it does not calculate hiring probabilities or automatically reject candidates.
