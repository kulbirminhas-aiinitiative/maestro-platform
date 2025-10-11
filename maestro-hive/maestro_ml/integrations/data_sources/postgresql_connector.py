"""
PostgreSQL Data Source Connector for Maestro ML Platform

Features:
- Connection pooling
- Query execution
- Batch operations
- Transaction management
- DataFrame integration
"""

import psycopg2
from psycopg2 import pool, sql
from psycopg2.extras import RealDictCursor, execute_batch
from typing import Optional, List, Dict, Any, Tuple
import logging
import pandas as pd
from contextlib import contextmanager

logger = logging.getLogger(__name__)


class PostgreSQLConnector:
    """
    PostgreSQL connector with connection pooling

    Usage:
        connector = PostgreSQLConnector(
            host="localhost",
            port=5432,
            database="mydb",
            user="user",
            password="pass"
        )

        # Execute query
        results = connector.execute_query("SELECT * FROM users WHERE id = %s", (1,))

        # Load to DataFrame
        df = connector.query_to_dataframe("SELECT * FROM users")

        # Batch insert
        connector.batch_insert("users", [
            {"name": "Alice", "email": "alice@example.com"},
            {"name": "Bob", "email": "bob@example.com"}
        ])
    """

    def __init__(
        self,
        host: str,
        port: int = 5432,
        database: str = "postgres",
        user: str = "postgres",
        password: Optional[str] = None,
        min_connections: int = 1,
        max_connections: int = 10
    ):
        """
        Initialize PostgreSQL connector

        Args:
            host: Database host
            port: Database port
            database: Database name
            user: Database user
            password: Database password
            min_connections: Minimum pool connections
            max_connections: Maximum pool connections
        """
        self.host = host
        self.port = port
        self.database = database
        self.user = user

        # Create connection pool
        try:
            self.connection_pool = pool.ThreadedConnectionPool(
                min_connections,
                max_connections,
                host=host,
                port=port,
                database=database,
                user=user,
                password=password
            )

            logger.info(
                f"PostgreSQL connector initialized: {user}@{host}:{port}/{database}"
            )

        except psycopg2.Error as e:
            logger.error(f"Failed to create connection pool: {e}")
            raise

    @contextmanager
    def get_connection(self):
        """
        Get connection from pool (context manager)

        Usage:
            with connector.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT * FROM users")
        """
        conn = self.connection_pool.getconn()
        try:
            yield conn
        finally:
            self.connection_pool.putconn(conn)

    @contextmanager
    def get_cursor(self, cursor_factory=RealDictCursor):
        """
        Get cursor from pool connection

        Args:
            cursor_factory: Cursor factory (RealDictCursor for dict results)

        Usage:
            with connector.get_cursor() as cur:
                cur.execute("SELECT * FROM users")
                results = cur.fetchall()
        """
        with self.get_connection() as conn:
            cursor = conn.cursor(cursor_factory=cursor_factory)
            try:
                yield cursor
                conn.commit()
            except Exception as e:
                conn.rollback()
                logger.error(f"Transaction rolled back: {e}")
                raise
            finally:
                cursor.close()

    def execute_query(
        self,
        query: str,
        params: Optional[Tuple] = None,
        fetch: bool = True
    ) -> Optional[List[Dict[str, Any]]]:
        """
        Execute query and return results

        Args:
            query: SQL query
            params: Query parameters
            fetch: Whether to fetch results

        Returns:
            List of result dictionaries or None
        """
        try:
            with self.get_cursor() as cur:
                cur.execute(query, params)

                if fetch:
                    results = cur.fetchall()
                    logger.debug(f"Query returned {len(results)} rows")
                    return results
                else:
                    logger.debug(f"Query executed: {cur.rowcount} rows affected")
                    return None

        except psycopg2.Error as e:
            logger.error(f"Query execution failed: {e}")
            raise

    def execute_many(
        self,
        query: str,
        params_list: List[Tuple]
    ) -> int:
        """
        Execute query with multiple parameter sets

        Args:
            query: SQL query
            params_list: List of parameter tuples

        Returns:
            Number of rows affected
        """
        try:
            with self.get_cursor(cursor_factory=None) as cur:
                execute_batch(cur, query, params_list)
                rowcount = cur.rowcount

                logger.debug(f"Batch execution: {rowcount} rows affected")
                return rowcount

        except psycopg2.Error as e:
            logger.error(f"Batch execution failed: {e}")
            raise

    def query_to_dataframe(
        self,
        query: str,
        params: Optional[Tuple] = None,
        chunk_size: Optional[int] = None
    ) -> pd.DataFrame:
        """
        Execute query and return results as DataFrame

        Args:
            query: SQL query
            params: Query parameters
            chunk_size: Chunk size for large results (None = load all)

        Returns:
            pandas DataFrame
        """
        try:
            with self.get_connection() as conn:
                if chunk_size:
                    # Iterator for large datasets
                    chunks = pd.read_sql(
                        query,
                        conn,
                        params=params,
                        chunksize=chunk_size
                    )
                    df = pd.concat(chunks, ignore_index=True)
                else:
                    df = pd.read_sql(query, conn, params=params)

                logger.info(f"Loaded {len(df)} rows to DataFrame")
                return df

        except Exception as e:
            logger.error(f"Query to DataFrame failed: {e}")
            raise

    def insert(
        self,
        table: str,
        data: Dict[str, Any]
    ) -> Optional[int]:
        """
        Insert single row

        Args:
            table: Table name
            data: Dictionary of column -> value

        Returns:
            Inserted row ID or None
        """
        try:
            columns = list(data.keys())
            values = list(data.values())

            query = sql.SQL("INSERT INTO {} ({}) VALUES ({}) RETURNING id").format(
                sql.Identifier(table),
                sql.SQL(", ").join(map(sql.Identifier, columns)),
                sql.SQL(", ").join(sql.Placeholder() * len(values))
            )

            with self.get_cursor(cursor_factory=None) as cur:
                cur.execute(query, values)
                result = cur.fetchone()

                if result:
                    row_id = result[0]
                    logger.debug(f"Inserted row: {table} id={row_id}")
                    return row_id

        except psycopg2.Error as e:
            logger.error(f"Insert failed: {e}")
            raise

    def batch_insert(
        self,
        table: str,
        data: List[Dict[str, Any]]
    ) -> int:
        """
        Batch insert multiple rows

        Args:
            table: Table name
            data: List of dictionaries (column -> value)

        Returns:
            Number of rows inserted
        """
        if not data:
            return 0

        try:
            # All rows must have same columns
            columns = list(data[0].keys())

            query = sql.SQL("INSERT INTO {} ({}) VALUES ({})").format(
                sql.Identifier(table),
                sql.SQL(", ").join(map(sql.Identifier, columns)),
                sql.SQL(", ").join(sql.Placeholder() * len(columns))
            )

            # Extract values in correct order
            params_list = [
                tuple(row[col] for col in columns)
                for row in data
            ]

            with self.get_cursor(cursor_factory=None) as cur:
                execute_batch(cur, query, params_list)
                rowcount = cur.rowcount

                logger.info(f"Batch inserted {rowcount} rows into {table}")
                return rowcount

        except psycopg2.Error as e:
            logger.error(f"Batch insert failed: {e}")
            raise

    def update(
        self,
        table: str,
        data: Dict[str, Any],
        where_clause: str,
        where_params: Tuple
    ) -> int:
        """
        Update rows

        Args:
            table: Table name
            data: Dictionary of column -> value to update
            where_clause: WHERE clause (e.g., "id = %s")
            where_params: WHERE clause parameters

        Returns:
            Number of rows updated
        """
        try:
            set_clause = sql.SQL(", ").join(
                sql.SQL("{} = {}").format(
                    sql.Identifier(col),
                    sql.Placeholder()
                )
                for col in data.keys()
            )

            query = sql.SQL("UPDATE {} SET {} WHERE {}").format(
                sql.Identifier(table),
                set_clause,
                sql.SQL(where_clause)
            )

            params = list(data.values()) + list(where_params)

            with self.get_cursor(cursor_factory=None) as cur:
                cur.execute(query, params)
                rowcount = cur.rowcount

                logger.debug(f"Updated {rowcount} rows in {table}")
                return rowcount

        except psycopg2.Error as e:
            logger.error(f"Update failed: {e}")
            raise

    def delete(
        self,
        table: str,
        where_clause: str,
        where_params: Tuple
    ) -> int:
        """
        Delete rows

        Args:
            table: Table name
            where_clause: WHERE clause (e.g., "id = %s")
            where_params: WHERE clause parameters

        Returns:
            Number of rows deleted
        """
        try:
            query = sql.SQL("DELETE FROM {} WHERE {}").format(
                sql.Identifier(table),
                sql.SQL(where_clause)
            )

            with self.get_cursor(cursor_factory=None) as cur:
                cur.execute(query, where_params)
                rowcount = cur.rowcount

                logger.debug(f"Deleted {rowcount} rows from {table}")
                return rowcount

        except psycopg2.Error as e:
            logger.error(f"Delete failed: {e}")
            raise

    def dataframe_to_table(
        self,
        df: pd.DataFrame,
        table: str,
        if_exists: str = "append",
        chunk_size: int = 1000
    ):
        """
        Write DataFrame to table

        Args:
            df: pandas DataFrame
            table: Table name
            if_exists: What to do if table exists (fail, replace, append)
            chunk_size: Number of rows per batch
        """
        try:
            with self.get_connection() as conn:
                df.to_sql(
                    table,
                    conn,
                    if_exists=if_exists,
                    index=False,
                    method="multi",
                    chunksize=chunk_size
                )

                logger.info(f"Wrote {len(df)} rows to {table}")

        except Exception as e:
            logger.error(f"DataFrame to table failed: {e}")
            raise

    def table_exists(self, table: str) -> bool:
        """
        Check if table exists

        Args:
            table: Table name

        Returns:
            Exists boolean
        """
        query = """
            SELECT EXISTS (
                SELECT FROM information_schema.tables
                WHERE table_schema = 'public'
                AND table_name = %s
            )
        """

        result = self.execute_query(query, (table,))
        return result[0]['exists'] if result else False

    def close(self):
        """Close all connections in pool"""
        if hasattr(self, 'connection_pool'):
            self.connection_pool.closeall()
            logger.info("Connection pool closed")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
