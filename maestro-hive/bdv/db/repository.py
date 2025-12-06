"""
BDV Repository (MD-2097)

Repository pattern implementation for BDV database operations.
Provides clean interface for saving and retrieving test results.
"""

import logging
import os
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Dict, List, Optional, Any
from contextlib import contextmanager

from sqlalchemy import create_engine, desc, func
from sqlalchemy.orm import sessionmaker, Session

from .models import (
    Base,
    BDVExecution,
    BDVScenarioResult,
    BDVContractFulfillment,
    BDVFlakeHistory
)

logger = logging.getLogger(__name__)


class BDVRepository:
    """
    Repository for BDV database operations.

    Provides methods to save and retrieve:
    - Test executions
    - Scenario results
    - Contract fulfillment records
    - Flake history
    """

    def __init__(self, database_url: Optional[str] = None):
        """
        Initialize repository.

        Args:
            database_url: PostgreSQL connection URL.
                         Defaults to DATABASE_URL env var or SQLite for testing.
        """
        self.database_url = database_url or os.getenv(
            'DATABASE_URL',
            'sqlite:///bdv_results.db'
        )

        self.engine = create_engine(
            self.database_url,
            echo=False,
            pool_pre_ping=True
        )
        self.SessionLocal = sessionmaker(bind=self.engine)

        logger.info(f"BDVRepository initialized with {self._get_db_type()}")

    def _get_db_type(self) -> str:
        """Get database type from URL"""
        if 'postgresql' in self.database_url:
            return 'PostgreSQL'
        elif 'sqlite' in self.database_url:
            return 'SQLite'
        return 'Unknown'

    def create_tables(self):
        """Create all tables in the database"""
        Base.metadata.create_all(self.engine)
        logger.info("Database tables created")

    def drop_tables(self):
        """Drop all tables (use with caution!)"""
        Base.metadata.drop_all(self.engine)
        logger.warning("Database tables dropped")

    @contextmanager
    def session_scope(self):
        """Provide a transactional scope around operations"""
        session = self.SessionLocal()
        try:
            yield session
            session.commit()
        except Exception as e:
            session.rollback()
            logger.error(f"Database error: {e}")
            raise
        finally:
            session.close()

    # ============ Execution Operations ============

    def save_execution(
        self,
        execution_id: str,
        iteration_id: str,
        started_at: datetime,
        completed_at: Optional[datetime] = None,
        total_scenarios: int = 0,
        passed: int = 0,
        failed: int = 0,
        skipped: int = 0,
        duration_seconds: float = 0.0,
        flake_rate: Optional[float] = None,
        execution_mode: str = 'sequential',
        worker_count: int = 1
    ) -> Dict[str, Any]:
        """
        Save a BDV execution record.

        Args:
            execution_id: Unique execution identifier
            iteration_id: Iteration identifier
            started_at: Execution start time
            completed_at: Execution completion time
            total_scenarios: Total number of scenarios
            passed: Number of passed scenarios
            failed: Number of failed scenarios
            skipped: Number of skipped scenarios
            duration_seconds: Total execution duration
            flake_rate: Calculated flake rate
            execution_mode: Execution mode (sequential/parallel)
            worker_count: Number of workers used

        Returns:
            Dictionary with saved execution data
        """
        with self.session_scope() as session:
            execution = BDVExecution(
                execution_id=execution_id,
                iteration_id=iteration_id,
                started_at=started_at,
                completed_at=completed_at,
                total_scenarios=total_scenarios,
                passed=passed,
                failed=failed,
                skipped=skipped,
                duration_seconds=duration_seconds,
                flake_rate=Decimal(str(flake_rate)) if flake_rate is not None else None,
                execution_mode=execution_mode,
                worker_count=worker_count
            )
            session.add(execution)
            session.flush()

            result = execution.to_dict()
            logger.debug(f"Saved execution: {execution_id}")
            return result

    def get_execution(self, execution_id: str) -> Optional[Dict[str, Any]]:
        """Get execution by ID"""
        with self.session_scope() as session:
            execution = session.query(BDVExecution).filter_by(
                execution_id=execution_id
            ).first()
            return execution.to_dict() if execution else None

    def get_execution_history(
        self,
        days: int = 30,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Get execution history.

        Args:
            days: Number of days to look back
            limit: Maximum records to return

        Returns:
            List of execution dictionaries
        """
        cutoff = datetime.utcnow() - timedelta(days=days)

        with self.session_scope() as session:
            executions = session.query(BDVExecution).filter(
                BDVExecution.created_at >= cutoff
            ).order_by(
                desc(BDVExecution.created_at)
            ).limit(limit).all()

            return [e.to_dict() for e in executions]

    def update_execution(
        self,
        execution_id: str,
        **updates
    ) -> Optional[BDVExecution]:
        """Update an execution record"""
        with self.session_scope() as session:
            execution = session.query(BDVExecution).filter_by(
                execution_id=execution_id
            ).first()

            if execution:
                for key, value in updates.items():
                    if hasattr(execution, key):
                        if key == 'flake_rate' and value is not None:
                            value = Decimal(str(value))
                        setattr(execution, key, value)
                return execution

            return None

    # ============ Scenario Result Operations ============

    def save_scenario_result(
        self,
        execution_id: str,
        feature_file: str,
        scenario_name: str,
        status: str,
        duration_ms: int = 0,
        error_message: Optional[str] = None,
        contract_id: Optional[str] = None,
        contract_version: Optional[str] = None,
        run_number: int = 1,
        worker_id: Optional[str] = None,
        retry_count: int = 0
    ) -> Dict[str, Any]:
        """
        Save a scenario result.

        Args:
            execution_id: Parent execution ID
            feature_file: Feature file path
            scenario_name: Scenario name
            status: Test status (passed/failed/skipped)
            duration_ms: Duration in milliseconds
            error_message: Error message if failed
            contract_id: Associated contract ID
            contract_version: Contract version
            run_number: Run number (for flake detection)
            worker_id: Worker identifier
            retry_count: Number of retries

        Returns:
            Dictionary with saved scenario result data
        """
        with self.session_scope() as session:
            result = BDVScenarioResult(
                execution_id=execution_id,
                feature_file=feature_file,
                scenario_name=scenario_name,
                status=status,
                duration_ms=duration_ms,
                error_message=error_message,
                contract_id=contract_id,
                contract_version=contract_version,
                run_number=run_number,
                worker_id=worker_id,
                retry_count=retry_count
            )
            session.add(result)
            session.flush()

            result_dict = result.to_dict()
            logger.debug(f"Saved scenario result: {scenario_name}")
            return result_dict

    def save_scenario_results_batch(
        self,
        execution_id: str,
        results: List[Dict[str, Any]]
    ) -> int:
        """
        Save multiple scenario results in batch.

        Args:
            execution_id: Parent execution ID
            results: List of result dictionaries

        Returns:
            Number of records saved
        """
        with self.session_scope() as session:
            scenario_results = [
                BDVScenarioResult(
                    execution_id=execution_id,
                    feature_file=r.get('feature_file', ''),
                    scenario_name=r.get('scenario_name', ''),
                    status=r.get('status', 'unknown'),
                    duration_ms=int(r.get('duration', 0) * 1000),
                    error_message=r.get('error_message'),
                    contract_id=r.get('contract_id'),
                    contract_version=r.get('contract_version'),
                    run_number=r.get('run_number', 1),
                    worker_id=r.get('worker_id'),
                    retry_count=r.get('retry_count', 0)
                )
                for r in results
            ]

            session.bulk_save_objects(scenario_results)
            return len(scenario_results)

    def get_scenario_results(
        self,
        execution_id: str
    ) -> List[Dict[str, Any]]:
        """Get all scenario results for an execution"""
        with self.session_scope() as session:
            results = session.query(BDVScenarioResult).filter_by(
                execution_id=execution_id
            ).all()

            return [r.to_dict() for r in results]

    def get_scenario_history(
        self,
        feature_file: str,
        scenario_name: str,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Get historical results for a specific scenario"""
        with self.session_scope() as session:
            results = session.query(BDVScenarioResult).filter_by(
                feature_file=feature_file,
                scenario_name=scenario_name
            ).order_by(
                desc(BDVScenarioResult.created_at)
            ).limit(limit).all()

            return [r.to_dict() for r in results]

    # ============ Contract Fulfillment Operations ============

    def save_contract_fulfillment(
        self,
        execution_id: str,
        contract_id: str,
        is_fulfilled: bool,
        contract_name: Optional[str] = None,
        contract_version: Optional[str] = None,
        pass_rate: Optional[float] = None,
        scenarios_passed: int = 0,
        scenarios_failed: int = 0,
        scenarios_skipped: int = 0
    ) -> Dict[str, Any]:
        """
        Save contract fulfillment record.

        Args:
            execution_id: Parent execution ID
            contract_id: Contract identifier
            is_fulfilled: Whether contract is fulfilled
            contract_name: Contract name
            contract_version: Contract version
            pass_rate: Pass rate for contract scenarios
            scenarios_passed: Number of passed scenarios
            scenarios_failed: Number of failed scenarios
            scenarios_skipped: Number of skipped scenarios

        Returns:
            Dictionary with saved contract fulfillment data
        """
        with self.session_scope() as session:
            fulfillment = BDVContractFulfillment(
                execution_id=execution_id,
                contract_id=contract_id,
                contract_name=contract_name,
                contract_version=contract_version,
                is_fulfilled=is_fulfilled,
                pass_rate=Decimal(str(pass_rate)) if pass_rate is not None else None,
                scenarios_passed=scenarios_passed,
                scenarios_failed=scenarios_failed,
                scenarios_skipped=scenarios_skipped
            )
            session.add(fulfillment)
            session.flush()

            result = fulfillment.to_dict()
            logger.debug(f"Saved contract fulfillment: {contract_id}")
            return result

    def get_contract_fulfillment_history(
        self,
        contract_id: str,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Get fulfillment history for a contract"""
        with self.session_scope() as session:
            fulfillments = session.query(BDVContractFulfillment).filter_by(
                contract_id=contract_id
            ).order_by(
                desc(BDVContractFulfillment.created_at)
            ).limit(limit).all()

            return [f.to_dict() for f in fulfillments]

    # ============ Flake History Operations ============

    def save_flake_history(
        self,
        scenario_id: str,
        scenario_name: str,
        feature_file: str,
        flake_rate: float,
        run_count: int = 3,
        passed_runs: int = 0,
        failed_runs: int = 0,
        is_quarantined: bool = False,
        quarantine_reason: Optional[str] = None,
        iteration_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Save flake history record.

        Args:
            scenario_id: Scenario identifier
            scenario_name: Scenario name
            feature_file: Feature file path
            flake_rate: Calculated flake rate
            run_count: Number of runs
            passed_runs: Number of passed runs
            failed_runs: Number of failed runs
            is_quarantined: Whether scenario is quarantined
            quarantine_reason: Reason for quarantine
            iteration_id: Iteration identifier

        Returns:
            Dictionary with saved flake history data
        """
        with self.session_scope() as session:
            history = BDVFlakeHistory(
                scenario_id=scenario_id,
                scenario_name=scenario_name,
                feature_file=feature_file,
                flake_rate=Decimal(str(flake_rate)),
                run_count=run_count,
                passed_runs=passed_runs,
                failed_runs=failed_runs,
                is_quarantined=is_quarantined,
                quarantine_reason=quarantine_reason,
                iteration_id=iteration_id
            )
            session.add(history)
            session.flush()

            result = history.to_dict()
            logger.debug(f"Saved flake history: {scenario_id}")
            return result

    def get_historical_flake_rate(
        self,
        scenario_id: str,
        days: int = 30
    ) -> float:
        """
        Get average historical flake rate for a scenario.

        Args:
            scenario_id: Scenario identifier
            days: Number of days to consider

        Returns:
            Average flake rate
        """
        cutoff = datetime.utcnow() - timedelta(days=days)

        with self.session_scope() as session:
            result = session.query(
                func.avg(BDVFlakeHistory.flake_rate)
            ).filter(
                BDVFlakeHistory.scenario_id == scenario_id,
                BDVFlakeHistory.created_at >= cutoff
            ).scalar()

            return float(result) if result else 0.0

    def get_quarantined_scenarios(self) -> List[Dict[str, Any]]:
        """Get all currently quarantined scenarios"""
        with self.session_scope() as session:
            # Get latest record for each quarantined scenario
            subquery = session.query(
                BDVFlakeHistory.scenario_id,
                func.max(BDVFlakeHistory.created_at).label('max_created')
            ).filter(
                BDVFlakeHistory.is_quarantined == True
            ).group_by(
                BDVFlakeHistory.scenario_id
            ).subquery()

            results = session.query(BDVFlakeHistory).join(
                subquery,
                (BDVFlakeHistory.scenario_id == subquery.c.scenario_id) &
                (BDVFlakeHistory.created_at == subquery.c.max_created)
            ).all()

            return [r.to_dict() for r in results]

    def update_quarantine_status(
        self,
        scenario_id: str,
        is_quarantined: bool,
        reason: Optional[str] = None
    ):
        """Update quarantine status for latest flake history record"""
        with self.session_scope() as session:
            latest = session.query(BDVFlakeHistory).filter_by(
                scenario_id=scenario_id
            ).order_by(
                desc(BDVFlakeHistory.created_at)
            ).first()

            if latest:
                latest.is_quarantined = is_quarantined
                latest.quarantine_reason = reason
                latest.last_checked_at = datetime.utcnow()

    # ============ Statistics Operations ============

    def get_execution_stats(self, days: int = 7) -> Dict[str, Any]:
        """
        Get execution statistics.

        Args:
            days: Number of days to analyze

        Returns:
            Dictionary with statistics
        """
        cutoff = datetime.utcnow() - timedelta(days=days)

        with self.session_scope() as session:
            stats = session.query(
                func.count(BDVExecution.id).label('total_executions'),
                func.sum(BDVExecution.total_scenarios).label('total_scenarios'),
                func.sum(BDVExecution.passed).label('total_passed'),
                func.sum(BDVExecution.failed).label('total_failed'),
                func.avg(BDVExecution.duration_seconds).label('avg_duration')
            ).filter(
                BDVExecution.created_at >= cutoff
            ).first()

            return {
                'total_executions': stats.total_executions or 0,
                'total_scenarios': stats.total_scenarios or 0,
                'total_passed': stats.total_passed or 0,
                'total_failed': stats.total_failed or 0,
                'avg_duration_seconds': float(stats.avg_duration or 0),
                'days_analyzed': days
            }


# Global repository instance
_repository: Optional[BDVRepository] = None


def get_bdv_repository(database_url: Optional[str] = None) -> BDVRepository:
    """Get or create global BDV repository instance"""
    global _repository
    if _repository is None:
        _repository = BDVRepository(database_url)
        _repository.create_tables()
    return _repository


# Example usage
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    # Create repository (uses SQLite by default for testing)
    repo = get_bdv_repository()

    # Save an execution
    execution = repo.save_execution(
        execution_id="exec-001",
        iteration_id="iter-001",
        started_at=datetime.utcnow(),
        completed_at=datetime.utcnow(),
        total_scenarios=10,
        passed=8,
        failed=2,
        skipped=0,
        duration_seconds=45.5,
        flake_rate=0.05
    )
    print(f"Saved execution: {execution.execution_id}")

    # Save scenario results
    count = repo.save_scenario_results_batch(
        execution_id="exec-001",
        results=[
            {'feature_file': 'auth.feature', 'scenario_name': 'Login', 'status': 'passed', 'duration': 1.2},
            {'feature_file': 'auth.feature', 'scenario_name': 'Logout', 'status': 'passed', 'duration': 0.8},
        ]
    )
    print(f"Saved {count} scenario results")

    # Get stats
    stats = repo.get_execution_stats()
    print(f"Stats: {stats}")
