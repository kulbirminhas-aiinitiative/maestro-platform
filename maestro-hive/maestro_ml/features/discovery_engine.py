"""
Feature Discovery Orchestrator

Main interface for running complete feature discovery analysis.
"""

import pandas as pd
from typing import Optional, List
import logging

from .analysis import DatasetProfiler, CorrelationAnalyzer, ImportanceCalculator
from .models.feature_schema import (
    FeatureDiscoveryReport,
    CorrelationMethod,
    ImportanceMethod,
    FeatureRecommendation,
)


logger = logging.getLogger(__name__)


class FeatureDiscoveryEngine:
    """
    Complete feature discovery orchestrator

    Runs all analyses and generates comprehensive feature discovery report.

    Example:
        >>> engine = FeatureDiscoveryEngine()
        >>> df = pd.read_csv("data.csv")
        >>> report = engine.discover(df, target="price")
        >>> print(f"Top features: {report.importance.top_features}")
    """

    def __init__(
        self,
        correlation_threshold: float = 0.5,
        max_unique_for_categorical: int = 50,
        random_state: int = 42
    ):
        """
        Initialize discovery engine

        Args:
            correlation_threshold: Threshold for high correlations
            max_unique_for_categorical: Max unique values for categorical features
            random_state: Random seed for reproducibility
        """
        self.profiler = DatasetProfiler(max_unique_for_categorical=max_unique_for_categorical)
        self.correlation_analyzer = CorrelationAnalyzer(correlation_threshold=correlation_threshold)
        self.importance_calculator = ImportanceCalculator(random_state=random_state)

    def discover(
        self,
        df: pd.DataFrame,
        target: Optional[str] = None,
        dataset_name: str = "dataset",
        run_profiling: bool = True,
        run_correlation: bool = True,
        run_importance: bool = True,
        correlation_method: CorrelationMethod = CorrelationMethod.PEARSON,
        importance_method: ImportanceMethod = ImportanceMethod.RANDOM_FOREST,
        is_classification: bool = True,
        top_n_features: int = 20
    ) -> FeatureDiscoveryReport:
        """
        Run complete feature discovery analysis

        Args:
            df: Input DataFrame
            target: Target variable name (required for importance analysis)
            dataset_name: Dataset identifier
            run_profiling: Whether to profile dataset
            run_correlation: Whether to analyze correlations
            run_importance: Whether to calculate feature importance
            correlation_method: Correlation calculation method
            importance_method: Importance calculation method
            is_classification: Whether task is classification
            top_n_features: Number of top features to track

        Returns:
            FeatureDiscoveryReport with complete analysis
        """
        logger.info(f"Starting feature discovery for '{dataset_name}'")

        report = FeatureDiscoveryReport(dataset_name=dataset_name)

        # 1. Dataset Profiling
        if run_profiling:
            logger.info("Running dataset profiling...")
            report.profile = self.profiler.profile(df, dataset_name)

        # 2. Correlation Analysis
        if run_correlation:
            logger.info("Running correlation analysis...")
            report.correlations = self.correlation_analyzer.analyze(
                df,
                dataset_name=dataset_name,
                target=target,
                method=correlation_method
            )

        # 3. Feature Importance
        if run_importance and target:
            if target not in df.columns:
                logger.error(f"Target '{target}' not found in DataFrame")
            else:
                logger.info("Running feature importance analysis...")
                X = df.drop(columns=[target])
                y = df[target]

                report.importance = self.importance_calculator.calculate(
                    X, y,
                    dataset_name=dataset_name,
                    method=importance_method,
                    is_classification=is_classification,
                    top_n=top_n_features
                )

        # 4. Generate Recommendations
        report.recommendations = self._generate_recommendations(report)

        # 5. Extract Insights
        report.insights = self._extract_insights(report)

        logger.info(f"Feature discovery complete. Generated {len(report.insights)} insights.")

        return report

    def _generate_recommendations(self, report: FeatureDiscoveryReport) -> List[FeatureRecommendation]:
        """Generate feature recommendations based on analyses"""
        recommendations = []

        # Recommend based on importance
        if report.importance:
            for imp in report.importance.importances[:10]:  # Top 10
                recommendations.append(FeatureRecommendation(
                    feature=imp.feature,
                    score=imp.importance,
                    reason=f"High feature importance (rank #{imp.rank}, {imp.method.value})",
                    evidence={
                        "importance": imp.importance,
                        "rank": imp.rank,
                        "method": imp.method.value
                    }
                ))

        # Recommend based on correlation with target
        if report.correlations and report.correlations.target:
            target = report.correlations.target
            target_corrs = [
                pair for pair in report.correlations.correlations
                if target in [pair.feature1, pair.feature2]
            ]

            target_corrs.sort(key=lambda x: abs(x.correlation), reverse=True)

            for pair in target_corrs[:10]:  # Top 10
                other_feat = pair.feature2 if pair.feature1 == target else pair.feature1

                # Check if already recommended
                if not any(r.feature == other_feat for r in recommendations):
                    recommendations.append(FeatureRecommendation(
                        feature=other_feat,
                        score=abs(pair.correlation),
                        reason=f"{pair.strength.replace('_', ' ').title()} correlation with target ({pair.correlation:.3f})",
                        evidence={
                            "correlation": pair.correlation,
                            "strength": pair.strength,
                            "p_value": pair.p_value
                        }
                    ))

        # Sort by score
        recommendations.sort(key=lambda x: x.score, reverse=True)

        return recommendations[:20]  # Top 20 recommendations

    def _extract_insights(self, report: FeatureDiscoveryReport) -> List[str]:
        """Extract key insights from the analyses"""
        insights = []

        # Data quality insights
        if report.profile:
            if report.profile.null_percentage > 10:
                insights.append(
                    f"⚠️ High missing data: {report.profile.null_percentage:.1f}% of values are null"
                )

            if len(report.profile.numerical_features) == 0:
                insights.append(
                    "⚠️ No numerical features found - consider feature engineering"
                )

            if len(report.profile.categorical_features) > 0.7 * report.profile.num_features:
                insights.append(
                    f"ℹ️ Mostly categorical features ({len(report.profile.categorical_features)}/{report.profile.num_features}) - consider encoding strategies"
                )

        # Correlation insights
        if report.correlations:
            high_corr_count = len(report.correlations.high_correlations)
            if high_corr_count > 0:
                insights.append(
                    f"🔗 Found {high_corr_count} feature pairs with high correlation (>0.5) - consider removing redundant features"
                )

            # Multicollinearity warning
            very_high_corrs = [
                pair for pair in report.correlations.high_correlations
                if abs(pair.correlation) > 0.9
            ]
            if len(very_high_corrs) > 0:
                insights.append(
                    f"⚠️ {len(very_high_corrs)} feature pairs have very high correlation (>0.9) - multicollinearity risk"
                )

        # Importance insights
        if report.importance:
            top_5_importance = sum([imp.importance for imp in report.importance.importances[:5]])
            if top_5_importance > 0.8:
                insights.append(
                    f"⭐ Top 5 features account for {top_5_importance*100:.1f}% of importance - consider focusing on these"
                )

            low_importance_count = len([
                imp for imp in report.importance.importances
                if imp.importance < 0.01
            ])
            if low_importance_count > 0:
                insights.append(
                    f"🗑️ {low_importance_count} features have very low importance (<0.01) - candidates for removal"
                )

        # Recommendation insights
        if report.recommendations:
            insights.append(
                f"💡 Generated {len(report.recommendations)} feature recommendations based on analysis"
            )

        return insights

    def quick_discover(
        self,
        df: pd.DataFrame,
        target: str,
        dataset_name: str = "dataset"
    ) -> FeatureDiscoveryReport:
        """
        Quick discovery with default settings

        Args:
            df: Input DataFrame
            target: Target variable name
            dataset_name: Dataset identifier

        Returns:
            FeatureDiscoveryReport
        """
        # Auto-detect classification vs regression
        is_classification = df[target].dtype == 'object' or df[target].nunique() < 20

        return self.discover(
            df=df,
            target=target,
            dataset_name=dataset_name,
            is_classification=is_classification
        )
