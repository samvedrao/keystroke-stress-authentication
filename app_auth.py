import sys
import os
import json
import joblib
import random
from datetime import datetime, timedelta
from functools import wraps
import hashlib
import threading
import time
from typing import Optional
from werkzeug.security import generate_password_hash, check_password_hash

from flask import Flask, render_template, jsonify, request, send_file, redirect, url_for, session
from flask_sqlalchemy import SQLAlchemy
import numpy as np
import traceback
from sqlalchemy import inspect, text

from src.metrics_tracker import MetricsTracker
from src.load_data import load_cmu
from src.features import extract_cmu_features

# Add keystroke_project to path for importing modules
KEYSTROKE_PROJECT_PATH = os.path.join(os.path.dirname(__file__), 'keystroke_project')
if KEYSTROKE_PROJECT_PATH not in sys.path:
    sys.path.insert(0, KEYSTROKE_PROJECT_PATH)

# Import continuous auth and config from keystroke_project
import importlib.util
continuous_auth_path = os.path.join(KEYSTROKE_PROJECT_PATH, 'src', 'continuous_auth.py')
spec = importlib.util.spec_from_file_location("continuous_auth", continuous_auth_path)
continuous_auth_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(continuous_auth_module)

project_start_continuous_auth_checker = continuous_auth_module.start_continuous_auth_checker
check_user_continuous_auth = continuous_auth_module.check_user_continuous_auth

# Load config
config_path = os.path.join(KEYSTROKE_PROJECT_PATH, 'config.py')
spec = importlib.util.spec_from_file_location("config", config_path)
config_module = importlib.util.module_from_spec(spec)
sys.modules['keystroke_project.config'] = config_module
spec.loader.exec_module(config_module)

config = config_module.get_config()

# Initialize Flask app
app = Flask(__name__, template_folder='templates', static_folder='static')
app.config.from_object(config)
app.config['JSON_SORT_KEYS'] = False


@app.after_request
def add_no_cache_headers(response):
    """Disable client-side caching so UI changes appear immediately in development."""
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response

# Initialize database
db = SQLAlchemy(app, session_options={'expire_on_commit': False})

# Initialize metrics tracker
tracker = MetricsTracker()

# Get base directory
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
BASELINE_TARGET_SAMPLES = 3
BASELINE_MIN_ACCURACY = 0.75
QUALITY_MIN_KEYSTROKES = 8
QUALITY_MIN_DURATION_MS = 800
MAX_REASONABLE_TYPING_SPEED = 18.0
AUTH_RETRY_THRESHOLD = 65.0

# Randomized practice prompts (20 options, each with two sentences)
SAMPLE_TEXTS = [
    "Typing rhythm can reveal personal behavior in subtle ways. Keep your pace natural and avoid forcing speed.",
    "Consistent timing helps improve reliable biometric patterns. Focus on comfort and steady movement while typing.",
    "This session captures your normal keyboard interaction profile. Type smoothly and let mistakes happen naturally.",
    "Small delays between keys are part of your typing signature. Maintain your usual posture and typing style.",
    "Behavioral signals become stronger with repeated natural samples. Stay relaxed and type as you would in daily use.",
    "Keystroke analysis depends on both speed and consistency metrics. Use your regular rhythm without overthinking each key.",
    "This prompt supports account verification through timing features. Enter the text at a comfortable and stable pace.",
    "Your hold time and transition time patterns are being measured. Type clearly and do not intentionally rush the sentence.",
    "Session quality improves when input is calm and consistent. Keep your hands in a familiar position while typing.",
    "Authentication confidence grows from realistic typing behavior. Treat this as a normal message you write every day.",
    "Every user has a distinct timing fingerprint on the keyboard. Continue typing steadily to capture that personal pattern.",
    "Accurate modeling uses both variation and stability indicators. Type at your normal speed and avoid dramatic pauses.",
    "This sample helps the system compare you with your prior sessions. Stay natural and focus on smooth key transitions.",
    "Reliable verification comes from repeated and genuine interaction data. Type the text exactly while keeping a calm rhythm.",
    "The model observes tempo, consistency, and latency between keys. Keep your typing behavior close to your everyday style.",
    "Natural patterns are better than perfect accuracy for this task. Type confidently and continue without constant corrections.",
    "Your current sample will be compared with account history. Use your usual typing flow from start to finish.",
    "This phrase supports stress and identity analysis together. Enter it in one continuous attempt at a steady pace.",
    "Behavioral biometrics rely on timing rather than visible content. Type normally and avoid changing your usual technique.",
    "Each new sample helps estimate account match confidence. Keep a consistent rhythm and complete the text in one pass."
]


# ============================================================================
# DATABASE MODELS
# ============================================================================

class User(db.Model):
    """User account model"""
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    typing_sessions = db.relationship('TypingSession', backref='user', lazy=True, cascade='all, delete-orphan')
    
    def set_password(self, password):
        """Hash and set password"""
        # Use PBKDF2 (Werkzeug) for stronger hashing
        self.password_hash = generate_password_hash(password, method='pbkdf2:sha256', salt_length=16)
    
    def check_password(self, password):
        """Verify password"""
        # Support both PBKDF2 hashed passwords and legacy SHA256 hashes.
        try:
            if isinstance(self.password_hash, str) and self.password_hash.startswith('pbkdf2:'):
                return check_password_hash(self.password_hash, password)
            # Legacy SHA256 comparison
            if self.password_hash == hashlib.sha256(password.encode()).hexdigest():
                # Transparent upgrade: re-hash with PBKDF2 and persist
                try:
                    self.password_hash = generate_password_hash(password, method='pbkdf2:sha256', salt_length=16)
                    db.session.add(self)
                    db.session.commit()
                except Exception:
                    db.session.rollback()
                return True
        except Exception:
            pass
        return False


class TypingSession(db.Model):
    """User typing session with keystroke features and predictions"""
    __tablename__ = 'typing_sessions'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    # Keystroke features
    mean_hold_time = db.Column(db.Float)
    std_hold_time = db.Column(db.Float)
    mean_flight_time = db.Column(db.Float)
    std_flight_time = db.Column(db.Float)
    typing_speed = db.Column(db.Float)
    error_proxy = db.Column(db.Float)
    consistency_score = db.Column(db.Float)
    pause_frequency = db.Column(db.Float)
    
    # Predictions
    rf_prediction = db.Column(db.Integer)  # 0 = Low Stress, 1 = High Stress
    rf_confidence = db.Column(db.Float)
    xgb_prediction = db.Column(db.Integer)
    xgb_confidence = db.Column(db.Float)
    ensemble_prediction = db.Column(db.Integer)  # Consensus prediction
    
    # Metadata
    text_typed = db.Column(db.String(500))  # Store what was typed (optional privacy)
    num_keystrokes = db.Column(db.Integer)
    duration_ms = db.Column(db.Integer)  # Session duration in ms
    # Store full feature JSON blob for later analysis and debugging
    feature_blob = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        """Convert to dictionary for JSON serialization"""
        rf_conf = float(self.rf_confidence or 0.0)
        xgb_conf = float(self.xgb_confidence or 0.0)
        if self.rf_confidence is not None and self.xgb_confidence is not None:
            ensemble_conf = float((rf_conf + xgb_conf) / 2.0)
        else:
            ensemble_conf = float(max(rf_conf, xgb_conf))
        feature_blob = None
        if self.feature_blob:
            try:
                feature_blob = json.loads(self.feature_blob)
            except Exception:
                feature_blob = None
        is_baseline = self.text_typed == 'baseline_profile' or bool((feature_blob or {}).get('is_baseline'))
        stress_model_evaluated = not is_baseline and self.rf_confidence is not None and self.xgb_confidence is not None
        return {
            'id': self.id,
            'timestamp': self.created_at.isoformat(),
            'created_at': self.created_at.isoformat(),
            'mean_hold_time': self.mean_hold_time,
            'std_hold_time': self.std_hold_time,
            'mean_flight_time': self.mean_flight_time,
            'std_flight_time': self.std_flight_time,
            'typing_speed': self.typing_speed,
            'error_proxy': self.error_proxy,
            'consistency_score': self.consistency_score,
            'pause_frequency': self.pause_frequency,
            'rf_prediction': self.rf_prediction,
            'rf_confidence': self.rf_confidence,
            'rf_label': 'High Stress' if self.rf_prediction == 1 else 'Low Stress',
            'xgb_prediction': self.xgb_prediction,
            'xgb_confidence': self.xgb_confidence,
            'xgb_label': 'High Stress' if self.xgb_prediction == 1 else 'Low Stress',
            'ensemble_prediction': self.ensemble_prediction,
            'ensemble_confidence': ensemble_conf,
            'ensemble_label': 'High Stress' if self.ensemble_prediction == 1 else 'Low Stress',
            'mood_label': 'Stressed' if self.ensemble_prediction == 1 else 'Regular',
            'num_keystrokes': self.num_keystrokes,
            'duration_ms': self.duration_ms,
            'feature_blob': feature_blob,
            'is_baseline': is_baseline,
            'stress_model_evaluated': stress_model_evaluated
        }


