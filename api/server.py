"""
KPI Anomaly Detection — FastAPI backend

Endpoints:
  POST /api/login            — returns JWT token (no auth required)
  GET  /api/me               — returns current username (auth required)
  POST /api/run-pipeline     — triggers full pipeline run (auth required)
  GET  /api/pipeline-status  — returns current run state (auth required)
"""

import asyncio
import shutil
import subprocess
import sys
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel

from auth import authenticate, create_token, decode_token

BASE_DIR       = Path(__file__).parent.parent
SCRIPTS_DIR    = BASE_DIR / "scripts"
DASHBOARD_OUT_DIR = BASE_DIR / "outputs" / "dashboard"
DASHBOARD_DATA = BASE_DIR / "kpi-anomaly-dashboard" / "public" / "data"

PIPELINE_SCRIPTS = [
    "1.1_build_master_dataset.py",
    "1.2_1.3_ingest_and_engineer.py",
    "2.1_kpi_monitoring_tiers.py",
    "2.2a_statistical_baseline.py",
    "2.2b_isolation_forest.py",
    "2.2c_prophet.py",
    "2.3_ensemble_voting.py",
    "3.1_dependency_graph.py",
    "3.2_causal_inference.py",
    "3.3_external_drivers.py",
    "3.4_rca_assembly.py",
    "4.1_business_impact_quantification.py",
    "4.2_prioritization_engine.py",
    "4.3_recommendation_engine.py",
    "4.4_intelligence_assembly.py",
    "5.1_alert_formatter.py",
    "5.2_report_generator.py",
    "5.3_delivery_simulation.py",
    "5.4_communication_assembly.py",
    "5.5_dashboard_data_prep.py",
]

_pipeline_status: dict = {"state": "idle", "step": None, "error": None}

app = FastAPI(title="KPI Anomaly Detection API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

_bearer = HTTPBearer()


def _get_current_user(creds: HTTPAuthorizationCredentials = Depends(_bearer)) -> str:
    try:
        return decode_token(creds.credentials)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token")


# ── Request models ─────────────────────────────────────────────────────────────

class LoginRequest(BaseModel):
    username: str
    password: str


# ── Endpoints ──────────────────────────────────────────────────────────────────

@app.post("/api/login")
def login(body: LoginRequest):
    if not authenticate(body.username, body.password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid username or password")
    return {"token": create_token(body.username), "username": body.username}


@app.get("/api/me")
def me(user: str = Depends(_get_current_user)):
    return {"username": user}


@app.get("/api/pipeline-status")
def pipeline_status(user: str = Depends(_get_current_user)):
    return _pipeline_status


@app.post("/api/run-pipeline")
async def run_pipeline(user: str = Depends(_get_current_user)):
    if _pipeline_status["state"] == "running":
        raise HTTPException(status_code=409, detail="Pipeline is already running")
    asyncio.create_task(_execute_pipeline())
    return {"message": "Pipeline started"}


# ── Pipeline runner ────────────────────────────────────────────────────────────

async def _execute_pipeline() -> None:
    global _pipeline_status
    _pipeline_status = {"state": "running", "step": None, "error": None}

    try:
        for script in PIPELINE_SCRIPTS:
            _pipeline_status["step"] = script
            result = await asyncio.to_thread(
                subprocess.run,
                [sys.executable, str(SCRIPTS_DIR / script)],
                capture_output=True,
                text=True,
                cwd=str(BASE_DIR),
            )
            if result.returncode != 0:
                _pipeline_status = {
                    "state": "error",
                    "step": script,
                    "error": (result.stderr or result.stdout)[-600:].strip(),
                }
                return

        # Copy freshly generated CSVs into the dashboard's public/data/
        DASHBOARD_DATA.mkdir(parents=True, exist_ok=True)
        for csv_file in DASHBOARD_OUT_DIR.glob("*.csv"):
            shutil.copy2(csv_file, DASHBOARD_DATA / csv_file.name)

        _pipeline_status = {"state": "done", "step": None, "error": None}

    except Exception as exc:
        _pipeline_status = {
            "state": "error",
            "step": _pipeline_status.get("step"),
            "error": str(exc),
        }
