"""
Snowflake Data Source Connector for Maestro ML Platform
"""

import snowflake.connector
from snowflake.connector import DictCursor
from snowflake.connector.pandas_tools import write_pandas, pd_writer
from typing import Optional, List, Dict, Any, Tuple
import logging
import pandas as pd
from contextlib import contextmanager

logger = logging.getLogger(__name__)


class SnowflakeConnector:
    """
    Snowflake connector

    Usage:
        connector = SnowflakeConnector(
            account="myaccount",
            user="myuser",
            password="mypass",
            warehouse="COMPUTE_WH",
            database="MYDB",
            schema="PUBLIC"
        )

        # Execute query
        results = connector.execute_query("SELECT * FROM users")

        # Load to DataFrame
        df = connector.query_to_dataframe("SELECT * FROM users")

        # Write DataFrame to table
        connector.dataframe_to_table(df, "users")
    """

    def __init__(
        self,
        account: str,
        user: str,
        password: Optional[str] = None,
        warehouse: Optional[str] = None,
        database: Optional[str] = None,
        schema: Optional[str] = None,
        role: Optional[str] = None,
        authenticator: Optional[str] = None
    ):
        """
        Initialize Snowflake connector

        Args:
            account: Snowflake account identifier
            user: Username
            password: Password (if not using SSO)
            warehouse: Warehouse name
            database: Database name
            schema: Schema name
            role: Role name
            authenticator: Authentication method (externalbrowser for SSO)
        """
        self.account = account
        self.user = user
        self.warehouse = warehouse
        self.database = database
        self.schema = schema

        # Connection parameters
        conn_params = {
            "account": account,
            "user": user,
        }

        if password:
            conn_params["password"] = password

        if authenticator:
            conn_params["authenticator"] = authenticator

        if warehouse:
            conn_params["warehouse"] = warehouse

        if database:
            conn_params["database"] = database

        if schema:
            conn_params["schema"] = schema

        if role:
            conn_params["role"] = role

        try:
            self.connection = snowflake.connector.connect(**conn_params)

            logger.info(
                f"Snowflake connector initialized: {user}@{account}"
                f"/{database or 'None'}.{schema or 'None'}"
            )

        except Exception as e:
            logger.error(f"Failed to connect to Snowflake: {e}")
            raise

    @contextmanager
    def get_cursor(self, cursor_class=DictCursor):
        """Get cursor (context manager)"""
        cursor = self.connection.cursor(cursor_class)
        try:
            yield cursor
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
                cur.execute(query, params or ())

                if fetch:
                    results = cur.fetchall()
                    logger.debug(f"Query returned {len(results)} rows")
                    return results
                else:
                    logger.debug(f"Query executed")
                    return None

        except Exception as e:
            logger.error(f"Query execution failed: {e}")
            raise

    def query_to_dataframe(
        self,
        query: str,
        params: Optional[Tuple] = None
    ) -> pd.DataFrame:
        """
        Execute query and return DataFrame

        Args:
            query: SQL query
            params: Query parameters

        Returns:
            pandas DataFrame
        """
        try:
            with self.get_cursor(cursor_class=snowflake.connector.cursor.SnowflakeCursor) as cur:
                cur.execute(query, params or ())
                df = cur.fetch_pandas_all()

                logger.info(f"Loaded {len(df)} rows to DataFrame")
                return df

        except Exception as e:
            logger.error(f"Query to DataFrame failed: {e}")
            raise

    def dataframe_to_table(
        self,
        df: pd.DataFrame,
        table: str,
        database: Optional[str] = None,
        schema: Optional[str] = None,
        auto_create_table: bool = True,
        overwrite: bool = False,
        chunk_size: int = 16000
    ):
        """
        Write DataFrame to Snowflake table

        Args:
            df: pandas DataFrame
            table: Table name
            database: Database name (uses default if not provided)
            schema: Schema name (uses default if not provided)
            auto_create_table: Auto-create table if doesn't exist
            overwrite: Truncate table before insert
            chunk_size: Rows per chunk
        """
        try:
            # Use provided database/schema or defaults
            db = database or self.database
            sch = schema or self.schema

            # Overwrite if requested
            if overwrite:
                truncate_query = f"TRUNCATE TABLE IF EXISTS {db}.{sch}.{table}"
                self.execute_query(truncate_query, fetch=False)

            # Write DataFrame
            success, num_chunks, num_rows, _ = write_pandas(
                conn=self.connection,
                df=df,
                table_name=table.upper(),
                database=db.upper() if db else None,
                schema=sch.upper() if sch else None,
                chunk_size=chunk_size,
                auto_create_table=auto_create_table
            )

            if success:
                logger.info(
                    f"Wrote {num_rows} rows to {db}.{sch}.{table} "
                    f"({num_chunks} chunks)"
                )
            else:
                raise Exception("DataFrame write failed")

        except Exception as e:
            logger.error(f"DataFrame to table failed: {e}")
            raise

    def execute_file(self, file_path: str):
        """
        Execute SQL from file

        Args:
            file_path: Path to SQL file
        """
        try:
            with open(file_path, 'r') as f:
                sql_script = f.read()

            # Split by semicolon and execute each statement
            statements = [s.strip() for s in sql_script.split(';') if s.strip()]

            for statement in statements:
                self.execute_query(statement, fetch=False)

            logger.info(f"Executed {len(statements)} statements from {file_path}")

        except Exception as e:
            logger.error(f"Execute file failed: {e}")
            raise

    def list_databases(self) -> List[str]:
        """List available databases"""
        results = self.execute_query("SHOW DATABASES")
        return [row['name'] for row in results]

    def list_schemas(self, database: Optional[str] = None) -> List[str]:
        """List schemas in database"""
        db = database or self.database
        query = f"SHOW SCHEMAS IN DATABASE {db}" if db else "SHOW SCHEMAS"

        results = self.execute_query(query)
        return [row['name'] for row in results]

    def list_tables(
        self,
        database: Optional[str] = None,
        schema: Optional[str] = None
    ) -> List[str]:
        """List tables in schema"""
        db = database or self.database
        sch = schema or self.schema

        if db and sch:
            query = f"SHOW TABLES IN {db}.{sch}"
        elif sch:
            query = f"SHOW TABLES IN SCHEMA {sch}"
        else:
            query = "SHOW TABLES"

        results = self.execute_query(query)
        return [row['name'] for row in results]

    def table_exists(
        self,
        table: str,
        database: Optional[str] = None,
        schema: Optional[str] = None
    ) -> bool:
        """Check if table exists"""
        tables = self.list_tables(database, schema)
        return table.upper() in [t.upper() for t in tables]

    def get_table_info(
        self,
        table: str,
        database: Optional[str] = None,
        schema: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get table metadata"""
        db = database or self.database
        sch = schema or self.schema

        query = f"DESCRIBE TABLE {db}.{sch}.{table}"
        columns = self.execute_query(query)

        return {
            "columns": [
                {
                    "name": col["name"],
                    "type": col["type"],
                    "nullable": col["null?"] == "Y"
                }
                for col in columns
            ]
        }

    def close(self):
        """Close Snowflake connection"""
        if hasattr(self, 'connection') and self.connection:
            self.connection.close()
            logger.info("Snowflake connection closed")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
