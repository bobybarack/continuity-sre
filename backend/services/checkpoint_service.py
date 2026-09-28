"""CONTINUITY Durable Checkpointing & State Persistence Service.

Provides SQLite / Cloud SQL durable storage for incidents, remediation transactions,
state snapshots, and human-in-the-loop (HITL) checkpoints so execution survives
container restarts and maintains an immutable audit ledger.
"""

from __future__ import annotations

import json
import sqlite3
import time
import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from services.remediation_models import (
    RemediationTransaction,
    HealthSnapshot,
    RecoveryProof,
    EscalationPackage,
)

logger = logging.getLogger("continuity.checkpoint")

DEFAULT_DB_PATH = Path(__file__).resolve().parent.parent / "continuity_checkpoint.db"


class CheckpointService:
    """Manages persistent SQLite ledger for incident transactions and HITL graph checkpoints."""

    def __init__(self, db_path: Optional[Path | str] = None):
        if db_path:
            self.db_path = Path(db_path)
        else:
            worker = os.environ.get("PYTEST_XDIST_WORKER")
            if worker:
                self.db_path = Path(__file__).resolve().parent.parent / f"continuity_checkpoint_{worker}.db"
            else:
                self.db_path = DEFAULT_DB_PATH
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path), timeout=10.0)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode = WAL;")
        conn.execute("PRAGMA synchronous = NORMAL;")
        return conn

    def _init_db(self):
        """Initializes relational tables if they do not exist."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS incidents (
                    incident_id TEXT PRIMARY KEY,
                    stream_title TEXT,
                    severity TEXT,
                    status TEXT,
                    failure_mode TEXT,
                    created_at REAL,
                    updated_at REAL,
                    payload TEXT
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS transactions (
                    transaction_id TEXT PRIMARY KEY,
                    incident_id TEXT,
                    idempotency_key TEXT UNIQUE,
                    action_name TEXT,
                    status TEXT,
                    created_at REAL,
                    pre_snapshot TEXT,
                    post_snapshot TEXT,
                    rollback_action TEXT,
                    rollback_status TEXT,
                    recovery_proof TEXT,
                    FOREIGN KEY (incident_id) REFERENCES incidents (incident_id)
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS checkpoints (
                    checkpoint_id TEXT PRIMARY KEY,
                    incident_id TEXT,
                    step_name TEXT,
                    suspended_at REAL,
                    status TEXT,
                    state_data TEXT,
                    resolution_data TEXT
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS audit_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp REAL,
                    incident_id TEXT,
                    role TEXT,
                    event_type TEXT,
                    details TEXT
                )
            """)
            conn.commit()

    # --------------------------------------------------------------------------
    # Transactions Persistence
    # --------------------------------------------------------------------------

    def save_transaction(self, tx: RemediationTransaction):
        """Persists or updates an ACID remediation transaction."""
        prev_state_json = json.dumps(tx.previous_state) if tx.previous_state else None
        intended_state_json = json.dumps(tx.intended_state) if tx.intended_state else None
        proof_json = json.dumps(tx.proof.model_dump()) if tx.proof else None

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO transactions (
                    transaction_id, incident_id, idempotency_key, action_name,
                    status, created_at, pre_snapshot, post_snapshot,
                    rollback_action, rollback_status, recovery_proof
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(transaction_id) DO UPDATE SET
                    status = excluded.status,
                    post_snapshot = excluded.post_snapshot,
                    rollback_status = excluded.rollback_status,
                    recovery_proof = excluded.recovery_proof
            """, (
                tx.transaction_id,
                tx.incident_id,
                tx.idempotency_key,
                tx.action,
                tx.status,
                tx.applied_at,
                prev_state_json,
                intended_state_json,
                tx.rollback_action,
                tx.status if tx.status == "ROLLED_BACK" else None,
                proof_json
            ))
            conn.commit()

    def _row_to_transaction(self, row) -> RemediationTransaction:
        prev_state = json.loads(row["pre_snapshot"]) if row["pre_snapshot"] else {}
        intended_state = json.loads(row["post_snapshot"]) if row["post_snapshot"] else None
        proof = RecoveryProof.model_validate(json.loads(row["recovery_proof"])) if row["recovery_proof"] else None

        return RemediationTransaction(
            transaction_id=row["transaction_id"],
            incident_id=row["incident_id"],
            idempotency_key=row["idempotency_key"],
            action=row["action_name"],
            status=row["status"],
            applied_at=row["created_at"],
            previous_state=prev_state,
            intended_state=intended_state,
            rollback_action=row["rollback_action"],
            failure_mode=None,
            proof=proof
        )

    def get_transaction(self, transaction_id: str) -> Optional[RemediationTransaction]:
        """Loads a transaction from SQLite storage."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM transactions WHERE transaction_id = ?", (transaction_id,))
            row = cursor.fetchone()
            if not row:
                return None
            return self._row_to_transaction(row)

    def get_transaction_by_idempotency(self, idempotency_key: str) -> Optional[RemediationTransaction]:
        """Loads a transaction by idempotency key from SQLite storage."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM transactions WHERE idempotency_key = ?", (idempotency_key,))
            row = cursor.fetchone()
            if not row:
                return None
            return self._row_to_transaction(row)

    # --------------------------------------------------------------------------
    # Checkpoints & Graph Suspension (HITL)
    # --------------------------------------------------------------------------

    def save_checkpoint(
        self,
        checkpoint_id: str,
        incident_id: str,
        step_name: str,
        state_data: Dict[str, Any]
    ):
        """Saves an execution checkpoint when graph interrupts for human approval."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO checkpoints (
                    checkpoint_id, incident_id, step_name, suspended_at, status, state_data, resolution_data
                ) VALUES (?, ?, ?, ?, 'SUSPENDED', ?, NULL)
            """, (
                checkpoint_id,
                incident_id,
                step_name,
                time.time(),
                json.dumps(state_data)
            ))
            conn.commit()

    def get_checkpoint(self, checkpoint_id: str) -> Optional[Dict[str, Any]]:
        """Retrieves checkpoint state for resumption."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM checkpoints WHERE checkpoint_id = ?", (checkpoint_id,))
            row = cursor.fetchone()
            if not row:
                return None
            return {
                "checkpoint_id": row["checkpoint_id"],
                "incident_id": row["incident_id"],
                "step_name": row["step_name"],
                "suspended_at": row["suspended_at"],
                "status": row["status"],
                "state_data": json.loads(row["state_data"]) if row["state_data"] else {},
                "resolution_data": json.loads(row["resolution_data"]) if row["resolution_data"] else None
            }

    def resume_checkpoint(
        self,
        checkpoint_id: str,
        resolution_data: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Resumes a suspended checkpoint with the supervisor's decision (Approve/Deny)."""
        chk = self.get_checkpoint(checkpoint_id)
        if not chk or chk["status"] != "SUSPENDED":
            return None

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE checkpoints
                SET status = 'RESUMED', resolution_data = ?
                WHERE checkpoint_id = ?
            """, (json.dumps(resolution_data), checkpoint_id))
            conn.commit()

        chk["status"] = "RESUMED"
        chk["resolution_data"] = resolution_data
        return chk

    def list_suspended_checkpoints(self) -> List[Dict[str, Any]]:
        """Lists all checkpoints currently awaiting human operator approval."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM checkpoints WHERE status = 'SUSPENDED' ORDER BY suspended_at DESC")
            rows = cursor.fetchall()
            return [
                {
                    "checkpoint_id": r["checkpoint_id"],
                    "incident_id": r["incident_id"],
                    "step_name": r["step_name"],
                    "suspended_at": r["suspended_at"],
                    "state_data": json.loads(r["state_data"]) if r["state_data"] else {}
                }
                for r in rows
            ]

    def get_suspended_checkpoint_by_incident(self, incident_id: str) -> Optional[Dict[str, Any]]:
        """Retrieves an active suspended checkpoint for a specific incident."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM checkpoints WHERE incident_id = ? AND status = 'SUSPENDED' ORDER BY suspended_at DESC LIMIT 1",
                (incident_id,)
            )
            row = cursor.fetchone()
            if not row:
                return None
            return {
                "checkpoint_id": row["checkpoint_id"],
                "incident_id": row["incident_id"],
                "step_name": row["step_name"],
                "suspended_at": row["suspended_at"],
                "status": row["status"],
                "state_data": json.loads(row["state_data"]) if row["state_data"] else {},
                "resolution_data": json.loads(row["resolution_data"]) if row["resolution_data"] else None
            }

    def get_latest_checkpoint_by_incident(self, incident_id: str) -> Optional[Dict[str, Any]]:
        """Retrieves the latest checkpoint for a specific incident regardless of status."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM checkpoints WHERE incident_id = ? ORDER BY suspended_at DESC LIMIT 1",
                (incident_id,)
            )
            row = cursor.fetchone()
            if not row:
                return None
            return {
                "checkpoint_id": row["checkpoint_id"],
                "incident_id": row["incident_id"],
                "step_name": row["step_name"],
                "suspended_at": row["suspended_at"],
                "status": row["status"],
                "state_data": json.loads(row["state_data"]) if row["state_data"] else {},
                "resolution_data": json.loads(row["resolution_data"]) if row["resolution_data"] else None
            }

    # --------------------------------------------------------------------------
    # Audit Logging
    # --------------------------------------------------------------------------

    def log_audit_event(
        self,
        incident_id: str,
        role: str,
        event_type: str,
        details: Dict[str, Any]
    ):
        """Appends an immutable audit log entry."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO audit_logs (timestamp, incident_id, role, event_type, details)
                VALUES (?, ?, ?, ?, ?)
            """, (time.time(), incident_id, role, event_type, json.dumps(details)))
            conn.commit()

    def clear(self):
        """Resets all database tables for test isolation."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM audit_logs")
            cursor.execute("DELETE FROM checkpoints")
            cursor.execute("DELETE FROM transactions")
            cursor.execute("DELETE FROM incidents")
            conn.commit()


# Singleton instance
checkpoint_service = CheckpointService()
