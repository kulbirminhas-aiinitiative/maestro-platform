"""
LIME (Local Interpretable Model-agnostic Explanations) Explainer

Provides local explanations by fitting a simple interpretable model locally.
"""

import logging
from collections.abc import Callable
from typing import Any, Optional, Union

import numpy as np
import pandas as pd

try:
    from lime import lime_tabular
    from lime.lime_text import LimeTextExplainer

    LIME_AVAILABLE = True
except ImportError:
    LIME_AVAILABLE = False

from ..models.explanation_models import (
    ExplanationType,
    LIMEExplanation,
    LocalExplanation,
    ModelType,
)

logger = logging.getLogger(__name__)


class LIMEExplainer:
    """
    LIME-based model explainer

    LIME works by:
    1. Perturbing the input instance
    2. Getting predictions for perturbed instances
    3. Fitting a simple interpretable model (linear) to the local neighborhood
    4. Using the interpretable model's weights as explanations

    Advantages:
    - Model-agnostic (works with any black-box model)
    - Easy to understand (linear approximation)
    - Works with tabular, text, and image data

    Disadvantages:
    - Only local explanations (per instance)
    - Can be unstable (different perturbations = different explanations)
    """

    def __init__(
        self,
        predict_fn: Callable,
        training_data: Union[np.ndarray, pd.DataFrame],
        feature_names: Optional[list[str]] = None,
        class_names: Optional[list[str]] = None,
        categorical_features: Optional[list[int]] = None,
        mode: str = "classification",  # or "regression"
    ):
        """
        Initialize LIME explainer

        Args:
            predict_fn: Prediction function (takes array, returns predictions)
            training_data: Training data (used to determine feature ranges)
            feature_names: List of feature names
            class_names: List of class names (for classification)
            categorical_features: Indices of categorical features
            mode: "classification" or "regression"
        """
        if not LIME_AVAILABLE:
            raise ImportError("LIME is not installed. Install with: pip install lime")

        self.predict_fn = predict_fn
        self.feature_names = feature_names
        self.class_names = class_names
        self.mode = mode
        self.logger = logger

        # Convert training data
        if isinstance(training_data, pd.DataFrame):
            if self.feature_names is None:
                self.feature_names = training_data.columns.tolist()
            training_array = training_data.values
        else:
            training_array = training_data

        # Initialize LIME explainer
        self.explainer = lime_tabular.LimeTabularExplainer(
            training_data=training_array,
            feature_names=self.feature_names,
            class_names=self.class_names,
            categorical_features=categorical_features,
            mode=mode,
            verbose=False,
        )

        self.logger.info(f"Initialized LIME explainer in {mode} mode")

    def explain_local(
        self,
        instance: Union[np.ndarray, pd.DataFrame],
        instance_id: Optional[str] = None,
        top_k: int = 5,
        num_samples: int = 5000,
        num_features: Optional[int] = None,
    ) -> LocalExplanation:
        """
        Explain a single prediction

        Args:
            instance: Single instance to explain
            instance_id: Optional identifier for this instance
            top_k: Number of top features to return
            num_samples: Number of perturbed samples to generate
            num_features: Number of features to include in explanation

        Returns:
            Local explanation with LIME coefficients
        """
        # Convert to array
        if isinstance(instance, pd.DataFrame):
            instance_array = (
                instance.values[0] if len(instance.shape) == 2 else instance.values
            )
        else:
            instance_array = (
                instance.reshape(-1) if len(instance.shape) == 1 else instance[0]
            )

        # Get prediction
        prediction = self.predict_fn(instance_array.reshape(1, -1))[0]

        # Generate explanation
        if num_features is None:
            num_features = min(top_k * 2, len(instance_array))

        explanation = self.explainer.explain_instance(
            data_row=instance_array,
            predict_fn=self.predict_fn,
            num_features=num_features,
            num_samples=num_samples,
        )

        # Extract feature contributions from LIME
        if self.mode == "classification":
            # For classification, get explanation for positive class (class 1)
            lime_exp = (
                explanation.as_list(label=1)
                if len(self.class_names or [0, 1]) > 1
                else explanation.as_list()
            )
        else:
            lime_exp = explanation.as_list()

        # Parse LIME explanation
        # LIME returns tuples like ("feature_name <= 5.0", 0.23)
        feature_contributions = {}
        for feature_desc, coefficient in lime_exp:
            # Extract feature name (before comparison operator)
            feature_name = (
                feature_desc.split()[0] if " " in feature_desc else feature_desc
            )
            feature_contributions[feature_name] = float(coefficient)

        # Get feature values
        if self.feature_names:
            feature_values = {
                name: float(instance_array[i])
                if isinstance(instance_array[i], (int, float, np.number))
                else instance_array[i]
                for i, name in enumerate(self.feature_names)
            }
        else:
            feature_values = {
                f"feature_{i}": float(val)
                if isinstance(val, (int, float, np.number))
                else val
                for i, val in enumerate(instance_array)
            }

        # Sort features by absolute contribution
        sorted_features = sorted(
            feature_contributions.items(), key=lambda x: abs(x[1]), reverse=True
        )

        # Split into positive and negative
        positive = [(f, v) for f, v in sorted_features if v > 0][:top_k]
        negative = [(f, v) for f, v in sorted_features if v < 0][:top_k]

        # Get intercept (baseline prediction)
        intercept = (
            explanation.intercept[1]
            if self.mode == "classification"
            else explanation.intercept[0]
        )

        return LocalExplanation(
            instance_id=instance_id,
            prediction=float(prediction),
            expected_value=float(intercept),
            feature_contributions=feature_contributions,
            feature_values=feature_values,
            top_positive_features=positive,
            top_negative_features=negative,
            explanation_type=ExplanationType.LIME,
            model_type=ModelType.BLACK_BOX,
        )

    def get_lime_explanation(
        self,
        instance: Union[np.ndarray, pd.DataFrame],
        num_samples: int = 5000,
        num_features: Optional[int] = None,
    ) -> LIMEExplanation:
        """
        Get raw LIME explanation

        Args:
            instance: Instance to explain
            num_samples: Number of perturbed samples
            num_features: Number of features to include

        Returns:
            LIME explanation object
        """
        # Convert to array
        if isinstance(instance, pd.DataFrame):
            instance_array = (
                instance.values[0] if len(instance.shape) == 2 else instance.values
            )
        else:
            instance_array = (
                instance.reshape(-1) if len(instance.shape) == 1 else instance[0]
            )

        # Generate explanation
        if num_features is None:
            num_features = len(instance_array)

        explanation = self.explainer.explain_instance(
            data_row=instance_array,
            predict_fn=self.predict_fn,
            num_features=num_features,
            num_samples=num_samples,
        )

        # Extract coefficients
        if self.mode == "classification":
            lime_exp = (
                explanation.as_list(label=1)
                if len(self.class_names or [0, 1]) > 1
                else explanation.as_list()
            )
            intercept = explanation.intercept[1]
            local_pred = (
                explanation.local_pred[1]
                if hasattr(explanation, "local_pred")
                else None
            )
            proba = (
                explanation.predict_proba
                if hasattr(explanation, "predict_proba")
                else None
            )
        else:
            lime_exp = explanation.as_list()
            intercept = explanation.intercept[0]
            local_pred = (
                explanation.local_pred[0]
                if hasattr(explanation, "local_pred")
                else None
            )
            proba = None

        # Parse coefficients
        coefficients = {}
        for feature_desc, coef in lime_exp:
            feature_name = (
                feature_desc.split()[0] if " " in feature_desc else feature_desc
            )
            coefficients[feature_name] = float(coef)

        # Get R² score
        score = explanation.score if hasattr(explanation, "score") else 0.0

        # Get prediction
        prediction = self.predict_fn(instance_array.reshape(1, -1))[0]

        return LIMEExplanation(
            intercept=float(intercept),
            coefficients=coefficients,
            score=float(score),
            local_prediction=float(local_pred)
            if local_pred is not None
            else float(prediction),
            prediction_proba=proba.tolist() if proba is not None else None,
        )

    def plot_explanation(
        self,
        instance: Union[np.ndarray, pd.DataFrame],
        save_path: Optional[str] = None,
        num_features: int = 10,
    ):
        """
        Create LIME explanation plot

        Args:
            instance: Instance to explain
            save_path: Optional path to save plot
            num_features: Number of features to show
        """
        import matplotlib.pyplot as plt

        # Convert to array
        if isinstance(instance, pd.DataFrame):
            instance_array = (
                instance.values[0] if len(instance.shape) == 2 else instance.values
            )
        else:
            instance_array = (
                instance.reshape(-1) if len(instance.shape) == 1 else instance[0]
            )

        # Generate explanation
        explanation = self.explainer.explain_instance(
            data_row=instance_array,
            predict_fn=self.predict_fn,
            num_features=num_features,
        )

        # Create figure
        fig = explanation.as_pyplot_figure(
            label=1 if self.mode == "classification" else 0
        )

        if save_path:
            plt.savefig(save_path, bbox_inches="tight", dpi=300)
            self.logger.info(f"Saved LIME plot to {save_path}")
        else:
            plt.show()

        plt.close()


