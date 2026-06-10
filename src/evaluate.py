import os
from metrics_tracker import MetricsTracker


BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUTPUT_DIR = os.path.join(BASE_DIR, 'outputs')


def combined_report(stress_results, auth_results):
    """
    Generate a combined report of stress classification and authentication results.
    
    Prints a formatted summary showing:
    - Stress Classification: RF accuracy, XGBoost accuracy, winner
    - User Authentication: average accuracy, precision, recall
    - Overall project conclusion
    """
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    rf_model, xgb_model, X_test, y_test = stress_results
    auth_models, auth_metrics = auth_results
    
    # Calculate RF accuracy
    rf_pred = rf_model.predict(X_test)
    from sklearn.metrics import accuracy_score
    rf_accuracy = accuracy_score(y_test, rf_pred)
    
    # Calculate XGBoost accuracy
    xgb_pred = xgb_model.predict(X_test)
    xgb_accuracy = accuracy_score(y_test, xgb_pred)
    
    # Determine winner
    if rf_accuracy > xgb_accuracy:
        stress_winner = "Random Forest"
    else:
        stress_winner = "XGBoost"
    
    # Build report
    report = []
    report.append("="*70)
    report.append("KEYSTROKE DYNAMICS PROJECT - FINAL REPORT")
    report.append("="*70)
    report.append("")
    
    report.append("STRESS CLASSIFICATION RESULTS")
    report.append("-" * 70)
    report.append(f"Random Forest Accuracy:    {rf_accuracy:.4f}")
    report.append(f"XGBoost Accuracy:          {xgb_accuracy:.4f}")
    report.append(f"Best Model:                {stress_winner}")
    report.append("")
    
    report.append("USER AUTHENTICATION RESULTS")
    report.append("-" * 70)
    report.append(f"Average Accuracy:          {auth_metrics['avg_accuracy']:.4f}")
    report.append(f"Average Precision:         {auth_metrics['avg_precision']:.4f}")
    report.append(f"Average Recall:            {auth_metrics['avg_recall']:.4f}")
    report.append("")
    
    report.append("PROJECT CONCLUSION")
    report.append("-" * 70)
    conclusion = (
        f"This keystroke dynamics project successfully builds two models: "
        f"a {stress_winner} classifier achieving {max(rf_accuracy, xgb_accuracy):.1%} accuracy for stress detection, "
        f"and per-user Isolation Forest models achieving {auth_metrics['avg_accuracy']:.1%} average accuracy for user authentication. "
        f"Both models demonstrate the feasibility of using keystroke patterns for behavioral analysis and security applications."
    )
    report.append(conclusion)
    report.append("="*70)
    
    # Print report
    report_text = "\n".join(report)
    print("\n" + report_text)
    
    # Track metrics
    tracker = MetricsTracker(os.path.join(OUTPUT_DIR, 'training_metrics.json'))
    stress_metrics = {
        'rf_accuracy': rf_accuracy,
        'xgb_accuracy': xgb_accuracy,
        'best_model': stress_winner
    }
    tracker.add_training_run(stress_metrics, auth_metrics)
    print(f"Metrics saved to outputs/training_metrics.json")
