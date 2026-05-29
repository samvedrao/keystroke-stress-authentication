import pandas as pd
import numpy as np


def extract_cmu_features(df):
    """
    Extract keystroke dynamics features from CMU dataset per user per session.
    
    Computes: mean_hold_time, std_hold_time, mean_flight_time, std_flight_time,
    mean_dd_time, typing_speed, error_proxy, consistency_score, and pause_frequency.
    
    Returns a dataframe with subject, sessionIndex, and all computed features.
    """
    features_list = []
    
    # Group by subject and sessionIndex
    grouped = df.groupby(['subject', 'sessionIndex'])
    
    for (subject, session), group in grouped:
        features_row = {'subject': subject, 'sessionIndex': session}
        
        # Extract hold time columns (H.xxx pattern)
        hold_cols = [col for col in group.columns if col.startswith('H.')]
        # Extract flight time columns (UD.xxx pattern)
        flight_cols = [col for col in group.columns if col.startswith('UD.')]
        # Extract down-down time columns (DD.xxx pattern)
        dd_cols = [col for col in group.columns if col.startswith('DD.')]
        
        # Compute hold time statistics
        hold_times = group[hold_cols].values.flatten()
        hold_times = hold_times[~np.isnan(hold_times)]
        features_row['mean_hold_time'] = np.mean(hold_times) if len(hold_times) > 0 else 0
        features_row['std_hold_time'] = np.std(hold_times) if len(hold_times) > 0 else 0
        
        # Compute flight time statistics
        flight_times = group[flight_cols].values.flatten()
        flight_times = flight_times[~np.isnan(flight_times)]
        features_row['mean_flight_time'] = np.mean(flight_times) if len(flight_times) > 0 else 0
        features_row['std_flight_time'] = np.std(flight_times) if len(flight_times) > 0 else 0
        
        # Compute down-down time statistics
        dd_times = group[dd_cols].values.flatten()
        dd_times = dd_times[~np.isnan(dd_times)]
        features_row['mean_dd_time'] = np.mean(dd_times) if len(dd_times) > 0 else 0
        
        # Typing speed: total keys divided by total time (approximate as 1 / mean DD time)
        mean_dd = features_row['mean_dd_time']
        features_row['typing_speed'] = (1.0 / mean_dd) if mean_dd > 0 else 0
        
        # Error proxy: coefficient of variation of hold times
        if features_row['mean_hold_time'] > 0:
            features_row['error_proxy'] = features_row['std_hold_time'] / features_row['mean_hold_time']
        else:
            features_row['error_proxy'] = 0
        
        # Consistency score: 1 minus coefficient of variation (capped 0-1)
        features_row['consistency_score'] = max(0, min(1, 1 - features_row['error_proxy']))
        
        # Pause frequency: number of hold times above 1.5x the mean
        threshold = 1.5 * features_row['mean_hold_time']
        pause_count = np.sum(hold_times > threshold) if len(hold_times) > 0 else 0
        features_row['pause_frequency'] = pause_count
        
        features_list.append(features_row)
    
    return pd.DataFrame(features_list)


def extract_freetext_features(df):
    """
    Extract keystroke dynamics features from free-text dataset per user per input_type.
    
    Computes the same features as CMU extraction using hold_time and flight_time columns.
    Groups by user ID and input_type.
    
    Returns a dataframe with user_id, input_type, and all computed features.
    """
    features_list = []
    
    # Determine the user ID column name (could be 'user_id', 'userId', etc.)
    user_col = None
    for col in df.columns:
        if 'user' in col.lower() and 'id' in col.lower():
            user_col = col
            break
    
    if user_col is None:
        # Try first column as user identifier
        user_col = df.columns[0]
    
    # Group by user and input_type
    grouped = df.groupby([user_col, 'input_type'])
    
    for (user_id, input_type), group in grouped:
        features_row = {'user_id': user_id, 'input_type': input_type}
        
        # Extract hold time and flight time columns
        hold_cols = [col for col in group.columns if 'hold' in col.lower()]
        flight_cols = [col for col in group.columns if 'flight' in col.lower()]
        
        # Compute hold time statistics
        if hold_cols:
            hold_times = group[hold_cols].values.flatten()
            hold_times = hold_times[~np.isnan(hold_times)]
            features_row['mean_hold_time'] = np.mean(hold_times) if len(hold_times) > 0 else 0
            features_row['std_hold_time'] = np.std(hold_times) if len(hold_times) > 0 else 0
        else:
            features_row['mean_hold_time'] = 0
            features_row['std_hold_time'] = 0
        
        # Compute flight time statistics
        if flight_cols:
            flight_times = group[flight_cols].values.flatten()
            flight_times = flight_times[~np.isnan(flight_times)]
            features_row['mean_flight_time'] = np.mean(flight_times) if len(flight_times) > 0 else 0
            features_row['std_flight_time'] = np.std(flight_times) if len(flight_times) > 0 else 0
        else:
            features_row['mean_flight_time'] = 0
            features_row['std_flight_time'] = 0
        
        # For free-text, we approximate mean_dd_time using flight_time
        features_row['mean_dd_time'] = features_row['mean_flight_time'] if features_row['mean_flight_time'] > 0 else 0.1
        
        # Typing speed
        mean_dd = features_row['mean_dd_time']
        features_row['typing_speed'] = (1.0 / mean_dd) if mean_dd > 0 else 0
        
        # Error proxy
        if features_row['mean_hold_time'] > 0:
            features_row['error_proxy'] = features_row['std_hold_time'] / features_row['mean_hold_time']
        else:
            features_row['error_proxy'] = 0
        
        # Consistency score
        features_row['consistency_score'] = max(0, min(1, 1 - features_row['error_proxy']))
        
        # Pause frequency (count of hold times > 1.5x mean)
        if hold_cols:
            hold_times = group[hold_cols].values.flatten()
            hold_times = hold_times[~np.isnan(hold_times)]
            threshold = 1.5 * features_row['mean_hold_time']
            pause_count = np.sum(hold_times > threshold) if len(hold_times) > 0 else 0
            features_row['pause_frequency'] = pause_count
        else:
            features_row['pause_frequency'] = 0
        
        features_list.append(features_row)
    
    return pd.DataFrame(features_list)
