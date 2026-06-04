"""
Train calibrated stress classifiers for confidence values.

Run from the project root:
    .venv\\Scripts\\python.exe scripts\\train_calibrated_models.py
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(__file__)), 'src'))

import joblib
from sklearn.calibration import CalibratedClassifierCV
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from xgboost import XGBClassifier

from load_data import load_cmu
from features import extract_cmu_features
from stress_labels import generate_stress_labels


BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODELS_DIR = os.path.join(BASE_DIR, 'outputs', 'models')


def main():
    os.makedirs(MODELS_DIR, exist_ok=True)
    feature_cols = [
        'mean_hold_time', 'std_hold_time', 'mean_flight_time', 'std_flight_time',
        'typing_speed', 'error_proxy', 'consistency_score', 'pause_frequency'
    ]

    cmu_df = load_cmu()
    features_df = extract_cmu_features(cmu_df)
    labeled_df = generate_stress_labels(features_df)

    X = labeled_df[feature_cols]
    y = labeled_df['stress_label']
    X_train, X_cal, y_train, y_cal = train_test_split(
        X, y, test_size=0.25, stratify=y, random_state=42
    )

    rf = RandomForestClassifier(
        n_estimators=200,
        max_depth=15,
        min_samples_split=5,
        min_samples_leaf=2,
        random_state=42,
        n_jobs=-1,
        class_weight='balanced'
    )
    rf.fit(X_train, y_train)
    rf_calibrated = CalibratedClassifierCV(rf, method='sigmoid', cv='prefit')
    rf_calibrated.fit(X_cal, y_cal)

    xgb = XGBClassifier(
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
    xgb.fit(X_train, y_train)
    xgb_calibrated = CalibratedClassifierCV(xgb, method='sigmoid', cv='prefit')
    xgb_calibrated.fit(X_cal, y_cal)

    joblib.dump(rf_calibrated, os.path.join(MODELS_DIR, 'stress_random_forest_calibrated.pkl'))
    joblib.dump(xgb_calibrated, os.path.join(MODELS_DIR, 'stress_xgboost_calibrated.pkl'))
    print('Saved calibrated models to outputs/models/')


if __name__ == '__main__':
    main()
