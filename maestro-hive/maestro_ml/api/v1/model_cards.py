"""
Model Cards API Endpoints
"""

from fastapi import APIRouter, HTTPException, Depends, Query
from fastapi.responses import FileResponse
from typing import Optional
from pathlib import Path
import tempfile
import sys

# Add governance module to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from governance.model_cards import ModelCardGenerator, ModelCard
from ..config import settings
from ..schemas.common import SuccessResponse, ErrorResponse
from ..dependencies.auth import get_current_user
from ..dependencies.rbac import require_permissions
from ...enterprise.rbac.permissions import Permission

router = APIRouter(prefix="/model-cards", tags=["model-cards"])


def get_card_generator() -> ModelCardGenerator:
    """Get model card generator instance"""
    return ModelCardGenerator(mlflow_uri=settings.mlflow_tracking_uri)


@router.get("/{model_name}/versions/{version}", dependencies=[Depends(require_permissions(Permission.MODEL_VIEW))])
async def get_model_card(
    model_name: str,
    version: str,
    format: str = Query("json", regex="^(json|markdown|md)$"),
    generator: ModelCardGenerator = Depends(get_card_generator),
    current_user: dict = Depends(get_current_user)
):
    """
    Get model card for a specific model version

    - **model_name**: Model name
    - **version**: Model version
    - **format**: Output format (json, markdown, md)
    """
    try:
        # Generate model card
        card = generator.generate_from_mlflow(
            model_name=model_name,
            version=version
        )

        if format == "json":
            return card.model_dump()
        elif format in ["markdown", "md"]:
            # Generate markdown
            with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
                generator.save_markdown(card, Path(f.name))
                temp_path = f.name

            return FileResponse(
                path=temp_path,
                media_type="text/markdown",
                filename=f"{model_name}-v{version}.md"
            )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate model card: {str(e)}"
        )


@router.post("/{model_name}/versions/{version}/generate", dependencies=[Depends(require_permissions(Permission.MODEL_CREATE))])
async def generate_model_card_pdf(
    model_name: str,
    version: str,
    overrides: Optional[dict] = None,
    generator: ModelCardGenerator = Depends(get_card_generator),
    current_user: dict = Depends(get_current_user)
):
    """
    Generate model card PDF for a specific model version

    - **model_name**: Model name
    - **version**: Model version
    - **overrides**: Optional manual overrides for human-required sections
    """
    try:
        # Generate model card
        card = generator.generate_from_mlflow(
            model_name=model_name,
            version=version,
            overrides=overrides
        )

        # Generate PDF
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as f:
            temp_path = Path(f.name)

        generator.save_pdf(card, temp_path, pdf_service_url=settings.pdf_service_url)

        return FileResponse(
            path=str(temp_path),
            media_type="application/pdf",
            filename=f"{model_name}-v{version}.pdf"
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate PDF: {str(e)}"
        )


@router.post("/{model_name}/versions/{version}/validate", dependencies=[Depends(require_permissions(Permission.MODEL_VIEW))])
async def validate_model_card(
    model_name: str,
    version: str,
    card_data: dict,
    current_user: dict = Depends(get_current_user)
):
    """
    Validate model card data against schema

    - **model_name**: Model name
    - **version**: Model version
    - **card_data**: Model card data to validate
    """
    try:
        # Validate using Pydantic
        card = ModelCard(**card_data)

        return SuccessResponse(
            success=True,
            message="Model card is valid",
            data={
                "model_name": card.model_details.name,
                "model_version": card.model_details.version,
                "sections_complete": {
                    "model_details": True,
                    "intended_use": bool(card.intended_use.primary_uses),
                    "metrics": bool(card.metrics.model_performance),
                    "training_data": bool(card.training_data.dataset_name),
                    "ethical_considerations": bool(card.ethical_considerations.risks_and_harms),
                }
            }
        )
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"Validation failed: {str(e)}"
        )
