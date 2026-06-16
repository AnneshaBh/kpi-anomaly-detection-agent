"""
KPI Anomaly Detection — FastAPI backend

Endpoints:
  POST /api/run-pipeline     — triggers full pipeline run
  GET  /api/pipeline-status  — returns current run state
"""

import asyncio
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

BASE_DIR    = Path(__file__).parent.parent
load_dotenv(BASE_DIR / ".env")   # loads root .env (ANTHROPIC_API_KEY etc.)
SCRIPTS_DIR = BASE_DIR / "scripts"
LOGS_DIR    = BASE_DIR / "logs"
LOGS_DIR.mkdir(exist_ok=True)

PIPELINE_LAYERS = [
    {
        "name": "Layer 1 — Data Ingestion & Engineering",
        "scripts": [
            SCRIPTS_DIR / "raw"       / "1.1_build_master_dataset.py",
            SCRIPTS_DIR / "processed" / "1.2_1.3_ingest_and_engineer.py",
        ],
    },
    {
        "name": "Layer 2 — Anomaly Detection",
        "scripts": [
            SCRIPTS_DIR / "detection" / "2.1_KPI_Monitoring_Tiers.py",
            SCRIPTS_DIR / "detection" / "2.2A_Statistical_Baseline.py",
            SCRIPTS_DIR / "detection" / "2.2B_Isolation_Forest.py",
            SCRIPTS_DIR / "detection" / "2.2C_Prophet.py",
            SCRIPTS_DIR / "detection" / "2.3_Ensemble_Voting.py",
        ],
    },
    {
        "name": "Layer 3 — Root Cause Analysis",
        "scripts": [
            SCRIPTS_DIR / "rca" / "3.1_dependency_graph.py",
            SCRIPTS_DIR / "rca" / "3.2_causal_inference.py",
            SCRIPTS_DIR / "rca" / "3.3_external_drivers.py",
            SCRIPTS_DIR / "rca" / "3.4_rca_assembly.py",
        ],
    },
    {
        "name": "Layer 4 — Intelligence Engine",
        "scripts": [
            SCRIPTS_DIR / "intelligence" / "4.1_business_impact_quantification.py",
            SCRIPTS_DIR / "intelligence" / "4.2_prioritization_engine.py",
            SCRIPTS_DIR / "intelligence" / "4.3_recommendation_engine.py",
            SCRIPTS_DIR / "intelligence" / "4.4_intelligence_assembly.py",
        ],
    },
    {
        "name": "Layer 5 — Communication & Dashboard",
        "scripts": [
            SCRIPTS_DIR / "communication" / "5.1_alert_formatter.py",
            SCRIPTS_DIR / "communication" / "5.2_report_generator.py",
            SCRIPTS_DIR / "communication" / "5.3_delivery_simulation.py",
            SCRIPTS_DIR / "communication" / "5.4_communication_assembly.py",
            SCRIPTS_DIR / "communication" / "5.5_dashboard_data_prep.py",
        ],
    },
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


@app.get("/api/pipeline-status")
def pipeline_status():
    return _pipeline_status


@app.post("/api/run-pipeline")
async def run_pipeline():
    if _pipeline_status["state"] == "running":
        raise HTTPException(status_code=409, detail="Pipeline is already running")
    asyncio.create_task(_execute_pipeline())
    return {"message": "Pipeline started"}


# ── Logging helpers ────────────────────────────────────────────────────────────

def _ts() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def _log(f, msg: str) -> None:
    line = f"[{_ts()}] {msg}"
    print(line)
    f.write(line + "\n")
    f.flush()


# ── Pipeline runner ────────────────────────────────────────────────────────────

async def _execute_pipeline() -> None:
    global _pipeline_status
    _pipeline_status = {"state": "running", "step": None, "error": None}

    start_dt  = datetime.now()
    log_name  = f"pipeline_{start_dt.strftime('%Y-%m-%d_%H%M%S')}.log"
    log_path  = LOGS_DIR / log_name
    pipeline_start = time.monotonic()

    with open(log_path, "w", encoding="utf-8") as lf:
        # ── Header ──
        lf.write("=" * 60 + "\n")
        lf.write("  KPI ANOMALY DETECTION PIPELINE\n")
        lf.write(f"  Started: {start_dt.strftime('%Y-%m-%d %H:%M:%S')}\n")
        lf.write("=" * 60 + "\n\n")
        lf.flush()

        try:
            for layer in PIPELINE_LAYERS:
                layer_name    = layer["name"]
                layer_scripts = layer["scripts"]
                layer_start   = time.monotonic()

                _log(lf, f"{'─' * 50}")
                _log(lf, f"  {layer_name} — STARTED")
                _log(lf, f"{'─' * 50}")

                for script_path in layer_scripts:
                    script_name = script_path.name
                    _pipeline_status["step"] = script_name
                    _log(lf, f"  Running: {script_name}")
                    script_start = time.monotonic()

                    result = await asyncio.to_thread(
                        subprocess.run,
                        [sys.executable, str(script_path)],
                        capture_output=True,
                        text=True,
                        cwd=str(BASE_DIR),
                    )

                    elapsed = time.monotonic() - script_start

                    if result.returncode != 0:
                        _log(lf, f"  ERROR: {script_name} (after {elapsed:.1f}s)")
                        lf.write("\n--- STDOUT ---\n")
                        lf.write(result.stdout or "(empty)\n")
                        lf.write("--- STDERR ---\n")
                        lf.write(result.stderr or "(empty)\n")
                        lf.write("-" * 40 + "\n\n")

                        error_tail = (result.stderr or result.stdout)[-600:].strip()
                        _log(lf, f"  PIPELINE FAILED at {script_name}")
                        lf.write("\n" + "=" * 60 + "\n")
                        lf.write(f"  PIPELINE FAILED\n")
                        lf.write(f"  Failed script : {script_name}\n")
                        lf.write(f"  Layer         : {layer_name}\n")
                        lf.write(f"  Timestamp     : {_ts()}\n")
                        lf.write("=" * 60 + "\n")
                        lf.flush()

                        _pipeline_status = {
                            "state": "error",
                            "step":  script_name,
                            "error": error_tail,
                        }
                        return

                    _log(lf, f"  DONE:  {script_name} ({elapsed:.1f}s)")

                    # Log any warnings / info lines from stdout even on success
                    warn_lines = [
                        line for line in (result.stdout or "").splitlines()
                        if any(tag in line.upper() for tag in ("[WARN]", "WARNING", "  INFO ", "FAIL"))
                    ]
                    if warn_lines:
                        lf.write(f"  [notices from {script_name}]\n")
                        for wl in warn_lines:
                            lf.write(f"    {wl}\n")
                        lf.flush()

                    # Log stderr even on success (captures Python warnings, deprecations)
                    if result.stderr and result.stderr.strip():
                        lf.write(f"  [stderr from {script_name}]\n")
                        for line in result.stderr.strip().splitlines():
                            lf.write(f"    {line}\n")
                        lf.flush()

                layer_elapsed = time.monotonic() - layer_start
                _log(lf, f"{'─' * 50}")
                _log(lf, f"  {layer_name} — COMPLETE ({layer_elapsed:.1f}s)")
                _log(lf, f"{'─' * 50}\n")

            # ── Footer ──
            total = time.monotonic() - pipeline_start
            mins, secs = divmod(int(total), 60)
            lf.write("=" * 60 + "\n")
            lf.write("  PIPELINE COMPLETE\n")
            lf.write(f"  Finished  : {_ts()}\n")
            lf.write(f"  Duration  : {mins}m {secs}s\n")
            lf.write(f"  Log file  : {log_name}\n")
            lf.write("=" * 60 + "\n")
            lf.flush()

            _pipeline_status = {"state": "done", "step": None, "error": None}

        except Exception as exc:
            _log(lf, f"UNEXPECTED ERROR: {exc}")
            _pipeline_status = {
                "state": "error",
                "step":  _pipeline_status.get("step"),
                "error": str(exc),
            }