class ContinuousAuthStatus(db.Model):
    """Store continuous authentication status per user."""
    __tablename__ = 'continuous_auth'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), unique=True, nullable=False)
    last_score = db.Column(db.Float)
    is_authenticated = db.Column(db.Boolean, default=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        return {
            'user_id': self.user_id,
            'last_score': float(self.last_score or 0.0),
            'is_authenticated': bool(self.is_authenticated),
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }


# ============================================================================
# MODEL LOADING
# ============================================================================

def load_models():
    """Load all trained models."""
    try:
        rf_calibrated_path = os.path.join(BASE_DIR, 'outputs', 'models', 'stress_random_forest_calibrated.pkl')
        xgb_calibrated_path = os.path.join(BASE_DIR, 'outputs', 'models', 'stress_xgboost_calibrated.pkl')
        rf_path = rf_calibrated_path if os.path.exists(rf_calibrated_path) else os.path.join(BASE_DIR, 'outputs', 'models', 'stress_random_forest.pkl')
        xgb_path = xgb_calibrated_path if os.path.exists(xgb_calibrated_path) else os.path.join(BASE_DIR, 'outputs', 'models', 'stress_xgboost.pkl')
        auth_path = os.path.join(BASE_DIR, 'outputs', 'models', 'auth_models.pkl')
        
        stress_rf = joblib.load(rf_path) if os.path.exists(rf_path) else None
        stress_xgb = joblib.load(xgb_path) if os.path.exists(xgb_path) else None
        auth_models = joblib.load(auth_path) if os.path.exists(auth_path) else None
        
        return stress_rf, stress_xgb, auth_models
    except Exception as e:
        print(f"Error loading models: {e}")
        return None, None, None


def calculate_text_accuracy(sample_text, typed_text):
    """Return character-level accuracy for a typed sample."""
    if not sample_text:
        return 1.0
    typed_text = typed_text or ''
    correct = sum(
        1 for i, expected in enumerate(sample_text)
        if i < len(typed_text) and typed_text[i] == expected
    )
    length_penalty = abs(len(sample_text) - len(typed_text))
    return max(0.0, min(1.0, (correct - length_penalty) / max(len(sample_text), 1)))


def sanitize_keystroke_events(keystroke_data, limit=300):
    """Return a privacy-conscious event payload for replay/debug visualizations."""
    events = []
    for ev in (keystroke_data or [])[:limit]:
        timestamp = ev.get('timestamp', ev.get('time'))
        try:
            timestamp = int(timestamp)
        except Exception:
            continue
        key = str(ev.get('key', ''))
        if len(key) == 1 and key not in (' ',):
            key = 'char'
        elif key == ' ':
            key = 'space'
        elif key not in ('Backspace', 'Delete', 'Shift', 'Enter', 'Tab', 'Control', 'Alt', 'Meta'):
            key = 'special'
        events.append({
            'timestamp': timestamp,
            'key': key,
            'type': ev.get('type', ev.get('event', 'keydown'))
        })
    return events


def evaluate_sample_quality(keystroke_data, typed_text, sample_text=''):
    """Score whether a typing sample is usable for enrollment or verification."""
    events = keystroke_data or []
    timestamps = []
    paste_detected = False
    for ev in events:
        event_type = ev.get('type', ev.get('event', ''))
        if event_type == 'paste' or ev.get('key') == 'Paste':
            paste_detected = True
        timestamp = ev.get('timestamp', ev.get('time'))
        try:
            timestamps.append(int(timestamp))
        except Exception:
            pass

    duration_ms = max(timestamps) - min(timestamps) if len(timestamps) >= 2 else 0
    typed_len = len(typed_text or '')
    speed = (typed_len / max(duration_ms / 1000.0, 0.1)) if typed_len else 0.0
    accuracy = calculate_text_accuracy(sample_text, typed_text) if sample_text else 1.0

    issues = []
    if paste_detected:
        issues.append('Paste detected. Type the sample manually.')
    if len(events) < QUALITY_MIN_KEYSTROKES:
        issues.append('Sample is too short to analyze reliably.')
    if duration_ms < QUALITY_MIN_DURATION_MS:
        issues.append('Sample was completed too quickly to trust.')
    if speed > MAX_REASONABLE_TYPING_SPEED:
        issues.append('Typing speed is unrealistically high.')
    if sample_text and accuracy < BASELINE_MIN_ACCURACY:
        issues.append('Typed text does not match the sample closely enough.')

    penalty = 0
    penalty += 35 if paste_detected else 0
    penalty += 20 if len(events) < QUALITY_MIN_KEYSTROKES else 0
    penalty += 20 if duration_ms < QUALITY_MIN_DURATION_MS else 0
    penalty += 20 if speed > MAX_REASONABLE_TYPING_SPEED else 0
    penalty += max(0, int((BASELINE_MIN_ACCURACY - accuracy) * 100)) if sample_text else 0
    score = max(0, min(100, 100 - penalty))

    return {
        'score': score,
        'is_usable': not issues,
        'issues': issues,
        'duration_ms': duration_ms,
        'typing_speed': round(speed, 2),
        'accuracy': round(accuracy * 100.0, 1),
        'paste_detected': paste_detected
    }


def get_baseline_sessions(user_id):
    """Return sessions that were saved as enrollment baseline samples."""
    return TypingSession.query.filter_by(
        user_id=user_id,
        text_typed='baseline_profile'
    ).order_by(TypingSession.created_at.asc()).all()


def get_baseline_status(user_id):
    """Summarize baseline enrollment progress and quality."""
    baseline_sessions = get_baseline_sessions(user_id)
    accuracies = []
    consistencies = []

    for session_obj in baseline_sessions:
        consistencies.append(float(session_obj.consistency_score or 0.0))
        if session_obj.feature_blob:
            try:
                blob = json.loads(session_obj.feature_blob)
                if 'sample_accuracy' in blob:
                    accuracies.append(float(blob.get('sample_accuracy') or 0.0))
            except Exception:
                pass

    avg_accuracy = float(np.mean(accuracies)) if accuracies else (1.0 if baseline_sessions else 0.0)
    avg_consistency = float(np.mean(consistencies)) if consistencies else 0.0
    quality_score = round(((avg_accuracy * 0.6) + (avg_consistency * 0.4)) * 100.0, 1)
    count = len(baseline_sessions)

    if count >= BASELINE_TARGET_SAMPLES and quality_score >= 75:
        label = 'Strong'
    elif count >= BASELINE_TARGET_SAMPLES:
        label = 'Needs review'
    elif count > 0:
        label = 'In progress'
    else:
        label = 'Not started'

    return {
        'target_samples': BASELINE_TARGET_SAMPLES,
        'completed_samples': count,
        'remaining_samples': max(0, BASELINE_TARGET_SAMPLES - count),
        'is_complete': count >= BASELINE_TARGET_SAMPLES,
        'avg_accuracy': round(avg_accuracy * 100.0, 1),
        'avg_consistency': round(avg_consistency * 100.0, 1),
        'quality_score': quality_score,
        'quality_label': label
    }


def build_session_explanation(session_obj, previous_sessions=None):
    """Explain which metrics drove a session's auth/stress result."""
    previous_sessions = previous_sessions or []
    features = session_to_feature_dict(session_obj)
    explanations = []

    if previous_sessions:
        comparisons = [
            ('typing_speed', 'Typing speed', 'chars/sec'),
            ('mean_hold_time', 'Hold time', 'ms'),
            ('mean_flight_time', 'Flight time', 'ms'),
            ('consistency_score', 'Consistency', ''),
            ('pause_frequency', 'Pause frequency', '')
        ]
        for key, label, unit in comparisons:
            prior_values = [
                float(getattr(s, key, 0.0) or 0.0)
                for s in previous_sessions
                if getattr(s, key, None) is not None
            ]
            if not prior_values:
                continue
            baseline = float(np.mean(prior_values))
            current = float(features.get(key, 0.0))
            if abs(baseline) < 1e-6:
                continue
            change = ((current - baseline) / abs(baseline)) * 100.0
            if abs(change) >= 15:
                direction = 'higher' if change > 0 else 'lower'
                suffix = f' {unit}' if unit else ''
                explanations.append(
                    f"{label} was {abs(change):.0f}% {direction} than your recent baseline "
                    f"({current:.2f}{suffix} vs {baseline:.2f}{suffix})."
                )

    if float(session_obj.consistency_score or 0.0) < 0.55:
        explanations.append("Typing consistency was low, which can reduce identity confidence.")
    if float(session_obj.pause_frequency or 0.0) > 0.2:
        explanations.append("Pauses were more frequent than expected during this sample.")
    if session_obj.ensemble_prediction == 1:
        explanations.append("The ensemble model marked this sample as stressed or unusual.")
    if not explanations:
        explanations.append("This session stayed close to your current typing profile.")

    return explanations[:5]


def get_model_health():
    """Return model artifact availability and basic runtime health."""
    rf_calibrated_path = os.path.join(BASE_DIR, 'outputs', 'models', 'stress_random_forest_calibrated.pkl')
    xgb_calibrated_path = os.path.join(BASE_DIR, 'outputs', 'models', 'stress_xgboost_calibrated.pkl')
    calibration_available = os.path.exists(rf_calibrated_path) and os.path.exists(xgb_calibrated_path)
    model_specs = [
        ('stress_random_forest', os.path.join(BASE_DIR, 'outputs', 'models', 'stress_random_forest.pkl')),
        ('stress_random_forest_calibrated', rf_calibrated_path),
        ('stress_xgboost', os.path.join(BASE_DIR, 'outputs', 'models', 'stress_xgboost.pkl')),
        ('stress_xgboost_calibrated', xgb_calibrated_path),
        ('auth_models', os.path.join(BASE_DIR, 'outputs', 'models', 'auth_models.pkl')),
    ]
    models = []
    for name, path in model_specs:
        exists = os.path.exists(path)
        models.append({
            'name': name,
            'path': os.path.relpath(path, BASE_DIR),
            'exists': exists,
            'size_kb': round(os.path.getsize(path) / 1024.0, 1) if exists else 0,
            'modified_at': datetime.fromtimestamp(os.path.getmtime(path)).isoformat() if exists else None
        })

    latest_metrics = tracker.get_latest_metrics()
    return {
        'all_models_present': all(item['exists'] for item in models),
        'models': models,
        'latest_metrics': latest_metrics,
        'calibration': {
            'available': calibration_available,
            'method': 'sigmoid CalibratedClassifierCV' if calibration_available else 'Not fitted',
            'note': 'The app automatically prefers calibrated stress model artifacts when they exist.' if calibration_available else 'Run scripts/train_calibrated_models.py to create calibrated stress confidence artifacts.'
        },
        'database_uri': str(db.engine.url) if db.engine else None,
        'checked_at': datetime.now().isoformat()
    }


def get_model_comparison_payload():
    """Build model comparison details for the UI."""
    latest_metrics = tracker.get_latest_metrics() or {}
    stress_metrics = latest_metrics.get('stress_classification', {}) if isinstance(latest_metrics, dict) else {}
    model_health = get_model_health()
    return {
        'models': [
            {
                'name': 'Random Forest',
                'artifact': 'outputs/models/stress_random_forest.pkl',
                'accuracy': stress_metrics.get('random_forest_accuracy'),
                'strength': 'Stable baseline model with useful feature importance.',
                'limitation': 'Raw probabilities may need calibration.'
            },
            {
                'name': 'XGBoost',
                'artifact': 'outputs/models/stress_xgboost.pkl',
                'accuracy': stress_metrics.get('xgboost_accuracy'),
                'strength': 'Captures non-linear typing behavior well.',
                'limitation': 'Can become overconfident without calibration.'
            },
            {
                'name': 'Ensemble',
                'artifact': 'Runtime weighted vote',
                'accuracy': stress_metrics.get('best_accuracy') or stress_metrics.get('ensemble_accuracy'),
                'strength': 'Combines both stress models for a steadier result.',
                'limitation': 'Currently averages raw confidence values.'
            }
        ],
        'health': model_health,
        'plots': {
            'confusion_matrix': '/outputs/plots/stress_confusion_matrix.png',
            'feature_importance': '/outputs/plots/stress_feature_importance.png',
            'auth_accuracy': '/outputs/plots/auth_accuracy.png'
        }
    }


def get_admin_overview_payload():
    """Return project-level operational stats."""
    users = User.query.all()
    sessions = TypingSession.query.order_by(TypingSession.created_at.asc()).all()
    baseline_count = len([s for s in sessions if s.text_typed == 'baseline_profile'])
    verification_count = len(sessions) - baseline_count
    stress_count = len([s for s in sessions if s.ensemble_prediction == 1 and s.text_typed != 'baseline_profile'])
    avg_auth = 0.0
    if sessions:
        score_map_by_user = {}
        auth_scores = []
        for user_obj in users:
            user_sessions = [s for s in sessions if s.user_id == user_obj.id]
            score_map_by_user[user_obj.id] = build_session_auth_scores(user_sessions)
            auth_scores.extend(info['auth_match_score'] for info in score_map_by_user[user_obj.id].values())
        avg_auth = float(np.mean(auth_scores)) if auth_scores else 0.0

    return {
        'total_users': len(users),
        'total_sessions': len(sessions),
        'baseline_sessions': baseline_count,
        'verification_sessions': verification_count,
        'stress_sessions': stress_count,
        'avg_auth_match': round(avg_auth, 1),
        'model_health': get_model_health(),
        'baseline_target_samples': BASELINE_TARGET_SAMPLES
    }


def build_project_report_html(user_id=None):
    """Generate a lightweight HTML report for project submission/export."""
    admin = get_admin_overview_payload()
    model_comparison = get_model_comparison_payload()
    generated_at = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    return f"""<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"><title>Keystroke Dynamics Project Report</title>
<style>body{{font-family:Segoe UI,Arial,sans-serif;margin:32px;color:#2c3e50;line-height:1.5}}h1,h2{{color:#26384d}}.grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:12px}}.card{{border:1px solid #dfe6ee;border-radius:8px;padding:14px;background:#f8fafc}}table{{width:100%;border-collapse:collapse}}td,th{{padding:8px;border-bottom:1px solid #e6edf5;text-align:left}}</style></head>
<body>
<h1>Keystroke Dynamics Authentication and Stress Analysis</h1>
<p>Generated at {generated_at}</p>
<h2>System Overview</h2>
<div class="grid">
<div class="card"><strong>Total users</strong><br>{admin['total_users']}</div>
<div class="card"><strong>Total sessions</strong><br>{admin['total_sessions']}</div>
<div class="card"><strong>Baseline sessions</strong><br>{admin['baseline_sessions']}</div>
<div class="card"><strong>Verification sessions</strong><br>{admin['verification_sessions']}</div>
<div class="card"><strong>Average auth match</strong><br>{admin['avg_auth_match']}%</div>
</div>
<h2>Implemented Features</h2>
<ul>
<li>Multi-sample baseline enrollment with quality scoring.</li>
<li>Real keydown/keyup timing for hold and flight features.</li>
<li>Stress prediction with Random Forest, XGBoost, and ensemble output.</li>
<li>Continuous authentication scoring and anomaly timeline.</li>
<li>Session replay visualization and explainable result summaries.</li>
<li>Data export, model health, model comparison, and admin dashboard.</li>
</ul>
<h2>Model Comparison</h2>
<table><thead><tr><th>Model</th><th>Accuracy</th><th>Strength</th><th>Limitation</th></tr></thead><tbody>
{''.join(f"<tr><td>{m['name']}</td><td>{m.get('accuracy') if m.get('accuracy') is not None else 'N/A'}</td><td>{m['strength']}</td><td>{m['limitation']}</td></tr>" for m in model_comparison['models'])}
</tbody></table>
<h2>Confidence Note</h2>
<p>Baseline enrollment sessions are not stress-scored and should not display model confidence. Runtime stress confidence uses raw model probabilities unless calibrated models are trained and promoted.</p>
</body></html>"""


# ============================================================================
# AUTHENTICATION DECORATORS
# ============================================================================

def login_required(f):
    """Require user login"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            if request.path.startswith('/api/') or request.is_json:
                return jsonify({'error': 'Authentication required'}), 401
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function


# ============================================================================
# AUTHENTICATION ROUTES
# ============================================================================

@app.route('/register', methods=['GET', 'POST'])
def register():
    """User registration"""
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        
        # Validation
        if not username or not email or not password:
            return render_template('auth.html', error='All fields required', active_tab='register')

        if len(username) < 3 or len(username) > 20:
            return render_template('auth.html', error='Username must be 3-20 characters', active_tab='register')
        
        if len(password) < 6:
            return render_template('auth.html', error='Password must be at least 6 characters', active_tab='register')
        
        # Check if user exists
        if User.query.filter_by(username=username).first():
            return render_template('auth.html', error='Username already exists', active_tab='register')
        
        if User.query.filter_by(email=email).first():
            return render_template('auth.html', error='Email already registered', active_tab='register')
        
        # Create user
        try:
            user = User(username=username, email=email)
            user.set_password(password)
            db.session.add(user)
            db.session.commit()

            # Auto-login and set up baseline typing profile
            session['user_id'] = user.id
            session['username'] = user.username
            session.permanent = True
            app.permanent_session_lifetime = timedelta(days=7)

            return redirect(url_for('setup_typing'))
        except Exception as e:
            db.session.rollback()
            return render_template('auth.html', error=f'Registration failed: {str(e)}', active_tab='register')
    
    return render_template('auth.html', active_tab='register')


@app.route('/login', methods=['GET', 'POST'])
def login():
    """User login"""
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        
        # Find user
        user = User.query.filter_by(username=username).first()
        
        # Check authentication
        if not user or not user.check_password(password):
            return render_template('auth.html', error='Invalid username or password', active_tab='login')
        
        # Create session
        session['user_id'] = user.id
        session['username'] = user.username
        session.permanent = True
        app.permanent_session_lifetime = timedelta(days=7)
        
        return redirect(url_for('dashboard'))
    
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    
    return render_template('auth.html', active_tab='login')


@app.route('/logout')
def logout():
    """User logout"""
    session.clear()
    return redirect(url_for('login'))


# ============================================================================
# MAIN ROUTES
# ============================================================================

@app.route('/')
def index():
    """Home page - redirect to login or dashboard"""
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))


@app.route('/dashboard')
@login_required
def dashboard():
    """User dashboard with history"""
    user_id = session.get('user_id')
    user = User.query.get(user_id)
    
    # Get user's recent sessions
    sessions = TypingSession.query.filter_by(user_id=user_id).order_by(
        TypingSession.created_at.desc()
    ).limit(10).all()

    all_sessions_sorted = TypingSession.query.filter_by(user_id=user_id).order_by(
        TypingSession.created_at.asc()
    ).all()

    session_score_map = build_session_auth_scores(all_sessions_sorted)
    for s in sessions:
        match_info = session_score_map.get(s.id, {'auth_match_score': 100.0, 'auth_verified': True})
        s.auth_match_score = float(match_info['auth_match_score'])
        s.auth_verified = bool(match_info['auth_verified'])
    
    # Calculate stats
    all_sessions = TypingSession.query.filter_by(user_id=user_id).all()
    total_sessions = len(all_sessions)
    avg_speed = float(np.mean([s.typing_speed for s in all_sessions])) if all_sessions else 0
    best_consistency = float(max([s.consistency_score for s in all_sessions], default=0) * 100)
    regular_count = len([s for s in all_sessions if s.ensemble_prediction == 0])
    stressed_count = len([s for s in all_sessions if s.ensemble_prediction == 1])
    
    return render_template('dashboard_pro.html', 
                         user=user, 
                         sessions=sessions,
                         total_sessions=total_sessions,
                         avg_speed=avg_speed,
                         best_consistency=best_consistency,
                         regular_count=regular_count,
                         stressed_count=stressed_count)


@app.route('/typing')
@login_required
def typing():
    """Compatibility route - redirect to verification page"""
    return redirect(url_for('verify_typing'))


@app.route('/setup-typing')
@login_required
def setup_typing():
    """Setup baseline typing profile for new users"""
    user_id = session.get('user_id')
    return render_template(
        'typing_baseline.html',
        sample_text=get_random_sample_text(),
        baseline_status=get_baseline_status(user_id)
    )


@app.route('/verify-typing', methods=['GET', 'POST'])
@login_required
def verify_typing():
    """Verify user typing and analyze patterns"""
    if request.method == 'POST':
        try:
            data = request.json or {}
            user_id = session.get('user_id')
            typed_text = data.get('typed_text', '')
            sample_text = data.get('sample_text', '')
            keystroke_data = data.get('keystroke_data', [])

            features = calculate_keystroke_features(keystroke_data, typed_text)
            quality = evaluate_sample_quality(keystroke_data, typed_text, sample_text)
            features['sample_quality'] = quality
            features['keystroke_events'] = sanitize_keystroke_events(keystroke_data)
            features['is_baseline'] = False

            stress_rf, stress_xgb, _ = load_models()
            if stress_rf is None or stress_xgb is None:
                return jsonify({'error': 'Models not available'}), 500

            X = np.array([
                features.get('mean_hold_time', 0),
                features.get('std_hold_time', 0),
                features.get('mean_flight_time', 0),
                features.get('std_flight_time', 0),
                features.get('typing_speed', 0),
                features.get('error_proxy', 0),
                features.get('consistency_score', 0),
                features.get('pause_frequency', 0)
            ]).reshape(1, -1)

            rf_pred = int(stress_rf.predict(X)[0])
            xgb_pred = int(stress_xgb.predict(X)[0])
            rf_confidence = float(max(stress_rf.predict_proba(X)[0]))
            xgb_confidence = float(max(stress_xgb.predict_proba(X)[0]))

            combined_denom = (rf_confidence + xgb_confidence) or 1.0
            ensemble_pred = int(round((rf_pred * rf_confidence + xgb_pred * xgb_confidence) / combined_denom))

            previous_sessions = TypingSession.query.filter_by(user_id=user_id).all()
            auth_match_score = calculate_auth_match_score(features, previous_sessions)
            is_verified = auth_match_score >= AUTH_RETRY_THRESHOLD
            requires_retry = (not is_verified) or (not quality['is_usable'])

            duration_ms = 0
            if len(keystroke_data) >= 2:
                duration_ms = int(max(0, keystroke_data[-1].get('timestamp', 0) - keystroke_data[0].get('timestamp', 0)))

            # Build kwargs and only include feature_blob if the DB column exists
            kwargs = dict(
                user_id=user_id,
                mean_hold_time=features.get('mean_hold_time', 0),
                std_hold_time=features.get('std_hold_time', 0),
                mean_flight_time=features.get('mean_flight_time', 0),
                std_flight_time=features.get('std_flight_time', 0),
                typing_speed=features.get('typing_speed', 0),
                error_proxy=features.get('error_proxy', 0),
                consistency_score=features.get('consistency_score', 0),
                pause_frequency=features.get('pause_frequency', 0),
                rf_prediction=rf_pred,
                rf_confidence=rf_confidence,
                xgb_prediction=xgb_pred,
                xgb_confidence=xgb_confidence,
                ensemble_prediction=ensemble_pred,
                num_keystrokes=len(keystroke_data),
                duration_ms=duration_ms,
                text_typed=typed_text[:500],
            )
            if table_has_column('typing_sessions', 'feature_blob'):
                kwargs['feature_blob'] = json.dumps(features)
            session_record = TypingSession(**kwargs)
            db.session.add(session_record)
            db.session.commit()

            return jsonify({
                'success': True,
                'session_id': session_record.id,
                'is_verified': bool(is_verified),
                'auth_match_score': float(auth_match_score),
                'requires_retry': bool(requires_retry),
                'quality': quality,
                'retry_reason': 'Typing sample needs another verification attempt.' if requires_retry else None
            }), 200
        except Exception as e:
            db.session.rollback()
            return jsonify({'error': f'Verification failed: {str(e)}'}), 500

    return render_template('typing_verify.html', sample_text=get_random_sample_text())


@app.route('/analysis-results')
@login_required
def analysis_results():
    """Render analysis results page"""
    return render_template('analysis_results.html')


@app.route('/history')
@login_required
def history():
    """Typing history and analytics page"""
    user_id = session.get('user_id')
    user = User.query.get(user_id)
    return render_template('history.html', user=user)


@app.route('/profile')
@login_required
def profile():
    """User profile page"""
    user_id = session.get('user_id')
    user = User.query.get(user_id)
    
    all_sessions = TypingSession.query.filter_by(user_id=user_id).all()
    
    # Compile statistics
    stats = {
        'total_sessions': len(all_sessions),
        'avg_typing_speed': float(np.mean([s.typing_speed for s in all_sessions])) if all_sessions else 0,
        'avg_consistency': float(np.mean([s.consistency_score for s in all_sessions])) if all_sessions else 0,
        'avg_hold_time': float(np.mean([s.mean_hold_time for s in all_sessions])) if all_sessions else 0,
        'stress_trend': [s.to_dict() for s in all_sessions[-20:]]  # Last 20 sessions
    }
    
    avg_speed = float(np.mean([s.typing_speed for s in all_sessions])) if all_sessions else 0
    best_consistency = float(max([s.consistency_score for s in all_sessions], default=0))
    regular_count = len([s for s in all_sessions if s.ensemble_prediction == 0])
    
    return render_template('profile_pro.html', user=user, 
                         typing_sessions=all_sessions,
                         avg_speed=avg_speed,
                         best_consistency=best_consistency,
                         regular_count=regular_count,
                         baseline_status=get_baseline_status(user_id))


@app.route('/delete-account', methods=['POST'])
@login_required
def delete_account():
    """Delete currently logged-in user account and all sessions."""
    user_id = session.get('user_id')
    user = User.query.get(user_id)

    if user:
        db.session.delete(user)
        db.session.commit()

    session.clear()
    return redirect(url_for('login'))


@app.route('/reset-baseline', methods=['POST'])
@login_required
def reset_baseline():
    """Delete baseline enrollment sessions for the current user."""
    user_id = session.get('user_id')
    for session_obj in get_baseline_sessions(user_id):
        db.session.delete(session_obj)
    db.session.commit()
    return redirect(url_for('setup_typing'))


@app.route('/model-health')
@login_required
def model_health_page():
    """Render model/runtime health page."""
    return render_template('model_health.html')


@app.route('/model-comparison')
@login_required
def model_comparison_page():
    """Render model comparison page."""
    return render_template('model_comparison.html')


@app.route('/admin')
@login_required
def admin_dashboard_page():
    """Render project/admin overview page."""
    return render_template('admin_dashboard.html')


@app.route('/download/project-report')
@login_required
def download_project_report():
    """Download an HTML project report."""
    html = build_project_report_html(session.get('user_id'))
    filename = f"keystroke_project_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
    return app.response_class(
        response=html,
        status=200,
        mimetype='text/html',
        headers={'Content-Disposition': f'attachment; filename={filename}'}
    )


@app.route('/outputs/plots/<path:filename>')
@login_required
def output_plot(filename):
    """Serve generated model plots to authenticated users."""
    safe_path = os.path.join(BASE_DIR, 'outputs', 'plots', filename)
    if not os.path.abspath(safe_path).startswith(os.path.abspath(os.path.join(BASE_DIR, 'outputs', 'plots'))):
        return jsonify({'error': 'Invalid path'}), 400
    if not os.path.exists(safe_path):
        return jsonify({'error': 'Plot not found'}), 404
    return send_file(safe_path)


# ============================================================================
# API ROUTES - METRICS
# ============================================================================

@app.route('/api/metrics')
def api_metrics():
    """Get all training metrics"""
    return jsonify(tracker.get_all_metrics())


@app.route('/api/metrics/latest')
def api_latest_metrics():
    """Get latest training metrics"""
    latest = tracker.get_latest_metrics()
    if not latest:
        return jsonify({'error': 'No training metrics found'}), 404
    return jsonify(latest)


@app.route('/api/metrics/summary')
def api_summary():
    """Get summary statistics"""
    return jsonify(tracker.get_summary_stats())


@app.route('/api/models/status')
def api_models_status():
    """Check if models are loaded"""
    stress_rf, stress_xgb, auth_models = load_models()
    
    return jsonify({
        'stress_random_forest': stress_rf is not None,
        'stress_xgboost': stress_xgb is not None,
        'auth_models': auth_models is not None,
        'num_users': len(auth_models) if auth_models else 0
    })


@app.route('/api/model-health')
@login_required
def api_model_health():
    """Return model artifact and runtime health."""
    return jsonify(get_model_health())


@app.route('/api/model-comparison')
@login_required
def api_model_comparison():
    """Return model comparison details."""
    return jsonify(get_model_comparison_payload())


@app.route('/api/admin/overview')
@login_required
def api_admin_overview():
    """Return project-level overview statistics."""
    return jsonify(get_admin_overview_payload())


@app.route('/api/baseline/status')
@login_required
def api_baseline_status():
    """Return baseline enrollment status for the current user."""
    return jsonify(get_baseline_status(session.get('user_id')))


@app.route('/api/sample-quality', methods=['POST'])
@login_required
def api_sample_quality():
    """Evaluate sample quality before saving or verification."""
    data = request.json or {}
    return jsonify(evaluate_sample_quality(
        data.get('keystroke_data', []),
        data.get('typed_text', ''),
        data.get('sample_text', '')
    ))


# ============================================================================
# API ROUTES - PREDICTIONS
# ============================================================================

@app.route('/api/predict/stress', methods=['POST'])
@login_required
def api_predict_stress():
    """Predict stress level and save session"""
    try:
        data = request.json
        user_id = session.get('user_id')
        
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
        
        # Get predictions
        rf_pred = stress_rf.predict(X)[0]
        xgb_pred = stress_xgb.predict(X)[0]
        
        rf_proba = stress_rf.predict_proba(X)[0]
        xgb_proba = stress_xgb.predict_proba(X)[0]
        
        rf_confidence = float(max(rf_proba))
        xgb_confidence = float(max(xgb_proba))
        
        # Ensemble prediction (majority vote with confidence weighting)
        combined_pred = round((rf_pred * rf_confidence + xgb_pred * xgb_confidence) / 
                             (rf_confidence + xgb_confidence))
        
        # Save session to database
        try:
            # Build a full feature dict if provided, otherwise map from provided flat fields
            feature_dict = data.get('features') if isinstance(data.get('features'), dict) else {
                'mean_hold_time': features[0],
                'std_hold_time': features[1],
                'mean_flight_time': features[2],
                'std_flight_time': features[3],
                'typing_speed': features[4],
                'error_proxy': features[5],
                'consistency_score': features[6],
                'pause_frequency': features[7]
            }
            pkwargs = dict(
                user_id=user_id,
                mean_hold_time=features[0],
                std_hold_time=features[1],
                mean_flight_time=features[2],
                std_flight_time=features[3],
                typing_speed=features[4],
                error_proxy=features[5],
                consistency_score=features[6],
                pause_frequency=features[7],
                rf_prediction=int(rf_pred),
                rf_confidence=rf_confidence,
                xgb_prediction=int(xgb_pred),
                xgb_confidence=xgb_confidence,
                ensemble_prediction=int(combined_pred),
                num_keystrokes=data.get('num_keystrokes', 0),
                duration_ms=data.get('duration_ms', 0),
                text_typed=data.get('text_typed', ''),
            )
            if table_has_column('typing_sessions', 'feature_blob'):
                pkwargs['feature_blob'] = json.dumps(feature_dict)
            session_record = TypingSession(**pkwargs)
            db.session.add(session_record)
            db.session.commit()
        except Exception as e:
            print(f"Error saving session: {e}")
            db.session.rollback()
        
        return jsonify({
            'random_forest': {
                'prediction': int(rf_pred),
                'label': 'High Stress' if rf_pred == 1 else 'Low Stress',
                'confidence': rf_confidence
            },
            'xgboost': {
                'prediction': int(xgb_pred),
                'label': 'High Stress' if xgb_pred == 1 else 'Low Stress',
                'confidence': xgb_confidence
            },
            'ensemble': {
                'prediction': int(combined_pred),
                'label': 'High Stress' if combined_pred == 1 else 'Low Stress',
                'confidence': float((rf_confidence + xgb_confidence) / 2)
            },
            'interpretation': generate_interpretation(
                int(combined_pred),
                features[6],  # consistency_score
                features[4]   # typing_speed
            )
        })
    
    except Exception as e:
        return jsonify({'error': f'Prediction failed: {str(e)}'}), 500


@app.route('/save-baseline', methods=['POST'])
@login_required
def save_baseline():
    """Save baseline typing profile session"""
    print('\n/save-baseline called')
    try:
        print('session user_id (entry):', session.get('user_id'))
        try:
            print('incoming json keys:', list((request.json or {}).keys()))
        except Exception as _:
            print('could not read request.json directly')
        data = request.json or {}
        user_id = session.get('user_id')
        typed_text = data.get('typed_text', '')
        sample_text = data.get('sample_text', '')
        keystroke_data = data.get('keystroke_data', [])
        sample_accuracy = calculate_text_accuracy(sample_text, typed_text)

        if sample_text and sample_accuracy < BASELINE_MIN_ACCURACY:
            return jsonify({
                'error': 'Please type the sample more accurately before saving this baseline.',
                'sample_accuracy': round(sample_accuracy * 100.0, 1),
                'baseline_status': get_baseline_status(user_id)
            }), 400

        print('typed_text length:', len(typed_text), 'keystrokes length:', len(keystroke_data))
        features = calculate_keystroke_features(keystroke_data, typed_text)
        quality = evaluate_sample_quality(keystroke_data, typed_text, sample_text)
        if sample_text and not quality['is_usable']:
            return jsonify({
                'error': quality['issues'][0] if quality['issues'] else 'Sample quality is too low.',
                'quality': quality,
                'baseline_status': get_baseline_status(user_id)
            }), 400
        features['sample_accuracy'] = sample_accuracy
        features['sample_text_length'] = len(sample_text)
        features['is_baseline'] = True
        features['stress_model_evaluated'] = False
        features['sample_quality'] = quality
        features['keystroke_events'] = sanitize_keystroke_events(keystroke_data)

        duration_ms = 0
        if len(keystroke_data) >= 2:
            duration_ms = int(max(0, keystroke_data[-1].get('timestamp', 0) - keystroke_data[0].get('timestamp', 0)))

        # Build kwargs and include feature_blob only if supported by DB
        bkwargs = dict(
            user_id=user_id,
            mean_hold_time=features.get('mean_hold_time', 0),
            std_hold_time=features.get('std_hold_time', 0),
            mean_flight_time=features.get('mean_flight_time', 0),
            std_flight_time=features.get('std_flight_time', 0),
            typing_speed=features.get('typing_speed', 0),
            error_proxy=features.get('error_proxy', 0),
            consistency_score=features.get('consistency_score', 0),
            pause_frequency=features.get('pause_frequency', 0),
            rf_prediction=0,
            rf_confidence=None,
            xgb_prediction=0,
            xgb_confidence=None,
            ensemble_prediction=0,
            num_keystrokes=len(keystroke_data),
            duration_ms=duration_ms,
            text_typed='baseline_profile',
        )
        if table_has_column('typing_sessions', 'feature_blob'):
            bkwargs['feature_blob'] = json.dumps(features)
        baseline_session = TypingSession(**bkwargs)
        db.session.add(baseline_session)
        db.session.commit()
        baseline_status = get_baseline_status(user_id)

        return jsonify({
            'success': True,
            'session_id': baseline_session.id,
            'baseline_status': baseline_status,
            'quality': quality,
            'next_sample_text': get_random_sample_text() if not baseline_status['is_complete'] else None
        }), 201
    except Exception as e:
        # Log detailed error to server console for debugging
        print('Error in /save-baseline:', str(e))
        traceback.print_exc()
        print('Request data keys:', list((request.json or {}).keys()))
        print('Session user_id:', session.get('user_id'))
        db.session.rollback()
        return jsonify({'error': f'Failed to save baseline: {str(e)}'}), 500


@app.route('/api/session/<int:session_id>')
@login_required
def api_get_session(session_id):
    """Get a specific user session by id"""
    user_id = session.get('user_id')
    session_obj = TypingSession.query.filter_by(id=session_id, user_id=user_id).first()
    if not session_obj:
        return jsonify({'error': 'Session not found'}), 404
    previous_sessions = TypingSession.query.filter(
        TypingSession.user_id == user_id,
        TypingSession.created_at < session_obj.created_at
    ).order_by(TypingSession.created_at.asc()).all()

    payload = session_obj.to_dict()
    session_features = session_to_feature_dict(session_obj)
    auth_match_score = calculate_auth_match_score(session_features, previous_sessions)
    payload['auth_match_score'] = float(auth_match_score)
    payload['auth_verified'] = bool(auth_match_score >= 65.0)
    payload['explanations'] = build_session_explanation(session_obj, previous_sessions)
    payload['confidence_sections'] = {
        'identity': {
            'score': float(auth_match_score),
            'label': 'Verified' if auth_match_score >= AUTH_RETRY_THRESHOLD else 'Retry recommended'
        },
        'stress': {
            'evaluated': bool(payload.get('stress_model_evaluated')),
            'label': payload.get('ensemble_label') if payload.get('stress_model_evaluated') else 'Not evaluated for baseline enrollment'
        }
    }

    return jsonify(payload), 200


@app.route('/api/session/<int:session_id>/replay')
@login_required
def api_session_replay(session_id):
    """Return privacy-safe keystroke replay events for a session."""
    user_id = session.get('user_id')
    session_obj = TypingSession.query.filter_by(id=session_id, user_id=user_id).first()
    if not session_obj:
        return jsonify({'error': 'Session not found'}), 404
    blob = {}
    if session_obj.feature_blob:
        try:
            blob = json.loads(session_obj.feature_blob)
        except Exception:
            blob = {}
    return jsonify({
        'session_id': session_obj.id,
        'events': blob.get('keystroke_events', []),
        'duration_ms': session_obj.duration_ms or 0,
        'quality': blob.get('sample_quality')
    })


@app.route('/api/user/sessions')
@login_required
def api_user_sessions():
    """Get user's typing sessions"""
    user_id = session.get('user_id')
    sessions_asc = TypingSession.query.filter_by(user_id=user_id).order_by(
        TypingSession.created_at.asc()
    ).all()
    session_score_map = build_session_auth_scores(sessions_asc)

    payload = []
    for s in reversed(sessions_asc):
        row = s.to_dict()
        match_info = session_score_map.get(s.id, {'auth_match_score': 100.0, 'auth_verified': True})
        row['auth_match_score'] = float(match_info['auth_match_score'])
        row['auth_verified'] = bool(match_info['auth_verified'])
        payload.append(row)

    return jsonify(payload)


@app.route('/api/user/stats')
@login_required
def api_user_stats():
    """Get user statistics"""
    user_id = session.get('user_id')
    all_sessions = TypingSession.query.filter_by(user_id=user_id).all()
    latest_session = TypingSession.query.filter_by(user_id=user_id).order_by(
        TypingSession.created_at.desc()
    ).first()
    
    if not all_sessions:
        return jsonify({
            'total_sessions': 0,
            'avg_typing_speed': 0,
            'avg_consistency': 0,
            'avg_hold_time': 0,
            'stress_events': 0,
            'low_stress_events': 0
        })
    
    return jsonify({
        'total_sessions': len(all_sessions),
        'avg_typing_speed': float(np.mean([s.typing_speed for s in all_sessions])),
        'avg_consistency': float(np.mean([s.consistency_score for s in all_sessions])),
        'avg_hold_time': float(np.mean([s.mean_hold_time for s in all_sessions])),
        'stress_events': len([s for s in all_sessions if s.ensemble_prediction == 1]),
        'low_stress_events': len([s for s in all_sessions if s.ensemble_prediction == 0]),
        'last_session': latest_session.to_dict() if latest_session else None
    })


@app.route('/api/analytics/overview')
@login_required
def api_analytics_overview():
    """Get timeline and cross-user analytics for dashboard/history charts."""
    user_id = session.get('user_id')

    current_user_sessions = TypingSession.query.filter_by(user_id=user_id).order_by(
        TypingSession.created_at.asc()
    ).all()

    score_map = build_session_auth_scores(current_user_sessions)

    timeline = [
        {
            'id': s.id,
            'timestamp': s.created_at.isoformat(),
            'typing_speed': float(s.typing_speed or 0.0),
            'consistency_score': float(s.consistency_score or 0.0),
            'ensemble_prediction': int(s.ensemble_prediction or 0),
            'mood_label': 'Stressed' if s.ensemble_prediction == 1 else 'Regular',
            'auth_match_score': float(score_map.get(s.id, {}).get('auth_match_score', 100.0)),
            'auth_verified': bool(score_map.get(s.id, {}).get('auth_verified', True)),
            'is_baseline': s.text_typed == 'baseline_profile'
        }
        for s in current_user_sessions
    ]

    peer_summary = []
    users = User.query.order_by(User.username.asc()).all()
    for peer_index, u in enumerate(users, start=1):
        user_sessions = TypingSession.query.filter_by(user_id=u.id).all()
        if not user_sessions:
            continue

        peer_summary.append({
            'username': 'You' if u.id == user_id else f'User {peer_index}',
            'total_sessions': len(user_sessions),
            'avg_speed': float(np.mean([s.typing_speed for s in user_sessions])),
            'regular_count': len([s for s in user_sessions if s.ensemble_prediction == 0]),
            'stressed_count': len([s for s in user_sessions if s.ensemble_prediction == 1])
        })

    return jsonify({
        'current_user_timeline': timeline,
        'peer_summary': peer_summary
    })


@app.route('/api/anomaly-timeline')
@login_required
def api_anomaly_timeline():
    """Return identity confidence over time for anomaly visualization."""
    user_id = session.get('user_id')
    sessions_asc = TypingSession.query.filter_by(user_id=user_id).order_by(
        TypingSession.created_at.asc()
    ).all()
    score_map = build_session_auth_scores(sessions_asc)
    rows = []
    for s in sessions_asc:
        score = float(score_map.get(s.id, {}).get('auth_match_score', 100.0))
        rows.append({
            'id': s.id,
            'timestamp': s.created_at.isoformat(),
            'auth_match_score': score,
            'risk_level': 'high' if score < 50 else ('watch' if score < AUTH_RETRY_THRESHOLD else 'trusted'),
            'is_baseline': s.text_typed == 'baseline_profile'
        })
    return jsonify({'timeline': rows, 'threshold': AUTH_RETRY_THRESHOLD})


@app.route('/api/continuous_status')
@login_required
def api_continuous_status():
    """Get current user's continuous authentication status."""
    user_id = session.get('user_id')
    status = ContinuousAuthStatus.query.filter_by(user_id=user_id).first()
    if not status:
        return jsonify({'user_id': user_id, 'last_score': None, 'is_authenticated': True}), 200
    return jsonify(status.to_dict()), 200


@app.route('/api/continuous_status/<int:user_id>')
@login_required
def api_continuous_status_by_user(user_id):
    """Get continuous auth status for a specific user id."""
    status = ContinuousAuthStatus.query.filter_by(user_id=user_id).first()
    if not status:
        return jsonify({'error': 'Status not found'}), 404
    return jsonify(status.to_dict()), 200


@app.route('/api/export/feature-blobs', methods=['GET'])
@login_required
def api_export_feature_blobs():
    """Export user's feature_blob data as JSON lines."""
    user_id = session.get('user_id')
    sessions = TypingSession.query.filter_by(user_id=user_id).order_by(
        TypingSession.created_at.asc()
    ).all()
    
    blobs = []
    for s in sessions:
        if s.feature_blob:
            try:
                blob_data = json.loads(s.feature_blob)
                blob_data['session_id'] = s.id
                blob_data['timestamp'] = s.created_at.isoformat()
                blobs.append(blob_data)
            except Exception:
                pass
    
    return jsonify({'feature_blobs': blobs, 'count': len(blobs)}), 200


@app.route('/api/export/feature-blobs/csv', methods=['GET'])
@login_required
def api_export_feature_blobs_csv():
    """Export user's feature_blob data as CSV file."""
    import csv
    from io import StringIO
    
    user_id = session.get('user_id')
    sessions = TypingSession.query.filter_by(user_id=user_id).order_by(
        TypingSession.created_at.asc()
    ).all()
    
    # Collect all feature keys
    all_keys = set()
    rows = []
    for s in sessions:
        if s.feature_blob:
            try:
                blob_data = json.loads(s.feature_blob)
                all_keys.update(blob_data.keys())
                blob_data['session_id'] = s.id
                blob_data['timestamp'] = s.created_at.isoformat()
                rows.append(blob_data)
            except Exception:
                pass
    
    # Build CSV
    if not rows:
        return jsonify({'error': 'No feature data to export'}), 400
    
    fieldnames = ['session_id', 'timestamp'] + sorted(list(all_keys - {'session_id', 'timestamp'}))
    output = StringIO()
    writer = csv.DictWriter(output, fieldnames=fieldnames)
    writer.writeheader()
    for row in rows:
        writer.writerow({k: row.get(k, '') for k in fieldnames})
    
    # Return as downloadable file
    response = app.response_class(
        response=output.getvalue(),
        status=200,
        mimetype='text/csv',
        headers={'Content-Disposition': f'attachment; filename=keystroke_features_{user_id}.csv'}
    )
    return response


# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def calculate_keystroke_features(keystroke_data, text_typed):
    """Calculate keystroke features from raw key events.

    Enhanced features added:
    - median, variance, percentiles, longest pause, entropy
    - pause counts >1s, pause frequency, bursts
    - backspace/delete counts and correction streaks (if keys present)
    - digraph timing for common digraphs (if keys present)
    """
    # Minimal default
    default_features = {
        'mean_hold_time': 100.0,
        'median_hold_time': 100.0,
        'std_hold_time': 20.0,
        'var_hold_time': 400.0,
        'mean_flight_time': 50.0,
        'std_flight_time': 15.0,
        'var_flight_time': 225.0,
        'typing_speed': 0.0,
        'error_proxy': 0.0,
        'consistency_score': 0.5,
        'pause_frequency': 0.0,
        'pause_count_long': 0,
        'longest_pause': 0,
        'hold_entropy': 0.0,
        'burst_frequency': 0.0,
        'backspace_count': 0,
        'backspace_ratio': 0.0,
        'delete_count': 0,
        'max_correction_streak': 0,
        'digraph_th': 0.0,
        'digraph_er': 0.0,
        'digraph_in': 0.0,
        'digraph_an': 0.0
    }

    if not keystroke_data or len(keystroke_data) < 2:
        return default_features

    normalized_events = []
    for ev in keystroke_data:
        timestamp = ev.get('timestamp', ev.get('time'))
        if timestamp is None:
            continue
        try:
            timestamp = int(timestamp)
        except Exception:
            try:
                timestamp = int(float(timestamp))
            except Exception:
                continue

        key = ev.get('key', '')
        event_type = ev.get('type', ev.get('event', 'keydown'))
        if event_type not in ('keydown', 'keyup'):
            event_type = 'keydown'

        normalized_events.append({
            'timestamp': timestamp,
            'key': str(key),
            'type': event_type
        })

    normalized_events.sort(key=lambda item: item['timestamp'])
    timestamps = [ev['timestamp'] for ev in normalized_events]
    if len(timestamps) < 2:
        return default_features

    keydown_times = []
    hold_times = []
    flight_times = []
    active_keys = {}
    previous_keyup = None
    for ev in normalized_events:
        key = ev['key']
        timestamp = ev['timestamp']
        if ev['type'] == 'keydown':
            keydown_times.append(timestamp)
            active_keys.setdefault(key, []).append(timestamp)
            if previous_keyup is not None:
                flight_times.append(max(0, timestamp - previous_keyup))
        elif ev['type'] == 'keyup':
            starts = active_keys.get(key) or []
            if starts:
                hold_times.append(max(0, timestamp - starts.pop(0)))
            previous_keyup = timestamp

    intervals = hold_times if hold_times else []
    fallback_intervals = []
    pauses = 0
    for i in range(1, len(timestamps)):
        delta = max(0, timestamps[i] - timestamps[i - 1])
        if delta > 0:
            fallback_intervals.append(delta)
            if delta >= 1000:
                pauses += 1

    if not intervals:
        intervals = fallback_intervals or [100.0]
    if not flight_times:
        flight_times = fallback_intervals or [50.0]

    total_duration_sec = max((timestamps[-1] - timestamps[0]) / 1000.0, 0.1)
    typing_speed = min(len(text_typed) / total_duration_sec, 20.0)

    mean_hold = float(np.mean(intervals))
    median_hold = float(np.median(intervals))
    std_hold = float(np.std(intervals))
    var_hold = float(np.var(intervals))
    mean_flight = float(np.mean(flight_times))
    std_flight = float(np.std(flight_times))
    var_flight = float(np.var(flight_times))

    # percentiles
    p10 = float(np.percentile(intervals, 10))
    p25 = float(np.percentile(intervals, 25))
    p50 = float(np.percentile(intervals, 50))
    p75 = float(np.percentile(intervals, 75))
    p90 = float(np.percentile(intervals, 90))

    # bursts: consecutive intervals under threshold (e.g., 150ms)
    burst_threshold = 150
    burst_min_len = 3
    bursts = 0
    cur = 0
    for iv in intervals:
        if iv < burst_threshold:
            cur += 1
        else:
            if cur >= burst_min_len:
                bursts += 1
            cur = 0
    if cur >= burst_min_len:
        bursts += 1
    burst_frequency = bursts / max(total_duration_sec / 60.0, 1.0)

    # entropy over discretized interval bins
    try:
        bins = np.histogram_bin_edges(intervals, bins='auto')
        hist, _ = np.histogram(intervals, bins=bins)
        probs = hist / np.sum(hist)
        probs = probs[probs > 0]
        hold_entropy = float(-np.sum(probs * np.log2(probs)))
    except Exception:
        hold_entropy = 0.0

    # backspace / delete stats and correction streaks (if keys present)
    backspace_count = 0
    delete_count = 0
    max_corr_streak = 0
    cur_streak = 0
    typed_chars = []
    for ev in normalized_events:
        k = ev.get('key', '') if isinstance(ev.get('key', ''), str) else ''
        if k == 'Backspace':
            backspace_count += 1
            cur_streak += 1
        else:
            if cur_streak > max_corr_streak:
                max_corr_streak = cur_streak
            cur_streak = 0
        if k == 'Delete':
            delete_count += 1
        # capture typed characters for digraphs if available
        if k and len(k) == 1:
            typed_chars.append(k)
    if cur_streak > max_corr_streak:
        max_corr_streak = cur_streak

    backspace_ratio = float(backspace_count / max(1, len(normalized_events)))

    # digraph timing for common digraphs
    common = ['th', 'er', 'in', 'an']
    digraph_means = {d: [] for d in common}
    # build timestamps map for characters sequence
    char_times = []
    for ev in normalized_events:
        k = ev.get('key', '')
        ts = ev.get('timestamp', None)
        if ev.get('type') == 'keydown' and isinstance(k, str) and len(k) == 1 and ts is not None:
            char_times.append((k, int(ts)))
    for i in range(1, len(char_times)):
        prev_c, prev_t = char_times[i - 1]
        cur_c, cur_t = char_times[i]
        pair = (prev_c + cur_c).lower()
        if pair in digraph_means:
            digraph_means[pair].append(cur_t - prev_t)
    # aggregate
    digraph_features = {}
    for d in common:
        vals = digraph_means.get(d, [])
        digraph_features[f'digraph_{d}'] = float(np.mean(vals)) if len(vals) > 0 else 0.0

    variation_ratio = std_hold / max(mean_hold, 1.0)
    consistency_score = float(max(0.0, min(1.0, 1.0 - min(variation_ratio, 1.0))))
    pause_frequency = float(pauses / max(total_duration_sec, 1.0))

    features = {
        'mean_hold_time': mean_hold,
        'median_hold_time': median_hold,
        'std_hold_time': std_hold,
        'var_hold_time': var_hold,
        'mean_flight_time': mean_flight,
        'std_flight_time': std_flight,
        'var_flight_time': var_flight,
        'typing_speed': typing_speed,
        'error_proxy': 0.0,
        'consistency_score': consistency_score,
        'pause_frequency': pause_frequency,
        'pause_count_long': pauses,
        'longest_pause': float(np.max(intervals)),
        'hold_entropy': hold_entropy,
        'burst_frequency': burst_frequency,
        'backspace_count': backspace_count,
        'backspace_ratio': backspace_ratio,
        'delete_count': delete_count,
        'max_correction_streak': max_corr_streak,
    }
    features.update(digraph_features)

    return features


def get_random_sample_text():
    """Return one random typing prompt from the prepared prompt pool."""
    return random.choice(SAMPLE_TEXTS)


def session_to_feature_dict(session_obj):
    """Convert a TypingSession object to feature dict for auth matching."""
    return {
        'mean_hold_time': float(session_obj.mean_hold_time or 0.0),
        'std_hold_time': float(session_obj.std_hold_time or 0.0),
        'mean_flight_time': float(session_obj.mean_flight_time or 0.0),
        'std_flight_time': float(session_obj.std_flight_time or 0.0),
        'typing_speed': float(session_obj.typing_speed or 0.0),
        'error_proxy': float(session_obj.error_proxy or 0.0),
        'consistency_score': float(session_obj.consistency_score or 0.0),
        'pause_frequency': float(session_obj.pause_frequency or 0.0)
    }


def calculate_auth_match_score(current_features, previous_sessions):
    """Calculate account match score (0-100) against historical typing profile."""
    if not previous_sessions:
        return 100.0

    feature_weights = {
        'mean_hold_time': 0.20,
        'std_hold_time': 0.10,
        'mean_flight_time': 0.20,
        'std_flight_time': 0.10,
        'typing_speed': 0.15,
        'consistency_score': 0.15,
        'pause_frequency': 0.10
    }

    weighted_similarity = 0.0
    total_weight = 0.0

    for feature_name, weight in feature_weights.items():
        values = [
            float(getattr(s, feature_name, 0.0) or 0.0)
            for s in previous_sessions
            if getattr(s, feature_name, None) is not None
        ]

        if not values:
            continue

        baseline_mean = float(np.mean(values))
        baseline_std = float(np.std(values))

        current_value = float(current_features.get(feature_name, baseline_mean))

        adaptive_std = baseline_std
        if adaptive_std < 1e-6:
            adaptive_std = max(abs(baseline_mean) * 0.1, 0.1)

        # Similarity is 1.0 at baseline mean and smoothly decreases with distance.
        z_distance = abs(current_value - baseline_mean) / (2.5 * adaptive_std)
        similarity = max(0.0, 1.0 - min(z_distance, 1.0))

        weighted_similarity += similarity * weight
        total_weight += weight

    if total_weight <= 0.0:
        return 100.0

    return round((weighted_similarity / total_weight) * 100.0, 1)


def build_session_auth_scores(sessions_asc):
    """Build per-session auth score map using only prior sessions as reference."""
    score_map = {}
    seen_sessions = []

    for session_obj in sessions_asc:
        features = session_to_feature_dict(session_obj)
        score = calculate_auth_match_score(features, seen_sessions)
        score_map[session_obj.id] = {
            'auth_match_score': float(score),
            'auth_verified': bool(score >= 65.0)
        }
        seen_sessions.append(session_obj)

    return score_map


def verify_user_identity(current_features, previous_sessions):
    """Heuristic verification against user's historical typing profile."""
    return calculate_auth_match_score(current_features, previous_sessions) >= 65.0

def generate_interpretation(stress_pred, consistency, typing_speed):
    """Generate AI interpretation of typing pattern"""
    
    stress_level = "HIGH" if stress_pred == 1 else "LOW"
    
    messages = []
    
    # Stress level
    if stress_pred == 1:
        messages.append("High stress detected in your keystroke pattern")
    else:
        messages.append("Low stress detected. You appear relaxed")
    
    # Consistency analysis
    if consistency > 0.8:
        messages.append("Excellent consistency. Very steady typing")
    elif consistency > 0.6:
        messages.append("Good consistency. Relatively steady typing")
    elif consistency > 0.4:
        messages.append("Moderate consistency. Some variation in typing")
    else:
        messages.append("Low consistency. Highly variable typing pattern")
    
    # Typing speed analysis
    if typing_speed > 8:
        messages.append("Fast typing speed")
    elif typing_speed > 4:
        messages.append("Moderate typing speed")
    else:
        messages.append("Slower typing speed")
    
    # Recommendations
    recommendations = []
    if stress_pred == 1:
        recommendations.append("Take breaks to reduce stress")
        recommendations.append("Practice relaxation techniques")
        recommendations.append("Ensure good posture and environment")
    else:
        recommendations.append("Keep maintaining this relaxed state")
        recommendations.append("Your typing pattern is healthy")
    
    return {
        'stress_level': stress_level,
        'observations': messages,
        'recommendations': recommendations
    }


# ============================================================================
# ERROR HANDLERS
# ============================================================================

@app.errorhandler(404)
def not_found(e):
    return jsonify({'error': 'Not found'}), 404


@app.errorhandler(500)
def server_error(e):
    return jsonify({'error': 'Server error'}), 500


@app.route('/health')
def health():
    """Health check endpoint for load balancers and local checks."""
    return jsonify({'status': 'ok', 'timestamp': datetime.now().isoformat()})


# ============================================================================
# DATABASE INITIALIZATION
# ============================================================================

def init_db():
    """Initialize database"""
    with app.app_context():
        # Create any missing tables first
        db.create_all()
        try:
            print('SQLALCHEMY DB URL:', db.engine.url)
        except Exception:
            try:
                print('session bind:', db.session.bind)
            except Exception:
                pass

        # Lightweight migration: ensure new columns exist on existing tables
        try:
            # Check if 'feature_blob' column exists in typing_sessions
            res = db.session.execute(text("PRAGMA table_info('typing_sessions')")).fetchall()
            cols = [r[1] for r in res]
            if 'feature_blob' not in cols:
                try:
                    db.session.execute(text("ALTER TABLE typing_sessions ADD COLUMN feature_blob TEXT"))
                    db.session.commit()
                    print("Added missing column: typing_sessions.feature_blob")
                except Exception as e:
                    db.session.rollback()
                    print(f"Failed to add feature_blob column: {e}")
        except Exception:
            # If PRAGMA or ALTER not supported for the DB engine, skip migration
            pass

        print("Database initialized")


def table_has_column(table_name, column_name):
    try:
        inspector = inspect(db.engine)
        cols = [c['name'] for c in inspector.get_columns(table_name)]
        return column_name in cols
    except Exception:
        return False


def compute_continuous_score_for_user(user_id: int, window: int = 5) -> float:
    """Compute a rolling auth match score for a user using their recent sessions."""
    with app.app_context():
        sessions = TypingSession.query.filter_by(user_id=user_id).order_by(TypingSession.created_at.desc()).limit(window + 1).all()
        if not sessions:
            return 100.0
        # latest is current; previous are the rest
        current = sessions[0]
        previous = sessions[1:]
        current_features = session_to_feature_dict(current)
        score = calculate_auth_match_score(current_features, previous)
        return float(score)


def update_continuous_status_for_user(user_id: int, score: float, threshold: float) -> None:
    with app.app_context():
        status = ContinuousAuthStatus.query.filter_by(user_id=user_id).first()
        is_auth = score >= threshold
        if not status:
            status = ContinuousAuthStatus(user_id=user_id, last_score=score, is_authenticated=is_auth)
            db.session.add(status)
        else:
            status.last_score = score
            status.is_authenticated = is_auth
        try:
            db.session.commit()
        except Exception:
            db.session.rollback()


def continuous_auth_checker(interval: int = 60, threshold: float = 65.0):
    """Background loop that periodically recomputes continuous auth for all users."""
    while True:
        try:
            with app.app_context():
                users = User.query.all()
                for u in users:
                    try:
                        score = compute_continuous_score_for_user(u.id)
                        update_continuous_status_for_user(u.id, score, threshold)
                    except Exception:
                        continue
        except Exception:
            pass
        time.sleep(interval)


def start_continuous_auth_checker():
    """Start the background thread for continuous auth if not already running."""
    interval = int(os.environ.get('KEYSTROKE_CONTINUOUS_INTERVAL', '60'))
    threshold = float(os.environ.get('KEYSTROKE_CONTINUOUS_THRESHOLD', '65.0'))
    t = threading.Thread(target=continuous_auth_checker, args=(interval, threshold), daemon=True)
    t.start()


def init_app():
    """Initialize Flask app, database, and background services."""
    init_db()
    start_continuous_auth_checker()
    print("Continuous authentication checker started")


if __name__ == '__main__':
    try:
        init_app()
    except Exception as exc:
        print(f'Application initialization failed: {exc}')
        raise
    # Allow configuring host/port via environment for flexibility
    host = os.environ.get('KEYSTROKE_HOST', '0.0.0.0')
    port = int(os.environ.get('KEYSTROKE_PORT', '5000'))
    debug = os.environ.get('FLASK_DEBUG', '1') == '1'
    # Run without auto-reloader to keep logs stable during debugging
    app.run(debug=debug, use_reloader=False, host=host, port=port)
