#!/usr/bin/env python3
"""
Cost-Aware Hyperparameter Optimization with Optuna
Balances model performance with training cost (time/resources)
"""

import argparse
import optuna
import mlflow
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import cross_val_score
from sklearn.datasets import load_breast_cancer
from sklearn.model_selection import train_test_split
import time
import os


class CostAwareObjective:
    """
    Multi-objective optimization balancing accuracy and training cost
    """

    def __init__(self, X_train, y_train, cost_weight=0.3):
        """
        Args:
            X_train: Training features
            y_train: Training labels
            cost_weight: Weight for cost in final score (0-1)
        """
        self.X_train = X_train
        self.y_train = y_train
        self.cost_weight = cost_weight
        self.max_cost = 60.0  # Max expected cost in seconds

    def __call__(self, trial):
        """
        Objective function with cost awareness

        Returns:
            tuple: (accuracy, cost) for multi-objective optimization
        """
        # Hyperparameters
        params = {
            'n_estimators': trial.suggest_int('n_estimators', 10, 200),
            'max_depth': trial.suggest_int('max_depth', 3, 30),
            'min_samples_split': trial.suggest_int('min_samples_split', 2, 20),
            'max_features': trial.suggest_categorical('max_features', ['sqrt', 'log2']),
            'n_jobs': 1,  # Single thread for consistent timing
            'random_state': 42
        }

        # Measure training time (proxy for cost)
        start_time = time.time()

        model = RandomForestClassifier(**params)
        cv_scores = cross_val_score(
            model, self.X_train, self.y_train,
            cv=3,  # Reduce CV folds for speed
            scoring='accuracy'
        )

        training_time = time.time() - start_time

        # Calculate accuracy
        accuracy = cv_scores.mean()

        # Estimate cost (normalize by max expected cost)
        # Cost factors: training time, model complexity
        complexity_cost = params['n_estimators'] * params['max_depth'] / 6000.0
        time_cost = training_time / self.max_cost
        total_cost = (time_cost + complexity_cost) / 2.0

        # Log metrics
        trial.set_user_attr('training_time', training_time)
        trial.set_user_attr('complexity_cost', complexity_cost)
        trial.set_user_attr('total_cost', total_cost)

        # Return tuple for multi-objective optimization
        return accuracy, total_cost


def single_objective_cost_aware(trial, X_train, y_train, cost_weight=0.3):
    """
    Single objective function combining accuracy and cost

    Args:
        trial: Optuna trial
        X_train: Training features
        y_train: Training labels
        cost_weight: Weight for cost (higher = prioritize lower cost)

    Returns:
        float: Combined score (higher is better)
    """
    # Hyperparameters
    params = {
        'n_estimators': trial.suggest_int('n_estimators', 10, 200),
        'max_depth': trial.suggest_int('max_depth', 3, 30),
        'min_samples_split': trial.suggest_int('min_samples_split', 2, 20),
        'max_features': trial.suggest_categorical('max_features', ['sqrt', 'log2']),
        'n_jobs': -1,
        'random_state': 42
    }

    # Measure training time
    start_time = time.time()

    model = RandomForestClassifier(**params)
    cv_scores = cross_val_score(
        model, X_train, y_train,
        cv=3,
        scoring='accuracy'
    )

    training_time = time.time() - start_time

    # Calculate metrics
    accuracy = cv_scores.mean()

    # Estimate resource cost
    # Factors: n_estimators (more trees = more compute)
    #          max_depth (deeper = more memory)
    #          training_time
    complexity = params['n_estimators'] * params['max_depth']
    normalized_complexity = min(complexity / 6000.0, 1.0)  # Normalize to 0-1
    normalized_time = min(training_time / 60.0, 1.0)  # Normalize to 0-1

    # Combined cost metric (0-1, lower is better)
    cost_metric = (normalized_complexity + normalized_time) / 2.0

    # Store user attributes
    trial.set_user_attr('training_time', training_time)
    trial.set_user_attr('complexity', complexity)
    trial.set_user_attr('cost_metric', cost_metric)

    # Combined score: maximize accuracy, minimize cost
    # Score = accuracy - (cost_weight * cost)
    combined_score = accuracy - (cost_weight * cost_metric)

    return combined_score


