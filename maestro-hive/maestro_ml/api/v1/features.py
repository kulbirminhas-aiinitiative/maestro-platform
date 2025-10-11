"""
Feature Discovery API Endpoints
"""

from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from typing import Optional
import pandas as pd
import io
import sys
from pathlib import Path

# Add features module to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from features.discovery_engine import FeatureDiscoveryEngine
from features.models.feature_schema import (
    FeatureDiscoveryReport,
    CorrelationMethod,
    ImportanceMethod
)
from ..schemas.common import SuccessResponse
from ..dependencies.rbac import require_permissions
from ...enterprise.rbac.permissions import Permission

router = APIRouter(prefix="/features", tags=["features"])


@router.post("/discover", response_model=FeatureDiscoveryReport, dependencies=[Depends(require_permissions(Permission.DATA_VIEW))])
async def discover_features(
    file: UploadFile = File(...),
    target: Optional[str] = Form(None),
    correlation_method: str = Form("pearson"),
    importance_method: str = Form("random_forest"),
    is_classification: bool = Form(True)
):
    """
    Run complete feature discovery analysis on uploaded dataset

    - **file**: CSV file upload
    - **target**: Target variable name (required for importance analysis)
    - **correlation_method**: pearson, spearman, or kendall
    - **importance_method**: random_forest, gradient_boosting, or mutual_info
    - **is_classification**: Whether task is classification (vs regression)
    """
    try:
        # Read CSV
        contents = await file.read()
        df = pd.read_csv(io.BytesIO(contents))

        # Initialize engine
        engine = FeatureDiscoveryEngine()

        # Run discovery
        report = engine.discover(
            df=df,
            target=target,
            dataset_name=file.filename.replace('.csv', ''),
            correlation_method=CorrelationMethod(correlation_method),
            importance_method=ImportanceMethod(importance_method),
            is_classification=is_classification
        )

        return report

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Feature discovery failed: {str(e)}"
        )


@router.post("/profile", dependencies=[Depends(require_permissions(Permission.DATA_VIEW))])
async def profile_dataset(file: UploadFile = File(...)):
    """
    Profile dataset statistics

    - **file**: CSV file upload
    """
    try:
        contents = await file.read()
        df = pd.read_csv(io.BytesIO(contents))

        engine = FeatureDiscoveryEngine()
        profile = engine.profiler.profile(df, file.filename.replace('.csv', ''))

        return profile

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Profiling failed: {str(e)}"
        )


@router.post("/correlate", dependencies=[Depends(require_permissions(Permission.DATA_VIEW))])
async def analyze_correlations(
    file: UploadFile = File(...),
    target: Optional[str] = Form(None),
    method: str = Form("pearson"),
    threshold: float = Form(0.5)
):
    """
    Analyze feature correlations

    - **file**: CSV file upload
    - **target**: Optional target variable to focus on
    - **method**: pearson, spearman, or kendall
    - **threshold**: Correlation threshold for "high" correlations
    """
    try:
        contents = await file.read()
        df = pd.read_csv(io.BytesIO(contents))

        engine = FeatureDiscoveryEngine(correlation_threshold=threshold)
        corr_matrix = engine.correlation_analyzer.analyze(
            df,
            dataset_name=file.filename.replace('.csv', ''),
            target=target,
            method=CorrelationMethod(method)
        )

        return corr_matrix

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Correlation analysis failed: {str(e)}"
        )


@router.post("/importance", dependencies=[Depends(require_permissions(Permission.DATA_VIEW))])
async def calculate_importance(
    file: UploadFile = File(...),
    target: str = Form(...),
    method: str = Form("random_forest"),
    is_classification: bool = Form(True),
    top_n: int = Form(20)
):
    """
    Calculate feature importance

    - **file**: CSV file upload
    - **target**: Target variable name
    - **method**: random_forest, gradient_boosting, permutation, or mutual_info
    - **is_classification**: Whether task is classification
    - **top_n**: Number of top features to return
    """
    try:
        contents = await file.read()
        df = pd.read_csv(io.BytesIO(contents))

        if target not in df.columns:
            raise HTTPException(
                status_code=400,
                detail=f"Target column '{target}' not found in dataset"
            )

        X = df.drop(columns=[target])
        y = df[target]

        engine = FeatureDiscoveryEngine()
        importance = engine.importance_calculator.calculate(
            X, y,
            dataset_name=file.filename.replace('.csv', ''),
            method=ImportanceMethod(method),
            is_classification=is_classification,
            top_n=top_n
        )

        return importance

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Importance calculation failed: {str(e)}"
        )
