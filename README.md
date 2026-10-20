# Job Search Assistant

Build a PDF résumé from one structured profile, discover job listings, track applications, and draft cover letters. A Streamlit interface brings the command-line tools together. Optional Claude features tailor or rewrite a résumé.

## Quick start

Use Python 3.12 (the CI version). From the repository root:

```bash
python -m venv .venv
source .venv/bin/activate
# Windows: .venv\Scripts\activate
python -m pip install -r requirements.txt
cp data/profile.example.json data/profile.json
streamlit run streamlit_app.py
```

Edit `data/profile.json` with your own information. Open http://localhost:8501. The existing interface and application status identifiers use Turkish; this guide explains the workflow in English.

## Tools

| Tool | Purpose | API key |
|---|---|---|
| `app.cv_generator` | Generate a single-column PDF résumé | None |
| `app.job_search` | Search supported job boards and save deduplicated SQLite listings | None |
| `app.tracker` | Manage application statuses and notes | None |
| `app.cover_letter` | Create an editable cover-letter draft in text/PDF | None |
| `app.cv_tailor` | Reorder and tailor an existing profile for a job | `ANTHROPIC_API_KEY` |
| `app.cv_rewrite` | Rewrite an existing text/PDF résumé into the profile schema | `ANTHROPIC_API_KEY` |

```bash
python -m app.cv_generator --profile data/profile.json --output cv.pdf
python -m app.job_search --search-term "Backend Developer" --location "Istanbul, Turkey" --results 20 --sites linkedin,indeed --profile data/profile.json
python -m app.tracker list
python -m app.tracker --db data/jobs.db set "<job_url>" başvuruldu --notes "Applied today"
python -m app.tracker stats
python -m app.cover_letter --profile data/profile.json --title "Backend Developer" --company "Acme" --job-description-file job.txt --output cover_letter.txt --pdf cover_letter.pdf
python -m app.cv_tailor --profile data/profile.json --job-description-file job.txt --output cv_tailored.pdf
python -m app.cv_rewrite --input original_cv.txt --output data/profile.json --pdf rewritten_cv.pdf
```

Use `--help` on a module to see its current options. Tracker statuses are `yeni` (new), `başvuruldu` (applied), `mülakat` (interview), `reddedildi` (rejected), and `teklif` (offer). Put the tracker's `--db` option before its subcommand.

## Storage and repeat searches

Listings live in `data/jobs.db`, keyed by job URL. Repeat searches refresh the title, company, location, dates and available description/score without changing your application status or notes. Missing descriptions and scores do not erase existing values. The reported new-listing count counts only newly inserted URLs, including when a search returns duplicates.

The profile schema is defined in `app/models.py`; PDF fonts live in `assets/fonts/`. Matching scores are keyword-based relevance estimates. They do not predict hiring outcomes or guarantee ATS acceptance. Review generated documents and verify every fact before sending them.

## Privacy and configuration

`data/profile.json` and `data/jobs.db` are ignored by Git. Keep backups outside the repository. Local generation and tracking do not need an AI key. Job searches contact the selected job boards; optional Claude features send the supplied résumé/profile/job text to the configured API. Keep keys in your environment and never commit them.

Job-board availability varies by region and provider. A provider failure does not discard results from the other providers. Use modest search volumes and respect each provider's terms and request limits.

## Validation

```bash
python -m pip install pytest
python -m compileall -q app streamlit_app.py
python -m pytest -q
```

GitHub Actions runs compilation and storage regressions on Python 3.12. Tests use temporary databases and do not scrape live job boards or call paid AI services. [Detailed previous guide (Turkish)](README.tr.md).
