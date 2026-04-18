"""Standalone background worker process.

Runs the notification scheduler and AI case-record summarizer.
Deployed as a separate container (backend-worker) so the main
Gunicorn workers are not burdened and these tasks run exactly once.

Usage: python scripts/run_worker.py
"""
import asyncio
import os
import sys

# Ensure the app package is on the path when run from the scripts/ dir
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.services.notification_scheduler import run_notification_scheduler
from app.services.case_record_summarizer import summarize_pending_case_records
import app.models  # noqa: F401 — register all ORM models


async def _run_ai_summarizer():
    while True:
        try:
            count = await summarize_pending_case_records()
            if count:
                print(f"[AI Summarizer] Summarized {count} case record(s)", flush=True)
        except Exception as exc:
            print(f"[AI Summarizer] Error: {exc}", flush=True)
        await asyncio.sleep(120)


async def main():
    print("[Worker] Starting background services…", flush=True)
    await asyncio.gather(
        run_notification_scheduler(),
        _run_ai_summarizer(),
    )


if __name__ == "__main__":
    asyncio.run(main())
