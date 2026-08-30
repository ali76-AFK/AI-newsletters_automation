#!/usr/bin/env python3
"""Test script for ScheduleRun helper methods."""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.db import SessionLocal
from app.models import ScheduleRun, NewsletterSchedule

def main():
    db = SessionLocal()
    try:
        # List all schedules
        schedules = db.query(NewsletterSchedule).all()
        print(f"Found {len(schedules)} schedule(s):\n")
        
        for sched in schedules:
            print(f"Schedule ID: {sched.id}")
            print(f"  Email: {sched.email}")
            print(f"  Enabled: {sched.enabled}")
            print(f"  Timezone: {sched.timezone}")
            print(f"  Delivery time: {sched.delivery_time}")
            
            # Get runs by status
            runs_by_status = ScheduleRun.get_schedule_runs_by_status(db, sched.id)
            print(f"  Runs by status: {runs_by_status}")
            
            # Get recent runs
            recent = ScheduleRun.get_recent_runs(db, sched.id, limit=5)
            if recent:
                print(f"  Recent runs ({len(recent)}):")
                for run in recent:
                    print(f"    - {run.started_at} | status={run.status} | newsletter_id={run.newsletter_id}")
            else:
                print(f"  Recent runs: None")
            print()
    finally:
        db.close()

if __name__ == "__main__":
    main()
