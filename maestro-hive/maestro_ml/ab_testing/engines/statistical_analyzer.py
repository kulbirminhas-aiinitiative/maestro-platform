"""
Statistical Analysis Engine for A/B Testing
"""

import logging
from typing import Optional

import numpy as np
from scipy import stats

from ..models.experiment_models import (
    BayesianResult,
    ComparisonResult,
    ExperimentMetric,
    ExperimentResult,
    ExperimentStatus,
    StatisticalTest,
    VariantMetrics,
)

logger = logging.getLogger(__name__)


class StatisticalAnalyzer:
    """
    Statistical analysis engine for A/B testing

    Supports:
    - Frequentist tests (t-test, chi-square, Mann-Whitney)
    - Bayesian analysis
    - Power analysis
    - Sample size calculation
    - Effect size estimation
    """

    def __init__(self):
        self.logger = logger

    def analyze_experiment(
        self,
        experiment_id: str,
        experiment_name: str,
        variant_data: dict[
            str, dict[str, list[float]]
        ],  # variant_id -> metric_name -> values
        metrics: list[ExperimentMetric],
        control_variant_id: str,
        status: ExperimentStatus,
        experiment_duration_hours: float,
    ) -> ExperimentResult:
        """
        Complete analysis of an A/B test experiment

        Args:
            experiment_id: Experiment ID
            experiment_name: Experiment name
            variant_data: Raw data for each variant
            metrics: Metric definitions
            control_variant_id: Control variant ID
            status: Experiment status
            experiment_duration_hours: Duration

        Returns:
            Complete experiment results
        """
        # Calculate metrics for each variant
        variant_metrics = []
        for variant_id, metric_values in variant_data.items():
            vm = self._calculate_variant_metrics(variant_id, metric_values)
            variant_metrics.append(vm)

        # Compare each treatment to control
        comparisons = []
        for metric in metrics:
            for variant_id in variant_data.keys():
                if variant_id != control_variant_id:
                    comparison = self._compare_variants(
                        control_variant_id=control_variant_id,
                        treatment_variant_id=variant_id,
                        metric=metric,
                        variant_data=variant_data,
                    )
                    comparisons.append(comparison)

        # Determine winner
        winning_variant_id, confidence = self._determine_winner(
            comparisons=comparisons, metrics=metrics, variant_metrics=variant_metrics
        )

        # Calculate data quality
        total_samples = sum(vm.sample_size for vm in variant_metrics)
        data_quality = self._calculate_data_quality(variant_metrics, metrics)

        # Generate recommendation
        recommendation, reason = self._generate_recommendation(
            comparisons=comparisons,
            winning_variant_id=winning_variant_id,
            confidence=confidence,
            data_quality=data_quality,
            metrics=metrics,
        )

        return ExperimentResult(
            experiment_id=experiment_id,
            experiment_name=experiment_name,
            status=status,
            variant_metrics=variant_metrics,
            comparisons=comparisons,
            winning_variant_id=winning_variant_id,
            confidence_in_winner=confidence,
            total_sample_size=total_samples,
            experiment_duration_hours=experiment_duration_hours,
            data_quality_score=data_quality,
            recommendation=recommendation,
            reason=reason,
        )

    def _calculate_variant_metrics(
        self, variant_id: str, metric_values: dict[str, list[float]]
    ) -> VariantMetrics:
        """Calculate summary statistics for a variant"""
        metrics = {}
        metric_std = {}
        confidence_intervals = {}

        sample_size = 0
        for metric_name, values in metric_values.items():
            if len(values) == 0:
                continue

            sample_size = max(sample_size, len(values))
            values_array = np.array(values)

            # Mean and std
            metrics[metric_name] = float(np.mean(values_array))
            metric_std[metric_name] = float(np.std(values_array, ddof=1))

            # 95% confidence interval
            ci = stats.t.interval(
                confidence=0.95,
                df=len(values) - 1,
                loc=np.mean(values_array),
                scale=stats.sem(values_array),
            )
            confidence_intervals[metric_name] = (float(ci[0]), float(ci[1]))

        return VariantMetrics(
            variant_id=variant_id,
            sample_size=sample_size,
            metrics=metrics,
            metric_std=metric_std,
            confidence_intervals=confidence_intervals,
        )

    def _compare_variants(
        self,
        control_variant_id: str,
        treatment_variant_id: str,
        metric: ExperimentMetric,
        variant_data: dict[str, dict[str, list[float]]],
    ) -> ComparisonResult:
        """Compare two variants on a single metric"""
        control_values = variant_data[control_variant_id][metric.metric_name]
        treatment_values = variant_data[treatment_variant_id][metric.metric_name]

        # Perform statistical test
        if metric.statistical_test == StatisticalTest.T_TEST:
            test_stat, p_value = stats.ttest_ind(treatment_values, control_values)
        elif metric.statistical_test == StatisticalTest.MANN_WHITNEY:
            test_stat, p_value = stats.mannwhitneyu(
                treatment_values, control_values, alternative="two-sided"
            )
        elif metric.statistical_test == StatisticalTest.CHI_SQUARE:
            # For categorical/conversion metrics
            test_stat, p_value, _, _ = stats.chi2_contingency(
                [
                    [
                        sum(treatment_values),
                        len(treatment_values) - sum(treatment_values),
                    ],
                    [sum(control_values), len(control_values) - sum(control_values)],
                ]
            )
        else:
            # Default to t-test
            test_stat, p_value = stats.ttest_ind(treatment_values, control_values)

        # Calculate effect sizes
        control_mean = np.mean(control_values)
        treatment_mean = np.mean(treatment_values)

        absolute_diff = treatment_mean - control_mean
        relative_diff = (absolute_diff / control_mean * 100) if control_mean != 0 else 0

        # Confidence interval for difference
        diff_values = np.array(treatment_values) - np.mean(control_values)
        ci = stats.t.interval(
            confidence=0.95,
            df=len(diff_values) - 1,
            loc=np.mean(diff_values),
            scale=stats.sem(diff_values),
        )

        # Statistical significance
        is_significant = p_value < metric.significance_level

        # Power analysis
        effect_size = (
            absolute_diff / np.std(control_values) if np.std(control_values) > 0 else 0
        )
        power = self._calculate_power(
            effect_size=effect_size,
            sample_size=len(control_values),
            alpha=metric.significance_level,
        )

        # Recommendation
        if is_significant and absolute_diff > 0 and metric.higher_is_better:
            recommendation = "deploy"
        elif is_significant and absolute_diff < 0 and not metric.higher_is_better:
            recommendation = "deploy"
        elif power < 0.8:
            recommendation = "continue"  # Need more data
        else:
            recommendation = "stop"  # No significant difference found

        return ComparisonResult(
            control_variant_id=control_variant_id,
            treatment_variant_id=treatment_variant_id,
            metric_name=metric.metric_name,
            test_statistic=float(test_stat),
            p_value=float(p_value),
            is_significant=is_significant,
            absolute_difference=float(absolute_diff),
            relative_difference_percent=float(relative_diff),
            confidence_interval=(float(ci[0]), float(ci[1])),
            statistical_power=float(power),
            recommendation=recommendation,
        )

    def _calculate_power(
        self, effect_size: float, sample_size: int, alpha: float = 0.05
    ) -> float:
        """Calculate statistical power"""
        # Simplified power calculation
        # In production, use statsmodels.stats.power
        from scipy.stats import norm

        z_alpha = norm.ppf(1 - alpha / 2)
        z_beta = effect_size * np.sqrt(sample_size / 2) - z_alpha
        power = norm.cdf(z_beta)

        return max(0.0, min(1.0, power))

    def _determine_winner(
        self,
        comparisons: list[ComparisonResult],
        metrics: list[ExperimentMetric],
        variant_metrics: list[VariantMetrics],
    ) -> tuple[Optional[str], Optional[float]]:
        """Determine winning variant based on primary metric"""
        # Find primary metric comparisons
        primary_metric = next((m for m in metrics if m.is_primary), metrics[0])

        primary_comparisons = [
            c for c in comparisons if c.metric_name == primary_metric.metric_name
        ]

        if not primary_comparisons:
            return None, None

        # Find best treatment
        best_comparison = None
        best_improvement = -float("inf")

        for comp in primary_comparisons:
            if comp.is_significant:
                improvement = comp.relative_difference_percent
                if primary_metric.higher_is_better:
                    if improvement > best_improvement:
                        best_improvement = improvement
                        best_comparison = comp
                else:
                    if -improvement > best_improvement:
                        best_improvement = -improvement
                        best_comparison = comp

        if best_comparison:
            # Confidence based on p-value
            confidence = 1.0 - best_comparison.p_value
            return best_comparison.treatment_variant_id, confidence

        return None, None

    def _calculate_data_quality(
        self, variant_metrics: list[VariantMetrics], metrics: list[ExperimentMetric]
    ) -> float:
        """Calculate data quality score (0-1)"""
        scores = []

        for metric in metrics:
            for vm in variant_metrics:
                # Check sample size
                if vm.sample_size >= metric.min_sample_size_per_variant:
                    scores.append(1.0)
                else:
                    scores.append(vm.sample_size / metric.min_sample_size_per_variant)

                # Check variance (not too high)
                if (
                    metric.metric_name in vm.metric_std
                    and metric.metric_name in vm.metrics
                ):
                    mean = vm.metrics[metric.metric_name]
                    std = vm.metric_std[metric.metric_name]
                    cv = std / mean if mean != 0 else float("inf")
                    # Coefficient of variation < 0.5 is good
                    scores.append(max(0.0, 1.0 - cv / 0.5))

        return np.mean(scores) if scores else 0.5

    def _generate_recommendation(
        self,
        comparisons: list[ComparisonResult],
        winning_variant_id: Optional[str],
        confidence: Optional[float],
        data_quality: float,
        metrics: list[ExperimentMetric],
    ) -> tuple[str, str]:
        """Generate experiment recommendation"""
        if data_quality < 0.6:
            return "continue", "Data quality is low. Continue collecting samples."

        if winning_variant_id is None:
            return (
                "continue",
                "No significant winner found. Continue experiment or declare no difference.",
            )

        if confidence and confidence > 0.95:
            return (
                "deploy",
                f"Strong evidence for variant {winning_variant_id}. Deploy to production.",
            )
        elif confidence and confidence > 0.80:
            return (
                "deploy_cautiously",
                f"Moderate evidence for variant {winning_variant_id}. Consider gradual rollout.",
            )
        else:
            return (
                "continue",
                "Winner identified but confidence is low. Continue collecting data.",
            )

    def calculate_required_sample_size(
        self,
        baseline_conversion_rate: float,
        minimum_detectable_effect: float,
        alpha: float = 0.05,
        power: float = 0.8,
    ) -> int:
        """
        Calculate required sample size per variant

        Args:
            baseline_conversion_rate: Current conversion rate
            minimum_detectable_effect: Minimum effect to detect (e.g., 0.05 for 5%)
            alpha: Significance level
            power: Desired statistical power

        Returns:
            Required sample size per variant
        """
        from scipy.stats import norm

        p1 = baseline_conversion_rate
        p2 = p1 * (1 + minimum_detectable_effect)

        z_alpha = norm.ppf(1 - alpha / 2)
        z_beta = norm.ppf(power)

        numerator = (z_alpha + z_beta) ** 2 * (p1 * (1 - p1) + p2 * (1 - p2))
        denominator = (p2 - p1) ** 2

        n = numerator / denominator

        return int(np.ceil(n))

    def bayesian_analysis(
        self,
        variant_data: dict[str, list[float]],
        prior_mean: float = 0.0,
        prior_std: float = 1.0,
    ) -> list[BayesianResult]:
        """
        Perform Bayesian analysis on variants

        Uses Beta-Binomial for conversion rates or Normal-Normal for continuous metrics
        """
        results = []

        # For each variant, calculate posterior distribution
        posteriors = {}
        for variant_id, values in variant_data.items():
            # Assuming normal prior and normal likelihood
            values_array = np.array(values)

            # Posterior parameters
            n = len(values)
            sample_mean = np.mean(values_array)
            sample_std = np.std(values_array, ddof=1)

            # Update posterior
            posterior_precision = 1 / (prior_std**2) + n / (sample_std**2)
            posterior_std = np.sqrt(1 / posterior_precision)
            posterior_mean = (
                prior_mean / (prior_std**2) + n * sample_mean / (sample_std**2)
            ) * (posterior_std**2)

            posteriors[variant_id] = {"mean": posterior_mean, "std": posterior_std}

        # Monte Carlo simulation to calculate probability of being best
        n_samples = 10000
        samples = {}
        for variant_id, posterior in posteriors.items():
            samples[variant_id] = np.random.normal(
                posterior["mean"], posterior["std"], n_samples
            )

        # Calculate probability of being best
        for variant_id in variant_data.keys():
            is_best = np.ones(n_samples, dtype=bool)
            for other_id in variant_data.keys():
                if other_id != variant_id:
                    is_best &= samples[variant_id] > samples[other_id]

            prob_best = np.mean(is_best)

            # Expected loss
            best_samples = np.maximum.reduce([samples[vid] for vid in samples.keys()])
            expected_loss = np.mean(np.maximum(0, best_samples - samples[variant_id]))

            # Credible interval
            ci = np.percentile(samples[variant_id], [2.5, 97.5])

            results.append(
                BayesianResult(
                    variant_id=variant_id,
                    probability_of_being_best=float(prob_best),
                    expected_loss=float(expected_loss),
                    credible_interval_95=(float(ci[0]), float(ci[1])),
                )
            )

        return results
