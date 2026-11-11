# SAMPLEAI / TANDEM — LOCAL TESTING GUIDE

This guide provides instructions to run and manually test the full three-sided recruitment platform locally on Windows.

---

## 1. Environment & Configuration

The local environment is configured with:
- **Backend API:** `http://localhost:8000` (FastAPI + SQLAlchemy)
- **Frontend App:** `http://localhost:5173` (React + Vite + TypeScript)
- **Database:** SQLite 3 at `data/recruitment.db` (Preserved and backed up at `data/recruitment.db.backup_final`)
- **AI Inference Provider:** Hugging Face Hosted Inference API
  - Primary LLM: `Qwen/Qwen2.5-72B-Instruct`
  - Embedding Model: `sentence-transformers/all-MiniLM-L6-v2`
- **Frontend Configuration (`frontend/.env`):**
  ```env
  VITE_API_BASE_URL=http://localhost:8000/api/v1
  VITE_USE_MOCKS=false
  ```
- **Backend Configuration (`.env` and `backend/.env`):**
  ```env
  DATABASE_URL=sqlite:///./data/recruitment.db
  ACCESS_TOKEN_SECRET=<your_32_character_secret>
  INFERENCE_ENABLED=true
  INFERENCE_API_KEY=<your_hugging_face_token>
  INFERENCE_PROVIDER=auto
  INFERENCE_CHAT_MODEL=Qwen/Qwen2.5-72B-Instruct
  INFERENCE_EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2
  ```

---

## 2. Local Startup Commands (Windows PowerShell)

Open separate PowerShell terminal windows for each service.

### Terminal 1: Backend API Server
```powershell
cd "c:\Users\welcome\Downloads\SAMPLE ai"
.\.venv\Scripts\Activate.ps1
cd backend
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```
- API will be accessible at: `http://localhost:8000`
- Swagger Interactive Documentation: `http://localhost:8000/docs`
- Healthcheck endpoint: `http://localhost:8000/health`

### Terminal 2: Background Worker (Optional / Standalone Queue Processing)
*Note: The FastAPI backend already automatically spawns asynchronous background tasks for immediate resume parsing and matching runs upon upload. To run the dedicated standalone worker loop as well:*
```powershell
cd "c:\Users\welcome\Downloads\SAMPLE ai"
.\.venv\Scripts\Activate.ps1
$env:PYTHONPATH = "backend"
python -m app.worker
```

### Terminal 3: Frontend Development Server
```powershell
cd "c:\Users\welcome\Downloads\SAMPLE ai\frontend"
npm run dev
```
- Frontend will be accessible at: `http://localhost:5173`

---

## 3. Seeded Accounts for Manual Testing

The SQLite database (`data/recruitment.db`) comes pre-seeded with 25 diverse candidate resumes, 3 independent employers, and 6 active jobs.

### Candidate Credentials:
- **Email:** `suriyaprakash444m@gmail.com`
- **Password:** `Password123!`
- *(Or register any new candidate directly in the portal with a 6+ character password)*

### Recruiter Credentials:
- **Northstar Technologies:** `recruiter.northstar@example.com` / `RecruiterPassword123!`
- **Apex Systems:** `recruiter.apex@example.com` / `RecruiterPassword123!`
- **Horizon Health:** `recruiter.horizon@example.com` / `RecruiterPassword123!`

### Administrator Credentials:
- **Email:** `admin@tandem.test`
- **Password:** `AdminPassword123!`

---

## 4. Manual Testing Walkthrough

### A. Candidate Portal (`http://localhost:5173/portal/candidate/resume`)
1. **Sign In or Register:**
   - Sign in using `suriyaprakash444m@gmail.com` / `Password123!` or create a new candidate account.
2. **Resume Upload & AI Parsing:**
   - Drop or select a `.pdf`, `.docx`, or `.txt` resume file.
   - Check the AI processing consent checkbox.
   - Click **"Upload & Store in Database"**.
   - Watch the pipeline extract verified skills, headline, work history, and summary.
   - Click **"Confirm & Save to SQLite Talent Pool"** to index your profile for employer matching.
3. **Explore Active Jobs:**
   - Switch to the **"Explore Active Jobs"** tab.
   - Search by role or keyword across all SQLite published jobs.
   - Click **"Apply with Resume"** on any job (e.g. *Senior Python & AI Platform Engineer*).
4. **Track Applications:**
   - Switch to the **"My Applications"** tab to view your application status.

---

### B. Recruiter Claude/ChatGPT Portal (`http://localhost:5173/portal/recruiter/overview`)
1. **Sign In:**
   - Sign in as `recruiter.northstar@example.com` (`RecruiterPassword123!`).
2. **Saved JDs in Sidebar:**
   - Inspect the left sidebar showing saved SQLite job descriptions.
   - Click on any job to view candidate recommendations.
3. **Upload or Paste a New JD:**
   - Click **"+ Upload / New JD"** or type/paste in the bottom input dock.
   - Attach a `.pdf`, `.docx`, or `.txt` file, or type requirements into the prompt dock.
   - Click Send / Run.
4. **Review Top 5 Candidate Recommendations:**
   - View the Top 5 candidates ranked by merit (100-point composite score).
   - Check the highlighted **"Why this candidate is strong"** callout box.
   - Click **"More Details"** on any candidate to inspect their complete verified dossier.

---

### C. Admin Operations Portal (`http://localhost:5173/portal/admin/overview`)
1. **Sign In:**
   - Sign in as `admin@tandem.test` (`AdminPassword123!`).
2. **System Telemetry Overview:**
   - View live SQLite counts: Total Candidates (25+), Active Employers (3), Confirmed JDs (6), and FTS5 Search Index.
3. **Sub-Tab Operations:**
   - **Candidates:** Browse registered candidate pool.
   - **Recruiters:** Inspect employer organizations and verification statuses.
   - **Jobs:** Inspect all active job descriptions across the platform.
   - **AI Pipeline:** Monitor Hugging Face LLM and embedding request telemetry.

---

## 5. Development & Automated Verification Commands

To verify code quality and database health at any time:

```powershell
# Run backend test suite (13 tests)
.\.venv\Scripts\python.exe -m pytest backend/tests/test_matching_logic.py backend/tests/test_queue_search.py backend/tests/test_multi_employer_isolation.py backend/tests/test_evaluation_benchmark.py -v

# Run benchmark evaluation script
$env:PYTHONPATH = "backend"
.\.venv\Scripts\python.exe backend/scripts/evaluate_benchmarks.py

# Verify frontend production build
npm --prefix frontend run build
```
