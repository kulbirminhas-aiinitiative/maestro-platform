"""
Data Ingestion Pipeline Template

Template for ingesting data from various sources.
"""

import logging
from pathlib import Path
from typing import Any, Optional

import pandas as pd

from ..pipeline_builder import PipelineBuilder

logger = logging.getLogger(__name__)


def load_from_csv(input_path: str, **kwargs) -> pd.DataFrame:
    """
    Load data from CSV file

    Args:
        input_path: Path to CSV file

    Returns:
        DataFrame with loaded data
    """
    logger.info(f"Loading data from CSV: {input_path}")
    df = pd.read_csv(input_path)
    logger.info(f"Loaded {len(df)} rows, {len(df.columns)} columns")
    return df


def load_from_database(connection_string: str, query: str, **kwargs) -> pd.DataFrame:
    """
    Load data from database

    Args:
        connection_string: Database connection string
        query: SQL query

    Returns:
        DataFrame with query results
    """
    logger.info(f"Loading data from database")
    logger.info(f"Query: {query}")

    try:
        import sqlalchemy
        engine = sqlalchemy.create_engine(connection_string)
        df = pd.read_sql(query, engine)
        logger.info(f"Loaded {len(df)} rows from database")
        return df
    except ImportError:
        logger.error("SQLAlchemy not installed. Install with: pip install sqlalchemy")
        raise


def validate_data(df: pd.DataFrame, required_columns: Optional[list[str]] = None, **kwargs) -> pd.DataFrame:
    """
    Validate loaded data

    Args:
        df: DataFrame to validate
        required_columns: List of required column names

    Returns:
        Validated DataFrame
    """
    logger.info("Validating data...")

    # Check for empty DataFrame
    if df.empty:
        raise ValueError("DataFrame is empty")

    # Check required columns
    if required_columns:
        missing = set(required_columns) - set(df.columns)
        if missing:
            raise ValueError(f"Missing required columns: {missing}")

    # Check for duplicates
    dup_count = df.duplicated().sum()
    if dup_count > 0:
        logger.warning(f"Found {dup_count} duplicate rows")

    # Check for missing values
    null_counts = df.isnull().sum()
    if null_counts.any():
        logger.warning(f"Missing values:\n{null_counts[null_counts > 0]}")

    logger.info("Data validation completed")
    return df


def clean_data(df: pd.DataFrame, drop_duplicates: bool = True, **kwargs) -> pd.DataFrame:
    """
    Clean data

    Args:
        df: DataFrame to clean
        drop_duplicates: Whether to drop duplicate rows

    Returns:
        Cleaned DataFrame
    """
    logger.info("Cleaning data...")

    original_rows = len(df)

    # Drop duplicates
    if drop_duplicates:
        df = df.drop_duplicates()
        logger.info(f"Dropped {original_rows - len(df)} duplicate rows")

    # Drop rows with all NaN
    df = df.dropna(how='all')

    logger.info(f"Cleaned data: {len(df)} rows remaining")
    return df


def save_data(
    df: pd.DataFrame,
    output_path: str,
    format: str = "parquet",
    **kwargs
) -> dict[str, Any]:
    """
    Save data to file

    Args:
        df: DataFrame to save
        output_path: Output file path
        format: File format (parquet, csv, json)

    Returns:
        Dictionary with save statistics
    """
    logger.info(f"Saving data to {output_path} ({format} format)")

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)

    if format == "parquet":
        df.to_parquet(output_path, index=False)
    elif format == "csv":
        df.to_csv(output_path, index=False)
    elif format == "json":
        df.to_json(output_path, orient='records')
    else:
        raise ValueError(f"Unsupported format: {format}")

    logger.info(f"Saved {len(df)} rows to {output_path}")

    return {
        "output_path": output_path,
        "rows": len(df),
        "columns": len(df.columns),
        "format": format
    }


def create_ingestion_pipeline(
    pipeline_id: str = "data_ingestion",
    name: str = "Data Ingestion Pipeline"
) -> PipelineBuilder:
    """
    Create data ingestion pipeline

    Returns:
        PipelineBuilder configured for data ingestion
    """
    builder = PipelineBuilder(
        pipeline_id=pipeline_id,
        name=name,
        description="Load, validate, clean, and save data"
    )

    # Add tasks
    builder.add_task(
        task_id="load_data",
        function=load_from_csv,
        name="Load Data from Source",
        retry_count=2
    )

    builder.add_task(
        task_id="validate_data",
        function=validate_data,
        name="Validate Data Quality",
        dependencies=["load_data"],
        retry_count=0
    )

    builder.add_task(
        task_id="clean_data",
        function=clean_data,
        name="Clean Data",
        dependencies=["validate_data"],
        retry_count=0
    )

    builder.add_task(
        task_id="save_data",
        function=save_data,
        name="Save Processed Data",
        dependencies=["clean_data"],
        retry_count=2
    )

    return builder


# Example usage
if __name__ == "__main__":
    # Create and execute ingestion pipeline
    pipeline = create_ingestion_pipeline()

    results = pipeline.execute(
        input_path="data/raw/dataset.csv",
        output_path="data/processed/dataset.parquet",
        required_columns=["feature1", "feature2", "target"],
        drop_duplicates=True,
        format="parquet"
    )

    print("\nPipeline Results:")
    for task_id, result in results.items():
        print(f"  {task_id}: {result.status.value}")
        if result.duration_seconds:
            print(f"    Duration: {result.duration_seconds:.2f}s")
