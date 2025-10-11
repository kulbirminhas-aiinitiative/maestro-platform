"""
Data Validation Framework
Validates data quality, schema, and business rules
"""

from typing import Dict, List, Optional, Tuple, Any
import pandas as pd
import numpy as np
from dataclasses import dataclass
from enum import Enum
import logging
from datetime import datetime


class ValidationSeverity(Enum):
    """Validation issue severity levels"""
    ERROR = "error"  # Must fix - blocks pipeline
    WARNING = "warning"  # Should fix - logged but continues
    INFO = "info"  # Informational only


@dataclass
class ValidationResult:
    """Result of a validation check"""
    check_name: str
    passed: bool
    severity: ValidationSeverity
    message: str
    failed_records: int = 0
    details: Dict[str, Any] = None

    def to_dict(self) -> Dict:
        return {
            "check_name": self.check_name,
            "passed": self.passed,
            "severity": self.severity.value,
            "message": self.message,
            "failed_records": self.failed_records,
            "details": self.details or {}
        }


class DataValidator:
    """Comprehensive data validation framework"""

    def __init__(self, logger: Optional[logging.Logger] = None):
        self.logger = logger or logging.getLogger(__name__)
        self.validation_results: List[ValidationResult] = []

    def validate_schema(self, data: pd.DataFrame, expected_schema: Dict[str, str]) -> ValidationResult:
        """Validate dataframe schema matches expected schema"""
        missing_columns = set(expected_schema.keys()) - set(data.columns)
        extra_columns = set(data.columns) - set(expected_schema.keys())

        if missing_columns:
            return ValidationResult(
                check_name="schema_validation",
                passed=False,
                severity=ValidationSeverity.ERROR,
                message=f"Missing required columns: {missing_columns}",
                details={"missing_columns": list(missing_columns)}
            )

        # Check data types
        type_mismatches = []
        for col, expected_type in expected_schema.items():
            if col in data.columns:
                actual_type = str(data[col].dtype)
                if not self._types_compatible(actual_type, expected_type):
                    type_mismatches.append({
                        "column": col,
                        "expected": expected_type,
                        "actual": actual_type
                    })

        if type_mismatches:
            return ValidationResult(
                check_name="schema_validation",
                passed=False,
                severity=ValidationSeverity.WARNING,
                message=f"Type mismatches in {len(type_mismatches)} columns",
                details={"type_mismatches": type_mismatches}
            )

        message = "Schema validation passed"
        if extra_columns:
            message += f" (extra columns ignored: {extra_columns})"

        return ValidationResult(
            check_name="schema_validation",
            passed=True,
            severity=ValidationSeverity.INFO,
            message=message
        )

    def validate_completeness(self, data: pd.DataFrame, required_columns: List[str],
                            max_null_percentage: float = 0.05) -> ValidationResult:
        """Validate data completeness (no excessive nulls)"""
        null_percentages = {}
        failed_columns = []

        for col in required_columns:
            if col in data.columns:
                null_pct = data[col].isnull().sum() / len(data)
                null_percentages[col] = round(null_pct, 4)

                if null_pct > max_null_percentage:
                    failed_columns.append({
                        "column": col,
                        "null_percentage": null_pct,
                        "threshold": max_null_percentage
                    })

        if failed_columns:
            return ValidationResult(
                check_name="completeness_validation",
                passed=False,
                severity=ValidationSeverity.ERROR,
                message=f"{len(failed_columns)} columns exceed null threshold",
                failed_records=sum(data[fc['column']].isnull().sum() for fc in failed_columns),
                details={"failed_columns": failed_columns}
            )

        return ValidationResult(
            check_name="completeness_validation",
            passed=True,
            severity=ValidationSeverity.INFO,
            message="All columns meet completeness requirements"
        )

    def validate_uniqueness(self, data: pd.DataFrame, unique_columns: List[str]) -> ValidationResult:
        """Validate uniqueness constraints"""
        duplicate_info = []

        for col in unique_columns:
            if col in data.columns:
                duplicates = data[col].duplicated().sum()
                if duplicates > 0:
                    duplicate_info.append({
                        "column": col,
                        "duplicates": int(duplicates),
                        "duplicate_percentage": round(duplicates / len(data), 4)
                    })

        if duplicate_info:
            total_duplicates = sum(d['duplicates'] for d in duplicate_info)
            return ValidationResult(
                check_name="uniqueness_validation",
                passed=False,
                severity=ValidationSeverity.ERROR,
                message=f"Found duplicates in {len(duplicate_info)} unique columns",
                failed_records=total_duplicates,
                details={"duplicate_info": duplicate_info}
            )

        return ValidationResult(
            check_name="uniqueness_validation",
            passed=True,
            severity=ValidationSeverity.INFO,
            message="All uniqueness constraints satisfied"
        )

    def validate_ranges(self, data: pd.DataFrame, range_constraints: Dict[str, Tuple[float, float]]) -> ValidationResult:
        """Validate numeric columns are within expected ranges"""
        violations = []

        for col, (min_val, max_val) in range_constraints.items():
            if col in data.columns:
                out_of_range = ((data[col] < min_val) | (data[col] > max_val)).sum()

                if out_of_range > 0:
                    violations.append({
                        "column": col,
                        "expected_range": [min_val, max_val],
                        "actual_range": [float(data[col].min()), float(data[col].max())],
                        "violations": int(out_of_range)
                    })

        if violations:
            total_violations = sum(v['violations'] for v in violations)
            return ValidationResult(
                check_name="range_validation",
                passed=False,
                severity=ValidationSeverity.WARNING,
                message=f"Range violations in {len(violations)} columns",
                failed_records=total_violations,
                details={"violations": violations}
            )

        return ValidationResult(
            check_name="range_validation",
            passed=True,
            severity=ValidationSeverity.INFO,
            message="All values within expected ranges"
        )

    def validate_categorical(self, data: pd.DataFrame, categorical_constraints: Dict[str, List[str]]) -> ValidationResult:
        """Validate categorical columns contain only allowed values"""
        violations = []

        for col, allowed_values in categorical_constraints.items():
            if col in data.columns:
                actual_values = set(data[col].unique())
                invalid_values = actual_values - set(allowed_values)

                if invalid_values:
                    invalid_count = data[col].isin(invalid_values).sum()
                    violations.append({
                        "column": col,
                        "allowed_values": allowed_values,
                        "invalid_values": list(invalid_values),
                        "invalid_count": int(invalid_count)
                    })

        if violations:
            total_violations = sum(v['invalid_count'] for v in violations)
            return ValidationResult(
                check_name="categorical_validation",
                passed=False,
                severity=ValidationSeverity.ERROR,
                message=f"Invalid categorical values in {len(violations)} columns",
                failed_records=total_violations,
                details={"violations": violations}
            )

        return ValidationResult(
            check_name="categorical_validation",
            passed=True,
            severity=ValidationSeverity.INFO,
            message="All categorical values are valid"
        )

    def validate_freshness(self, data: pd.DataFrame, timestamp_column: str,
                          max_age_hours: int = 24) -> ValidationResult:
        """Validate data freshness"""
        if timestamp_column not in data.columns:
            return ValidationResult(
                check_name="freshness_validation",
                passed=False,
                severity=ValidationSeverity.ERROR,
                message=f"Timestamp column '{timestamp_column}' not found"
            )

        latest_timestamp = pd.to_datetime(data[timestamp_column]).max()
        age_hours = (datetime.now() - latest_timestamp).total_seconds() / 3600

        if age_hours > max_age_hours:
            return ValidationResult(
                check_name="freshness_validation",
                passed=False,
                severity=ValidationSeverity.WARNING,
                message=f"Data is {age_hours:.1f} hours old (max: {max_age_hours})",
                details={"age_hours": age_hours, "max_age_hours": max_age_hours}
            )

        return ValidationResult(
            check_name="freshness_validation",
            passed=True,
            severity=ValidationSeverity.INFO,
            message=f"Data is fresh ({age_hours:.1f} hours old)"
        )

    def validate_distribution(self, data: pd.DataFrame, column: str,
                            expected_mean: float, tolerance: float = 0.2) -> ValidationResult:
        """Validate statistical distribution hasn't shifted significantly"""
        if column not in data.columns:
            return ValidationResult(
                check_name="distribution_validation",
                passed=False,
                severity=ValidationSeverity.ERROR,
                message=f"Column '{column}' not found"
            )

        actual_mean = data[column].mean()
        deviation = abs(actual_mean - expected_mean) / expected_mean

        if deviation > tolerance:
            return ValidationResult(
                check_name="distribution_validation",
                passed=False,
                severity=ValidationSeverity.WARNING,
                message=f"Mean shifted by {deviation:.1%} (tolerance: {tolerance:.1%})",
                details={
                    "column": column,
                    "expected_mean": expected_mean,
                    "actual_mean": float(actual_mean),
                    "deviation": float(deviation)
                }
            )

        return ValidationResult(
            check_name="distribution_validation",
            passed=True,
            severity=ValidationSeverity.INFO,
            message=f"Distribution within tolerance ({deviation:.1%} deviation)"
        )

    def validate_all(self, data: pd.DataFrame, validation_config: Dict[str, Any]) -> Tuple[bool, List[ValidationResult]]:
        """Run all configured validations"""
        self.validation_results = []

        # Schema validation
        if 'schema' in validation_config:
            result = self.validate_schema(data, validation_config['schema'])
            self.validation_results.append(result)

        # Completeness
        if 'required_columns' in validation_config:
            result = self.validate_completeness(
                data,
                validation_config['required_columns'],
                validation_config.get('max_null_percentage', 0.05)
            )
            self.validation_results.append(result)

        # Uniqueness
        if 'unique_columns' in validation_config:
            result = self.validate_uniqueness(data, validation_config['unique_columns'])
            self.validation_results.append(result)

        # Range constraints
        if 'range_constraints' in validation_config:
            result = self.validate_ranges(data, validation_config['range_constraints'])
            self.validation_results.append(result)

        # Categorical constraints
        if 'categorical_constraints' in validation_config:
            result = self.validate_categorical(data, validation_config['categorical_constraints'])
            self.validation_results.append(result)

        # Freshness
        if 'freshness' in validation_config:
            result = self.validate_freshness(
                data,
                validation_config['freshness']['timestamp_column'],
                validation_config['freshness'].get('max_age_hours', 24)
            )
            self.validation_results.append(result)

        # Distribution
        if 'distribution' in validation_config:
            for col, expected_mean in validation_config['distribution'].items():
                result = self.validate_distribution(data, col, expected_mean)
                self.validation_results.append(result)

        # Determine overall pass/fail
        has_errors = any(r.severity == ValidationSeverity.ERROR and not r.passed for r in self.validation_results)
        all_passed = not has_errors

        self._log_results()

        return all_passed, self.validation_results

    def _log_results(self):
        """Log validation results"""
        passed = sum(1 for r in self.validation_results if r.passed)
        total = len(self.validation_results)

        self.logger.info(f"Validation Results: {passed}/{total} passed")

        for result in self.validation_results:
            level = logging.ERROR if result.severity == ValidationSeverity.ERROR else logging.WARNING if result.severity == ValidationSeverity.WARNING else logging.INFO
            self.logger.log(level, f"  [{result.severity.value.upper()}] {result.check_name}: {result.message}")

    def _types_compatible(self, actual_type: str, expected_type: str) -> bool:
        """Check if data types are compatible"""
        type_mappings = {
            'int': ['int', 'int64', 'int32', 'Int64'],
            'float': ['float', 'float64', 'float32', 'Float64'],
            'string': ['object', 'string', 'str'],
            'datetime': ['datetime64', 'datetime'],
            'bool': ['bool', 'boolean']
        }

        for base_type, compatible_types in type_mappings.items():
            if expected_type in compatible_types and any(ct in actual_type for ct in compatible_types):
                return True

        return actual_type == expected_type

    def generate_report(self) -> Dict:
        """Generate comprehensive validation report"""
        return {
            "timestamp": datetime.now().isoformat(),
            "total_checks": len(self.validation_results),
            "passed": sum(1 for r in self.validation_results if r.passed),
            "failed": sum(1 for r in self.validation_results if not r.passed),
            "errors": sum(1 for r in self.validation_results if r.severity == ValidationSeverity.ERROR and not r.passed),
            "warnings": sum(1 for r in self.validation_results if r.severity == ValidationSeverity.WARNING and not r.passed),
            "results": [r.to_dict() for r in self.validation_results]
        }