def main(args):
    # Set up MLflow
    mlflow.set_tracking_uri(os.environ.get('MLFLOW_TRACKING_URI', 'http://localhost:5000'))
    mlflow.set_experiment(args.experiment_name)

    # Load data
    print("Loading dataset...")
    data = load_breast_cancer()
    X_train, X_test, y_train, y_test = train_test_split(
        data.data, data.target,
        test_size=0.2,
        random_state=42
    )

    # Optuna storage
    storage_url = os.environ.get(
        'OPTUNA_STORAGE',
        'postgresql://postgres:postgres@postgres.ml-platform.svc.cluster.local:5432/optuna'
    )

    print(f"\n{'='*60}")
    print(f"Cost-Aware Hyperparameter Optimization")
    print(f"{'='*60}")
    print(f"Study: {args.study_name}")
    print(f"Cost weight: {args.cost_weight}")
    print(f"Budget constraint: {args.max_trials} trials, {args.time_budget}s max")
    print(f"{'='*60}\n")

    if args.multi_objective:
        # Multi-objective optimization (Pareto front)
        print("Using multi-objective optimization (accuracy vs cost)")

        study = optuna.create_study(
            study_name=args.study_name,
            storage=storage_url,
            load_if_exists=True,
            directions=['maximize', 'minimize'],  # Maximize accuracy, minimize cost
            sampler=optuna.samplers.NSGAIISampler(seed=42)
        )

        objective = CostAwareObjective(X_train, y_train, args.cost_weight)
        study.optimize(
            objective,
            n_trials=args.n_trials,
            timeout=args.time_budget if args.time_budget > 0 else None,
            show_progress_bar=True
        )

        # Analyze Pareto front
        print("\n=== Pareto Front (Best Trade-offs) ===")
        pareto_trials = [t for t in study.best_trials]
        for i, trial in enumerate(pareto_trials[:5]):  # Top 5
            print(f"\nOption {i+1}:")
            print(f"  Accuracy: {trial.values[0]:.4f}")
            print(f"  Cost: {trial.values[1]:.4f}")
            print(f"  Params: {trial.params}")

        # Select best trade-off (can use different criteria)
        best_trial = pareto_trials[0]  # First in Pareto front

    else:
        # Single-objective optimization (combined score)
        print(f"Using single-objective optimization (combined score)")

        study = optuna.create_study(
            study_name=args.study_name,
            storage=storage_url,
            load_if_exists=True,
            direction='maximize',
            sampler=optuna.samplers.TPESampler(seed=42)
        )

        study.optimize(
            lambda trial: single_objective_cost_aware(trial, X_train, y_train, args.cost_weight),
            n_trials=args.n_trials,
            timeout=args.time_budget if args.time_budget > 0 else None,
            show_progress_bar=True
        )

        best_trial = study.best_trial
        print(f"\nBest trial: {best_trial.number}")
        print(f"Combined score: {best_trial.value:.4f}")
        print(f"Training time: {best_trial.user_attrs['training_time']:.2f}s")
        print(f"Cost metric: {best_trial.user_attrs['cost_metric']:.4f}")

    # Train final model
    print("\n=== Training Final Model ===")
    with mlflow.start_run(run_name=f"{args.study_name}_cost_aware"):
        final_model = RandomForestClassifier(**best_trial.params)
        final_model.fit(X_train, y_train)

        test_accuracy = final_model.score(X_test, y_test)

        # Log to MLflow
        mlflow.log_params(best_trial.params)
        mlflow.log_params({
            'cost_weight': args.cost_weight,
            'optimization_type': 'multi_objective' if args.multi_objective else 'single_objective'
        })

        mlflow.log_metrics({
            'test_accuracy': test_accuracy,
            'training_time': best_trial.user_attrs.get('training_time', 0),
            'cost_metric': best_trial.user_attrs.get('cost_metric', 0),
            'n_trials': len(study.trials)
        })

        mlflow.sklearn.log_model(
            final_model,
            "model",
            registered_model_name=args.model_name
        )

        print(f"Test accuracy: {test_accuracy:.4f}")
        print(f"Model registered: {args.model_name}")

    # Cost analysis
    print("\n=== Cost Analysis ===")
    all_trials = study.trials
    total_time = sum(t.user_attrs.get('training_time', 0) for t in all_trials)
    avg_time = total_time / len(all_trials) if all_trials else 0

    print(f"Total trials: {len(all_trials)}")
    print(f"Total training time: {total_time:.2f}s ({total_time/60:.1f}m)")
    print(f"Average time per trial: {avg_time:.2f}s")
    print(f"Time saved vs exhaustive: ~{max(0, args.time_budget - total_time):.1f}s")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Cost-aware hyperparameter optimization')
    parser.add_argument('--study-name', default='cost-aware-optimization', help='Study name')
    parser.add_argument('--experiment-name', default='cost-aware-tuning', help='MLflow experiment')
    parser.add_argument('--model-name', default='cost-optimized-model', help='Model name')
    parser.add_argument('--n-trials', type=int, default=30, help='Number of trials')
    parser.add_argument('--cost-weight', type=float, default=0.3, help='Cost weight (0-1)')
    parser.add_argument('--time-budget', type=int, default=300, help='Max time budget (seconds, 0=unlimited)')
    parser.add_argument('--multi-objective', action='store_true', help='Use multi-objective optimization')

    args = parser.parse_args()
    main(args)
