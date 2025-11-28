"""Query handler base class and registry."""
from abc import ABC, abstractmethod
from typing import Dict, Type, TypeVar, Generic
from .base_query import Query, QueryResult


TQuery = TypeVar('TQuery', bound=Query)
TResult = TypeVar('TResult')


class QueryHandler(ABC, Generic[TQuery, TResult]):
    """Base class for query handlers."""

    @abstractmethod
    async def handle(self, query: TQuery) -> QueryResult[TResult]:
        """Handle a query."""
        pass


class QueryBus:
    """Query bus for routing queries to handlers."""

    def __init__(self):
        self._handlers: Dict[Type[Query], QueryHandler] = {}

    def register(self, query_type: Type[Query], handler: QueryHandler) -> None:
        """Register a query handler."""
        self._handlers[query_type] = handler

    async def dispatch(self, query: Query) -> QueryResult:
        """Dispatch a query to its handler."""
        query_type = type(query)

        if query_type not in self._handlers:
            return QueryResult(
                success=False,
                message=f"No handler registered for {query_type.__name__}"
            )

        handler = self._handlers[query_type]

        try:
            return await handler.handle(query)
        except Exception as e:
            return QueryResult(
                success=False,
                message=f"Error handling query: {str(e)}",
                errors={"exception": str(e)}
            )