"""
Feast Feature Store Client

Wrapper around Feast for seamless feature store integration.
Provides easy access to online/offline feature serving and materialization.
"""

import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Optional

import pandas as pd

logger = logging.getLogger(__name__)


class FeatureStoreClient:
    """
    Feast Feature Store Client

    Provides high-level interface for:
    - Feature registration and management
    - Online feature serving (low-latency)
    - Offline feature serving (batch/training)
    - Feature materialization
    - Feature monitoring
    """

    def __init__(
        self,
        repo_path: Optional[str] = None,
        online_store_uri: Optional[str] = None
    ):
        """
        Initialize Feast client

        Args:
            repo_path: Path to Feast repository
            online_store_uri: Online store connection URI (Redis, etc.)
        """
        try:
            from feast import FeatureStore
            self.feast_available = True
        except ImportError:
            logger.warning(
                "Feast not installed. Install with: pip install feast\n"
                "Feature store functionality will be limited."
            )
            self.feast_available = False
            self.store = None
            return

        # Initialize Feast store
        if repo_path:
            self.repo_path = Path(repo_path)
        else:
            # Default to mlops/feast/feature_repo
            self.repo_path = Path(__file__).parent.parent / "mlops" / "feast" / "feature_repo"

        if not self.repo_path.exists():
            logger.warning(f"Feast repository not found at {self.repo_path}")
            self.store = None
            return

        try:
            self.store = FeatureStore(repo_path=str(self.repo_path))
            logger.info(f"Feast store initialized from {self.repo_path}")
        except Exception as e:
            logger.error(f"Failed to initialize Feast store: {e}")
            self.store = None

    def get_online_features(
        self,
        features: list[str],
        entity_rows: list[dict[str, Any]],
        full_feature_names: bool = False
    ) -> pd.DataFrame:
        """
        Get features from online store (low-latency serving)

        Args:
            features: List of feature references (e.g., ["user_features:age", "user_features:country"])
            entity_rows: List of entity dictionaries (e.g., [{"user_id": 123}, {"user_id": 456}])
            full_feature_names: Whether to use full feature names in output

        Returns:
            DataFrame with features for each entity

        Example:
            >>> client = FeatureStoreClient()
            >>> features = client.get_online_features(
            ...     features=["user_features:age", "user_features:country"],
            ...     entity_rows=[{"user_id": 123}, {"user_id": 456}]
            ... )
        """
        if not self.feast_available or not self.store:
            raise RuntimeError("Feast store not available")

        try:
            feature_vector = self.store.get_online_features(
                features=features,
                entity_rows=entity_rows,
                full_feature_names=full_feature_names
            )

            return feature_vector.to_df()

        except Exception as e:
            logger.error(f"Failed to get online features: {e}")
            raise

    def get_historical_features(
        self,
        entity_df: pd.DataFrame,
        features: list[str],
        full_feature_names: bool = False
    ) -> pd.DataFrame:
        """
        Get historical features from offline store (training data)

        Args:
            entity_df: DataFrame with entity keys and timestamps
            features: List of feature references
            full_feature_names: Whether to use full feature names

        Returns:
            DataFrame with historical features joined to entity_df

        Example:
            >>> entity_df = pd.DataFrame({
            ...     "user_id": [123, 456],
            ...     "event_timestamp": [datetime(2024, 1, 1), datetime(2024, 1, 2)]
            ... })
            >>> training_df = client.get_historical_features(
            ...     entity_df=entity_df,
            ...     features=["user_features:age", "user_features:country"]
            ... )
        """
        if not self.feast_available or not self.store:
            raise RuntimeError("Feast store not available")

        try:
            training_df = self.store.get_historical_features(
                entity_df=entity_df,
                features=features,
                full_feature_names=full_feature_names
            ).to_df()

            return training_df

        except Exception as e:
            logger.error(f"Failed to get historical features: {e}")
            raise

    def materialize(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        feature_views: Optional[list[str]] = None
    ) -> dict[str, Any]:
        """
        Materialize features to online store

        Args:
            start_date: Start of materialization window (default: 1 day ago)
            end_date: End of materialization window (default: now)
            feature_views: Specific feature views to materialize (default: all)

        Returns:
            Materialization statistics

        Example:
            >>> # Materialize last 24 hours
            >>> stats = client.materialize()
            >>>
            >>> # Materialize specific time range
            >>> stats = client.materialize(
            ...     start_date=datetime(2024, 1, 1),
            ...     end_date=datetime(2024, 1, 31)
            ... )
        """
        if not self.feast_available or not self.store:
            raise RuntimeError("Feast store not available")

        # Default time range: last 24 hours
        if end_date is None:
            end_date = datetime.utcnow()
        if start_date is None:
            start_date = end_date - timedelta(days=1)

        try:
            logger.info(f"Materializing features from {start_date} to {end_date}")

            if feature_views:
                # Materialize specific feature views
                for fv_name in feature_views:
                    self.store.materialize(
                        start_date=start_date,
                        end_date=end_date,
                        feature_views=[fv_name]
                    )
            else:
                # Materialize all feature views
                self.store.materialize(
                    start_date=start_date,
                    end_date=end_date
                )

            logger.info("Materialization completed successfully")

            return {
                "status": "success",
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
                "feature_views": feature_views or "all"
            }

        except Exception as e:
            logger.error(f"Materialization failed: {e}")
            return {
                "status": "failed",
                "error": str(e)
            }

    def materialize_incremental(
        self,
        end_date: Optional[datetime] = None,
        feature_views: Optional[list[str]] = None
    ) -> dict[str, Any]:
        """
        Incrementally materialize features (from last materialization)

        Args:
            end_date: End of materialization window (default: now)
            feature_views: Specific feature views to materialize

        Returns:
            Materialization statistics
        """
        if not self.feast_available or not self.store:
            raise RuntimeError("Feast store not available")

        if end_date is None:
            end_date = datetime.utcnow()

        try:
            logger.info(f"Incremental materialization to {end_date}")

            if feature_views:
                for fv_name in feature_views:
                    self.store.materialize_incremental(
                        end_date=end_date,
                        feature_views=[fv_name]
                    )
            else:
                self.store.materialize_incremental(end_date=end_date)

            logger.info("Incremental materialization completed")

            return {
                "status": "success",
                "end_date": end_date.isoformat(),
                "feature_views": feature_views or "all"
            }

        except Exception as e:
            logger.error(f"Incremental materialization failed: {e}")
            return {
                "status": "failed",
                "error": str(e)
            }

    def list_feature_views(self) -> list[str]:
        """List all registered feature views"""
        if not self.feast_available or not self.store:
            return []

        try:
            feature_views = self.store.list_feature_views()
            return [fv.name for fv in feature_views]
        except Exception as e:
            logger.error(f"Failed to list feature views: {e}")
            return []

    def list_entities(self) -> list[str]:
        """List all registered entities"""
        if not self.feast_available or not self.store:
            return []

        try:
            entities = self.store.list_entities()
            return [entity.name for entity in entities]
        except Exception as e:
            logger.error(f"Failed to list entities: {e}")
            return []

    def get_feature_view(self, name: str) -> Optional[Any]:
        """Get feature view by name"""
        if not self.feast_available or not self.store:
            return None

        try:
            return self.store.get_feature_view(name)
        except Exception as e:
            logger.error(f"Failed to get feature view {name}: {e}")
            return None

    def apply(self):
        """
        Apply feature definitions to registry

        This registers all feature views, entities, and data sources
        defined in the repository.
        """
        if not self.feast_available or not self.store:
            raise RuntimeError("Feast store not available")

        try:
            logger.info("Applying feature definitions...")
            self.store.apply(objects=None)  # Apply all objects in repo
            logger.info("Feature definitions applied successfully")
        except Exception as e:
            logger.error(f"Failed to apply feature definitions: {e}")
            raise

    def get_online_feature_latency(
        self,
        features: list[str],
        entity_rows: list[dict[str, Any]],
        num_samples: int = 100
    ) -> dict[str, float]:
        """
        Measure online feature serving latency

        Args:
            features: Feature references to test
            entity_rows: Sample entity rows
            num_samples: Number of samples to measure

        Returns:
            Latency statistics (P50, P95, P99)
        """
        if not self.feast_available or not self.store:
            raise RuntimeError("Feast store not available")

        import time

        latencies = []

        for _ in range(num_samples):
            start = time.time()
            try:
                self.get_online_features(features=features, entity_rows=entity_rows)
                latency = (time.time() - start) * 1000  # Convert to ms
                latencies.append(latency)
            except Exception as e:
                logger.warning(f"Latency test failed: {e}")

        if not latencies:
            return {}

        latencies.sort()

        return {
            "p50_ms": latencies[int(len(latencies) * 0.5)],
            "p95_ms": latencies[int(len(latencies) * 0.95)],
            "p99_ms": latencies[int(len(latencies) * 0.99)],
            "mean_ms": sum(latencies) / len(latencies),
            "min_ms": min(latencies),
            "max_ms": max(latencies),
            "samples": num_samples
        }

    def check_health(self) -> dict[str, Any]:
        """
        Health check for feature store

        Returns:
            Health status and diagnostics
        """
        health = {
            "feast_installed": self.feast_available,
            "store_initialized": self.store is not None,
            "repo_path": str(self.repo_path) if hasattr(self, 'repo_path') else None,
            "repo_exists": self.repo_path.exists() if hasattr(self, 'repo_path') else False
        }

        if self.feast_available and self.store:
            try:
                health["feature_views"] = len(self.list_feature_views())
                health["entities"] = len(self.list_entities())
                health["status"] = "healthy"
            except Exception as e:
                health["status"] = "unhealthy"
                health["error"] = str(e)
        else:
            health["status"] = "unavailable"

        return health
