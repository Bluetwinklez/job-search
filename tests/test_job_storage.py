import sqlite3
import pandas as pd
from app.job_search import save_jobs, get_job, set_status


def test_rescans_refresh_metadata_without_counting_existing_jobs(tmp_path):
    db = tmp_path / 'jobs.db'
    frame = pd.DataFrame([dict(job_url='https://example.test/job', title='Old', description='Original')])
    assert save_jobs(frame, db) == 1
    set_status(db, 'https://example.test/job', 'başvuruldu', 'Keep my notes')
    frame['title'] = 'Updated'
    frame['description'] = 'Updated description'
    assert save_jobs(frame, db) == 0
    job = get_job(db, 'https://example.test/job')
    assert job['title'] == 'Updated'
    assert job['description'] == 'Updated description'
    assert job['status'] == 'başvuruldu'
    assert job['notes'] == 'Keep my notes'


def test_duplicate_rows_are_counted_once_and_partial_scans_keep_description(tmp_path):
    db = tmp_path / 'jobs.db'
    row = dict(job_url='https://example.test/job', title='Title', description='Keep this')
    assert save_jobs(pd.DataFrame([row, row]), db) == 1
    with sqlite3.connect(db) as conn:
        conn.execute('UPDATE jobs SET match_score = 0.8')
    assert save_jobs(pd.DataFrame([{**row, 'description': None}]), db) == 0
    job = get_job(db, row['job_url'])
    assert job['description'] == 'Keep this'
    assert job['match_score'] == 0.8
