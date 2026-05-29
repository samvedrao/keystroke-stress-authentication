import pandas as pd
import numpy as np
from sklearn.preprocessing import MinMaxScaler


def generate_stress_labels(features_df):
    """
    Generate stress labels for the features dataframe using a composite stress score.
    
    Computes stress_score using:
    - normalized std_hold_time (weight 0.3)
    - normalized std_flight_time (weight 0.3)
    - normalized error_proxy (weight 0.25)
    - (1 - normalized typing_speed) (weight 0.15)
    
    Labels: 1 = High Stress (score >= 0.5), 0 = Low Stress (score < 0.5)
    Adds stress_label column and prints class distribution.
    
    Returns the labeled dataframe.
    """
    df = features_df.copy()
    
    # Initialize stress components
    scaler = MinMaxScaler()
    
    # Normalize components
    df['norm_std_hold_time'] = scaler.fit_transform(df[['std_hold_time']])
    df['norm_std_flight_time'] = scaler.fit_transform(df[['std_flight_time']])
    df['norm_error_proxy'] = scaler.fit_transform(df[['error_proxy']])
    df['norm_typing_speed'] = scaler.fit_transform(df[['typing_speed']])
    
    # Compute stress score
    df['stress_score'] = (
        df['norm_std_hold_time'] * 0.3 +
        df['norm_std_flight_time'] * 0.3 +
        df['norm_error_proxy'] * 0.25 +
        (1 - df['norm_typing_speed']) * 0.15
    )
    
    # Label: 1 = High Stress, 0 = Low Stress
    df['stress_label'] = (df['stress_score'] >= 0.5).astype(int)
    
    # Print class distribution
    print("\nStress Label Distribution:")
    print(df['stress_label'].value_counts())
    print(f"Low Stress (0): {(df['stress_label'] == 0).sum()}")
    print(f"High Stress (1): {(df['stress_label'] == 1).sum()}")
    
    return df
