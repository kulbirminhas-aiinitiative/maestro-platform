"""
Model Card Generator - Auto-generates model cards from MLflow metadata
"""

import mlflow
from mlflow.tracking import MlflowClient
from datetime import datetime
from typing import Optional, Dict, Any
from pathlib import Path
import json

from .model_card_schema import (
    ModelCard, ModelDetails, IntendedUse, PerformanceMetrics,
    TrainingData, EvaluationData, Metric, ModelType
)


class ModelCardGenerator:
    """
    Generates model cards from MLflow metadata

    Auto-populates what it can from MLflow, allows manual overrides for
    ethical considerations and other human-required sections.

    Example:
        >>> generator = ModelCardGenerator()
        >>> card = generator.generate_from_mlflow(
        ...     model_name="fraud-detector",
        ...     version="3"
        ... )
        >>> generator.save_markdown(card, "fraud-detector-v3.md")
    """

    def __init__(self, mlflow_uri: Optional[str] = None):
        """
        Initialize the generator

        Args:
            mlflow_uri: MLflow tracking URI (uses default if None)
        """
        if mlflow_uri:
            mlflow.set_tracking_uri(mlflow_uri)
        self.client = MlflowClient()

    def generate_from_mlflow(
        self,
        model_name: str,
        version: str,
        overrides: Optional[Dict[str, Any]] = None
    ) -> ModelCard:
        """
        Generate model card from MLflow model version

        Args:
            model_name: Registered model name
            version: Model version
            overrides: Manual overrides/additions to auto-extracted data

        Returns:
            ModelCard object

        Example:
            >>> card = generator.generate_from_mlflow(
            ...     "fraud-detector", "3",
            ...     overrides={
            ...         "intended_use": {
            ...             "primary_uses": ["Fraud detection"],
            ...             "out_of_scope": ["Credit scoring"]
            ...         }
            ...     }
            ... )
        """
        # Get model version from MLflow
        model_version = self.client.get_model_version(model_name, version)
        run = self.client.get_run(model_version.run_id)

        # Extract model details
        model_details = self._extract_model_details(model_version, run)

        # Extract metrics
        metrics = self._extract_metrics(run)

        # Extract training data info
        training_data = self._extract_training_data(run)

        # Create base model card
        card_data = {
            "model_details": model_details,
            "metrics": metrics,
            "training_data": training_data,
            "mlflow_run_id": model_version.run_id,
            "mlflow_model_uri": model_version.source,
            "deployment_status": model_version.current_stage,
        }

        # Apply overrides
        if overrides:
            card_data.update(overrides)

        return ModelCard(**card_data)

    def _extract_model_details(self, model_version, run) -> ModelDetails:
        """Extract model details from MLflow"""
        tags = {**run.data.tags, **model_version.tags}

        # Infer model type from tags or name
        model_type = ModelType.OTHER
        if "model_type" in tags:
            try:
                model_type = ModelType(tags["model_type"])
            except ValueError:
                pass

        return ModelDetails(
            name=model_version.name,
            version=model_version.version,
            model_type=model_type,
            date=datetime.fromtimestamp(model_version.creation_timestamp / 1000),
            framework=tags.get("framework", tags.get("mlflow.source.type")),
            algorithm=tags.get("algorithm"),
            owners=[tags.get("owner", model_version.user_id)] if tags.get("owner") or model_version.user_id else [],
            license=tags.get("license"),
            references=[tags.get("reference")] if tags.get("reference") else [],
        )

    def _extract_metrics(self, run) -> PerformanceMetrics:
        """Extract performance metrics from MLflow run"""
        metrics_list = []

        for metric_name, metric_value in run.data.metrics.items():
            metrics_list.append(
                Metric(
                    name=metric_name,
                    value=metric_value
                )
            )

        return PerformanceMetrics(model_performance=metrics_list)

    def _extract_training_data(self, run) -> TrainingData:
        """Extract training data info from MLflow run"""
        params = run.data.params
        tags = run.data.tags

        return TrainingData(
            dataset_name=tags.get("dataset_name", params.get("dataset")),
            dataset_version=tags.get("dataset_version"),
            num_samples=int(params.get("num_samples")) if params.get("num_samples") else None,
            preprocessing=self._extract_list_param(params, "preprocessing"),
            features=self._extract_list_param(tags, "features"),
        )

    def _extract_list_param(self, params_dict: Dict, key: str) -> list:
        """Extract a list parameter (might be JSON string)"""
        if key not in params_dict:
            return []

        value = params_dict[key]
        if isinstance(value, str):
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                return [v.strip() for v in value.split(",") if v.strip()]
        return value if isinstance(value, list) else []

    def save_markdown(self, card: ModelCard, output_path: Path) -> None:
        """
        Save model card as Markdown

        Args:
            card: ModelCard object
            output_path: Path to save markdown file
        """
        md_content = self._render_markdown(card)

        with open(output_path, "w") as f:
            f.write(md_content)

    def _render_markdown(self, card: ModelCard) -> str:
        """Render model card as Markdown"""
        sections = []

        # Header
        sections.append(f"# Model Card: {card.model_details.name} v{card.model_details.version}")
        sections.append("")
        sections.append(f"**Generated**: {card.last_updated.strftime('%Y-%m-%d %H:%M:%S')}")
        sections.append(f"**Status**: {card.deployment_status or 'Development'}")
        sections.append("")

        # Model Details
        sections.append("## Model Details")
        sections.append("")
        sections.append(f"- **Type**: {card.model_details.model_type.value}")
        sections.append(f"- **Framework**: {card.model_details.framework or 'N/A'}")
        sections.append(f"- **Algorithm**: {card.model_details.algorithm or 'N/A'}")
        sections.append(f"- **Created**: {card.model_details.date.strftime('%Y-%m-%d')}")
        if card.model_details.owners:
            sections.append(f"- **Owners**: {', '.join(card.model_details.owners)}")
        if card.model_details.license:
            sections.append(f"- **License**: {card.model_details.license}")
        sections.append("")

        # Intended Use
        if card.intended_use.primary_uses or card.intended_use.primary_users:
            sections.append("## Intended Use")
            sections.append("")
            if card.intended_use.primary_uses:
                sections.append("### Primary Uses")
                for use in card.intended_use.primary_uses:
                    sections.append(f"- {use}")
                sections.append("")
            if card.intended_use.primary_users:
                sections.append("### Primary Users")
                for user in card.intended_use.primary_users:
                    sections.append(f"- {user}")
                sections.append("")
            if card.intended_use.out_of_scope:
                sections.append("### Out of Scope Uses")
                for use in card.intended_use.out_of_scope:
                    sections.append(f"- {use}")
                sections.append("")

        # Metrics
        if card.metrics.model_performance:
            sections.append("## Performance Metrics")
            sections.append("")
            sections.append("| Metric | Value |")
            sections.append("|--------|-------|")
            for metric in card.metrics.model_performance:
                sections.append(f"| {metric.name} | {metric.value:.4f} |")
            sections.append("")

        # Training Data
        sections.append("## Training Data")
        sections.append("")
        if card.training_data.dataset_name:
            sections.append(f"- **Dataset**: {card.training_data.dataset_name}")
        if card.training_data.num_samples:
            sections.append(f"- **Samples**: {card.training_data.num_samples:,}")
        if card.training_data.preprocessing:
            sections.append(f"- **Preprocessing**: {', '.join(card.training_data.preprocessing)}")
        sections.append("")

        # Ethical Considerations
        if card.ethical_considerations.risks_and_harms or card.ethical_considerations.mitigations:
            sections.append("## Ethical Considerations")
            sections.append("")
            if card.ethical_considerations.risks_and_harms:
                sections.append("### Risks and Harms")
                for risk in card.ethical_considerations.risks_and_harms:
                    sections.append(f"- {risk}")
                sections.append("")
            if card.ethical_considerations.mitigations:
                sections.append("### Mitigations")
                for mitigation in card.ethical_considerations.mitigations:
                    sections.append(f"- {mitigation}")
                sections.append("")

        # Caveats
        if card.caveats_and_recommendations.caveats or card.caveats_and_recommendations.recommendations:
            sections.append("## Caveats and Recommendations")
            sections.append("")
            if card.caveats_and_recommendations.caveats:
                sections.append("### Caveats")
                for caveat in card.caveats_and_recommendations.caveats:
                    sections.append(f"- {caveat}")
                sections.append("")
            if card.caveats_and_recommendations.recommendations:
                sections.append("### Recommendations")
                for rec in card.caveats_and_recommendations.recommendations:
                    sections.append(f"- {rec}")
                sections.append("")

        # Footer
        sections.append("---")
        sections.append("")
        sections.append(f"*Generated by Maestro ML Platform*")
        if card.mlflow_run_id:
            sections.append(f"*MLflow Run ID: `{card.mlflow_run_id}`*")

        return "\n".join(sections)

    def save_json(self, card: ModelCard, output_path: Path) -> None:
        """Save model card as JSON"""
        with open(output_path, "w") as f:
            f.write(card.model_dump_json(indent=2))

    def to_pdf_request_format(self, card: ModelCard) -> dict:
        """
        Convert ModelCard to PDF service request format

        Returns dict compatible with MAESTRO PDF Generator Service
        """
        return {
            "template_type": "model_card",
            "title": f"Model Card: {card.model_details.name} v{card.model_details.version}",
            "content": {
                "model_details": {
                    "name": card.model_details.name,
                    "version": card.model_details.version,
                    "model_type": card.model_details.model_type.value,
                    "framework": card.model_details.framework,
                    "algorithm": card.model_details.algorithm,
                    "owners": card.model_details.owners,
                    "license": card.model_details.license,
                },
                "intended_use": {
                    "primary_uses": card.intended_use.primary_uses,
                    "primary_users": card.intended_use.primary_users,
                    "out_of_scope": card.intended_use.out_of_scope,
                },
                "metrics": {
                    "model_performance": [
                        {"name": m.name, "value": m.value, "threshold": m.threshold}
                        for m in card.metrics.model_performance
                    ]
                },
                "training_data": {
                    "dataset_name": card.training_data.dataset_name,
                    "num_samples": card.training_data.num_samples,
                    "preprocessing": card.training_data.preprocessing,
                    "features": card.training_data.features,
                },
                "ethical_considerations": {
                    "risks_and_harms": card.ethical_considerations.risks_and_harms,
                    "mitigations": card.ethical_considerations.mitigations,
                },
                "caveats_and_recommendations": {
                    "caveats": card.caveats_and_recommendations.caveats,
                    "recommendations": card.caveats_and_recommendations.recommendations,
                },
                "mlflow_run_id": card.mlflow_run_id,
                "deployment_status": card.deployment_status,
            },
            "author": card.model_details.owners[0] if card.model_details.owners else "Maestro ML Platform",
            "format": "pdf",
            "page_size": "A4",
        }

    async def save_pdf_async(self, card: ModelCard, output_path: Path, pdf_service_url: str = "http://localhost:9550") -> None:
        """
        Save model card as PDF using MAESTRO PDF Generator Service

        Args:
            card: ModelCard object
            output_path: Path to save PDF file
            pdf_service_url: URL of PDF generator service
        """
        import aiohttp

        # Convert card to PDF service format
        pdf_request = self.to_pdf_request_format(card)

        async with aiohttp.ClientSession() as session:
            # Request PDF generation
            async with session.post(
                f"{pdf_service_url}/api/v1/generate/pdf",
                json=pdf_request
            ) as response:
                if response.status != 200:
                    raise Exception(f"PDF generation failed: {response.status}")

                result = await response.json()
                file_url = result["file_url"]

            # Download generated PDF
            async with session.get(f"{pdf_service_url}{file_url}") as response:
                if response.status != 200:
                    raise Exception(f"PDF download failed: {response.status}")

                content = await response.read()

                # Save to file
                with open(output_path, "wb") as f:
                    f.write(content)

    def save_pdf(self, card: ModelCard, output_path: Path, pdf_service_url: str = "http://localhost:9550") -> None:
        """
        Save model card as PDF (synchronous wrapper)

        Args:
            card: ModelCard object
            output_path: Path to save PDF file
            pdf_service_url: URL of PDF generator service
        """
        import asyncio
        asyncio.run(self.save_pdf_async(card, output_path, pdf_service_url))
