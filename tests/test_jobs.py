from litgraph.core.jobs import JobManager, JobStatus


def test_job_manager_list_and_status():
    jm = JobManager()
    job_id = jm.create_job()
    jm.update_job(job_id, status=JobStatus.RUNNING, total_items=2, processed_items=1)
    jobs = jm.list_jobs()
    assert len(jobs) == 1
    payload = jm.job_to_dict(jobs[0])
    assert payload["status"] == "running"
    assert payload["progress_percentage"] == 50.0
    jm.complete_job(job_id, {"extracted": 2})
    done = jm.job_to_dict(jm.get_job(job_id))
    assert done["status"] == "completed"
    assert done["result"]["extracted"] == 2
