"""
Flask web application for Keystroke Dynamics Dashboard
"""

import os
import sys
import json
import joblib
from flask import Flask, render_template, jsonify, request, send_file
from datetime import datetime
import numpy as np

from src.metrics_tracker import MetricsTracker
from src.load_data import load_cmu
from src.features import extract_cmu_features

app = Flask(__name__, template_folder='templates', static_folder='static')
app.config['JSON_SORT_KEYS'] = False

# Initialize metrics tracker
tracker = MetricsTracker()

# Get base directory
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Load trained models
def load_models():
    """Load all trained models."""
    try:
        rf_path = os.path.join(BASE_DIR, 'outputs', 'models', 'stress_random_forest.pkl')
        xgb_path = os.path.join(BASE_DIR, 'outputs', 'models', 'stress_xgboost.pkl')
        auth_path = os.path.join(BASE_DIR, 'outputs', 'models', 'auth_models.pkl')
        
        stress_rf = joblib.load(rf_path) if os.path.exists(rf_path) else None
        stress_xgb = joblib.load(xgb_path) if os.path.exists(xgb_path) else None
        auth_models = joblib.load(auth_path) if os.path.exists(auth_path) else None
        
        return stress_rf, stress_xgb, auth_models
    except Exception as e:
        print(f"Error loading models: {e}")
        return None, None, None


@app.route('/')
def index():
    """Main dashboard."""
    latest = tracker.get_latest_metrics()
    summary = tracker.get_summary_stats() or {
        'total_runs': 0,
        'avg_rf_accuracy': 0,
        'avg_xgb_accuracy': 0,
        'avg_auth_accuracy': 0,
        'best_rf_accuracy': 0,
        'best_xgb_accuracy': 0,
        'best_auth_accuracy': 0
    }
    
    return render_template('index.html', 
                         latest=latest,
                         summary=summary)


@app.route('/typing')
def typing():
    """Live typing stress analyzer page."""
    return render_template('typing.html')


@app.route('/api/metrics')
def api_metrics():
    """Get all training metrics."""
    return jsonify(tracker.get_all_metrics())


@app.route('/api/metrics/latest')
def api_latest_metrics():
    """Get latest training metrics."""
    latest = tracker.get_latest_metrics()
    if not latest:
        return jsonify({'error': 'No training metrics found'}), 404
    return jsonify(latest)


@app.route('/api/metrics/summary')
def api_summary():
    """Get summary statistics."""
    return jsonify(tracker.get_summary_stats())


@app.route('/api/models/status')
def api_models_status():
    """Check if models are loaded."""
    stress_rf, stress_xgb, auth_models = load_models()
    
    return jsonify({
        'stress_random_forest': stress_rf is not None,
        'stress_xgboost': stress_xgb is not None,
        'auth_models': auth_models is not None,
        'num_users': len(auth_models) if auth_models else 0
    })


@app.route('/api/predict/stress', methods=['POST'])
def api_predict_stress():
    """Predict stress level."""
    try:
        data = request.json
        
        # Extract features
        features = [
            data.get('mean_hold_time', 0),
            data.get('std_hold_time', 0),
            data.get('mean_flight_time', 0),
            data.get('std_flight_time', 0),
            data.get('typing_speed', 0),
            data.get('error_proxy', 0),
            data.get('consistency_score', 0),
            data.get('pause_frequency', 0)
        ]
        
        stress_rf, stress_xgb, _ = load_models()
        
        if stress_rf is None or stress_xgb is None:
            return jsonify({'error': 'Models not loaded'}), 500
        
        X = np.array(features).reshape(1, -1)
        
        rf_pred = stress_rf.predict(X)[0]
        xgb_pred = stress_xgb.predict(X)[0]
        
        rf_proba = stress_rf.predict_proba(X)[0]
        xgb_proba = stress_xgb.predict_proba(X)[0]
        
        return jsonify({
            'random_forest': {
                'prediction': int(rf_pred),
                'label': 'High Stress' if rf_pred == 1 else 'Low Stress',
                'confidence': float(max(rf_proba))
            },
            'xgboost': {
                'prediction': int(xgb_pred),
                'label': 'High Stress' if xgb_pred == 1 else 'Low Stress',
                'confidence': float(max(xgb_proba))
            }
        })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 400


@app.route('/api/predict/auth/<user_id>', methods=['POST'])
def api_predict_auth(user_id):
    """Predict if user is legitimate."""
    try:
        data = request.json
        
        # Extract features
        features = np.array([
            data.get('mean_hold_time', 0),
            data.get('std_hold_time', 0),
            data.get('mean_flight_time', 0),
            data.get('std_flight_time', 0),
            data.get('typing_speed', 0),
            data.get('error_proxy', 0),
            data.get('consistency_score', 0),
            data.get('pause_frequency', 0)
        ]).reshape(1, -1)
        
        _, _, auth_models = load_models()
        
        if auth_models is None or user_id not in auth_models:
            return jsonify({'error': f'User {user_id} model not found'}), 404
        
        model = auth_models[user_id]
        prediction = model.predict(features)[0]
        
        return jsonify({
            'user_id': user_id,
            'prediction': int(prediction),
            'label': 'Legitimate' if prediction == 1 else 'Impostor',
            'is_legitimate': prediction == 1
        })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 400


@app.route('/api/users')
def api_users():
    """Get list of available users for authentication."""
    _, _, auth_models = load_models()
    
    if auth_models is None:
        return jsonify([])
    
    return jsonify(sorted(list(auth_models.keys())))


@app.route('/metrics')
def metrics_page():
    """Metrics history page."""
    all_metrics = tracker.get_all_metrics()
    return render_template('metrics.html', all_metrics=all_metrics)


@app.route('/download/report')
def download_report():
    """Download the latest report."""
    try:
        return send_file(os.path.join('outputs', 'stress_auth_report.txt'),
                        as_attachment=True)
    except:
        return jsonify({'error': 'Report not found'}), 404


@app.route('/download/metrics')
def download_metrics():
    """Download metrics JSON."""
    try:
        from flask import send_file
        import io
        
        metrics = tracker.get_all_metrics()
        json_str = json.dumps(metrics, indent=2)
        
        return send_file(
            io.BytesIO(json_str.encode()),
            mimetype='application/json',
            as_attachment=True,
            download_name=f'metrics_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
        )
    except:
        return jsonify({'error': 'Error generating file'}), 500


@app.route('/health')
def health():
    """Health check endpoint."""
    return jsonify({'status': 'ok', 'timestamp': datetime.now().isoformat()})


if __name__ == '__main__':
    print("Starting Keystroke Dynamics Dashboard...")
    print("Open your browser and navigate to: http://localhost:5000")
    app.run(debug=True, port=5000)
