"""CrewAI mission endpoints — launch a crew, list/inspect jobs.

Extracted from main.py. Shares the _crew_jobs registry via app_state.
"""

import time

from app_state import _crew_jobs
from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel

router = APIRouter(tags=["crew"])


class CrewRequest(BaseModel):
    mission:      str
    mission_type: str = "auto"


# ─── moved verbatim from main.py ───
@router.post("/v1/crew/run")
def run_crew_endpoint(req: CrewRequest, background: BackgroundTasks):
    job_id = f"crew_{int(time.time())}"
    _crew_jobs[job_id] = {
        "id":         job_id,
        "mission":    req.mission,
        "status":     "running",
        "started_at": time.time(),
        "result":     None,
    }

    def _run():
        try:
            from crew_factory import run_crew
            result = run_crew(req.mission, req.mission_type)
            _crew_jobs[job_id].update({
                "status":   "done",
                "result":   result,
                "ended_at": time.time(),
            })
        except Exception as e:
            _crew_jobs[job_id].update({
                "status":   "failed",
                "error":    str(e),
                "ended_at": time.time(),
            })
            print(f"[crew] erreur: {e}")

    background.add_task(_run)
    timeout = 300
    start   = time.time()
    while _crew_jobs[job_id]["status"] == "running":
        if time.time() - start > timeout:
            return {"error": "Timeout — crew trop long"}
        time.sleep(1)

    return _crew_jobs[job_id].get("result", {"error": _crew_jobs[job_id].get("error")})

@router.get("/v1/crew/jobs")
def list_crew_jobs():
    return {"jobs": list(_crew_jobs.values())}

@router.get("/v1/crew/jobs/{job_id}")
def get_crew_job(job_id: str):
    job = _crew_jobs.get(job_id)
    if not job:
        raise HTTPException(404, "Mission non trouvée")
    return job
