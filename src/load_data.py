import pandas as pd
import os


BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, 'data')


def load_cmu():
    """
    Load CMU DSL-StrongPasswordData.csv
    
    Returns a cleaned dataframe with subject column preserved.
    The file has columns: subject, sessionIndex, rep, and 34 timing columns
    (H.xxx for hold time, DD.xxx for down-down, UD.xxx for up-down).
    """
    filepath = os.path.join(DATA_DIR, 'DSL-StrongPasswordData.csv')
    df = pd.read_csv(filepath)
    
    # Handle missing values
    df = df.fillna(df.mean(numeric_only=True))
    
    return df


def load_freetext():
    """
    Load free-text keystroke data from email, fullname, and phone datasets.
    
    Each file contains keystroke timing data with columns for user ID, 
    hold_time, and flight_time. Concatenates all three into one dataframe
    and adds an input_type column ('email', 'fullname', 'phone').
    
    Returns the combined dataframe.
    """
    email_path = os.path.join(DATA_DIR, 'email_userInformation.csv')
    fullname_path = os.path.join(DATA_DIR, 'fullname_userInformation.csv')
    phone_path = os.path.join(DATA_DIR, 'phone_userInformation.csv')
    
    dfs = []
    
    # Load each file if it exists
    for filepath, input_type in [(email_path, 'email'), 
                                  (fullname_path, 'fullname'), 
                                  (phone_path, 'phone')]:
        if os.path.exists(filepath):
            df = pd.read_csv(filepath)
            df['input_type'] = input_type
            dfs.append(df)
    
    # Concatenate all dataframes
    if dfs:
        combined_df = pd.concat(dfs, ignore_index=True)
        # Handle missing values
        combined_df = combined_df.fillna(combined_df.mean(numeric_only=True))
        return combined_df
    else:
        # Return empty dataframe if no files found
        return pd.DataFrame()
