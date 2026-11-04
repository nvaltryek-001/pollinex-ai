# Local setup on Windows (N:\pollinex-ai)

The scripts are verified on a fresh clone in GitHub Actions (`windows-latest`, job *Windows PowerShell setup + tests*). They
use paths relative to the repository, so any drive works. The repository includes the models, the datasets and the lock
files, so the only things needed from the internet are Python and npm packages.

**Prerequisites:** Git, Python 3.11–3.13 (python.org, with *Add to PATH*), and Node.js 20 or 22 LTS. PostgreSQL is optional,
because SQLite is the default.

```powershell
# 1. Clone
N:
git clone https://github.com/nvaltryek-001/pollinex-ai.git N:\pollinex-ai
cd N:\pollinex-ai

# 2-3. Install dependencies and create .env (random JWT_SECRET, SQLite by default). Run once.
powershell -ExecutionPolicy Bypass -File scripts\setup_windows.ps1
#    Optional - local PostgreSQL instead of SQLite (also runs the migrations):
#    powershell -ExecutionPolicy Bypass -File scripts\setup_windows.ps1 -Postgres -PgPassword "<your local password>"

# 4. Database: SQLite (backend\pollinex.db) is created and migrated on first start.
#    To migrate by hand:
cd backend; ..\.venv\Scripts\python.exe -m alembic upgrade head; cd ..

# 5-6. Start the backend (http://127.0.0.1:8000) and the frontend (http://localhost:5173) together; opens the browser
powershell -ExecutionPolicy Bypass -File scripts\run_windows.ps1

# 7. Tests: engine + simulator, backend, Vitest, TypeScript, build; add -E2E for Playwright
powershell -ExecutionPolicy Bypass -File scripts\test_windows.ps1
powershell -ExecutionPolicy Bypass -File scripts\test_windows.ps1 -E2E

# 8. Stop: press Ctrl+C in the run_windows.ps1 window. It also ends the backend process.
#    If a backend was left running:
Get-Process python -ErrorAction SilentlyContinue | Where-Object { $_.Path -like "N:\pollinex-ai\*" } | Stop-Process
```

Other useful commands:

```powershell
.venv\Scripts\python.exe scripts\check_dependencies.py          # environment check
.venv\Scripts\python.exe scripts\evaluate_deployed_models.py    # reproduce the published model metrics (~3 min)
.venv\Scripts\python.exe scripts\sample_inference_check.py --mode closeup   # full pipeline on real photos of all 9 species
```

Notes:
* The first account registered on a fresh database becomes **admin**.
* `.env`, `backend\pollinex.db` and uploaded images in `backend\storage` are git-ignored. Never commit them.
* The camera needs `http://localhost` or HTTPS. On a phone, open the app over HTTPS, for example the Render demo.
* If PowerShell blocks scripts, keep `-ExecutionPolicy Bypass` as shown. It applies only to that command.
