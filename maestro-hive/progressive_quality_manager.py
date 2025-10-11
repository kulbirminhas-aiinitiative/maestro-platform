#!/usr/bin/env python3
"""
Progressive Quality Manager

Manages progressive quality thresholds across iterations.
Implements quality ratcheting - thresholds increase with each iteration,
ensuring continuous improvement.
"""

import logging
from typing import Dict, List, Optional
from phase_models import SDLCPhase, PhaseExecution, QualityThresholds

logger = logging.getLogger(__name__)


class ProgressiveQualityManager:
    """
    Manages progressive quality thresholds
    
    Key Concept: Quality Ratcheting
    - Iteration 1: 60% completeness, 0.50 quality (exploratory)
    - Iteration 2: 70% completeness, 0.60 quality (foundation)
    - Iteration 3: 80% completeness, 0.70 quality (refinement)
    - Iteration 4: 90% completeness, 0.80 quality (production-ready)
    - Iteration 5: 95% completeness, 0.85 quality (excellence)
    
    Benefits:
    - Prevents quality regression
    - Incentivizes continuous improvement
    - Realistic expectations for early iterations
    - High bar for later iterations
    """
    
    def __init__(
        self,
        baseline_completeness: float = 0.60,
        baseline_quality: float = 0.50,
        baseline_test_coverage: float = 0.60,
        increment_per_iteration: float = 0.10,
        max_completeness: float = 0.95,
        max_quality: float = 0.90,
        max_test_coverage: float = 0.90
    ):
        """
        Initialize progressive quality manager
        
        Args:
            baseline_completeness: Starting completeness threshold (default: 60%)
            baseline_quality: Starting quality threshold (default: 0.50)
            baseline_test_coverage: Starting test coverage threshold (default: 60%)
            increment_per_iteration: How much to increase per iteration (default: 10%)
            max_completeness: Maximum completeness threshold (default: 95%)
            max_quality: Maximum quality threshold (default: 0.90)
            max_test_coverage: Maximum test coverage threshold (default: 90%)
        """
        self.baseline_thresholds = {
            'completeness': baseline_completeness,
            'quality': baseline_quality,
            'test_coverage': baseline_test_coverage
        }
        
        self.increment_per_iteration = {
            'completeness': increment_per_iteration,
            'quality': increment_per_iteration,
            'test_coverage': increment_per_iteration
        }
        
        self.max_thresholds = {
            'completeness': max_completeness,
            'quality': max_quality,
            'test_coverage': max_test_coverage
        }
    
    def get_thresholds_for_iteration(
        self,
        phase: SDLCPhase,
        iteration: int
    ) -> QualityThresholds:
        """
        Calculate quality thresholds for a specific iteration
        
        Args:
            phase: SDLC phase
            iteration: Iteration number (1-based)
        
        Returns:
            QualityThresholds with completeness, quality, test_coverage
        """
        
        if iteration < 1:
            iteration = 1
        
        thresholds = {}
        
        for metric, baseline in self.baseline_thresholds.items():
            # Calculate progressive threshold
            increment = self.increment_per_iteration[metric]
            max_threshold = self.max_thresholds[metric]
            
            # Formula: baseline + (iteration - 1) * increment, capped at max
            threshold = min(
                baseline + (iteration - 1) * increment,
                max_threshold
            )
            
            thresholds[metric] = threshold
        
        # Phase-specific adjustments
        if phase == SDLCPhase.REQUIREMENTS:
            # Requirements need high completeness early
            thresholds['completeness'] = min(
                thresholds['completeness'] + 0.10,
                self.max_thresholds['completeness']
            )
            logger.debug(f"  Requirements phase: +10% completeness")
        
        elif phase == SDLCPhase.TESTING:
            # Testing needs high test coverage
            thresholds['test_coverage'] = min(
                thresholds['test_coverage'] + 0.10,
                self.max_thresholds['test_coverage']
            )
            logger.debug(f"  Testing phase: +10% test coverage")
        
        elif phase == SDLCPhase.DEPLOYMENT:
            # Deployment needs everything high
            thresholds['completeness'] = min(
                thresholds['completeness'] + 0.10,
                0.98  # Very high for deployment
            )
            thresholds['quality'] = min(
                thresholds['quality'] + 0.10,
                self.max_thresholds['quality']
            )
            logger.debug(f"  Deployment phase: +10% completeness and quality")
        
        logger.info(
            f"📊 Quality thresholds for {phase.value} iteration {iteration}: "
            f"completeness={thresholds['completeness']:.0%}, "
            f"quality={thresholds['quality']:.2f}, "
            f"test_coverage={thresholds['test_coverage']:.0%}"
        )
        
        return QualityThresholds(
            completeness=thresholds['completeness'],
            quality=thresholds['quality'],
            test_coverage=thresholds['test_coverage']
        )
    
    def check_quality_regression(
        self,
        phase: SDLCPhase,
        current_metrics: Dict[str, float],
        previous_metrics: Optional[Dict[str, float]],
        tolerance: float = 0.05
    ) -> Dict[str, any]:
        """
        Check for quality regression between iterations
        
        Args:
            phase: Current phase
            current_metrics: Current quality metrics
            previous_metrics: Previous iteration metrics
            tolerance: Tolerance for regression detection (default: 5%)
        
        Returns:
            {
                'has_regression': bool,
                'regressed_metrics': List[str],
                'improvements': List[str],
                'recommendations': List[str]
            }
        """
        
        if not previous_metrics:
            return {
                'has_regression': False,
                'regressed_metrics': [],
                'improvements': [],
                'recommendations': []
            }
        
        regressed = []
        improved = []
        
        for metric, current_value in current_metrics.items():
            if metric in previous_metrics:
                previous_value = previous_metrics[metric]
                delta = current_value - previous_value
                
                if delta < -tolerance:  # Regression
                    regressed.append(
                        f"{metric}: {previous_value:.2f} → {current_value:.2f} ({delta:.2f})"
                    )
                    logger.warning(
                        f"  📉 Regression in {metric}: {previous_value:.2f} → {current_value:.2f}"
                    )
                elif delta > tolerance:  # Improvement
                    improved.append(
                        f"{metric}: {previous_value:.2f} → {current_value:.2f} (+{delta:.2f})"
                    )
                    logger.info(
                        f"  📈 Improvement in {metric}: {previous_value:.2f} → {current_value:.2f}"
                    )
        
        recommendations = []
        if regressed:
            recommendations.append(
                "Quality regression detected - review changes since last iteration"
            )
            recommendations.append(
                "Consider reverting recent changes or targeted fixes"
            )
            recommendations.append(
                f"Focus on improving: {', '.join([r.split(':')[0] for r in regressed])}"
            )
        
        return {
            'has_regression': len(regressed) > 0,
            'regressed_metrics': regressed,
            'improvements': improved,
            'recommendations': recommendations
        }
    
    def calculate_quality_trend(
        self,
        phase_history: List[PhaseExecution],
        metric: str = 'completeness'
    ) -> Dict[str, any]:
        """
        Calculate quality trends across iterations
        
        Args:
            phase_history: History of phase executions
            metric: Metric to analyze ('completeness', 'quality_score', 'test_coverage')
        
        Returns:
            {
                'trend': str ('improving', 'declining', 'stable', 'insufficient_data'),
                'velocity': float (rate of change),
                'direction': str ('up', 'down', 'flat'),
                'iterations': int,
                'latest_value': float,
                'projection': float (predicted next value)
            }
        """
        
        if len(phase_history) < 2:
            return {
                'trend': 'insufficient_data',
                'velocity': 0.0,
                'direction': 'unknown',
                'iterations': len(phase_history),
                'latest_value': 0.0,
                'projection': 0.0
            }
        
        # Extract metric values over time
        if metric == 'completeness':
            values = [p.completeness for p in phase_history]
        elif metric == 'quality_score':
            values = [p.quality_score for p in phase_history]
        elif metric == 'test_coverage':
            values = [p.test_coverage for p in phase_history]
        else:
            values = [p.completeness for p in phase_history]
        
        # Calculate trend (simple linear regression)
        velocity = self._calculate_trend(values)
        
        # Determine trend direction
        if velocity > 0.05:
            trend = 'improving'
            direction = 'up'
        elif velocity < -0.05:
            trend = 'declining'
            direction = 'down'
        else:
            trend = 'stable'
            direction = 'flat'
        
        # Project next value
        latest_value = values[-1]
        projection = min(max(latest_value + velocity, 0.0), 1.0)
        
        logger.info(
            f"📈 Quality trend for {metric}: {trend} "
            f"(velocity: {velocity:+.3f}, latest: {latest_value:.2f})"
        )
        
        return {
            'trend': trend,
            'velocity': velocity,
            'direction': direction,
            'iterations': len(phase_history),
            'latest_value': latest_value,
            'projection': projection
        }
    
    def _calculate_trend(self, values: List[float]) -> float:
        """
        Simple linear regression to calculate trend
        
        Returns slope (velocity) of the trend line
        """
        if len(values) < 2:
            return 0.0
        
        n = len(values)
        x = list(range(n))
        
        # Calculate means
        x_mean = sum(x) / n
        y_mean = sum(values) / n
        
        # Calculate slope
        numerator = sum((x[i] - x_mean) * (values[i] - y_mean) for i in range(n))
        denominator = sum((x[i] - x_mean) ** 2 for i in range(n))
        
        if denominator == 0:
            return 0.0
        
        slope = numerator / denominator
        return slope
    
    def get_quality_summary(
        self,
        phase_history: List[PhaseExecution]
    ) -> Dict[str, any]:
        """
        Generate comprehensive quality summary across all iterations
        
        Returns summary with trends, regressions, and recommendations
        """
        if not phase_history:
            return {
                'iterations': 0,
                'trends': {},
                'current_quality': {},
                'recommendations': ['Insufficient data for quality analysis']
            }
        
        latest = phase_history[-1]
        previous = phase_history[-2] if len(phase_history) >= 2 else None
        
        # Calculate trends
        completeness_trend = self.calculate_quality_trend(phase_history, 'completeness')
        quality_trend = self.calculate_quality_trend(phase_history, 'quality_score')
        
        # Check for regression
        current_metrics = {
            'completeness': latest.completeness,
            'quality_score': latest.quality_score,
            'test_coverage': latest.test_coverage
        }
        
        previous_metrics = None
        if previous:
            previous_metrics = {
                'completeness': previous.completeness,
                'quality_score': previous.quality_score,
                'test_coverage': previous.test_coverage
            }
        
        regression_check = self.check_quality_regression(
            latest.phase,
            current_metrics,
            previous_metrics
        )
        
        # Generate recommendations
        recommendations = []
        
        if completeness_trend['trend'] == 'declining':
            recommendations.append("⚠️ Completeness is declining - review scope and deliverables")
        elif completeness_trend['trend'] == 'stable' and latest.completeness < 0.80:
            recommendations.append("⚠️ Completeness stagnant - consider adding more personas or support")
        
        if quality_trend['trend'] == 'declining':
            recommendations.append("⚠️ Quality is declining - review code quality and add tests")
        elif quality_trend['trend'] == 'stable' and latest.quality_score < 0.70:
            recommendations.append("⚠️ Quality stagnant - focus on removing stubs and improving documentation")
        
        if regression_check['has_regression']:
            recommendations.extend(regression_check['recommendations'])
        
        if not recommendations:
            if latest.completeness >= 0.90 and latest.quality_score >= 0.80:
                recommendations.append("✅ Excellent quality - ready for production")
            elif latest.completeness >= 0.80 and latest.quality_score >= 0.70:
                recommendations.append("✅ Good quality - continue to next phase")
            else:
                recommendations.append("Continue improving completeness and quality")
        
        return {
            'iterations': len(phase_history),
            'trends': {
                'completeness': completeness_trend,
                'quality': quality_trend
            },
            'current_quality': {
                'completeness': latest.completeness,
                'quality_score': latest.quality_score,
                'test_coverage': latest.test_coverage
            },
            'regression_check': regression_check,
            'recommendations': recommendations
        }