class LIMETextExplainerWrapper:
    """
    LIME explainer for text data

    Useful for NLP models (sentiment analysis, text classification, etc.)
    """

    def __init__(self, predict_proba_fn: Callable, class_names: list[str]):
        """
        Initialize LIME text explainer

        Args:
            predict_proba_fn: Function that takes text and returns class probabilities
            class_names: List of class names
        """
        if not LIME_AVAILABLE:
            raise ImportError("LIME is not installed. Install with: pip install lime")

        self.predict_proba_fn = predict_proba_fn
        self.class_names = class_names
        self.explainer = LimeTextExplainer(class_names=class_names)
        self.logger = logger

    def explain_text(
        self, text: str, num_features: int = 10, num_samples: int = 5000
    ) -> dict[str, Any]:
        """
        Explain a text classification prediction

        Args:
            text: Text to explain
            num_features: Number of words to include
            num_samples: Number of perturbed samples

        Returns:
            Explanation dict with word contributions
        """
        # Generate explanation
        explanation = self.explainer.explain_instance(
            text_instance=text,
            classifier_fn=self.predict_proba_fn,
            num_features=num_features,
            num_samples=num_samples,
        )

        # Get prediction
        proba = self.predict_proba_fn([text])[0]
        predicted_class = np.argmax(proba)

        # Extract word contributions
        word_contributions = dict(explanation.as_list(label=predicted_class))

        return {
            "text": text,
            "predicted_class": self.class_names[predicted_class],
            "prediction_proba": proba.tolist(),
            "word_contributions": word_contributions,
            "explanation": explanation,
        }

    def plot_explanation(
        self, text: str, save_path: Optional[str] = None, num_features: int = 10
    ):
        """
        Create text explanation plot

        Args:
            text: Text to explain
            save_path: Optional path to save
            num_features: Number of words to show
        """
        import matplotlib.pyplot as plt

        explanation = self.explainer.explain_instance(
            text_instance=text,
            classifier_fn=self.predict_proba_fn,
            num_features=num_features,
        )

        # Get predicted class
        proba = self.predict_proba_fn([text])[0]
        predicted_class = np.argmax(proba)

        fig = explanation.as_pyplot_figure(label=predicted_class)

        if save_path:
            plt.savefig(save_path, bbox_inches="tight", dpi=300)
            self.logger.info(f"Saved LIME text plot to {save_path}")
        else:
            plt.show()

        plt.close()
