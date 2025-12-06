"""
Tests for Integration Adapters (MD-2104)

Tests for:
- ITaskAdapter interface (MD-2109)
- IDocumentAdapter interface (MD-2110)
- ConfluenceAdapter (MD-2111)
- AdapterRegistry (MD-2112)
"""

import pytest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

from services.integration import (
    ITaskAdapter,
    IDocumentAdapter,
    AdapterRegistry,
    get_adapter_registry
)
from services.integration.interfaces import (
    TaskData,
    DocumentData,
    TaskStatus,
    TaskPriority,
    TaskType,
    SearchQuery,
    AdapterResult
)
from services.integration.adapters import (
    JiraAdapter,
    ConfluenceAdapter
)
from services.integration.adapter_registry import reset_adapter_registry


# =============================================================================
# Test Fixtures
# =============================================================================

@pytest.fixture
def mock_task_data():
    """Create mock task data"""
    return TaskData(
        id="task-1",
        external_id="MD-100",
        title="Test Task",
        description="Test description",
        type=TaskType.TASK,
        status=TaskStatus.TODO,
        priority=TaskPriority.MEDIUM,
        project_id="MD",
        created_at=datetime.utcnow()
    )


@pytest.fixture
def mock_document_data():
    """Create mock document data"""
    return DocumentData(
        id="doc-1",
        external_id="12345",
        title="Test Document",
        content="<p>Test content</p>",
        space_id="DEV",
        version=1,
        created_at=datetime.utcnow()
    )


@pytest.fixture(autouse=True)
def reset_registry():
    """Reset adapter registry before each test"""
    reset_adapter_registry()
    yield
    reset_adapter_registry()


# =============================================================================
# Test TaskData
# =============================================================================

class TestTaskData:
    """Tests for TaskData dataclass"""

    def test_task_data_creation(self, mock_task_data):
        """Test TaskData creation"""
        assert mock_task_data.id == "task-1"
        assert mock_task_data.external_id == "MD-100"
        assert mock_task_data.title == "Test Task"
        assert mock_task_data.type == TaskType.TASK
        assert mock_task_data.status == TaskStatus.TODO

    def test_task_data_to_dict(self, mock_task_data):
        """Test TaskData serialization"""
        data = mock_task_data.to_dict()
        assert data['id'] == "task-1"
        assert data['external_id'] == "MD-100"
        assert data['type'] == "task"
        assert data['status'] == "todo"
        assert data['priority'] == "medium"

    def test_task_data_defaults(self):
        """Test TaskData default values"""
        task = TaskData(
            id="t1",
            external_id="T-1",
            title="Test"
        )
        assert task.description == ""
        assert task.type == TaskType.TASK
        assert task.status == TaskStatus.TODO
        assert task.labels == []


# =============================================================================
# Test DocumentData
# =============================================================================

class TestDocumentData:
    """Tests for DocumentData dataclass"""

    def test_document_data_creation(self, mock_document_data):
        """Test DocumentData creation"""
        assert mock_document_data.id == "doc-1"
        assert mock_document_data.title == "Test Document"
        assert mock_document_data.version == 1

    def test_document_data_to_dict(self, mock_document_data):
        """Test DocumentData serialization"""
        data = mock_document_data.to_dict()
        assert data['id'] == "doc-1"
        assert data['title'] == "Test Document"
        assert data['space_id'] == "DEV"
        assert data['version'] == 1


# =============================================================================
# Test SearchQuery
# =============================================================================

class TestSearchQuery:
    """Tests for SearchQuery"""

    def test_search_query_defaults(self):
        """Test SearchQuery default values"""
        query = SearchQuery()
        assert query.project_id is None
        assert query.status is None
        assert query.limit == 50
        assert query.offset == 0

    def test_search_query_with_params(self):
        """Test SearchQuery with parameters"""
        query = SearchQuery(
            project_id="MD",
            status=TaskStatus.TODO,
            type=TaskType.STORY,
            limit=20
        )
        assert query.project_id == "MD"
        assert query.status == TaskStatus.TODO
        assert query.type == TaskType.STORY
        assert query.limit == 20


# =============================================================================
# Test AdapterResult
# =============================================================================

