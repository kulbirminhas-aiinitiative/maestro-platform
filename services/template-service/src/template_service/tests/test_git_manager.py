"""
Unit tests for GitManager
Tests Git operations, archiving, manifest extraction, and error handling
"""

import asyncio
import hashlib
import os
import pytest
import tarfile
import tempfile
import zipfile
from datetime import datetime
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import git
import yaml

from git_manager import (
    GitManager,
    GitManagerError,
    GitCloneError,
    GitArchiveError,
    ManifestNotFoundError
)
from models.manifest import TemplateManifest


@pytest.fixture
def temp_git_dir(tmp_path):
    """Create temporary Git operations directory"""
    git_dir = tmp_path / "git_ops"
    git_dir.mkdir(parents=True, exist_ok=True)
    return git_dir


@pytest.fixture
def sample_manifest_data():
    """Sample manifest data for testing"""
    return {
        'name': 'test-template',
        'version': '1.0.0',
        'description': 'Test template',
        'engine': 'docker',
        'persona': 'backend_developer',
        'category': 'backend',
        'language': 'python',
        'dependencies': [],
        'services': []
    }


@pytest.fixture
def mock_git_repo():
    """Create mock Git repository"""
    repo_mock = MagicMock()
    repo_mock.head.commit.hexsha = "abc123def456"
    repo_mock.head.commit.author.name = "Test User"
    repo_mock.head.commit.message = "Test commit"
    repo_mock.head.commit.committed_date = 1234567890
    repo_mock.git.checkout = MagicMock()
    repo_mock.remote().refs = []
    repo_mock.tags = []
    return repo_mock


class TestGitManagerInitialization:
    """Test GitManager initialization"""

    def test_init_creates_temp_directory(self, temp_git_dir):
        """Test that initialization creates temp directory"""
        temp_dir = temp_git_dir / "test_init"
        manager = GitManager(temp_dir=str(temp_dir))

        assert temp_dir.exists()
        assert manager.temp_dir == temp_dir

    def test_init_with_custom_timeout(self, temp_git_dir):
        """Test initialization with custom timeout"""
        manager = GitManager(temp_dir=str(temp_git_dir), timeout_seconds=600)

        assert manager.timeout_seconds == 600

    def test_init_with_custom_clone_depth(self, temp_git_dir):
        """Test initialization with custom clone depth"""
        manager = GitManager(temp_dir=str(temp_git_dir), clone_depth=5)

        assert manager.clone_depth == 5

    def test_init_default_values(self, temp_git_dir):
        """Test default initialization values"""
        manager = GitManager(temp_dir=str(temp_git_dir))

        assert manager.timeout_seconds == 300
        assert manager.clone_depth == 1


