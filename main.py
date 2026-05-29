"""
Keystroke Dynamics Pipeline
Dual-task project for stress level classification and user authentication
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from load_data import load_cmu, load_freetext
from features import extract_cmu_features, extract_freetext_features
from stress_labels import generate_stress_labels
from model_stress import train_stress_model
from model_auth import train_auth_model
from evaluate import combined_report


def main():
    """
    Execute the complete keystroke dynamics pipeline:
    1. Load CMU and free-text datasets
    2. Extract features from both
    3. Generate stress labels
    4. Train stress classification models
    5. Train per-user authentication models
    6. Generate combined report
    """
    try:
        # Step 1: Load data
        print("Step 1: Loading data...")
        cmu_df = load_cmu()
        freetext_df = load_freetext()
        print(f"✓ CMU dataset: {len(cmu_df)} rows")
        print(f"✓ Free-text dataset: {len(freetext_df)} rows")
        
        # Step 2: Extract features
        print("\nStep 2: Extracting features...")
        cmu_features = extract_cmu_features(cmu_df)
        freetext_features = extract_freetext_features(freetext_df)
        print(f"✓ CMU features: {len(cmu_features)} rows, {len(cmu_features.columns)} columns")
        print(f"✓ Free-text features: {len(freetext_features)} rows, {len(freetext_features.columns)} columns")
        
        # Step 3: Generate stress labels (using CMU data)
        print("\nStep 3: Generating stress labels...")
        labeled_df = generate_stress_labels(cmu_features)
        print(f"✓ Stress labels generated for {len(labeled_df)} samples")
        
        # Step 4: Train stress classification models
        print("\nStep 4: Training stress classification models...")
        stress_results = train_stress_model(labeled_df)
        print(f"✓ Stress models trained and saved")
        
        # Step 5: Train authentication models
        print("\nStep 5: Training user authentication models...")
        auth_results = train_auth_model(labeled_df)
        print(f"✓ Authentication models trained and saved")
        
        # Step 6: Generate combined report
        print("\nStep 6: Generating combined report...")
        combined_report(stress_results, auth_results)
        print(f"✓ Report generated")
        
        print("\n" + "="*70)
        print("Pipeline complete. Check outputs/ folder for results.")
        print("="*70)
        
    except Exception as e:
        print(f"\n✗ Error: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
