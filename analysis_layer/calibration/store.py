"""Calibration store: persists every assessment and its resolvable claim, and on
resolution records the score (PRD A13/A11, FR-13).

Two interchangeable backends implement one interface: an in-memory store (the
default, keeps the offline harness infra-light) and Postgres+pgvector (the
production system of record, Section 9.2). The accumulating record of graded
judgments and outcomes is the layer's compounding asset (A11).
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from analysis_layer.config import Settings, get_settings
from analysis_layer.schema.assessment import Assessment, CalibrationStatus


@dataclass
class StoredAssessment:
    assessment: Assessment
    decision_type: str
    # Dominant source class of the diagnostic evidence, for per-segment
    # calibration (A11: calibration tracked per decision type and source class).
    source_class: str = "mixed"
    status: CalibrationStatus = CalibrationStatus.open
    forecast_probability: float = 0.5
    outcome: Optional[bool] = None  # True if the resolvable claim proved out
    brier_contribution: Optional[float] = None


class CalibrationStore(ABC):
    @abstractmethod
    def save(self, stored: StoredAssessment) -> None: ...

    @abstractmethod
    def get(self, assessment_id: str) -> Optional[StoredAssessment]: ...

    @abstractmethod
    def all(self) -> List[StoredAssessment]: ...

    @abstractmethod
    def resolve(self, assessment_id: str, outcome: bool, brier_contribution: float) -> None: ...

    def resolved(self) -> List[StoredAssessment]:
        return [s for s in self.all() if s.status != CalibrationStatus.open]


class MemoryStore(CalibrationStore):
    def __init__(self) -> None:
        self._items: Dict[str, StoredAssessment] = {}

    def save(self, stored: StoredAssessment) -> None:
        self._items[stored.assessment.id] = stored

    def get(self, assessment_id: str) -> Optional[StoredAssessment]:
        return self._items.get(assessment_id)

    def all(self) -> List[StoredAssessment]:
        return list(self._items.values())

    def resolve(self, assessment_id: str, outcome: bool, brier_contribution: float) -> None:
        stored = self._items.get(assessment_id)
        if stored is None:
            raise KeyError(f"No assessment {assessment_id!r} to resolve.")
        stored.outcome = outcome
        stored.brier_contribution = brier_contribution
        stored.status = (
            CalibrationStatus.proved_out if outcome else CalibrationStatus.disproved
        )


class PostgresStore(CalibrationStore):  # pragma: no cover - requires a live DB
    """Postgres + pgvector backend. Stores the assessment JSON and the
    calibration record; embeddings live alongside for reference-case retrieval.
    Imported lazily so the offline harness never needs psycopg installed."""

    def __init__(self, settings: Optional[Settings] = None) -> None:
        self.settings = settings or get_settings()
        try:
            import psycopg  # noqa: F401
        except ImportError as exc:
            raise RuntimeError(
                "The 'postgres' extra is not installed. Install with "
                "`pip install \"psycopg[binary]>=3.1\" \"pgvector>=0.2\"` or set "
                "ANALYSIS_LAYER_STORE_BACKEND=memory."
            ) from exc
        self._psycopg = psycopg
        self._dsn = self.settings.database_url
        self._ensure_schema()

    def _connect(self):
        return self._psycopg.connect(self._dsn)

    def _ensure_schema(self) -> None:
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS assessments (
                    id TEXT PRIMARY KEY,
                    decision_type TEXT NOT NULL,
                    source_class TEXT NOT NULL,
                    status TEXT NOT NULL,
                    forecast_probability DOUBLE PRECISION NOT NULL,
                    outcome BOOLEAN,
                    brier_contribution DOUBLE PRECISION,
                    payload JSONB NOT NULL
                );
                """
            )
            conn.commit()

    def save(self, stored: StoredAssessment) -> None:
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO assessments
                    (id, decision_type, source_class, status, forecast_probability,
                     outcome, brier_contribution, payload)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (id) DO UPDATE SET
                    decision_type = EXCLUDED.decision_type,
                    source_class = EXCLUDED.source_class,
                    status = EXCLUDED.status,
                    forecast_probability = EXCLUDED.forecast_probability,
                    outcome = EXCLUDED.outcome,
                    brier_contribution = EXCLUDED.brier_contribution,
                    payload = EXCLUDED.payload;
                """,
                (
                    stored.assessment.id,
                    stored.decision_type,
                    stored.source_class,
                    stored.status.value,
                    stored.forecast_probability,
                    stored.outcome,
                    stored.brier_contribution,
                    stored.assessment.model_dump_json(),
                ),
            )
            conn.commit()

    def _row_to_stored(self, row) -> StoredAssessment:
        (aid, decision_type, source_class, status, fp, outcome, brier, payload) = row
        return StoredAssessment(
            assessment=Assessment.model_validate_json(payload),
            decision_type=decision_type,
            source_class=source_class,
            status=CalibrationStatus(status),
            forecast_probability=fp,
            outcome=outcome,
            brier_contribution=brier,
        )

    def get(self, assessment_id: str) -> Optional[StoredAssessment]:
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute(
                "SELECT id, decision_type, source_class, status, forecast_probability, "
                "outcome, brier_contribution, payload FROM assessments WHERE id = %s",
                (assessment_id,),
            )
            row = cur.fetchone()
        return self._row_to_stored(row) if row else None

    def all(self) -> List[StoredAssessment]:
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute(
                "SELECT id, decision_type, source_class, status, forecast_probability, "
                "outcome, brier_contribution, payload FROM assessments"
            )
            rows = cur.fetchall()
        return [self._row_to_stored(r) for r in rows]

    def resolve(self, assessment_id: str, outcome: bool, brier_contribution: float) -> None:
        status = CalibrationStatus.proved_out if outcome else CalibrationStatus.disproved
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute(
                "UPDATE assessments SET status=%s, outcome=%s, brier_contribution=%s WHERE id=%s",
                (status.value, outcome, brier_contribution, assessment_id),
            )
            conn.commit()


def build_store(settings: Optional[Settings] = None) -> CalibrationStore:
    settings = settings or get_settings()
    backend = settings.store_backend.lower()
    if backend == "postgres":
        return PostgresStore(settings)
    if backend == "memory":
        return MemoryStore()
    raise ValueError(f"Unknown store backend: {settings.store_backend!r}")
