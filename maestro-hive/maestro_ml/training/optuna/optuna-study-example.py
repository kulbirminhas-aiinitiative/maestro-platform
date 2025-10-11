#!/usr/bin/env python3
"""
Optuna Hyperparameter Tuning Example with MLflow Integration
Demonstrates Bayesian optimization with distributed trials
"""

import argparse
import optuna
from optuna.integration.mlflow import MLflowCallback
import mlflow
import mlflow.sklearn
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import cross_val_score
from sklearn.datasets import load_breast_cancer
from sklearn.model_selection import train_test_split
import os
import joblib


def objective(trial, X_train, y_train):
    """
    Objective function for Optuna optimization

    Args:
        trial: Optuna trial object
        X_train: Training features
        y_train: Training labels

    Returns:
        float: Validation accuracy (to maximize)
    """
    # Define hyperparameter search space
    params = {
        'n_estimators': trial.suggest_int('n_estimators', 50, 200),
        'max_depth': trial.suggest_int('max_depth', 5, 30),
        'min_samples_split': trial.suggest_int('min_samples_split', 2, 20),
        'min_samples_leaf': trial.suggest_int('min_samples_leaf', 1, 10),
        'max_features': trial.suggest_categorical('max_features', ['sqrt', 'log2']),
        'bootstrap': trial.suggest_categorical('bootstrap', [True, False]),
        'random_state': 42
    }

    # Train model with suggested hyperparameters
    model = RandomForestClassifier(**params)

    # Use cross-validation for robust evaluation
    cv_scores = cross_val_score(
        model, X_train, y_train,
        cv=5,
        scoring='accuracy',
        n_jobs=-1
    )

    accuracy = cv_scores.mean()

    # Log intermediate values for visualization
    trial.set_user_attr('cv_std', cv_scores.std())

    return accuracy


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

    # Create Optuna study with PostgreSQL storage (distributed)
    storage_url = os.environ.get(
        'OPTUNA_STORAGE',
        'postgresql://postgres:postgres@postgres.ml-platform.svc.cluster.local:5432/optuna'
    )

    print(f"Creating Optuna study: {args.study_name}")
    print(f"Storage: {storage_url}")

    study = optuna.create_study(
        study_name=args.study_name,
        storage=storage_url,
        load_if_exists=True,
        direction='maximize',  # Maximize accuracy
        sampler=optuna.samplers.TPESampler(seed=42),  # Bayesian optimization
        pruner=optuna.pruners.MedianPruner(  # Early stopping
            n_startup_trials=5,
            n_warmup_steps=3,
            interval_steps=1
        )
    )

    # MLflow callback for automatic logging
    mlflc = MLflowCallback(
        tracking_uri=mlflow.get_tracking_uri(),
        metric_name='accuracy',
        create_experiment=False,
        mlflow_kwargs={
            'experiment_id': mlflow.get_experiment_by_name(args.experiment_name).experiment_id,
            'nested': True
        }
    )

    # Run optimization
    print(f"Starting optimization with {args.n_trials} trials...")
    print(f"Parallel jobs: {args.n_jobs}")

    study.optimize(
        lambda trial: objective(trial, X_train, y_train),
        n_trials=args.n_trials,
        n_jobs=args.n_jobs,
        callbacks=[mlflc],
        show_progress_bar=True
    )

    # Best trial results
    best_trial = study.best_trial
    print(f"\nBest trial: {best_trial.number}")
    print(f"Best accuracy: {best_trial.value:.4f}")
    print(f"Best hyperparameters: {best_trial.params}")

    # Train final model with best hyperparameters
    print("\nTraining final model with best hyperparameters...")

    with mlflow.start_run(run_name=f"{args.study_name}_best_model"):
        best_model = RandomForestClassifier(**best_trial.params)
        best_model.fit(X_train, y_train)

        # Evaluate on test set
        test_accuracy = best_model.score(X_test, y_test)

        # Log to MLflow
        mlflow.log_params(best_trial.params)
        mlflow.log_metrics({
            'cv_accuracy': best_trial.value,
            'test_accuracy': test_accuracy,
            'n_trials': len(study.trials)
        })

        # Log model
        mlflow.sklearn.log_model(
            best_model,
            "model",
            registered_model_name=args.model_name
        )

        # Save Optuna study for analysis
        study_path = f"/tmp/{args.study_name}.pkl"
        joblib.dump(study, study_path)
        mlflow.log_artifact(study_path, "optuna_study")

        print(f"\nFinal test accuracy: {test_accuracy:.4f}")
        print(f"Model registered as: {args.model_name}")

    # Print optimization history
    print("\n=== Optimization History ===")
    print(f"Total trials: {len(study.trials)}")
    print(f"Completed trials: {len([t for t in study.trials if t.state == optuna.trial.TrialState.COMPLETE])}")
    print(f"Pruned trials: {len([t for t in study.trials if t.state == optuna.trial.TrialState.PRUNED])}")
    print(f"Failed trials: {len([t for t in study.trials if t.state == optuna.trial.TrialState.FAIL])}")

    # Print importance
    print("\n=== Hyperparameter Importance ===")
    importance = optuna.importance.get_param_importances(study)
    for param, imp in importance.items():
        print(f"{param}: {imp:.4f}")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Optuna hyperparameter tuning with MLflow')
    parser.add_argument('--study-name', default='rf-optimization', help='Optuna study name')
    parser.add_argument('--experiment-name', default='hyperparameter-tuning', help='MLflow experiment')
    parser.add_argument('--model-name', default='optimized-rf-model', help='Model name for registry')
    parser.add_argument('--n-trials', type=int, default=50, help='Number of trials')
    parser.add_argument('--n-jobs', type=int, default=1, help='Parallel trials (-1 for all CPUs)')

    args = parser.parse_args()
    main(args)
