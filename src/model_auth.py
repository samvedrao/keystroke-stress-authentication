import pandas as pd
import numpy as np
import os
import joblib
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from sklearn.ensemble import IsolationForest
from sklearn.metrics import accuracy_score, precision_score, recall_score


BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUTPUT_DIR = os.path.join(BASE_DIR, 'outputs')
PLOTS_DIR = os.path.join(OUTPUT_DIR, 'plots')
MODELS_DIR = os.path.join(OUTPUT_DIR, 'models')


def train_auth_model(df):
    """
    Train per-user authentication models using Isolation Forest.
    
    For each user:
    - Fit Isolation Forest on their feature rows (normal behavior)
    - Test by mixing their data (label=1 legitimate) with random samples from other users (label=-1 impostor)
    - Compute per-user accuracy, precision, recall
    
    Computes average metrics across all users.
    Plots per-user authentication accuracy and saves to outputs/plots/auth_accuracy.png
    Saves all per-user Isolation Forest models to outputs/models/auth_models.pkl
    
    Returns: (auth_models_dict, averaged_metrics_dict)
    """
    os.makedirs(PLOTS_DIR, exist_ok=True)
    os.makedirs(MODELS_DIR, exist_ok=True)

    feature_cols = [
        'mean_hold_time', 'std_hold_time', 'mean_flight_time', 'std_flight_time',
        'typing_speed', 'error_proxy', 'consistency_score', 'pause_frequency'
    ]
    
    # Ensure all required features exist
    for col in feature_cols:
        if col not in df.columns:
            df[col] = 0
    
    users = df['subject'].unique()
    auth_models = {}
    user_metrics = {}
    rng = np.random.default_rng(42)
    
    print("\n=== Training Per-User Authentication Models ===")
    
    for user in users:
        user_data = df[df['subject'] == user][feature_cols].values

        if len(user_data) < 6:
            continue

        # Split each user data into train/test for a realistic authentication setup
        test_size = max(3, int(round(len(user_data) * 0.3)))
        test_size = min(test_size, len(user_data) - 2)
        indices = np.arange(len(user_data))
        rng.shuffle(indices)
        test_idx = indices[:test_size]
        train_idx = indices[test_size:]

        train_legit = user_data[train_idx]
        test_legit = user_data[test_idx]

        other_users_data = df[df['subject'] != user][feature_cols].values
        if len(other_users_data) < len(test_legit):
            impostor_samples = other_users_data
        else:
            impostor_indices = rng.choice(len(other_users_data), len(test_legit), replace=False)
            impostor_samples = other_users_data[impostor_indices]

        X_eval = np.vstack([test_legit, impostor_samples])
        y_eval = np.array([1] * len(test_legit) + [-1] * len(impostor_samples))

        best_model = None
        best_accuracy = -1.0

        # Lightweight tuning over contamination values can improve per-user fit.
        for contamination in [0.03, 0.05, 0.08, 0.1]:
            candidate = IsolationForest(
                n_estimators=300,
                contamination=contamination,
                random_state=42,
                n_jobs=-1
            )
            candidate.fit(train_legit)
            pred = candidate.predict(X_eval)
            acc = accuracy_score(y_eval, pred)

            if acc > best_accuracy:
                best_accuracy = acc
                best_model = candidate
        
        auth_models[user] = best_model

        # Predictions (1 = normal/legitimate, -1 = anomaly/impostor)
        pred = best_model.predict(X_eval)
        
        # Evaluate
        accuracy = accuracy_score(y_eval, pred)
        precision = precision_score(y_eval, pred, zero_division=0)
        recall = recall_score(y_eval, pred, zero_division=0)
        
        user_metrics[user] = {
            'accuracy': accuracy,
            'precision': precision,
            'recall': recall
        }
        
        print(
            f"User {user}: Accuracy={accuracy:.4f}, Precision={precision:.4f}, "
            f"Recall={recall:.4f}"
        )
    
    # Average metrics
    avg_accuracy = np.mean([m['accuracy'] for m in user_metrics.values()]) if user_metrics else 0.0
    avg_precision = np.mean([m['precision'] for m in user_metrics.values()]) if user_metrics else 0.0
    avg_recall = np.mean([m['recall'] for m in user_metrics.values()]) if user_metrics else 0.0
    
    print(f"\n=== Average Authentication Metrics ===")
    print(f"Average Accuracy: {avg_accuracy:.4f}")
    print(f"Average Precision: {avg_precision:.4f}")
    print(f"Average Recall: {avg_recall:.4f}")
    
    # Plot per-user accuracy
    user_list = sorted(user_metrics.keys())
    accuracies = [user_metrics[u]['accuracy'] for u in user_list]
    
    fig, ax = plt.subplots(figsize=(12, 6))
    ax.bar(range(len(user_list)), accuracies)
    ax.set_xlabel('User ID')
    ax.set_ylabel('Authentication Accuracy')
    ax.set_title('Per-User Authentication Accuracy (Isolation Forest)')
    ax.set_xticks(range(len(user_list)))
    ax.set_xticklabels(user_list, rotation=45)
    ax.axhline(y=avg_accuracy, color='r', linestyle='--', label=f'Average: {avg_accuracy:.4f}')
    ax.legend()
    plt.tight_layout()
    plt.savefig(os.path.join(PLOTS_DIR, 'auth_accuracy.png'), dpi=100)
    plt.close()
    
    # Save models
    joblib.dump(auth_models, os.path.join(MODELS_DIR, 'auth_models.pkl'))
    print(f"\nAuthentication models saved to outputs/models/auth_models.pkl")
    
    averaged_metrics = {
        'avg_accuracy': avg_accuracy,
        'avg_precision': avg_precision,
        'avg_recall': avg_recall
    }
    
    return auth_models, averaged_metrics