class TestAdapterResult:
    """Tests for AdapterResult"""

    def test_success_result(self, mock_task_data):
        """Test successful result"""
        result = AdapterResult(success=True, data=mock_task_data)
        assert result.success is True
        assert result.data == mock_task_data
        assert result.error is None

    def test_error_result(self):
        """Test error result"""
        result = AdapterResult(success=False, error="Connection failed")
        assert result.success is False
        assert result.error == "Connection failed"
        assert result.data is None


# =============================================================================
# Test Mock Task Adapter
# =============================================================================

class MockTaskAdapter(ITaskAdapter):
    """Mock implementation for testing"""

    @property
    def adapter_name(self) -> str:
        return "mock_task"

    async def create_task(self, title, **kwargs):
        return AdapterResult(
            success=True,
            data=TaskData(
                id="new-1",
                external_id="MOCK-1",
                title=title,
                type=kwargs.get('task_type', TaskType.TASK)
            )
        )

    async def update_task(self, task_id, **kwargs):
        return AdapterResult(success=True)

    async def transition_task(self, task_id, target_status):
        return AdapterResult(success=True)

    async def get_task(self, task_id):
        return AdapterResult(
            success=True,
            data=TaskData(id=task_id, external_id=task_id, title="Mock Task")
        )

    async def search_tasks(self, query):
        return AdapterResult(success=True, data=[])

    async def create_epic(self, title, **kwargs):
        return AdapterResult(
            success=True,
            data=TaskData(
                id="epic-1",
                external_id="MOCK-E1",
                title=title,
                type=TaskType.EPIC
            )
        )

    async def delete_task(self, task_id):
        return AdapterResult(success=True)


# =============================================================================
# Test Mock Document Adapter
# =============================================================================

class MockDocumentAdapter(IDocumentAdapter):
    """Mock implementation for testing"""

    @property
    def adapter_name(self) -> str:
        return "mock_doc"

    async def create_page(self, title, content, **kwargs):
        return AdapterResult(
            success=True,
            data=DocumentData(id="page-1", external_id="P1", title=title, content=content)
        )

    async def update_page(self, page_id, **kwargs):
        return AdapterResult(success=True)

    async def get_page(self, page_id):
        return AdapterResult(
            success=True,
            data=DocumentData(id=page_id, external_id=page_id, title="Mock Page")
        )

    async def delete_page(self, page_id):
        return AdapterResult(success=True)

    async def search_pages(self, query, **kwargs):
        return AdapterResult(success=True, data=[])

    async def get_page_children(self, page_id, **kwargs):
        return AdapterResult(success=True, data=[])


# =============================================================================
# Test ITaskAdapter Interface
# =============================================================================

class TestITaskAdapter:
    """Tests for ITaskAdapter interface"""

    @pytest.mark.asyncio
    async def test_create_task(self):
        """Test task creation"""
        adapter = MockTaskAdapter()
        result = await adapter.create_task("Test Task", description="Test")

        assert result.success is True
        assert result.data.title == "Test Task"
        assert result.data.type == TaskType.TASK

    @pytest.mark.asyncio
    async def test_create_epic(self):
        """Test epic creation"""
        adapter = MockTaskAdapter()
        result = await adapter.create_epic("Test Epic", description="Epic desc")

        assert result.success is True
        assert result.data.type == TaskType.EPIC

    @pytest.mark.asyncio
    async def test_get_task(self):
        """Test getting a task"""
        adapter = MockTaskAdapter()
        result = await adapter.get_task("MOCK-1")

        assert result.success is True
        assert result.data.id == "MOCK-1"

    @pytest.mark.asyncio
    async def test_adapter_name(self):
        """Test adapter name property"""
        adapter = MockTaskAdapter()
        assert adapter.adapter_name == "mock_task"

    @pytest.mark.asyncio
    async def test_health_check(self):
        """Test health check"""
        adapter = MockTaskAdapter()
        result = await adapter.health_check()
        assert result.success is True


# =============================================================================
# Test IDocumentAdapter Interface
# =============================================================================

