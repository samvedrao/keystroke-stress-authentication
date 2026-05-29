import pandas as pd
import numpy as np
import os
import joblib
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix
from xgboost import XGBClassifier


BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUTPUT_DIR = os.path.join(BASE_DIR, 'outputs')
PLOTS_DIR = os.path.join(OUTPUT_DIR, 'plots')
MODELS_DIR = os.path.join(OUTPUT_DIR, 'models')


def train_stress_model(df):
    """
    Train stress classification models (Random Forest and XGBoost) with optimized hyperparameters.
    
    Uses features: mean_hold_time, std_hold_time, mean_flight_time, std_flight_time,
    typing_speed, error_proxy, consistency_score, pause_frequency
    
    Target: stress_label
    
    Splits data 80/20 with stratification (random_state=42).
    Optimized hyperparameters for consistency between models.
    Prints accuracy, classification report, and confusion matrix for both models.
    Saves confusion matrix plot to outputs/plots/stress_confusion_matrix.png
    Saves feature importance plot to outputs/plots/stress_feature_importance.png
    Saves both models to outputs/models/
    
    Returns: (rf_model, xgb_model, X_test, y_test)
    """
    os.makedirs(PLOTS_DIR, exist_ok=True)
    os.makedirs(MODELS_DIR, exist_ok=True)

    # Feature selection
    feature_cols = [
        'mean_hold_time', 'std_hold_time', 'mean_flight_time', 'std_flight_time',
        'typing_speed', 'error_proxy', 'consistency_score', 'pause_frequency'
    ]
    
    X = df[feature_cols]
    y = df['stress_label']
    
    # Split data
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, stratify=y, random_state=42
    )
    
    # Train Random Forest with optimized hyperparameters
    print("\n=== Training Random Forest (Optimized) ===")
    rf_model = RandomForestClassifier(
        n_estimators=200,
        max_depth=15,
        min_samples_split=5,
        min_samples_leaf=2,
        random_state=42,
        n_jobs=-1,
        class_weight='balanced'
    )
    rf_model.fit(X_train, y_train)
    
    rf_pred = rf_model.predict(X_test)
    rf_acc = accuracy_score(y_test, rf_pred)
    print(f"Random Forest Accuracy: {rf_acc:.4f}")
    print("\nRandom Forest Classification Report:")
    print(classification_report(y_test, rf_pred))
    print("\nRandom Forest Confusion Matrix:")
    print(confusion_matrix(y_test, rf_pred))
    
    # Train XGBoost with optimized hyperparameters
    print("\n=== Training XGBoost (Optimized) ===")
    xgb_model = XGBClassifier(
        n_estimators=200,
        learning_rate=0.05,
        max_depth=7,
        min_child_weight=1,
        subsample=0.8,
        colsample_bytree=0.8,
        random_state=42,
        eval_metric='logloss',
        tree_method='hist',
        scale_pos_weight=1
    )
    xgb_model.fit(X_train, y_train)
    
    xgb_pred = xgb_model.predict(X_test)
    xgb_acc = accuracy_score(y_test, xgb_pred)
    print(f"XGBoost Accuracy: {xgb_acc:.4f}")
    print("\nXGBoost Classification Report:")
    print(classification_report(y_test, xgb_pred))
    print("\nXGBoost Confusion Matrix:")
    print(confusion_matrix(y_test, xgb_pred))
    
    # Plot confusion matrices side-by-side
    fig, axes = plt.subplots(1, 2, figsize=(12, 4))
    
    rf_cm = confusion_matrix(y_test, rf_pred)
    sns.heatmap(rf_cm, annot=True, fmt='d', cmap='Blues', ax=axes[0])
    axes[0].set_title('Random Forest Confusion Matrix')
    axes[0].set_ylabel('True Label')
    axes[0].set_xlabel('Predicted Label')
    
    xgb_cm = confusion_matrix(y_test, xgb_pred)
    sns.heatmap(xgb_cm, annot=True, fmt='d', cmap='Greens', ax=axes[1])
    axes[1].set_title('XGBoost Confusion Matrix')
    axes[1].set_ylabel('True Label')
    axes[1].set_xlabel('Predicted Label')
    
    plt.tight_layout()
    plt.savefig(os.path.join(PLOTS_DIR, 'stress_confusion_matrix.png'), dpi=100)
    plt.close()
    
    # Plot XGBoost feature importance
    fig, ax = plt.subplots(figsize=(10, 6))
    feature_importance = xgb_model.feature_importances_
    sorted_idx = np.argsort(feature_importance)
    
    plt.barh(range(len(sorted_idx)), feature_importance[sorted_idx])
    plt.yticks(range(len(sorted_idx)), [feature_cols[i] for i in sorted_idx])
    plt.xlabel('Feature Importance')
    plt.title('XGBoost Feature Importance for Stress Classification')
    plt.tight_layout()
    plt.savefig(os.path.join(PLOTS_DIR, 'stress_feature_importance.png'), dpi=100)
    plt.close()
    
    # Save models
    joblib.dump(rf_model, os.path.join(MODELS_DIR, 'stress_random_forest.pkl'))
    joblib.dump(xgb_model, os.path.join(MODELS_DIR, 'stress_xgboost.pkl'))
    
    print(f"\nModels saved to outputs/models/")
    
    return rf_model, xgb_model, X_test, y_test
