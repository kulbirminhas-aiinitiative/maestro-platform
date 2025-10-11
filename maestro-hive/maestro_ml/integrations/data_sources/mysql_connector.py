"""
MySQL Data Source Connector for Maestro ML Platform
"""

import mysql.connector
from mysql.connector import pooling, Error
from typing import Optional, List, Dict, Any, Tuple
import logging
import pandas as pd
from contextlib import contextmanager

logger = logging.getLogger(__name__)


class MySQLConnector:
    """
    MySQL connector with connection pooling

    Usage:
        connector = MySQLConnector(
            host="localhost",
            port=3306,
            database="mydb",
            user="user",
            password="pass"
        )

        results = connector.execute_query("SELECT * FROM users")
        df = connector.query_to_dataframe("SELECT * FROM users")
    """

    def __init__(
        self,
        host: str,
        port: int = 3306,
        database: str = "mysql",
        user: str = "root",
        password: Optional[str] = None,
        pool_size: int = 5
    ):
        """Initialize MySQL connector with connection pool"""
        self.host = host
        self.port = port
        self.database = database
        self.user = user

        try:
            self.connection_pool = pooling.MySQLConnectionPool(
                pool_name="maestro_pool",
                pool_size=pool_size,
                host=host,
                port=port,
                database=database,
                user=user,
                password=password
            )

            logger.info(f"MySQL connector initialized: {user}@{host}:{port}/{database}")

        except Error as e:
            logger.error(f"Failed to create connection pool: {e}")
            raise

    @contextmanager
    def get_connection(self):
        """Get connection from pool"""
        conn = self.connection_pool.get_connection()
        try:
            yield conn
        finally:
            conn.close()

    @contextmanager
    def get_cursor(self, dictionary=True):
        """Get cursor from pool connection"""
        with self.get_connection() as conn:
            cursor = conn.cursor(dictionary=dictionary)
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
        """Execute query and return results"""
        try:
            with self.get_cursor() as cur:
                cur.execute(query, params or ())

                if fetch:
                    results = cur.fetchall()
                    logger.debug(f"Query returned {len(results)} rows")
                    return results
                else:
                    logger.debug(f"Query executed: {cur.rowcount} rows affected")
                    return None

        except Error as e:
            logger.error(f"Query execution failed: {e}")
            raise

    def query_to_dataframe(self, query: str, params: Optional[Tuple] = None) -> pd.DataFrame:
        """Execute query and return DataFrame"""
        try:
            with self.get_connection() as conn:
                df = pd.read_sql(query, conn, params=params)
                logger.info(f"Loaded {len(df)} rows to DataFrame")
                return df

        except Exception as e:
            logger.error(f"Query to DataFrame failed: {e}")
            raise

    def batch_insert(self, table: str, data: List[Dict[str, Any]]) -> int:
        """Batch insert multiple rows"""
        if not data:
            return 0

        try:
            columns = list(data[0].keys())
            placeholders = ", ".join(["%s"] * len(columns))
            query = f"INSERT INTO {table} ({', '.join(columns)}) VALUES ({placeholders})"

            params_list = [tuple(row[col] for col in columns) for row in data]

            with self.get_cursor(dictionary=False) as cur:
                cur.executemany(query, params_list)
                rowcount = cur.rowcount

                logger.info(f"Batch inserted {rowcount} rows into {table}")
                return rowcount

        except Error as e:
            logger.error(f"Batch insert failed: {e}")
            raise
