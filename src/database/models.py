"""SQLAlchemy ORM models for EDA-Genius database."""

import uuid
from datetime import datetime
from typing import Optional, List, Dict, Any
from sqlalchemy import (
    Column,
    String,
    Float,
    Integer,
    BigInteger,
    DateTime,
    ForeignKey,
    Text,
    Enum as SQLEnum
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import declarative_base, relationship

from src.common.types import StageName, RunStatus, AnomalySeverity

Base = declarative_base()


class Design(Base):
    """Catalog of RTL digital designs."""
    __tablename__ = "designs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(128), nullable=False, unique=True, index=True)
    rtl_top_module = Column(String(128), nullable=False)
    source_repo_url = Column(Text, nullable=True)
    commit_hash = Column(String(64), nullable=True)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    runs = relationship("Run", back_populates="design", cascade="all, delete-orphan")


class Run(Base):
    """Individual EDA execution run."""
    __tablename__ = "runs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    design_id = Column(UUID(as_uuid=True), ForeignKey("designs.id", ondelete="CASCADE"), nullable=False, index=True)
    status = Column(SQLEnum(RunStatus), default=RunStatus.PENDING, nullable=False, index=True)
    target_pdk = Column(String(64), nullable=False, index=True)
    clock_period_ns = Column(Float, nullable=False)
    tool_versions = Column(JSONB, nullable=False, default=dict)
    run_config = Column(JSONB, nullable=False, default=dict)
    workdir_path = Column(Text, nullable=False)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    total_wall_time_s = Column(Float, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    design = relationship("Design", back_populates="runs")
    stages = relationship("RunStage", back_populates="run", cascade="all, delete-orphan")
    metrics = relationship("StageMetric", back_populates="run", cascade="all, delete-orphan")
    anomalies = relationship("RunAnomaly", back_populates="run", cascade="all, delete-orphan")


class RunStage(Base):
    """Fine-grained execution stage (synthesis, placement, routing, etc.)."""
    __tablename__ = "run_stages"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    run_id = Column(UUID(as_uuid=True), ForeignKey("runs.id", ondelete="CASCADE"), nullable=False, index=True)
    stage_name = Column(SQLEnum(StageName), nullable=False)
    stage_order = Column(Integer, nullable=False)
    tool_name = Column(String(64), nullable=False)
    status = Column(SQLEnum(RunStatus), default=RunStatus.PENDING, nullable=False)
    exit_code = Column(Integer, nullable=True)
    raw_log_path = Column(Text, nullable=True)
    output_artifact_path = Column(Text, nullable=True)
    runtime_s = Column(Float, nullable=True)
    peak_memory_mb = Column(Float, nullable=True)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)

    run = relationship("Run", back_populates="stages")
    metrics = relationship("StageMetric", back_populates="stage", cascade="all, delete-orphan")


class StageMetric(Base):
    """Atomic signoff or micro-metric extracted from tool reports with exact provenance."""
    __tablename__ = "stage_metrics"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    run_id = Column(UUID(as_uuid=True), ForeignKey("runs.id", ondelete="CASCADE"), nullable=False, index=True)
    run_stage_id = Column(UUID(as_uuid=True), ForeignKey("run_stages.id", ondelete="CASCADE"), nullable=True, index=True)
    metric_category = Column(String(64), nullable=False, index=True)
    metric_name = Column(String(128), nullable=False, index=True)
    float_value = Column(Float, nullable=True)
    string_value = Column(Text, nullable=True)
    metadata_json = Column(JSONB, nullable=True)
    log_line_number = Column(Integer, nullable=True)
    log_byte_offset = Column(BigInteger, nullable=True)
    recorded_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    run = relationship("Run", back_populates="metrics")
    stage = relationship("RunStage", back_populates="metrics")


class RunAnomaly(Base):
    """Detected anomaly, timing violation, or physical design divergence."""
    __tablename__ = "run_anomalies"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    run_id = Column(UUID(as_uuid=True), ForeignKey("runs.id", ondelete="CASCADE"), nullable=False, index=True)
    run_stage_id = Column(UUID(as_uuid=True), ForeignKey("run_stages.id", ondelete="SET NULL"), nullable=True)
    severity = Column(SQLEnum(AnomalySeverity), nullable=False, index=True)
    anomaly_type = Column(String(128), nullable=False)
    message = Column(Text, nullable=False)
    diagnostic_payload = Column(JSONB, nullable=True)
    detected_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    run = relationship("Run", back_populates="anomalies")