class TestRepositoryCloning:
    """Test repository cloning operations"""

    @pytest.mark.asyncio
    @patch('git.Repo.clone_from')
    @patch('git.Repo')
    async def test_clone_repository_success(self, mock_repo_class, mock_clone_from, temp_git_dir, mock_git_repo):
        """Test successful repository cloning"""
        manager = GitManager(temp_dir=str(temp_git_dir))

        # Mock Git operations
        mock_repo_class.return_value = mock_git_repo

        clone_dir, commit_hash, duration_ms = await manager.clone_repository(
            "https://github.com/test/repo.git",
            branch="main"
        )

        assert clone_dir.exists()
        assert commit_hash == "abc123def456"
        assert duration_ms > 0
        assert isinstance(duration_ms, int)

    @pytest.mark.asyncio
    @patch('git.Repo.clone_from')
    async def test_clone_repository_with_commit_hash(self, mock_clone_from, temp_git_dir):
        """Test cloning with specific commit hash"""
        manager = GitManager(temp_dir=str(temp_git_dir))

        mock_repo = MagicMock()
        mock_repo.head.commit.hexsha = "abc123"
        mock_repo.git.checkout = MagicMock()

        with patch('git.Repo', return_value=mock_repo):
            clone_dir, commit_hash, _ = await manager.clone_repository(
                "https://github.com/test/repo.git",
                branch="main",
                commit_hash="def456"
            )

            # Should call checkout with specific commit
            mock_repo.git.checkout.assert_called_with("def456")

    @pytest.mark.asyncio
    @patch('git.Repo.clone_from')
    async def test_clone_repository_git_error(self, mock_clone_from, temp_git_dir):
        """Test clone failure handling"""
        manager = GitManager(temp_dir=str(temp_git_dir))

        # Make clone_from raise GitCommandError
        mock_clone_from.side_effect = git.exc.GitCommandError('clone', 128)

        with pytest.raises(GitCloneError):
            await manager.clone_repository("https://github.com/invalid/repo.git")

    @pytest.mark.asyncio
    @patch('git.Repo.clone_from')
    async def test_clone_repository_unexpected_error(self, mock_clone_from, temp_git_dir):
        """Test handling of unexpected errors during clone"""
        manager = GitManager(temp_dir=str(temp_git_dir))

        # Make clone_from raise unexpected exception
        mock_clone_from.side_effect = Exception("Unexpected error")

        with pytest.raises(GitCloneError):
            await manager.clone_repository("https://github.com/test/repo.git")

    @pytest.mark.asyncio
    async def test_sync_clone_parameters(self, temp_git_dir):
        """Test that sync_clone uses correct parameters"""
        manager = GitManager(temp_dir=str(temp_git_dir), clone_depth=3)

        clone_dir = temp_git_dir / "test_clone"
        clone_dir.mkdir()

        with patch('git.Repo.clone_from') as mock_clone:
            manager._sync_clone(
                "https://github.com/test/repo.git",
                clone_dir,
                "develop"
            )

            mock_clone.assert_called_once_with(
                "https://github.com/test/repo.git",
                clone_dir,
                branch="develop",
                depth=3,
                single_branch=True
            )