class TestIDocumentAdapter:
    """Tests for IDocumentAdapter interface"""

    @pytest.mark.asyncio
    async def test_create_page(self):
        """Test page creation"""
        adapter = MockDocumentAdapter()
        result = await adapter.create_page("Test Page", "<p>Content</p>")

        assert result.success is True
        assert result.data.title == "Test Page"

    @pytest.mark.asyncio
    async def test_get_page(self):
        """Test getting a page"""
        adapter = MockDocumentAdapter()
        result = await adapter.get_page("page-1")

        assert result.success is True
        assert result.data.id == "page-1"

    @pytest.mark.asyncio
    async def test_adapter_name(self):
        """Test adapter name property"""
        adapter = MockDocumentAdapter()
        assert adapter.adapter_name == "mock_doc"


# =============================================================================
# Test AdapterRegistry
# =============================================================================

class TestAdapterRegistry:
    """Tests for AdapterRegistry"""

    def test_registry_initialization(self):
        """Test registry initialization"""
        registry = AdapterRegistry()
        assert registry.list_task_adapters() == []
        assert registry.list_document_adapters() == []

    def test_register_task_adapter(self):
        """Test registering task adapter"""
        registry = AdapterRegistry()
        adapter = MockTaskAdapter()

        registry.register_task_adapter(adapter)

        assert "mock_task" in registry.list_task_adapters()
        assert registry.get_task_adapter("mock_task") == adapter

    def test_register_document_adapter(self):
        """Test registering document adapter"""
        registry = AdapterRegistry()
        adapter = MockDocumentAdapter()

        registry.register_document_adapter(adapter)

        assert "mock_doc" in registry.list_document_adapters()
        assert registry.get_document_adapter("mock_doc") == adapter

    def test_default_task_adapter(self):
        """Test default task adapter"""
        registry = AdapterRegistry()
        adapter = MockTaskAdapter()

        registry.register_task_adapter(adapter, is_default=True)

        assert registry.get_default_task_adapter() == adapter

    def test_default_document_adapter(self):
        """Test default document adapter"""
        registry = AdapterRegistry()
        adapter = MockDocumentAdapter()

        registry.register_document_adapter(adapter, is_default=True)

        assert registry.get_default_document_adapter() == adapter

    def test_unregister_task_adapter(self):
        """Test unregistering task adapter"""
        registry = AdapterRegistry()
        adapter = MockTaskAdapter()

        registry.register_task_adapter(adapter)
        result = registry.unregister_task_adapter("mock_task")

        assert result is True
        assert "mock_task" not in registry.list_task_adapters()

    def test_unregister_nonexistent_adapter(self):
        """Test unregistering nonexistent adapter"""
        registry = AdapterRegistry()
        result = registry.unregister_task_adapter("nonexistent")
        assert result is False

    def test_set_default_task_adapter(self):
        """Test setting default task adapter"""
        registry = AdapterRegistry()
        adapter1 = MockTaskAdapter()

        # Create second adapter with different name
        class AnotherTaskAdapter(MockTaskAdapter):
            @property
            def adapter_name(self):
                return "another_task"

        adapter2 = AnotherTaskAdapter()

        registry.register_task_adapter(adapter1)
        registry.register_task_adapter(adapter2)

        registry.set_default_task_adapter("another_task")
        assert registry.get_default_task_adapter() == adapter2

    def test_get_stats(self):
        """Test getting registry statistics"""
        registry = AdapterRegistry()
        registry.register_task_adapter(MockTaskAdapter())
        registry.register_document_adapter(MockDocumentAdapter())

        stats = registry.get_stats()

        assert stats['task_adapters']['count'] == 1
        assert stats['document_adapters']['count'] == 1
        assert 'mock_task' in stats['task_adapters']['names']
        assert 'mock_doc' in stats['document_adapters']['names']

    @pytest.mark.asyncio
    async def test_health_check_all(self):
        """Test health check for all adapters"""
        registry = AdapterRegistry()
        registry.register_task_adapter(MockTaskAdapter())
        registry.register_document_adapter(MockDocumentAdapter())

        results = await registry.health_check_all()

        assert 'task:mock_task' in results
        assert 'document:mock_doc' in results
        assert results['task:mock_task'].success is True
        assert results['document:mock_doc'].success is True


# =============================================================================
# Test Singleton Registry
# =============================================================================

