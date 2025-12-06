"""
BDV Database Models (MD-2097)

SQLAlchemy models for storing BDV test execution results in PostgreSQL.

Tables:
- bdv_executions: Test execution metadata
- bdv_scenario_results: Individual scenario results
- bdv_contract_fulfillment: Contract fulfillment tracking
- bdv_flake_history: Flake rate tracking over time
"""

from datetime import datetime
from decimal import Decimal
from typing import Optional, List
from sqlalchemy import (
    Column, Integer, String, Boolean, Float, Text, DateTime,
    ForeignKey, Index, Numeric, create_engine
)
from sqlalchemy.orm import relationship, declarative_base, Session
from sqlalchemy.ext.declarative import declared_attr

Base = declarative_base()


class BDVExecution(Base):
    """
    Records a BDV test execution session.

    Stores overall execution metadata and aggregated results.
    """
    __tablename__ = 'bdv_executions'

    id = Column(Integer, primary_key=True, autoincrement=True)
    execution_id = Column(String(64), unique=True, nullable=False, index=True)
    iteration_id = Column(String(64), nullable=False, index=True)
    started_at = Column(DateTime, nullable=False)
    completed_at = Column(DateTime, nullable=True)
    total_scenarios = Column(Integer, nullable=False, default=0)
    passed = Column(Integer, default=0)
    failed = Column(Integer, default=0)
    skipped = Column(Integer, default=0)
    duration_seconds = Column(Float, default=0.0)
    flake_rate = Column(Numeric(5, 4), nullable=True)
    execution_mode = Column(String(20), default='sequential')  # sequential, parallel
    worker_count = Column(Integer, default=1)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    scenario_results = relationship("BDVScenarioResult", back_populates="execution", cascade="all, delete-orphan")
    contract_fulfillments = relationship("BDVContractFulfillment", back_populates="execution", cascade="all, delete-orphan")

    # Indexes
    __table_args__ = (
        Index('ix_bdv_executions_iteration_started', 'iteration_id', 'started_at'),
    )

    @property
    def pass_rate(self) -> float:
        """Calculate pass rate"""
        if self.total_scenarios == 0:
            return 0.0
        return self.passed / self.total_scenarios

    @property
    def is_successful(self) -> bool:
        """Check if execution was successful (no failures)"""
        return self.failed == 0

    def to_dict(self) -> dict:
        """Convert to dictionary"""
        return {
            'id': self.id,
            'execution_id': self.execution_id,
            'iteration_id': self.iteration_id,
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'total_scenarios': self.total_scenarios,
            'passed': self.passed,
            'failed': self.failed,
            'skipped': self.skipped,
            'duration_seconds': self.duration_seconds,
            'pass_rate': self.pass_rate,
            'flake_rate': float(self.flake_rate) if self.flake_rate else None,
            'execution_mode': self.execution_mode,
            'worker_count': self.worker_count,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class BDVScenarioResult(Base):
    """
    Records individual scenario test results.

    Each row represents a single scenario execution with its outcome.
    """
    __tablename__ = 'bdv_scenario_results'

    id = Column(Integer, primary_key=True, autoincrement=True)
    execution_id = Column(String(64), ForeignKey('bdv_executions.execution_id'), nullable=False, index=True)
    feature_file = Column(String(255), nullable=False)
    scenario_name = Column(String(255), nullable=False)
    status = Column(String(20), nullable=False)  # passed, failed, skipped
    duration_ms = Column(Integer, nullable=False, default=0)
    error_message = Column(Text, nullable=True)
    contract_id = Column(String(64), nullable=True, index=True)
    contract_version = Column(String(20), nullable=True)
    run_number = Column(Integer, default=1)
    worker_id = Column(String(32), nullable=True)
    retry_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    execution = relationship("BDVExecution", back_populates="scenario_results")

    # Indexes
    __table_args__ = (
        Index('ix_bdv_scenario_feature_scenario', 'feature_file', 'scenario_name'),
        Index('ix_bdv_scenario_status', 'status'),
    )

    @property
    def duration_seconds(self) -> float:
        """Get duration in seconds"""
        return self.duration_ms / 1000.0

    def to_dict(self) -> dict:
        """Convert to dictionary"""
        return {
            'id': self.id,
            'execution_id': self.execution_id,
            'feature_file': self.feature_file,
            'scenario_name': self.scenario_name,
            'status': self.status,
            'duration_ms': self.duration_ms,
            'duration_seconds': self.duration_seconds,
            'error_message': self.error_message,
            'contract_id': self.contract_id,
            'contract_version': self.contract_version,
            'run_number': self.run_number,
            'worker_id': self.worker_id,
            'retry_count': self.retry_count,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class BDVContractFulfillment(Base):
    """
    Tracks contract fulfillment status per execution.

    Records whether contracts were fulfilled based on test results.
    """
    __tablename__ = 'bdv_contract_fulfillment'

    id = Column(Integer, primary_key=True, autoincrement=True)
    execution_id = Column(String(64), ForeignKey('bdv_executions.execution_id'), nullable=False, index=True)
    contract_id = Column(String(64), nullable=False, index=True)
    contract_name = Column(String(128), nullable=True)
    contract_version = Column(String(20), nullable=True)
    is_fulfilled = Column(Boolean, nullable=False, default=False)
    pass_rate = Column(Numeric(5, 4), nullable=True)
    scenarios_passed = Column(Integer, default=0)
    scenarios_failed = Column(Integer, default=0)
    scenarios_skipped = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    execution = relationship("BDVExecution", back_populates="contract_fulfillments")

    # Indexes
    __table_args__ = (
        Index('ix_bdv_contract_execution_contract', 'execution_id', 'contract_id'),
    )

    @property
    def total_scenarios(self) -> int:
        """Total scenarios for this contract"""
        return (self.scenarios_passed or 0) + (self.scenarios_failed or 0) + (self.scenarios_skipped or 0)

    def to_dict(self) -> dict:
        """Convert to dictionary"""
        return {
            'id': self.id,
            'execution_id': self.execution_id,
            'contract_id': self.contract_id,
            'contract_name': self.contract_name,
            'contract_version': self.contract_version,
            'is_fulfilled': self.is_fulfilled,
            'pass_rate': float(self.pass_rate) if self.pass_rate else None,
            'scenarios_passed': self.scenarios_passed,
            'scenarios_failed': self.scenarios_failed,
            'scenarios_skipped': self.scenarios_skipped,
            'total_scenarios': self.total_scenarios,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class BDVFlakeHistory(Base):
    """
    Tracks flake rate history for scenarios over time.

    Used for identifying persistently flaky tests and trending.
    """
    __tablename__ = 'bdv_flake_history'

    id = Column(Integer, primary_key=True, autoincrement=True)
    scenario_id = Column(String(255), nullable=False, index=True)
    scenario_name = Column(String(255), nullable=False)
    feature_file = Column(String(255), nullable=False)
    flake_rate = Column(Numeric(5, 4), nullable=False)
    run_count = Column(Integer, nullable=False, default=3)
    passed_runs = Column(Integer, default=0)
    failed_runs = Column(Integer, default=0)
    is_quarantined = Column(Boolean, default=False)
    quarantine_reason = Column(String(255), nullable=True)
    iteration_id = Column(String(64), nullable=True)
    last_checked_at = Column(DateTime, default=datetime.utcnow)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Indexes
    __table_args__ = (
        Index('ix_bdv_flake_scenario_quarantine', 'scenario_id', 'is_quarantined'),
        Index('ix_bdv_flake_last_checked', 'last_checked_at'),
    )

    def to_dict(self) -> dict:
        """Convert to dictionary"""
        return {
            'id': self.id,
            'scenario_id': self.scenario_id,
            'scenario_name': self.scenario_name,
            'feature_file': self.feature_file,
            'flake_rate': float(self.flake_rate),
            'run_count': self.run_count,
            'passed_runs': self.passed_runs,
            'failed_runs': self.failed_runs,
            'is_quarantined': self.is_quarantined,
            'quarantine_reason': self.quarantine_reason,
            'iteration_id': self.iteration_id,
            'last_checked_at': self.last_checked_at.isoformat() if self.last_checked_at else None,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


# SQL schema for reference (can be used with raw SQL migrations)
CREATE_TABLES_SQL = """
-- BDV Executions
CREATE TABLE IF NOT EXISTS bdv_executions (
    id SERIAL PRIMARY KEY,
    execution_id VARCHAR(64) UNIQUE NOT NULL,
    iteration_id VARCHAR(64) NOT NULL,
    started_at TIMESTAMP NOT NULL,
    completed_at TIMESTAMP,
    total_scenarios INT NOT NULL DEFAULT 0,
    passed INT DEFAULT 0,
    failed INT DEFAULT 0,
    skipped INT DEFAULT 0,
    duration_seconds FLOAT DEFAULT 0.0,
    flake_rate DECIMAL(5,4),
    execution_mode VARCHAR(20) DEFAULT 'sequential',
    worker_count INT DEFAULT 1,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_bdv_executions_iteration_started
ON bdv_executions(iteration_id, started_at);

-- BDV Scenario Results
CREATE TABLE IF NOT EXISTS bdv_scenario_results (
    id SERIAL PRIMARY KEY,
    execution_id VARCHAR(64) REFERENCES bdv_executions(execution_id),
    feature_file VARCHAR(255) NOT NULL,
    scenario_name VARCHAR(255) NOT NULL,
    status VARCHAR(20) NOT NULL,
    duration_ms INT NOT NULL DEFAULT 0,
    error_message TEXT,
    contract_id VARCHAR(64),
    contract_version VARCHAR(20),
    run_number INT DEFAULT 1,
    worker_id VARCHAR(32),
    retry_count INT DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_bdv_scenario_feature_scenario
ON bdv_scenario_results(feature_file, scenario_name);
CREATE INDEX IF NOT EXISTS ix_bdv_scenario_status
ON bdv_scenario_results(status);

-- BDV Contract Fulfillment
CREATE TABLE IF NOT EXISTS bdv_contract_fulfillment (
    id SERIAL PRIMARY KEY,
    execution_id VARCHAR(64) REFERENCES bdv_executions(execution_id),
    contract_id VARCHAR(64) NOT NULL,
    contract_name VARCHAR(128),
    contract_version VARCHAR(20),
    is_fulfilled BOOLEAN NOT NULL DEFAULT FALSE,
    pass_rate DECIMAL(5,4),
    scenarios_passed INT DEFAULT 0,
    scenarios_failed INT DEFAULT 0,
    scenarios_skipped INT DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_bdv_contract_execution_contract
ON bdv_contract_fulfillment(execution_id, contract_id);

-- BDV Flake History
CREATE TABLE IF NOT EXISTS bdv_flake_history (
    id SERIAL PRIMARY KEY,
    scenario_id VARCHAR(255) NOT NULL,
    scenario_name VARCHAR(255) NOT NULL,
    feature_file VARCHAR(255) NOT NULL,
    flake_rate DECIMAL(5,4) NOT NULL,
    run_count INT NOT NULL DEFAULT 3,
    passed_runs INT DEFAULT 0,
    failed_runs INT DEFAULT 0,
    is_quarantined BOOLEAN DEFAULT FALSE,
    quarantine_reason VARCHAR(255),
    iteration_id VARCHAR(64),
    last_checked_at TIMESTAMP DEFAULT NOW(),
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_bdv_flake_scenario_quarantine
ON bdv_flake_history(scenario_id, is_quarantined);
CREATE INDEX IF NOT EXISTS ix_bdv_flake_last_checked
ON bdv_flake_history(last_checked_at);
"""
