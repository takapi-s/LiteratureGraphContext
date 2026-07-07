"""Background job management."""

from __future__ import annotations

import threading
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional


class JobStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class JobInfo:
    job_id: str
    status: JobStatus
    start_time: datetime
    end_time: Optional[datetime] = None
    total_items: int = 0
    processed_items: int = 0
    current_item: Optional[str] = None
    message: Optional[str] = None
    errors: List[str] = field(default_factory=list)
    result: Optional[Dict[str, Any]] = None

    @property
    def progress_percentage(self) -> float:
        if self.total_items == 0:
            return 0.0
        return (self.processed_items / self.total_items) * 100


class JobManager:
    def __init__(self) -> None:
        self._jobs: Dict[str, JobInfo] = {}
        self._lock = threading.Lock()

    def create_job(self) -> str:
        job_id = str(uuid.uuid4())
        with self._lock:
            self._jobs[job_id] = JobInfo(
                job_id=job_id,
                status=JobStatus.PENDING,
                start_time=datetime.now(),
            )
        return job_id

    def update_job(self, job_id: str, **kwargs: Any) -> None:
        with self._lock:
            job = self._jobs.get(job_id)
            if not job:
                return
            for key, value in kwargs.items():
                if hasattr(job, key):
                    setattr(job, key, value)

    def get_job(self, job_id: str) -> Optional[JobInfo]:
        with self._lock:
            return self._jobs.get(job_id)

    def list_jobs(self) -> List[JobInfo]:
        with self._lock:
            return list(self._jobs.values())

    def job_to_dict(self, job: JobInfo) -> Dict[str, Any]:
        return {
            "job_id": job.job_id,
            "status": job.status.value,
            "start_time": job.start_time.isoformat(),
            "end_time": job.end_time.isoformat() if job.end_time else None,
            "total_items": job.total_items,
            "processed_items": job.processed_items,
            "progress_percentage": round(job.progress_percentage, 1),
            "current_item": job.current_item,
            "message": job.message,
            "errors": job.errors,
            "result": job.result,
        }

    def complete_job(self, job_id: str, result: Optional[Dict[str, Any]] = None) -> None:
        self.update_job(
            job_id,
            status=JobStatus.COMPLETED,
            end_time=datetime.now(),
            result=result,
        )

    def fail_job(self, job_id: str, error: str) -> None:
        with self._lock:
            job = self._jobs.get(job_id)
            if not job:
                return
            job.status = JobStatus.FAILED
            job.end_time = datetime.now()
            job.errors.append(error)
