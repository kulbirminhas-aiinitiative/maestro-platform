"""
Feast Integration Tests

Tests for Feast feature store client and materialization.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta
import pandas as pd

from features import FeatureStoreClient, MaterializationJob, MaterializationScheduler


class TestFeatureStoreClient:
    """Test FeatureStoreClient"""

    def test_init_no_feast(self):
        """Test initialization when Feast is not installed"""
        with patch('features.feast_client.FeatureStore', side_effect=ImportError):
            client = FeatureStoreClient()
            assert client.feast_available is False
            assert client.store is None

    def test_init_with_repo_path(self, tmp_path):
        """Test initialization with custom repo path"""
        repo_path = tmp_path / "feature_repo"
        repo_path.mkdir()

        # Mock Feast to avoid actual initialization
        with patch('features.feast_client.FeatureStore'):
            client = FeatureStoreClient(repo_path=str(repo_path))
            assert client.repo_path == repo_path

    @patch('features.feast_client.FeatureStore')
    def test_get_online_features(self, mock_feast_store):
        """Test online feature retrieval"""
        # Mock Feast store
        mock_store = MagicMock()
        mock_feast_store.return_value = mock_store

        # Mock feature vector response
        mock_vector = MagicMock()
        mock_df = pd.DataFrame({
            "user_id": [123, 456],
            "age": [25, 30],
            "country": ["US", "UK"]
        })
        mock_vector.to_df.return_value = mock_df
        mock_store.get_online_features.return_value = mock_vector

        client = FeatureStoreClient()
        client.store = mock_store

        # Get features
        features = ["user_features:age", "user_features:country"]
        entity_rows = [{"user_id": 123}, {"user_id": 456}]

        result_df = client.get_online_features(features, entity_rows)

        assert isinstance(result_df, pd.DataFrame)
        assert len(result_df) == 2
        assert "user_id" in result_df.columns

    @patch('features.feast_client.FeatureStore')
    def test_get_historical_features(self, mock_feast_store):
        """Test historical feature retrieval"""
        mock_store = MagicMock()
        mock_feast_store.return_value = mock_store

        # Mock historical features
        mock_df = pd.DataFrame({
            "user_id": [123],
            "event_timestamp": [datetime.utcnow()],
            "age": [25],
            "country": ["US"]
        })
        mock_result = MagicMock()
        mock_result.to_df.return_value = mock_df
        mock_store.get_historical_features.return_value = mock_result

        client = FeatureStoreClient()
        client.store = mock_store

        entity_df = pd.DataFrame({
            "user_id": [123],
            "event_timestamp": [datetime.utcnow()]
        })

        result_df = client.get_historical_features(
            entity_df=entity_df,
            features=["user_features:age"]
        )

        assert isinstance(result_df, pd.DataFrame)
        assert "age" in result_df.columns

    @patch('features.feast_client.FeatureStore')
    def test_materialize(self, mock_feast_store):
        """Test feature materialization"""
        mock_store = MagicMock()
        mock_feast_store.return_value = mock_store

        client = FeatureStoreClient()
        client.store = mock_store

        # Materialize features
        start_date = datetime.utcnow() - timedelta(days=1)
        end_date = datetime.utcnow()

        result = client.materialize(start_date=start_date, end_date=end_date)

        assert result["status"] == "success"
        assert result["start_date"] == start_date.isoformat()
        assert result["end_date"] == end_date.isoformat()
        mock_store.materialize.assert_called_once()

    @patch('features.feast_client.FeatureStore')
    def test_materialize_incremental(self, mock_feast_store):
        """Test incremental materialization"""
        mock_store = MagicMock()
        mock_feast_store.return_value = mock_store

        client = FeatureStoreClient()
        client.store = mock_store

        result = client.materialize_incremental()

        assert result["status"] == "success"
        mock_store.materialize_incremental.assert_called_once()

    @patch('features.feast_client.FeatureStore')
    def test_list_feature_views(self, mock_feast_store):
        """Test listing feature views"""
        mock_store = MagicMock()
        mock_feast_store.return_value = mock_store

        # Mock feature views
        mock_fv1 = MagicMock()
        mock_fv1.name = "user_features"
        mock_fv2 = MagicMock()
        mock_fv2.name = "model_features"

        mock_store.list_feature_views.return_value = [mock_fv1, mock_fv2]

        client = FeatureStoreClient()
        client.store = mock_store

        feature_views = client.list_feature_views()

        assert len(feature_views) == 2
        assert "user_features" in feature_views
        assert "model_features" in feature_views

    @patch('features.feast_client.FeatureStore')
    def test_list_entities(self, mock_feast_store):
        """Test listing entities"""
        mock_store = MagicMock()
        mock_feast_store.return_value = mock_store

        # Mock entities
        mock_entity1 = MagicMock()
        mock_entity1.name = "user_id"
        mock_entity2 = MagicMock()
        mock_entity2.name = "model_id"

        mock_store.list_entities.return_value = [mock_entity1, mock_entity2]

        client = FeatureStoreClient()
        client.store = mock_store

        entities = client.list_entities()

        assert len(entities) == 2
        assert "user_id" in entities
        assert "model_id" in entities

    @patch('features.feast_client.FeatureStore')
    def test_apply(self, mock_feast_store):
        """Test applying feature definitions"""
        mock_store = MagicMock()
        mock_feast_store.return_value = mock_store

        client = FeatureStoreClient()
        client.store = mock_store

        client.apply()

        mock_store.apply.assert_called_once()

    @patch('features.feast_client.FeatureStore')
    def test_check_health(self, mock_feast_store):
        """Test health check"""
        mock_store = MagicMock()
        mock_feast_store.return_value = mock_store

        # Mock feature views and entities
        mock_store.list_feature_views.return_value = [MagicMock(), MagicMock()]
        mock_store.list_entities.return_value = [MagicMock()]

        client = FeatureStoreClient()
        client.store = mock_store

        health = client.check_health()

        assert health["feast_installed"] is True
        assert health["store_initialized"] is True
        assert health["status"] == "healthy"
        assert health["feature_views"] == 2
        assert health["entities"] == 1

    def test_health_check_feast_unavailable(self):
        """Test health check when Feast is unavailable"""
        with patch('features.feast_client.FeatureStore', side_effect=ImportError):
            client = FeatureStoreClient()
            health = client.check_health()

            assert health["feast_installed"] is False
            assert health["status"] == "unavailable"


class TestMaterializationJob:
    """Test MaterializationJob"""

    @patch('features.materialization.FeatureStoreClient')
    def test_job_initialization(self, mock_client_class):
        """Test job initialization"""
        job = MaterializationJob()

        assert job.feature_views is None
        assert job.stats["total_runs"] == 0
        assert job.stats["successful_runs"] == 0
        assert job.stats["failed_runs"] == 0

    @patch('features.materialization.FeatureStoreClient')
    def test_run_incremental_success(self, mock_client_class):
        """Test successful incremental run"""
        mock_client = MagicMock()
        mock_client.materialize_incremental.return_value = {"status": "success"}

        job = MaterializationJob(client=mock_client)
        result = job.run_incremental()

        assert result["status"] == "success"
        assert "duration_seconds" in result
        assert job.stats["total_runs"] == 1
        assert job.stats["successful_runs"] == 1
        assert job.stats["failed_runs"] == 0

    @patch('features.materialization.FeatureStoreClient')
    def test_run_incremental_failure(self, mock_client_class):
        """Test failed incremental run"""
        mock_client = MagicMock()
        mock_client.materialize_incremental.return_value = {
            "status": "failed",
            "error": "Test error"
        }

        job = MaterializationJob(client=mock_client)
        result = job.run_incremental()

        assert result["status"] == "failed"
        assert job.stats["total_runs"] == 1
        assert job.stats["successful_runs"] == 0
        assert job.stats["failed_runs"] == 1
        assert job.stats["last_error"] == "Test error"

    @patch('features.materialization.FeatureStoreClient')
    def test_run_full_success(self, mock_client_class):
        """Test successful full run"""
        mock_client = MagicMock()
        mock_client.materialize.return_value = {"status": "success"}

        job = MaterializationJob(client=mock_client)
        result = job.run_full()

        assert result["status"] == "success"
        assert job.stats["successful_runs"] == 1

    @patch('features.materialization.FeatureStoreClient')
    def test_get_stats(self, mock_client_class):
        """Test getting job statistics"""
        job = MaterializationJob()

        stats = job.get_stats()

        assert "total_runs" in stats
        assert "successful_runs" in stats
        assert "failed_runs" in stats
        assert "last_run_time" in stats


class TestMaterializationScheduler:
    """Test MaterializationScheduler"""

    @patch('features.materialization.FeatureStoreClient')
    def test_scheduler_initialization(self, mock_client_class):
        """Test scheduler initialization"""
        scheduler = MaterializationScheduler(interval_minutes=30)

        assert scheduler.interval_minutes == 30
        assert len(scheduler.jobs) == 0
        assert scheduler.running is False

    @patch('features.materialization.FeatureStoreClient')
    def test_register_job(self, mock_client_class):
        """Test job registration"""
        scheduler = MaterializationScheduler()

        scheduler.register_job("test_job", feature_views=["user_features"])

        assert "test_job" in scheduler.jobs
        assert scheduler.jobs["test_job"].feature_views == ["user_features"]

    @patch('features.materialization.FeatureStoreClient')
    def test_run_once(self, mock_client_class):
        """Test running all jobs once"""
        mock_client = MagicMock()
        mock_client.materialize_incremental.return_value = {"status": "success"}

        scheduler = MaterializationScheduler(client=mock_client)
        scheduler.register_job("job1")
        scheduler.register_job("job2")

        results = scheduler.run_once()

        assert len(results) == 2
        assert "job1" in results
        assert "job2" in results

    @patch('features.materialization.FeatureStoreClient')
    def test_get_all_stats(self, mock_client_class):
        """Test getting statistics for all jobs"""
        scheduler = MaterializationScheduler()
        scheduler.register_job("job1")
        scheduler.register_job("job2")

        stats = scheduler.get_all_stats()

        assert len(stats) == 2
        assert "job1" in stats
        assert "job2" in stats

    @patch('features.materialization.FeatureStoreClient')
    def test_stop_scheduler(self, mock_client_class):
        """Test stopping scheduler"""
        scheduler = MaterializationScheduler()
        scheduler.running = True

        scheduler.stop()

        assert scheduler.running is False


class TestFeatureDefinitions:
    """Test feature definition utilities"""

    def test_generate_sample_data(self):
        """Test sample data generation"""
        from features.feature_definitions import generate_sample_data

        data = generate_sample_data()

        assert "user_features" in data
        assert "model_performance_features" in data
        assert "project_features" in data

        # Check user features
        user_df = data["user_features"]
        assert len(user_df) == 100
        assert "user_id" in user_df.columns
        assert "age" in user_df.columns
        assert "country" in user_df.columns

        # Check model features
        model_df = data["model_performance_features"]
        assert len(model_df) == 200
        assert "model_id" in model_df.columns
        assert "accuracy" in model_df.columns

        # Check project features
        project_df = data["project_features"]
        assert len(project_df) == 50
        assert "project_id" in project_df.columns
        assert "team_size" in project_df.columns

    def test_save_sample_data(self, tmp_path):
        """Test saving sample data to files"""
        from features.feature_definitions import save_sample_data

        output_dir = tmp_path / "data"
        save_sample_data(output_dir=str(output_dir))

        # Check files exist
        assert (output_dir / "user_features.parquet").exists()
        assert (output_dir / "model_performance_features.parquet").exists()
        assert (output_dir / "project_features.parquet").exists()

        # Check file contents
        user_df = pd.read_parquet(output_dir / "user_features.parquet")
        assert len(user_df) == 100


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