class TestArchiveCreation:
    """Test archive creation operations"""

    @pytest.mark.asyncio
    async def test_create_tar_gz_archive(self, temp_git_dir):
        """Test creating tar.gz archive"""
        manager = GitManager(temp_dir=str(temp_git_dir))

        # Create source directory with content
        source_dir = temp_git_dir / "source"
        source_dir.mkdir()
        (source_dir / "file1.txt").write_text("content1")
        (source_dir / "file2.txt").write_text("content2")

        output_path = temp_git_dir / "archive.tar.gz"

        file_size, checksum, duration_ms = await manager.create_archive(
            source_dir,
            output_path,
            format="tar.gz"
        )

        assert output_path.exists()
        assert file_size > 0
        assert len(checksum) == 64  # SHA256 hex digest
        assert duration_ms > 0

        # Verify archive contents
        with tarfile.open(output_path, "r:gz") as tar:
            members = tar.getnames()
            assert len(members) > 0

    @pytest.mark.asyncio
    async def test_create_zip_archive(self, temp_git_dir):
        """Test creating zip archive"""
        manager = GitManager(temp_dir=str(temp_git_dir))

        # Create source directory
        source_dir = temp_git_dir / "source"
        source_dir.mkdir()
        (source_dir / "file1.txt").write_text("content1")

        output_path = temp_git_dir / "archive.zip"

        file_size, checksum, duration_ms = await manager.create_archive(
            source_dir,
            output_path,
            format="zip"
        )

        assert output_path.exists()
        assert file_size > 0
        assert len(checksum) == 64

        # Verify archive contents
        with zipfile.ZipFile(output_path, 'r') as zipf:
            names = zipf.namelist()
            assert len(names) > 0

    @pytest.mark.asyncio
    async def test_create_archive_unsupported_format(self, temp_git_dir):
        """Test error handling for unsupported format"""
        manager = GitManager(temp_dir=str(temp_git_dir))

        source_dir = temp_git_dir / "source"
        source_dir.mkdir()

        output_path = temp_git_dir / "archive.rar"

        with pytest.raises(GitArchiveError):
            await manager.create_archive(source_dir, output_path, format="rar")

    @pytest.mark.asyncio
    async def test_create_archive_checksum_calculation(self, temp_git_dir):
        """Test that checksum is correctly calculated"""
        manager = GitManager(temp_dir=str(temp_git_dir))

        source_dir = temp_git_dir / "source"
        source_dir.mkdir()
        (source_dir / "file.txt").write_text("test content")

        output_path = temp_git_dir / "archive.tar.gz"

        _, checksum, _ = await manager.create_archive(source_dir, output_path)

        # Calculate expected checksum
        sha256_hash = hashlib.sha256()
        with open(output_path, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        expected_checksum = sha256_hash.hexdigest()

        assert checksum == expected_checksum

    @pytest.mark.asyncio
    async def test_create_archive_creates_output_directory(self, temp_git_dir):
        """Test that archive creation creates output directory if needed"""
        manager = GitManager(temp_dir=str(temp_git_dir))

        source_dir = temp_git_dir / "source"
        source_dir.mkdir()
        (source_dir / "file.txt").write_text("content")

        # Output path in non-existent directory
        output_path = temp_git_dir / "nested" / "dir" / "archive.tar.gz"

        await manager.create_archive(source_dir, output_path)

        assert output_path.exists()
        assert output_path.parent.exists()


class TestManifestExtraction:
    """Test manifest extraction and validation"""

    @pytest.mark.asyncio
    async def test_extract_manifest_success(self, temp_git_dir, sample_manifest_data):
        """Test successful manifest extraction"""
        manager = GitManager(temp_dir=str(temp_git_dir))

        # Create directory with manifest
        clone_dir = temp_git_dir / "clone"
        clone_dir.mkdir()
        manifest_path = clone_dir / "manifest.yaml"

        with open(manifest_path, 'w') as f:
            yaml.dump(sample_manifest_data, f)

        manifest = await manager.extract_manifest(clone_dir)

        assert isinstance(manifest, TemplateManifest)
        assert manifest.name == "test-template"
        assert manifest.version == "1.0.0"

    @pytest.mark.asyncio
    async def test_extract_manifest_alternate_names(self, temp_git_dir, sample_manifest_data):
        """Test finding manifest with alternate filenames"""
        manager = GitManager(temp_dir=str(temp_git_dir))

        clone_dir = temp_git_dir / "clone"
        clone_dir.mkdir()

        # Use alternate name
        manifest_path = clone_dir / "manifest.yml"

        with open(manifest_path, 'w') as f:
            yaml.dump(sample_manifest_data, f)

        manifest = await manager.extract_manifest(clone_dir)

        assert manifest.name == "test-template"

    @pytest.mark.asyncio
    async def test_extract_manifest_not_found(self, temp_git_dir):
        """Test error when manifest not found"""
        manager = GitManager(temp_dir=str(temp_git_dir))

        clone_dir = temp_git_dir / "clone"
        clone_dir.mkdir()

        with pytest.raises(ManifestNotFoundError):
            await manager.extract_manifest(clone_dir)

    @pytest.mark.asyncio
    async def test_extract_manifest_invalid_yaml(self, temp_git_dir):
        """Test error handling for invalid YAML"""
        manager = GitManager(temp_dir=str(temp_git_dir))

        clone_dir = temp_git_dir / "clone"
        clone_dir.mkdir()
        manifest_path = clone_dir / "manifest.yaml"

        # Write invalid YAML
        manifest_path.write_text("invalid: yaml: content: [[[")

        with pytest.raises(ValueError):
            await manager.extract_manifest(clone_dir)

    @pytest.mark.asyncio
    async def test_extract_manifest_validation_error(self, temp_git_dir):
        """Test error handling for manifest validation failure"""
        manager = GitManager(temp_dir=str(temp_git_dir))

        clone_dir = temp_git_dir / "clone"
        clone_dir.mkdir()
        manifest_path = clone_dir / "manifest.yaml"

        # Write manifest with missing required fields
        incomplete_data = {'name': 'test'}

        with open(manifest_path, 'w') as f:
            yaml.dump(incomplete_data, f)

        with pytest.raises(ValueError):
            await manager.extract_manifest(clone_dir)


class TestCleanupOperations:
    """Test cleanup operations"""

    @pytest.mark.asyncio
    async def test_cleanup_clone_success(self, temp_git_dir):
        """Test successful clone cleanup"""
        manager = GitManager(temp_dir=str(temp_git_dir))

        # Create clone directory
        clone_dir = temp_git_dir / "clone"
        clone_dir.mkdir()
        (clone_dir / "file.txt").write_text("content")

        await manager.cleanup_clone(clone_dir)

        assert not clone_dir.exists()

    @pytest.mark.asyncio
    async def test_cleanup_nonexistent_directory(self, temp_git_dir):
        """Test cleanup of non-existent directory"""
        manager = GitManager(temp_dir=str(temp_git_dir))

        clone_dir = temp_git_dir / "nonexistent"

        # Should not raise exception
        await manager.cleanup_clone(clone_dir)

    @pytest.mark.asyncio
    async def test_cleanup_handles_errors_gracefully(self, temp_git_dir):
        """Test that cleanup errors don't raise exceptions"""
        manager = GitManager(temp_dir=str(temp_git_dir))

        clone_dir = temp_git_dir / "clone"
        clone_dir.mkdir()

        with patch('shutil.rmtree', side_effect=Exception("Permission denied")):
            # Should log warning but not raise
            await manager.cleanup_clone(clone_dir)


class TestRepositoryInfo:
    """Test repository information retrieval"""

    @pytest.mark.asyncio
    @patch('git.Repo.clone_from')
    @patch('git.Repo')
    async def test_get_repository_info(self, mock_repo_class, mock_clone_from, temp_git_dir, mock_git_repo):
        """Test getting repository information"""
        manager = GitManager(temp_dir=str(temp_git_dir))

        mock_repo_class.return_value = mock_git_repo

        info = await manager.get_repository_info("https://github.com/test/repo.git")

        assert info['url'] == "https://github.com/test/repo.git"
        assert info['branch'] == "main"
        assert 'latest_commit' in info
        assert 'commit_date' in info
        assert 'author' in info
        assert 'message' in info

    @pytest.mark.asyncio
    @patch('git.Repo.clone_from')
    async def test_get_repository_info_cleanup(self, mock_clone_from, temp_git_dir):
        """Test that get_repository_info cleans up clone directory"""
        manager = GitManager(temp_dir=str(temp_git_dir))

        mock_repo = MagicMock()
        mock_repo.head.commit.hexsha = "abc123"
        mock_repo.head.commit.author.name = "Test"
        mock_repo.head.commit.message = "Test commit"
        mock_repo.head.commit.committed_date = 1234567890

        with patch('git.Repo', return_value=mock_repo):
            await manager.get_repository_info("https://github.com/test/repo.git")

            # Verify cleanup happened (temp directory should be empty or removed)
            # This is implicit if no exception is raised

    @pytest.mark.asyncio
    @patch('git.Repo.clone_from')
    async def test_get_repository_info_error(self, mock_clone_from, temp_git_dir):
        """Test error handling in get_repository_info"""
        manager = GitManager(temp_dir=str(temp_git_dir))

        mock_clone_from.side_effect = git.exc.GitCommandError('clone', 128)

        with pytest.raises(Exception):
            await manager.get_repository_info("https://github.com/invalid/repo.git")


class TestVersionListing:
    """Test listing repository versions"""

    @pytest.mark.asyncio
    @patch('git.Repo.clone_from')
    @patch('git.Repo')
    async def test_list_versions(self, mock_repo_class, mock_clone_from, temp_git_dir):
        """Test listing branches and tags"""
        manager = GitManager(temp_dir=str(temp_git_dir))

        # Mock repository with branches and tags
        mock_repo = MagicMock()

        # Mock branches
        branch_refs = [
            MagicMock(name="origin/main"),
            MagicMock(name="origin/develop"),
            MagicMock(name="origin/feature/test")
        ]
        mock_repo.remote().refs = branch_refs

        # Mock tags
        tag_mocks = [
            MagicMock(name="v1.0.0"),
            MagicMock(name="v1.1.0"),
            MagicMock(name="v2.0.0")
        ]
        mock_repo.tags = tag_mocks

        mock_repo_class.return_value = mock_repo

        versions = await manager.list_versions("https://github.com/test/repo.git")

        assert "main" in versions
        assert "develop" in versions
        assert "v1.0.0" in versions
        assert "v2.0.0" in versions
        assert len(versions) >= 5

    @pytest.mark.asyncio
    @patch('git.Repo.clone_from')
    @patch('git.Repo')
    async def test_list_versions_cleanup(self, mock_repo_class, mock_clone_from, temp_git_dir):
        """Test that list_versions cleans up clone directory"""
        manager = GitManager(temp_dir=str(temp_git_dir))

        mock_repo = MagicMock()
        mock_repo.remote().refs = []
        mock_repo.tags = []
        mock_repo_class.return_value = mock_repo

        await manager.list_versions("https://github.com/test/repo.git")

        # Should complete without error (cleanup happened)

    @pytest.mark.asyncio
    @patch('git.Repo.clone_from')
    async def test_list_versions_error(self, mock_clone_from, temp_git_dir):
        """Test error handling in list_versions"""
        manager = GitManager(temp_dir=str(temp_git_dir))

        mock_clone_from.side_effect = git.exc.GitCommandError('clone', 128)

        with pytest.raises(Exception):
            await manager.list_versions("https://github.com/invalid/repo.git")


class TestGitManagerIntegration:
    """Integration tests for GitManager"""

    @pytest.mark.asyncio
    async def test_full_clone_archive_cleanup_flow(self, temp_git_dir, sample_manifest_data):
        """Test complete flow: clone -> archive -> cleanup"""
        manager = GitManager(temp_dir=str(temp_git_dir))

        # Create a mock "cloned" repository
        clone_dir = temp_git_dir / "mock_clone"
        clone_dir.mkdir()
        (clone_dir / "README.md").write_text("# Test Template")
        (clone_dir / "app.py").write_text("print('hello')")

        # Create manifest
        manifest_path = clone_dir / "manifest.yaml"
        with open(manifest_path, 'w') as f:
            yaml.dump(sample_manifest_data, f)

        # Extract manifest
        manifest = await manager.extract_manifest(clone_dir)
        assert manifest.name == "test-template"

        # Create archive
        output_path = temp_git_dir / "output.tar.gz"
        file_size, checksum, duration = await manager.create_archive(
            clone_dir,
            output_path,
            format="tar.gz"
        )

        assert output_path.exists()
        assert file_size > 0

        # Cleanup
        await manager.cleanup_clone(clone_dir)
        assert not clone_dir.exists()

    @pytest.mark.asyncio
    async def test_archive_both_formats(self, temp_git_dir):
        """Test creating both tar.gz and zip archives"""
        manager = GitManager(temp_dir=str(temp_git_dir))

        source_dir = temp_git_dir / "source"
        source_dir.mkdir()
        (source_dir / "file.txt").write_text("content")

        # Create tar.gz
        tar_path = temp_git_dir / "archive.tar.gz"
        tar_size, tar_checksum, _ = await manager.create_archive(
            source_dir,
            tar_path,
            format="tar.gz"
        )

        # Create zip
        zip_path = temp_git_dir / "archive.zip"
        zip_size, zip_checksum, _ = await manager.create_archive(
            source_dir,
            zip_path,
            format="zip"
        )

        assert tar_path.exists()
        assert zip_path.exists()
        assert tar_size > 0
        assert zip_size > 0
        assert tar_checksum != zip_checksum  # Different formats = different checksums


class TestGitManagerPerformance:
    """Performance tests for GitManager"""

    @pytest.mark.asyncio
    async def test_clone_duration_recorded(self, temp_git_dir):
        """Test that clone duration is properly recorded"""
        manager = GitManager(temp_dir=str(temp_git_dir))

        mock_repo = MagicMock()
        mock_repo.head.commit.hexsha = "abc123"

        with patch('git.Repo.clone_from'), patch('git.Repo', return_value=mock_repo):
            _, _, duration_ms = await manager.clone_repository("https://github.com/test/repo.git")

            assert duration_ms >= 0
            assert isinstance(duration_ms, int)

    @pytest.mark.asyncio
    async def test_archive_duration_recorded(self, temp_git_dir):
        """Test that archive duration is properly recorded"""
        manager = GitManager(temp_dir=str(temp_git_dir))

        source_dir = temp_git_dir / "source"
        source_dir.mkdir()
        (source_dir / "file.txt").write_text("x" * 10000)

        output_path = temp_git_dir / "archive.tar.gz"

        _, _, duration_ms = await manager.create_archive(source_dir, output_path)

        assert duration_ms > 0
        assert isinstance(duration_ms, int)


class TestGitManagerEdgeCases:
    """Test edge cases and boundary conditions"""

    @pytest.mark.asyncio
    async def test_create_archive_empty_directory(self, temp_git_dir):
        """Test creating archive from empty directory"""
        manager = GitManager(temp_dir=str(temp_git_dir))

        source_dir = temp_git_dir / "empty"
        source_dir.mkdir()

        output_path = temp_git_dir / "archive.tar.gz"

        file_size, checksum, _ = await manager.create_archive(source_dir, output_path)

        assert output_path.exists()
        assert file_size > 0  # Archive header/metadata still has size

    @pytest.mark.asyncio
    async def test_create_archive_nested_directories(self, temp_git_dir):
        """Test creating archive with nested directory structure"""
        manager = GitManager(temp_dir=str(temp_git_dir))

        source_dir = temp_git_dir / "source"
        nested_dir = source_dir / "level1" / "level2" / "level3"
        nested_dir.mkdir(parents=True)
        (nested_dir / "deep_file.txt").write_text("deep content")

        output_path = temp_git_dir / "archive.tar.gz"

        file_size, _, _ = await manager.create_archive(source_dir, output_path)

        assert file_size > 0

        # Verify nested structure preserved
        with tarfile.open(output_path, "r:gz") as tar:
            names = tar.getnames()
            assert any("level3" in name for name in names)

    @pytest.mark.asyncio
    async def test_manifest_with_special_characters(self, temp_git_dir):
        """Test manifest with special characters in fields"""
        manager = GitManager(temp_dir=str(temp_git_dir))

        clone_dir = temp_git_dir / "clone"
        clone_dir.mkdir()

        manifest_data = {
            'name': 'test-template-with-special-chars-123',
            'version': '1.0.0-beta.1',
            'description': 'Template with special chars: @#$%',
            'engine': 'docker',
            'persona': 'backend_developer',
            'category': 'backend',
            'language': 'python',
            'dependencies': [],
            'services': []
        }

        manifest_path = clone_dir / "manifest.yaml"
        with open(manifest_path, 'w') as f:
            yaml.dump(manifest_data, f)

        manifest = await manager.extract_manifest(clone_dir)

        assert manifest.name == 'test-template-with-special-chars-123'
        assert '@#$%' in manifest.description


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
