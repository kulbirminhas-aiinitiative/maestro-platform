#!/usr/bin/env python3
"""
Multi-Objective Hyperparameter Optimization
Optimize for multiple metrics simultaneously (accuracy, F1, precision, recall)
"""

import argparse
import optuna
import mlflow
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import cross_val_score
from sklearn.metrics import f1_score, precision_score, recall_score
from sklearn.datasets import load_breast_cancer
from sklearn.model_selection import train_test_split, cross_validate
import os


def multi_objective(trial, X_train, y_train):
    """
    Multi-objective optimization: maximize accuracy and F1 score

    Returns:
        tuple: (accuracy, f1_score)
    """
    # Hyperparameters
    params = {
        'n_estimators': trial.suggest_int('n_estimators', 50, 200),
        'max_depth': trial.suggest_int('max_depth', 5, 30),
        'min_samples_split': trial.suggest_int('min_samples_split', 2, 20),
        'min_samples_leaf': trial.suggest_int('min_samples_leaf', 1, 10),
        'max_features': trial.suggest_categorical('max_features', ['sqrt', 'log2']),
        'class_weight': trial.suggest_categorical('class_weight', ['balanced', None]),
        'random_state': 42
    }

    # Cross-validation with multiple metrics
    model = RandomForestClassifier(**params)

    scoring = {
        'accuracy': 'accuracy',
        'f1_weighted': 'f1_weighted',
        'precision_weighted': 'precision_weighted',
        'recall_weighted': 'recall_weighted'
    }

    cv_results = cross_validate(
        model, X_train, y_train,
        cv=5,
        scoring=scoring,
        n_jobs=-1
    )

    # Calculate mean scores
    accuracy = cv_results['test_accuracy'].mean()
    f1 = cv_results['test_f1_weighted'].mean()
    precision = cv_results['test_precision_weighted'].mean()
    recall = cv_results['test_recall_weighted'].mean()

    # Store additional metrics as user attributes
    trial.set_user_attr('precision', precision)
    trial.set_user_attr('recall', recall)
    trial.set_user_attr('f1', f1)

    # Return objectives (all to maximize)
    return accuracy, f1


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

    print(f"\n{'='*70}")
    print(f"Multi-Objective Hyperparameter Optimization")
    print(f"{'='*70}")
    print(f"Objectives: Accuracy, F1 Score")
    print(f"Study: {args.study_name}")
    print(f"Trials: {args.n_trials}")
    print(f"{'='*70}\n")

    # Create multi-objective study
    study = optuna.create_study(
        study_name=args.study_name,
        storage=storage_url,
        load_if_exists=True,
        directions=['maximize', 'maximize'],  # Maximize both accuracy and F1
        sampler=optuna.samplers.NSGAIISampler(  # Non-dominated Sorting GA-II
            population_size=20,
            seed=42
        )
    )

    # Run optimization
    print("Starting multi-objective optimization...")
    study.optimize(
        lambda trial: multi_objective(trial, X_train, y_train),
        n_trials=args.n_trials,
        show_progress_bar=True
    )

    # Analyze Pareto front
    print("\n=== Pareto Front Analysis ===")
    print(f"Total trials: {len(study.trials)}")
    print(f"Pareto optimal solutions: {len(study.best_trials)}\n")

    pareto_trials = study.best_trials

    # Sort by accuracy for display
    pareto_trials_sorted = sorted(pareto_trials, key=lambda t: t.values[0], reverse=True)

    print("Top Pareto-optimal trade-offs:\n")
    print(f"{'#':<4} {'Accuracy':<12} {'F1 Score':<12} {'Precision':<12} {'Recall':<12}")
    print("-" * 52)

    for i, trial in enumerate(pareto_trials_sorted[:10]):  # Top 10
        precision = trial.user_attrs.get('precision', 0)
        recall = trial.user_attrs.get('recall', 0)
        print(f"{i+1:<4} {trial.values[0]:<12.4f} {trial.values[1]:<12.4f} "
              f"{precision:<12.4f} {recall:<12.4f}")

    # Different selection strategies
    print("\n=== Model Selection Strategies ===\n")

    # Strategy 1: Highest accuracy
    best_accuracy_trial = max(pareto_trials, key=lambda t: t.values[0])
    print(f"1. Highest Accuracy Model:")
    print(f"   Accuracy: {best_accuracy_trial.values[0]:.4f}")
    print(f"   F1 Score: {best_accuracy_trial.values[1]:.4f}")
    print(f"   Params: {best_accuracy_trial.params}\n")

    # Strategy 2: Highest F1
    best_f1_trial = max(pareto_trials, key=lambda t: t.values[1])
    print(f"2. Highest F1 Score Model:")
    print(f"   Accuracy: {best_f1_trial.values[0]:.4f}")
    print(f"   F1 Score: {best_f1_trial.values[1]:.4f}")
    print(f"   Params: {best_f1_trial.params}\n")

    # Strategy 3: Best balanced (minimize distance to ideal point)
    ideal_point = (1.0, 1.0)  # Perfect accuracy and F1
    distances = [
        ((t.values[0] - ideal_point[0])**2 + (t.values[1] - ideal_point[1])**2)**0.5
        for t in pareto_trials
    ]
    best_balanced_idx = distances.index(min(distances))
    best_balanced_trial = pareto_trials[best_balanced_idx]
    print(f"3. Best Balanced Model (closest to ideal):")
    print(f"   Accuracy: {best_balanced_trial.values[0]:.4f}")
    print(f"   F1 Score: {best_balanced_trial.values[1]:.4f}")
    print(f"   Params: {best_balanced_trial.params}\n")

    # Select best trial based on strategy
    if args.selection_strategy == 'accuracy':
        selected_trial = best_accuracy_trial
    elif args.selection_strategy == 'f1':
        selected_trial = best_f1_trial
    else:  # balanced
        selected_trial = best_balanced_trial

    print(f"Selected strategy: {args.selection_strategy}")
    print(f"Selected trial: {selected_trial.number}")

    # Train final model with selected hyperparameters
    print("\n=== Training Final Model ===")

    with mlflow.start_run(run_name=f"{args.study_name}_{args.selection_strategy}"):
        final_model = RandomForestClassifier(**selected_trial.params)
        final_model.fit(X_train, y_train)

        # Test set evaluation
        y_pred = final_model.predict(X_test)
        test_accuracy = final_model.score(X_test, y_test)
        test_f1 = f1_score(y_test, y_pred, average='weighted')
        test_precision = precision_score(y_test, y_pred, average='weighted')
        test_recall = recall_score(y_test, y_pred, average='weighted')

        # Log to MLflow
        mlflow.log_params(selected_trial.params)
        mlflow.log_params({
            'selection_strategy': args.selection_strategy,
            'pareto_optimal_count': len(pareto_trials)
        })

        mlflow.log_metrics({
            'cv_accuracy': selected_trial.values[0],
            'cv_f1': selected_trial.values[1],
            'test_accuracy': test_accuracy,
            'test_f1': test_f1,
            'test_precision': test_precision,
            'test_recall': test_recall,
            'n_trials': len(study.trials)
        })

        # Log model
        mlflow.sklearn.log_model(
            final_model,
            "model",
            registered_model_name=args.model_name
        )

        print(f"\nTest Set Results:")
        print(f"  Accuracy:  {test_accuracy:.4f}")
        print(f"  F1 Score:  {test_f1:.4f}")
        print(f"  Precision: {test_precision:.4f}")
        print(f"  Recall:    {test_recall:.4f}")
        print(f"\nModel registered: {args.model_name}")

    # Visualization suggestion
    print("\n=== Visualization ===")
    print("To visualize the Pareto front, use:")
    print(f"  optuna.visualization.plot_pareto_front(study)")
    print(f"  optuna.visualization.plot_hyperparameter_importances(study)")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Multi-objective hyperparameter optimization')
    parser.add_argument('--study-name', default='multi-objective-optimization', help='Study name')
    parser.add_argument('--experiment-name', default='multi-objective-tuning', help='MLflow experiment')
    parser.add_argument('--model-name', default='multi-objective-model', help='Model name')
    parser.add_argument('--n-trials', type=int, default=50, help='Number of trials')
    parser.add_argument('--selection-strategy', choices=['accuracy', 'f1', 'balanced'],
                        default='balanced', help='Model selection strategy from Pareto front')

    args = parser.parse_args()
    main(args)
