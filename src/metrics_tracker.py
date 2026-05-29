import json
import os
from datetime import datetime


class MetricsTracker:
    """Track and persist training metrics over time."""
    
    def __init__(self, metrics_file='outputs/training_metrics.json'):
        if os.path.isabs(metrics_file):
            self.metrics_file = metrics_file
        else:
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            self.metrics_file = os.path.join(base_dir, metrics_file)
        os.makedirs(os.path.dirname(self.metrics_file), exist_ok=True)
        self.metrics = self.load_metrics()
    
    def load_metrics(self):
        """Load metrics from file."""
        if os.path.exists(self.metrics_file):
            with open(self.metrics_file, 'r') as f:
                return json.load(f)
        return []
    
    def save_metrics(self):
        """Save metrics to file."""
        with open(self.metrics_file, 'w') as f:
            json.dump(self.metrics, f, indent=2)
    
    def add_training_run(self, stress_metrics, auth_metrics):
        """
        Add a training run record.
        
        stress_metrics: dict with 'rf_accuracy' and 'xgb_accuracy'
        auth_metrics: dict with 'avg_accuracy', 'avg_precision', 'avg_recall'
        """
        run = {
            'timestamp': datetime.now().isoformat(),
            'stress_classification': {
                'random_forest_accuracy': stress_metrics.get('rf_accuracy', 0),
                'xgboost_accuracy': stress_metrics.get('xgb_accuracy', 0),
                'best_model': stress_metrics.get('best_model', 'Unknown')
            },
            'user_authentication': {
                'avg_accuracy': auth_metrics.get('avg_accuracy', 0),
                'avg_precision': auth_metrics.get('avg_precision', 0),
                'avg_recall': auth_metrics.get('avg_recall', 0)
            }
        }
        self.metrics.append(run)
        self.save_metrics()
        return run
    
    def get_latest_metrics(self):
        """Get the most recent training metrics."""
        return self.metrics[-1] if self.metrics else None
    
    def get_all_metrics(self):
        """Get all training metrics."""
        return self.metrics
    
    def get_summary_stats(self):
        """Get summary statistics across all runs."""
        if not self.metrics:
            return {}
        
        stress_rf = [m['stress_classification']['random_forest_accuracy'] for m in self.metrics]
        stress_xgb = [m['stress_classification']['xgboost_accuracy'] for m in self.metrics]
        auth_acc = [m['user_authentication']['avg_accuracy'] for m in self.metrics]
        
        return {
            'total_runs': len(self.metrics),
            'avg_rf_accuracy': sum(stress_rf) / len(stress_rf) if stress_rf else 0,
            'avg_xgb_accuracy': sum(stress_xgb) / len(stress_xgb) if stress_xgb else 0,
            'avg_auth_accuracy': sum(auth_acc) / len(auth_acc) if auth_acc else 0,
            'best_rf_accuracy': max(stress_rf) if stress_rf else 0,
            'best_xgb_accuracy': max(stress_xgb) if stress_xgb else 0,
            'best_auth_accuracy': max(auth_acc) if auth_acc else 0
        }
