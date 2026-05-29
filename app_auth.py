"""
Flask web application with User Authentication for Keystroke Dynamics
"""

import os
import sys
import json
import joblib
import random
from datetime import datetime, timedelta
from functools import wraps
import hashlib

from flask import Flask, render_template, jsonify, request, send_file, redirect, url_for, session
from flask_sqlalchemy import SQLAlchemy
import numpy as np
import traceback

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from metrics_tracker import MetricsTracker
from load_data import load_cmu
from features import extract_cmu_features

# Initialize Flask app
app = Flask(__name__, template_folder='templates', static_folder='static')
app.config['JSON_SORT_KEYS'] = False
app.secret_key = 'keystroke_dynamics_secret_2026'  # Change in production
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///keystroke_db.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False


@app.after_request
def add_no_cache_headers(response):
    """Disable client-side caching so UI changes appear immediately in development."""
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response

# Initialize database
db = SQLAlchemy(app)

# Initialize metrics tracker
tracker = MetricsTracker()

# Get base directory
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

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
        self.password_hash = hashlib.sha256(password.encode()).hexdigest()
    
    def check_password(self, password):
        """Verify password"""
        return self.password_hash == hashlib.sha256(password.encode()).hexdigest()


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
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        """Convert to dictionary for JSON serialization"""
        rf_conf = float(self.rf_confidence or 0.0)
        xgb_conf = float(self.xgb_confidence or 0.0)
        if self.rf_confidence is not None and self.xgb_confidence is not None:
            ensemble_conf = float((rf_conf + xgb_conf) / 2.0)
        else:
            ensemble_conf = float(max(rf_conf, xgb_conf))
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
            'duration_ms': self.duration_ms
        }


# ============================================================================
# MODEL LOADING
# ============================================================================

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


# ============================================================================
# AUTHENTICATION DECORATORS
# ============================================================================

def login_required(f):
    """Require user login"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
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
    return render_template('typing_baseline.html', sample_text=get_random_sample_text())


@app.route('/verify-typing', methods=['GET', 'POST'])
@login_required
def verify_typing():
    """Verify user typing and analyze patterns"""
    if request.method == 'POST':
        try:
            data = request.json or {}
            user_id = session.get('user_id')
            typed_text = data.get('typed_text', '')
            keystroke_data = data.get('keystroke_data', [])

            features = calculate_keystroke_features(keystroke_data, typed_text)

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
            is_verified = auth_match_score >= 65.0

            duration_ms = 0
            if len(keystroke_data) >= 2:
                duration_ms = int(max(0, keystroke_data[-1].get('timestamp', 0) - keystroke_data[0].get('timestamp', 0)))

            session_record = TypingSession(
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
            db.session.add(session_record)
            db.session.commit()

            return jsonify({
                'success': True,
                'session_id': session_record.id,
                'is_verified': bool(is_verified),
                'auth_match_score': float(auth_match_score)
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
                         regular_count=regular_count)


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
            session_record = TypingSession(
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
        keystroke_data = data.get('keystroke_data', [])

        print('typed_text length:', len(typed_text), 'keystrokes length:', len(keystroke_data))
        features = calculate_keystroke_features(keystroke_data, typed_text)

        duration_ms = 0
        if len(keystroke_data) >= 2:
            duration_ms = int(max(0, keystroke_data[-1].get('timestamp', 0) - keystroke_data[0].get('timestamp', 0)))

        baseline_session = TypingSession(
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
            rf_confidence=0.5,
            xgb_prediction=0,
            xgb_confidence=0.5,
            ensemble_prediction=0,
            num_keystrokes=len(keystroke_data),
            duration_ms=duration_ms,
            text_typed='baseline_profile',
        )
        db.session.add(baseline_session)
        db.session.commit()

        return jsonify({'success': True, 'session_id': baseline_session.id}), 201
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

    return jsonify(payload), 200


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
            'auth_match_score': float(score_map.get(s.id, {}).get('auth_match_score', 100.0))
        }
        for s in current_user_sessions
    ]

    peer_summary = []
    users = User.query.order_by(User.username.asc()).all()
    for u in users:
        user_sessions = TypingSession.query.filter_by(user_id=u.id).all()
        if not user_sessions:
            continue

        peer_summary.append({
            'username': u.username,
            'total_sessions': len(user_sessions),
            'avg_speed': float(np.mean([s.typing_speed for s in user_sessions])),
            'regular_count': len([s for s in user_sessions if s.ensemble_prediction == 0]),
            'stressed_count': len([s for s in user_sessions if s.ensemble_prediction == 1])
        })

    return jsonify({
        'current_user_timeline': timeline,
        'peer_summary': peer_summary
    })


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

    timestamps = [int(k.get('timestamp', 0)) for k in keystroke_data if 'timestamp' in k]
    if len(timestamps) < 2:
        return default_features

    intervals = []
    pauses = 0
    for i in range(1, len(timestamps)):
        delta = max(0, timestamps[i] - timestamps[i - 1])
        if delta > 0:
            intervals.append(delta)
            if delta >= 1000:
                pauses += 1

    if not intervals:
        intervals = [100.0]

    total_duration_sec = max((timestamps[-1] - timestamps[0]) / 1000.0, 0.1)
    typing_speed = min(len(text_typed) / total_duration_sec, 20.0)

    mean_hold = float(np.mean(intervals))
    median_hold = float(np.median(intervals))
    std_hold = float(np.std(intervals))
    var_hold = float(np.var(intervals))
    mean_flight = float(np.mean(intervals) * 0.5)
    std_flight = float(np.std(intervals) * 0.5)
    var_flight = float(np.var(intervals) * 0.25)

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
    for ev in keystroke_data:
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

    backspace_ratio = float(backspace_count / max(1, len(keystroke_data)))

    # digraph timing for common digraphs
    common = ['th', 'er', 'in', 'an']
    digraph_means = {d: [] for d in common}
    # build timestamps map for characters sequence
    char_times = []
    for ev in keystroke_data:
        k = ev.get('key', '')
        ts = ev.get('timestamp', None)
        if isinstance(k, str) and len(k) == 1 and ts is not None:
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
            res = db.session.execute("PRAGMA table_info('typing_sessions')").fetchall()
            cols = [r[1] for r in res]
            if 'feature_blob' not in cols:
                try:
                    db.session.execute("ALTER TABLE typing_sessions ADD COLUMN feature_blob TEXT")
                    db.session.commit()
                    print("Added missing column: typing_sessions.feature_blob")
                except Exception as e:
                    db.session.rollback()
                    print(f"Failed to add feature_blob column: {e}")
        except Exception:
            # If PRAGMA or ALTER not supported for the DB engine, skip migration
            pass

        print("Database initialized")


if __name__ == '__main__':
    init_db()
    # Allow configuring host/port via environment for flexibility
    host = os.environ.get('KEYSTROKE_HOST', '0.0.0.0')
    port = int(os.environ.get('KEYSTROKE_PORT', '5000'))
    debug = os.environ.get('FLASK_DEBUG', '1') == '1'
    # Run without auto-reloader to keep logs stable during debugging
    app.run(debug=debug, use_reloader=False, host=host, port=port)
