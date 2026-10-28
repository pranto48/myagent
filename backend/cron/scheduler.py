# ==============================================================================
# Copyright (c) 2026 IT support BD (https://itsupport.com.bd)
# Made By Arif (https://arifmahmud.com/)
# Project: MyAgent | Autonomous Cron Scheduler Engine
# ==============================================================================

import os
import time
import json
import uuid
import asyncio
import logging
import traceback
from datetime import datetime
from typing import Dict, Any, Optional, Set

try:
    import aiosqlite
except ImportError:
    aiosqlite = None

try:
    from config import settings
except ImportError:
    class DummySettings:
        DATA_DIR = os.environ.get("DATA_DIR", "./data")
    settings = DummySettings()

from cron.cron_parser import CronExpression, validate_cron_expression
from cron.job_executors import run_task_by_type

logger = logging.getLogger("myagent.cron.scheduler")

def _get_ops_db_path() -> str:
    if os.name == 'nt' or not os.path.exists(settings.DATA_DIR):
        return os.path.join("./data", "ops.db")
    return os.path.join(settings.DATA_DIR, "ops.db")

class CronScheduler:
    """
    Enterprise Autonomous Cron Scheduler.
    Executes scheduled maintenance, backups, security scans, and AI tasks asynchronously.
    """
    def __init__(self, tick_seconds: int = 15):
        self.tick_seconds = tick_seconds
        self._running = False
        self._loop_task: Optional[asyncio.Task] = None
        self._active_jobs: Set[str] = set()

    async def start(self):
        """Starts the background scheduler loop."""
        if self._running:
            return
        self._running = True
        logger.info("Initializing Autonomous Cron Scheduler Engine...")
        # Pre-calculate missing next_run timestamps
        await self._sync_next_runs()
        self._loop_task = asyncio.create_task(self._scheduler_loop())
        logger.info(f"Cron Scheduler started with {self.tick_seconds}s evaluation tick.")

    async def stop(self):
        """Gracefully halts the scheduler loop."""
        self._running = False
        if self._loop_task:
            self._loop_task.cancel()
            try:
                await self._loop_task
            except asyncio.CancelledError:
                pass
        logger.info("Cron Scheduler stopped.")

    def is_job_running(self, job_id: str) -> bool:
        return job_id in self._active_jobs

    async def _get_db(self):
        path = _get_ops_db_path()
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        db = await aiosqlite.connect(path)
        db.row_factory = aiosqlite.Row
        await db.execute("PRAGMA journal_mode=WAL;")
        return db

    async def _sync_next_runs(self):
        """Ensures all enabled jobs have a valid future next_run timestamp."""
        try:
            db = await self._get_db()
            async with db.execute("SELECT id, expression, next_run FROM ops_cron_jobs WHERE is_enabled = 1") as cursor:
                rows = await cursor.fetchall()
                for r in rows:
                    job_id = r["id"]
                    expr = r["expression"]
                    next_run = r["next_run"]

                    # Check if next_run is a valid future timestamp YYYY-MM-DD HH:MM:SS
                    needs_calc = False
                    if not next_run or len(str(next_run)) != 19 or "-" not in str(next_run):
                        needs_calc = True
                    else:
                        try:
                            dt = datetime.strptime(str(next_run), "%Y-%m-%d %H:%M:%S")
                            if dt <= datetime.now():
                                needs_calc = True
                        except Exception:
                            needs_calc = True

                    if needs_calc:
                        try:
                            cron = CronExpression(expr)
                            calc_next = cron.get_next_run().strftime("%Y-%m-%d %H:%M:%S")
                            await db.execute("UPDATE ops_cron_jobs SET next_run = ? WHERE id = ?", (calc_next, job_id))
                        except Exception as e:
                            logger.warning(f"Could not calculate next run for job {job_id} [{expr}]: {e}")
            await db.commit()
            await db.close()
        except Exception as e:
            logger.error(f"Error syncing next runs: {e}")

    async def _scheduler_loop(self):
        """Continuously polls for due jobs."""
        while self._running:
            try:
                await self._check_and_dispatch_due_jobs()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in scheduler tick: {e}")
            
            await asyncio.sleep(self.tick_seconds)

    async def _check_and_dispatch_due_jobs(self):
        """Identifies jobs whose next_run is past or now, and executes them."""
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        db = await self._get_db()
        try:
            async with db.execute("""
                SELECT * FROM ops_cron_jobs 
                WHERE is_enabled = 1 AND next_run IS NOT NULL AND next_run <= ?
            """, (now_str,)) as cursor:
                due_jobs = [dict(r) for r in await cursor.fetchall()]

            for job in due_jobs:
                job_id = job["id"]
                if job_id in self._active_jobs:
                    # Skip overlapping execution
                    continue
                
                # Launch execution in background task
                asyncio.create_task(self.execute_job(job))
        finally:
            await db.close()

    async def execute_job(self, job: Dict[str, Any]) -> Dict[str, Any]:
        """Executes a single job, records execution history, and schedules the next run."""
        job_id = job["id"]
        job_name = job["name"]
        task_type = job["task_type"]
        expr = job["expression"]
        payload_raw = job.get("payload")

        payload: Dict[str, Any] = {}
        if payload_raw:
            try:
                payload = json.loads(payload_raw) if isinstance(payload_raw, str) else payload_raw
            except Exception:
                payload = {}

        self._active_jobs.add(job_id)
        start_time = time.time()
        run_at_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        status = "SUCCESS"
        output = ""

        # Update last_status to RUNNING in database
        try:
            db = await self._get_db()
            await db.execute("UPDATE ops_cron_jobs SET last_status = 'RUNNING' WHERE id = ?", (job_id,))
            await db.commit()
            await db.close()
        except Exception:
            pass

        try:
            # Execute with a 180s timeout limit
            output = await asyncio.wait_for(run_task_by_type(task_type, payload), timeout=180.0)
        except asyncio.TimeoutError:
            status = "FAILED"
            output = f"Execution timed out after 180 seconds."
            logger.error(f"Cron job '{job_name}' timed out.")
        except Exception as e:
            status = "FAILED"
            output = f"Error: {str(e)}\n{traceback.format_exc()[:300]}"
            logger.error(f"Cron job '{job_name}' failed: {e}")
        finally:
            self._active_jobs.discard(job_id)

        duration_ms = int((time.time() - start_time) * 1000)

        # Calculate subsequent next_run
        next_run_str = None
        try:
            cron = CronExpression(expr)
            next_run_str = cron.get_next_run().strftime("%Y-%m-%d %H:%M:%S")
        except Exception as e:
            logger.warning(f"Failed to calculate next run for {job_id}: {e}")

        # Update job row and record history
        try:
            db = await self._get_db()
            await db.execute("""
                UPDATE ops_cron_jobs 
                SET last_run = ?, next_run = ?, last_status = ?
                WHERE id = ?
            """, (run_at_str, next_run_str, status, job_id))

            hist_id = str(uuid.uuid4())
            await db.execute("""
                INSERT INTO ops_cron_history (id, job_id, job_name, run_at, duration_ms, status, output)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (hist_id, job_id, job_name, run_at_str, duration_ms, status, output))
            
            # Record in ops_logs
            log_id = str(uuid.uuid4())
            await db.execute("""
                INSERT INTO ops_logs (id, timestamp, level, module, message, details)
                VALUES (?, ?, ?, 'OpsCron', ?, ?)
            """, (
                log_id,
                run_at_str,
                "INFO" if status == "SUCCESS" else "ERROR",
                f"Job '{job_name}' executed ({status}) in {duration_ms}ms.",
                json.dumps({"job_id": job_id, "duration_ms": duration_ms, "output": output}, ensure_ascii=False)
            ))

            await db.commit()
            await db.close()
        except Exception as e:
            logger.error(f"Error recording job execution for {job_id}: {e}")

        return {
            "success": status == "SUCCESS",
            "job_id": job_id,
            "job_name": job_name,
            "status": status,
            "duration_ms": duration_ms,
            "output": output,
            "next_run": next_run_str
        }

    async def trigger_job_by_id(self, job_id: str) -> Dict[str, Any]:
        """Manually triggers an immediate run of a job by ID."""
        db = await self._get_db()
        try:
            async with db.execute("SELECT * FROM ops_cron_jobs WHERE id = ?", (job_id,)) as cursor:
                row = await cursor.fetchone()
                if not row:
                    raise ValueError(f"Job '{job_id}' not found.")
                job = dict(row)
        finally:
            await db.close()

        return await self.execute_job(job)


# Global singleton scheduler instance
cron_scheduler = CronScheduler(tick_seconds=20)
