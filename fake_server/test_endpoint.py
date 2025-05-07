
# Assim que roda:
# .\.venv\Scripts\uvicorn.exe fake_server.test_endpoint:app --host 0.0.0.0 --port 8000

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from pathlib import Path
from datetime import datetime, timedelta

# ─── Diretórios ──────────────────────────────────────────────────────────────
BASE_DIR   = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"
TEST_DIR   = STATIC_DIR / "testjob"
FIXED_JOB_ID = "testjob"

# ─── Armazena tempo de criação dos jobs ──────────────────────────────────────
job_start_times = {}

# ─── App FastAPI ─────────────────────────────────────────────────────────────
app = FastAPI(title="TripoSR Fake Service")
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── Models ──────────────────────────────────────────────────────────────────
class Prompt(BaseModel):
    prompt: str

# ─── Endpoints Fake ──────────────────────────────────────────────────────────
@app.post("/generate")
async def generate(_: Prompt):
    """
    Cria um job fake com job_id fixo e armazena o tempo de criação.
    """
    job_start_times[FIXED_JOB_ID] = datetime.utcnow()
    return {"job_id": FIXED_JOB_ID}


@app.get("/result/{job_id}")
async def result(job_id: str):
    """
    Após 10s retorna os arquivos. Antes disso, simula progresso.
    """
    if job_id != FIXED_JOB_ID:
        raise HTTPException(404, "Job inexistente")

    start_time = job_start_times.get(FIXED_JOB_ID)
    if not start_time:
        raise HTTPException(404, "Job não iniciado")

    elapsed = (datetime.utcnow() - start_time).total_seconds()

    if elapsed < 10:
        progress = int((elapsed / 10) * 100)
        return {"status": "processing", "progress": progress}

    # Arquivos prontos após 10s
    test_obj = TEST_DIR / "mesh.obj"

    if not test_obj.exists() :
        raise HTTPException(500, "Arquivos de teste não encontrados.")

    base = f"/static/{FIXED_JOB_ID}"
    return {
        "status": "finished",
        "obj":   f"{base}/mesh.obj",
    }
