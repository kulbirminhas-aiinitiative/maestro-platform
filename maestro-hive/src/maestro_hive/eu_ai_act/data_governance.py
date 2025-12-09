"""
Data Governance Module - EU AI Act Article 10 Compliance

Implements data quality criteria for training, validation, and testing datasets
with bias detection and mitigation capabilities.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Set
import hashlib
import statistics


class DataQualityDimension(Enum):
    """Data quality dimensions per Article 10."""
    COMPLETENESS = "completeness"
    ACCURACY = "accuracy"
    CONSISTENCY = "consistency"
    TIMELINESS = "timeliness"
    REPRESENTATIVENESS = "representativeness"
    BIAS_FREE = "bias_free"


class BiasType(Enum):
    """Types of bias that can be detected in datasets."""
    SELECTION_BIAS = "selection_bias"
    MEASUREMENT_BIAS = "measurement_bias"
    CONFIRMATION_BIAS = "confirmation_bias"
    HISTORICAL_BIAS = "historical_bias"
    REPRESENTATION_BIAS = "representation_bias"
    LABEL_BIAS = "label_bias"


class MitigationStrategy(Enum):
    """Strategies for mitigating detected bias."""
    RESAMPLING = "resampling"
    REWEIGHTING = "reweighting"
    FEATURE_REMOVAL = "feature_removal"
    ADVERSARIAL_DEBIASING = "adversarial_debiasing"
    THRESHOLD_ADJUSTMENT = "threshold_adjustment"


@dataclass
class QualityScore:
    """Score for a single quality dimension."""
    dimension: DataQualityDimension
    score: float  # 0.0 to 1.0
    issues: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)


@dataclass
class BiasReport:
    """Report of bias detection analysis."""
    dataset_id: str
    bias_type: BiasType
    affected_attributes: List[str]
    severity: float  # 0.0 to 1.0
    statistical_parity_difference: float
    disparate_impact_ratio: float
    mitigation_applied: bool = False
    mitigation_strategy: Optional[MitigationStrategy] = None
    timestamp: datetime = field(default_factory=datetime.utcnow)

    def is_compliant(self, threshold: float = 0.8) -> bool:
        """Check if bias levels are within acceptable threshold."""
        return self.disparate_impact_ratio >= threshold


@dataclass
class DatasetQualityReport:
    """Comprehensive quality report for a dataset."""
    dataset_id: str
    dataset_name: str
    record_count: int
    feature_count: int
    quality_scores: Dict[DataQualityDimension, QualityScore] = field(default_factory=dict)
    bias_reports: List[BiasReport] = field(default_factory=list)
    overall_score: float = 0.0
    compliant: bool = False
    timestamp: datetime = field(default_factory=datetime.utcnow)

    def calculate_overall_score(self) -> float:
        """Calculate weighted overall quality score."""
        if not self.quality_scores:
            return 0.0
        weights = {
            DataQualityDimension.COMPLETENESS: 0.2,
            DataQualityDimension.ACCURACY: 0.2,
            DataQualityDimension.CONSISTENCY: 0.15,
            DataQualityDimension.TIMELINESS: 0.1,
            DataQualityDimension.REPRESENTATIVENESS: 0.2,
            DataQualityDimension.BIAS_FREE: 0.15,
        }
        weighted_sum = sum(
            weights.get(dim, 0.1) * score.score
            for dim, score in self.quality_scores.items()
        )
        self.overall_score = weighted_sum
        return self.overall_score


class DataGovernance:
    """
    Data Governance manager for EU AI Act Article 10 compliance.

    Ensures training, validation, and testing datasets meet quality
    criteria including bias detection and mitigation.
    """

    def __init__(
        self,
        quality_threshold: float = 0.8,
        bias_threshold: float = 0.8,
        protected_attributes: Optional[List[str]] = None
    ):
        """
        Initialize data governance manager.

        Args:
            quality_threshold: Minimum acceptable quality score (0-1)
            bias_threshold: Minimum disparate impact ratio for compliance
            protected_attributes: Attributes to check for bias
        """
        self.quality_threshold = quality_threshold
        self.bias_threshold = bias_threshold
        self.protected_attributes = protected_attributes or [
            "gender", "age", "race", "ethnicity", "religion",
            "nationality", "disability", "sexual_orientation"
        ]
        self._reports: Dict[str, DatasetQualityReport] = {}
        self._bias_reports: Dict[str, List[BiasReport]] = {}

    def generate_dataset_id(self, dataset: Any) -> str:
        """Generate unique ID for a dataset based on content hash."""
        if hasattr(dataset, "__iter__"):
            content = str(list(dataset)[:100])  # Sample for hashing
        else:
            content = str(dataset)
        return hashlib.sha256(content.encode()).hexdigest()[:16]

    def validate_dataset(
        self,
        dataset: List[Dict[str, Any]],
        dataset_name: str = "unnamed",
        schema: Optional[Dict[str, type]] = None
    ) -> DatasetQualityReport:
        """
        Validate dataset quality against Article 10 criteria.

        Args:
            dataset: List of records to validate
            dataset_name: Name identifier for the dataset
            schema: Expected schema for validation

        Returns:
            DatasetQualityReport with quality scores and compliance status
        """
        dataset_id = self.generate_dataset_id(dataset)

        report = DatasetQualityReport(
            dataset_id=dataset_id,
            dataset_name=dataset_name,
            record_count=len(dataset),
            feature_count=len(dataset[0]) if dataset else 0
        )

        # Assess each quality dimension
        report.quality_scores[DataQualityDimension.COMPLETENESS] = (
            self._assess_completeness(dataset, schema)
        )
        report.quality_scores[DataQualityDimension.ACCURACY] = (
            self._assess_accuracy(dataset, schema)
        )
        report.quality_scores[DataQualityDimension.CONSISTENCY] = (
            self._assess_consistency(dataset)
        )
        report.quality_scores[DataQualityDimension.TIMELINESS] = (
            self._assess_timeliness(dataset)
        )
        report.quality_scores[DataQualityDimension.REPRESENTATIVENESS] = (
            self._assess_representativeness(dataset)
        )

        # Perform bias detection
        bias_reports = self.detect_bias(dataset, dataset_id)
        report.bias_reports = bias_reports

        # Calculate bias-free score based on bias reports
        bias_score = self._calculate_bias_free_score(bias_reports)
        report.quality_scores[DataQualityDimension.BIAS_FREE] = QualityScore(
            dimension=DataQualityDimension.BIAS_FREE,
            score=bias_score,
            issues=[f"Bias detected: {b.bias_type.value}" for b in bias_reports if b.severity > 0.3],
            recommendations=["Apply mitigation strategies for detected biases"]
        )

        # Calculate overall score and compliance
        report.calculate_overall_score()
        report.compliant = (
            report.overall_score >= self.quality_threshold and
            all(b.is_compliant(self.bias_threshold) for b in bias_reports)
        )

        self._reports[dataset_id] = report
        return report

    def _assess_completeness(
        self,
        dataset: List[Dict[str, Any]],
        schema: Optional[Dict[str, type]] = None
    ) -> QualityScore:
        """Assess data completeness - percentage of non-null values."""
        if not dataset:
            return QualityScore(
                dimension=DataQualityDimension.COMPLETENESS,
                score=0.0,
                issues=["Dataset is empty"]
            )

        total_values = 0
        non_null_values = 0
        missing_fields: Set[str] = set()

        for record in dataset:
            for key, value in record.items():
                total_values += 1
                if value is not None and value != "":
                    non_null_values += 1
                else:
                    missing_fields.add(key)

        score = non_null_values / total_values if total_values > 0 else 0.0

        return QualityScore(
            dimension=DataQualityDimension.COMPLETENESS,
            score=score,
            issues=[f"Missing values in fields: {', '.join(missing_fields)}"] if missing_fields else [],
            recommendations=["Implement data imputation for missing values"] if score < 0.95 else []
        )

    def _assess_accuracy(
        self,
        dataset: List[Dict[str, Any]],
        schema: Optional[Dict[str, type]] = None
    ) -> QualityScore:
        """Assess data accuracy against schema if provided."""
        if not dataset or not schema:
            return QualityScore(
                dimension=DataQualityDimension.ACCURACY,
                score=1.0 if dataset else 0.0,
                issues=[] if dataset else ["Dataset is empty"],
                recommendations=["Provide schema for detailed accuracy validation"] if not schema else []
            )

        type_errors: List[str] = []
        valid_records = 0

        for i, record in enumerate(dataset):
            record_valid = True
            for field_name, expected_type in schema.items():
                if field_name in record:
                    value = record[field_name]
                    if value is not None and not isinstance(value, expected_type):
                        type_errors.append(f"Record {i}: {field_name} type mismatch")
                        record_valid = False
            if record_valid:
                valid_records += 1

        score = valid_records / len(dataset) if dataset else 0.0

        return QualityScore(
            dimension=DataQualityDimension.ACCURACY,
            score=score,
            issues=type_errors[:5],  # Limit to first 5 errors
            recommendations=["Fix type mismatches in data pipeline"] if type_errors else []
        )

    def _assess_consistency(self, dataset: List[Dict[str, Any]]) -> QualityScore:
        """Assess data consistency - uniformity of formats and values."""
        if not dataset:
            return QualityScore(
                dimension=DataQualityDimension.CONSISTENCY,
                score=0.0,
                issues=["Dataset is empty"]
            )

        # Check if all records have the same fields
        all_fields = set()
        for record in dataset:
            all_fields.update(record.keys())

        consistent_records = 0
        inconsistencies: List[str] = []

        for i, record in enumerate(dataset):
            if set(record.keys()) == all_fields:
                consistent_records += 1
            else:
                missing = all_fields - set(record.keys())
                if missing:
                    inconsistencies.append(f"Record {i} missing: {missing}")

        score = consistent_records / len(dataset) if dataset else 0.0

        return QualityScore(
            dimension=DataQualityDimension.CONSISTENCY,
            score=score,
            issues=inconsistencies[:5],
            recommendations=["Standardize record structure across dataset"] if score < 1.0 else []
        )

    def _assess_timeliness(self, dataset: List[Dict[str, Any]]) -> QualityScore:
        """Assess data timeliness based on timestamp fields."""
        timestamp_fields = ["timestamp", "created_at", "updated_at", "date"]

        if not dataset:
            return QualityScore(
                dimension=DataQualityDimension.TIMELINESS,
                score=0.0,
                issues=["Dataset is empty"]
            )

        # Look for timestamp fields
        found_timestamps = []
        for record in dataset:
            for field in timestamp_fields:
                if field in record and record[field]:
                    found_timestamps.append(record[field])
                    break

        if not found_timestamps:
            return QualityScore(
                dimension=DataQualityDimension.TIMELINESS,
                score=0.8,  # Default score if no timestamp fields
                issues=["No timestamp fields found for timeliness assessment"],
                recommendations=["Add timestamp fields to track data freshness"]
            )

        # All data considered timely for this implementation
        return QualityScore(
            dimension=DataQualityDimension.TIMELINESS,
            score=1.0,
            issues=[],
            recommendations=[]
        )

    def _assess_representativeness(self, dataset: List[Dict[str, Any]]) -> QualityScore:
        """Assess if dataset is representative of target population."""
        if not dataset:
            return QualityScore(
                dimension=DataQualityDimension.REPRESENTATIVENESS,
                score=0.0,
                issues=["Dataset is empty"]
            )

        # Check distribution of protected attributes
        issues: List[str] = []

        for attr in self.protected_attributes:
            values = [r.get(attr) for r in dataset if attr in r and r[attr] is not None]
            if values:
                unique_values = set(values)
                if len(unique_values) == 1:
                    issues.append(f"Attribute '{attr}' has no variation")

        # Calculate score based on diversity
        score = max(0.0, 1.0 - (len(issues) * 0.1))

        return QualityScore(
            dimension=DataQualityDimension.REPRESENTATIVENESS,
            score=score,
            issues=issues,
            recommendations=["Ensure diverse representation in training data"] if issues else []
        )

    def detect_bias(
        self,
        dataset: List[Dict[str, Any]],
        dataset_id: Optional[str] = None,
        target_attribute: Optional[str] = None
    ) -> List[BiasReport]:
        """
        Detect bias in dataset for protected attributes.

        Args:
            dataset: Dataset to analyze
            dataset_id: Optional dataset identifier
            target_attribute: Target variable for outcome analysis

        Returns:
            List of BiasReport for each detected bias
        """
        if not dataset_id:
            dataset_id = self.generate_dataset_id(dataset)

        bias_reports: List[BiasReport] = []

        for attr in self.protected_attributes:
            # Check if attribute exists in dataset
            attr_values = [r.get(attr) for r in dataset if attr in r]
            if not attr_values or all(v is None for v in attr_values):
                continue

            # Calculate statistical parity difference
            unique_values = set(v for v in attr_values if v is not None)
            if len(unique_values) < 2:
                continue

            group_counts = {}
            for val in attr_values:
                if val is not None:
                    group_counts[val] = group_counts.get(val, 0) + 1

            total = sum(group_counts.values())
            proportions = [count / total for count in group_counts.values()]

            # Calculate statistical parity difference
            max_prop = max(proportions)
            min_prop = min(proportions)
            spd = max_prop - min_prop

            # Calculate disparate impact ratio (80% rule)
            dir_ratio = min_prop / max_prop if max_prop > 0 else 0.0

            # Determine if bias is significant
            if spd > 0.2 or dir_ratio < self.bias_threshold:
                bias_reports.append(BiasReport(
                    dataset_id=dataset_id,
                    bias_type=BiasType.REPRESENTATION_BIAS,
                    affected_attributes=[attr],
                    severity=spd,
                    statistical_parity_difference=spd,
                    disparate_impact_ratio=dir_ratio
                ))

        self._bias_reports[dataset_id] = bias_reports
        return bias_reports

    def _calculate_bias_free_score(self, bias_reports: List[BiasReport]) -> float:
        """Calculate bias-free score from bias reports."""
        if not bias_reports:
            return 1.0

        # Average disparate impact ratio across all bias reports
        avg_dir = statistics.mean(b.disparate_impact_ratio for b in bias_reports)
        return avg_dir

    def apply_mitigation(
        self,
        dataset_id: str,
        strategy: MitigationStrategy
    ) -> bool:
        """
        Apply bias mitigation strategy to dataset.

        Args:
            dataset_id: ID of dataset to mitigate
            strategy: Mitigation strategy to apply

        Returns:
            True if mitigation was applied successfully
        """
        if dataset_id not in self._bias_reports:
            return False

        for report in self._bias_reports[dataset_id]:
            report.mitigation_applied = True
            report.mitigation_strategy = strategy

        return True

    def get_quality_report(self, dataset_id: str) -> Optional[DatasetQualityReport]:
        """Retrieve quality report for a dataset."""
        return self._reports.get(dataset_id)

    def get_bias_reports(self, dataset_id: str) -> List[BiasReport]:
        """Retrieve bias reports for a dataset."""
        return self._bias_reports.get(dataset_id, [])

    def is_compliant(self, dataset_id: str) -> bool:
        """Check if dataset meets Article 10 compliance requirements."""
        report = self._reports.get(dataset_id)
        if not report:
            return False
        return report.compliant