class TestSingletonRegistry:
    """Tests for singleton adapter registry"""

    def test_get_adapter_registry_singleton(self):
        """Test singleton pattern"""
        registry1 = get_adapter_registry()
        registry2 = get_adapter_registry()

        assert registry1 is registry2

    def test_registry_persists_adapters(self):
        """Test adapters persist in singleton"""
        registry = get_adapter_registry()
        registry.register_task_adapter(MockTaskAdapter())

        # Get again and check
        registry2 = get_adapter_registry()
        assert "mock_task" in registry2.list_task_adapters()


# =============================================================================
# Test JiraAdapter
# =============================================================================

class TestJiraAdapter:
    """Tests for JiraAdapter"""

    def test_adapter_name(self):
        """Test adapter name"""
        adapter = JiraAdapter()
        assert adapter.adapter_name == "jira"

    def test_initialization(self):
        """Test initialization with parameters"""
        adapter = JiraAdapter(
            base_url="http://test:8080",
            token="test-token",
            default_project="TEST"
        )
        assert adapter._base_url == "http://test:8080"
        assert adapter._token == "test-token"
        assert adapter._default_project == "TEST"

    @pytest.mark.asyncio
    async def test_get_task_mock(self):
        """Test get_task with mocked response"""
        adapter = JiraAdapter(token="test-token")

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'status': 'success',
            'output': {
                'id': 'jira-123',
                'externalId': 'MD-100',
                'title': 'Test Task',
                'type': 'task',
                'status': {'name': 'To Do'},
                'priority': 'medium'
            }
        }
        mock_response.raise_for_status = MagicMock()

        with patch.object(adapter, '_get_client') as mock_client:
            mock_async_client = AsyncMock()
            mock_async_client.get.return_value = mock_response
            mock_client.return_value = mock_async_client

            result = await adapter.get_task("MD-100")

            assert result.success is True
            assert result.data.external_id == "MD-100"
            assert result.data.title == "Test Task"


# =============================================================================
# Test ConfluenceAdapter
# =============================================================================

class TestConfluenceAdapter:
    """Tests for ConfluenceAdapter"""

    def test_adapter_name(self):
        """Test adapter name"""
        adapter = ConfluenceAdapter(
            base_url="https://test.atlassian.net",
            username="test@test.com",
            api_token="token"
        )
        assert adapter.adapter_name == "confluence"

    def test_initialization(self):
        """Test initialization with parameters"""
        adapter = ConfluenceAdapter(
            base_url="https://test.atlassian.net",
            username="test@test.com",
            api_token="token",
            default_space="DEV"
        )
        assert "test.atlassian.net" in adapter._base_url
        assert adapter._default_space == "DEV"

    @pytest.mark.asyncio
    async def test_get_page_mock(self):
        """Test get_page with mocked response"""
        adapter = ConfluenceAdapter(
            base_url="https://test.atlassian.net",
            username="test@test.com",
            api_token="token"
        )

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'id': '12345',
            'title': 'Test Page',
            'body': {
                'storage': {'value': '<p>Content</p>'}
            },
            'space': {'key': 'DEV'},
            'version': {'number': 1},
            '_links': {
                'base': 'https://test.atlassian.net/wiki',
                'webui': '/pages/12345'
            }
        }
        mock_response.raise_for_status = MagicMock()

        with patch.object(adapter, '_get_client') as mock_client:
            mock_async_client = AsyncMock()
            mock_async_client.get.return_value = mock_response
            mock_client.return_value = mock_async_client

            result = await adapter.get_page("12345")

            assert result.success is True
            assert result.data.id == "12345"
            assert result.data.title == "Test Page"


# =============================================================================
# Test Enums
# =============================================================================

class TestEnums:
    """Tests for enum values"""

    def test_task_status_values(self):
        """Test TaskStatus enum"""
        assert TaskStatus.TODO.value == "todo"
        assert TaskStatus.IN_PROGRESS.value == "in_progress"
        assert TaskStatus.DONE.value == "done"

    def test_task_priority_values(self):
        """Test TaskPriority enum"""
        assert TaskPriority.HIGHEST.value == "highest"
        assert TaskPriority.LOW.value == "low"

    def test_task_type_values(self):
        """Test TaskType enum"""
        assert TaskType.EPIC.value == "epic"
        assert TaskType.STORY.value == "story"
        assert TaskType.TASK.value == "task"
