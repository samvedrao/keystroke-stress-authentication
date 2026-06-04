# Keystroke Dynamics Authentication and Stress Detection Project

## 1. Project Overview

This project is a web-based keystroke dynamics system. It studies how a person types and uses those typing patterns for two main goals:

1. **Stress detection**: The system predicts whether a typing sample indicates low stress or high stress.
2. **User authentication / identity verification**: The system checks whether the current typing pattern looks similar to the user's own previous typing behavior.

The project combines a machine learning training pipeline, trained model artifacts, a Flask web application, user accounts, SQLite persistence, frontend typing capture, dashboards, analytics pages, model health pages, export endpoints, and continuous authentication logic.

The main application file is `app_auth.py`. There is also a simpler earlier dashboard app in `app.py`, but `app_auth.py` is the more complete version because it includes signup, login, baseline enrollment, verification, stress prediction, session history, continuous authentication, exports, admin summary, and model diagnostics.

At a high level, the system works like this:

1. A user creates an account.
2. The user types several prompted samples to create a baseline typing profile.
3. The browser records raw keydown and keyup events with timestamps.
4. The backend extracts timing features such as hold time, flight time, typing speed, pause frequency, and consistency.
5. During verification, the system compares the current typing sample with the user's previous sessions to estimate an authentication match score.
6. The same sample is also passed through trained stress models, Random Forest and XGBoost.
7. The app stores the session, model results, extracted features, quality information, and sanitized replay data in the database.
8. Dashboards and APIs expose the results for history, analytics, model health, and reporting.

## 2. Main Technologies Used

### Backend

The backend is built with **Python** and **Flask**.

Important backend technologies:

- **Flask**: Web framework used for routes, templates, request handling, sessions, and JSON APIs.
- **Flask-SQLAlchemy**: ORM layer used to define and interact with database models.
- **SQLite**: Local database engine. The configured default database URI is `sqlite:///keystroke_db.db`.
- **Werkzeug security**: Used for password hashing and password verification.
- **joblib**: Used to load and save trained machine learning model files.
- **NumPy**: Used for statistical feature calculations and scoring.
- **Pandas**: Used in the model training pipeline for dataset loading and preprocessing.
- **scikit-learn**: Used for Random Forest, Isolation Forest, train/test split, metrics, preprocessing, and model evaluation.
- **XGBoost**: Used for gradient boosted tree stress classification.
- **Matplotlib and Seaborn**: Used to generate training/evaluation plots.
- **python-dotenv**: Used when available to load environment variables from `.env`. The config now has a fallback if it is not installed.

### Frontend

The frontend uses standard web technologies:

- **HTML templates** in the `templates/` directory.
- **CSS** in `static/style.css`, `static/typing.css`, and inline page styles.
- **JavaScript** in `static/typing.js` and embedded scripts in templates.
- **Fetch API** for sending typing data to Flask endpoints.

The frontend captures typing behavior by listening to:

- `keydown`
- `keyup`
- `input`
- `paste`

For baseline and verification pages, paste is blocked and recorded as a quality issue because pasted text would not represent natural typing behavior.

## 3. Important Project Files and Folders

### Root application files

- `app_auth.py`: Main full application. Contains Flask setup, database models, routes, feature extraction, authentication scoring, stress prediction, analytics, exports, and background continuous authentication.
- `app.py`: Simpler dashboard version. It exposes model status, stress prediction, authentication prediction, metrics, and download routes.
- `main.py`: End-to-end training pipeline entry point.
- `requirements.txt`: Python dependencies.
- `pytest.ini`: Pytest configuration.

### Source modules

- `src/load_data.py`: Loads CMU and free-text datasets.
- `src/features.py`: Extracts features from training datasets.
- `src/stress_labels.py`: Generates synthetic stress labels from keystroke features.
- `src/model_stress.py`: Trains Random Forest and XGBoost stress classifiers.
- `src/model_auth.py`: Trains per-user Isolation Forest authentication models.
- `src/evaluate.py`: Generates combined training report and stores metrics.
- `src/metrics_tracker.py`: Persists and summarizes training metrics.

### Extended project modules

- `keystroke_project/config.py`: Environment-based Flask/app configuration.
- `keystroke_project/src/features_ext.py`: More advanced keystroke feature extraction.
- `keystroke_project/src/continuous_auth.py`: Continuous authentication anomaly checker.
- `keystroke_project/tests/`: Test suite for endpoints and feature extraction.

### Data and model artifacts

- `data/DSL-StrongPasswordData.csv`: CMU keystroke password dataset.
- `data/email_userInformation.csv`: Free-text keystroke dataset for email input.
- `data/fullname_userInformation.csv`: Free-text keystroke dataset for full name input.
- `data/phone_userInformation.csv`: Free-text keystroke dataset for phone input.
- `outputs/models/stress_random_forest.pkl`: Trained Random Forest stress model.
- `outputs/models/stress_xgboost.pkl`: Trained XGBoost stress model.
- `outputs/models/auth_models.pkl`: Dictionary of trained per-user Isolation Forest models.
- `outputs/plots/stress_confusion_matrix.png`: Stress model confusion matrix plot.
- `outputs/plots/stress_feature_importance.png`: XGBoost feature importance plot.
- `outputs/plots/auth_accuracy.png`: Per-user authentication accuracy plot.
- `outputs/training_metrics.json`: Historical training metrics.
- `outputs/stress_auth_report.txt`: Generated training summary report.

## 4. Datasets Used

### 4.1 CMU DSL Strong Password Dataset

File: `data/DSL-StrongPasswordData.csv`

This is the main dataset used by the training pipeline. It contains **20,400 rows**. The columns include:

- `subject`: User identifier.
- `sessionIndex`: Session number.
- `rep`: Repetition number.
- Timing columns such as:
  - `H.*`: hold/dwell time columns.
  - `DD.*`: down-down latency columns.
  - `UD.*`: up-down or flight timing columns.

The training pipeline groups this data by `subject` and `sessionIndex`, then extracts statistical timing features for each user/session.

### 4.2 Free-text User Information Datasets

The project also includes free-text style datasets:

- `data/email_userInformation.csv`: **24,595 rows**
- `data/fullname_userInformation.csv`: **20,166 rows**
- `data/phone_userInformation.csv`: **11,164 rows**

Each has columns:

- `id`
- `single_alphabet`
- `di-graph`
- `Dwell_time`
- `Interval_time`
- `Latency_time`
- `Flight_time`
- `Uptoup_time`

These datasets are loaded by `load_freetext()` and combined into one dataframe with an added `input_type` column indicating whether the source is `email`, `fullname`, or `phone`.

In the current `main.py` pipeline, both CMU and free-text data are loaded and features are extracted, but the stress labels and model training are based mainly on the CMU feature dataframe.

## 5. Machine Learning Pipeline

The full training pipeline is in `main.py`. It performs these steps:

1. Load CMU and free-text datasets.
2. Extract keystroke features.
3. Generate stress labels.
4. Train stress classification models.
5. Train per-user authentication models.
6. Generate a combined report and metrics.

### 5.1 Data Loading

`src/load_data.py` loads the datasets.

`load_cmu()`:

- Reads `data/DSL-StrongPasswordData.csv`.
- Fills missing numeric values with column means.
- Returns the cleaned dataframe.

`load_freetext()`:

- Reads email, fullname, and phone CSV files if they exist.
- Adds `input_type` to each dataframe.
- Concatenates them.
- Fills numeric missing values with means.

### 5.2 Feature Extraction for Training

`src/features.py` extracts features from datasets.

For the CMU dataset, `extract_cmu_features()` groups data by:

- `subject`
- `sessionIndex`

It then calculates:

- `mean_hold_time`
- `median_hold_time`
- `std_hold_time`
- `var_hold_time`
- hold time percentiles
- `longest_pause`
- `hold_entropy`
- `mean_flight_time`
- `std_flight_time`
- `var_flight_time`
- `mean_dd_time`
- `typing_speed`
- `error_proxy`
- `consistency_score`
- `pause_frequency`

Important feature meanings:

- **Hold time / dwell time**: How long a key is held down.
- **Flight time**: Time between release of one key and pressing the next key.
- **Down-down time**: Time between one key press and the next key press.
- **Typing speed**: Approximate typing rate.
- **Error proxy**: Coefficient of variation of hold times, calculated as `std_hold_time / mean_hold_time`.
- **Consistency score**: `1 - error_proxy`, bounded between 0 and 1.
- **Pause frequency**: Number of unusually long hold times or intervals.
- **Entropy**: How unpredictable the timing distribution is.

### 5.3 Stress Label Generation

`src/stress_labels.py` generates stress labels. This is a very important point for a report: the project does not appear to use externally measured stress labels. Instead, it creates labels from keystroke-derived behavior.

The stress score is calculated using normalized features:

- normalized `std_hold_time`, weight `0.30`
- normalized `std_flight_time`, weight `0.30`
- normalized `error_proxy`, weight `0.25`
- inverse normalized `typing_speed`, weight `0.15`

Formula:

```text
stress_score =
  0.30 * norm_std_hold_time
+ 0.30 * norm_std_flight_time
+ 0.25 * norm_error_proxy
+ 0.15 * (1 - norm_typing_speed)
```

Then:

- `stress_label = 1` if `stress_score >= 0.5`
- `stress_label = 0` if `stress_score < 0.5`

Meaning:

- `0`: Low stress
- `1`: High stress

Interpretation:

The stress model is learning to reproduce a rule-based stress label derived from timing variability and speed. Higher variability and slower typing increase the stress score.

## 6. Stress Detection Models

Stress classification is implemented in `src/model_stress.py`.

The project trains two supervised classification models:

1. **Random Forest Classifier**
2. **XGBoost Classifier**

Both use the same eight core features:

- `mean_hold_time`
- `std_hold_time`
- `mean_flight_time`
- `std_flight_time`
- `typing_speed`
- `error_proxy`
- `consistency_score`
- `pause_frequency`

### 6.1 Random Forest Model

The Random Forest is configured with:

- `n_estimators=200`
- `max_depth=15`
- `min_samples_split=5`
- `min_samples_leaf=2`
- `random_state=42`
- `n_jobs=-1`
- `class_weight='balanced'`

Random Forest is an ensemble of decision trees. Each tree learns decision rules from random subsets of features and samples. The final prediction is based on the vote of many trees. It is useful here because keystroke behavior is non-linear and noisy.

### 6.2 XGBoost Model

The XGBoost model is configured with:

- `n_estimators=200`
- `learning_rate=0.05`
- `max_depth=7`
- `min_child_weight=1`
- `subsample=0.8`
- `colsample_bytree=0.8`
- `random_state=42`
- `eval_metric='logloss'`
- `tree_method='hist'`

XGBoost builds trees sequentially, where each tree improves on mistakes from previous trees. It is generally strong for tabular data and can capture complex feature interactions.

### 6.3 Stress Model Evaluation

The pipeline splits data into training and test sets:

- 80% training
- 20% testing
- stratified by stress label
- `random_state=42`

Generated metrics from `outputs/stress_auth_report.txt`:

- Random Forest Accuracy: `1.0000`
- XGBoost Accuracy: `1.0000`
- Best Model: `XGBoost`

Report caveat:

The 100% accuracy should be interpreted carefully because stress labels are generated from the same kinds of features used to train the models. This can make the classification task easier than predicting medically verified or survey-verified stress.

### 6.4 Runtime Stress Prediction

At runtime, `app_auth.py` loads the trained stress models from:

- `outputs/models/stress_random_forest.pkl`
- `outputs/models/stress_xgboost.pkl`

It also checks for calibrated model artifacts:

- `outputs/models/stress_random_forest_calibrated.pkl`
- `outputs/models/stress_xgboost_calibrated.pkl`

If calibrated models exist, the app prefers them. Otherwise, it uses the normal saved models.

During verification:

1. The browser sends raw keystroke events to `/verify-typing`.
2. The backend extracts features.
3. The eight core features are converted into a NumPy array.
4. Random Forest predicts low/high stress.
5. XGBoost predicts low/high stress.
6. Both models return class probabilities.
7. The app computes an ensemble prediction using confidence-weighted voting.
8. Results are stored in the `typing_sessions` table.

The ensemble formula is essentially:

```text
ensemble = round(
  (rf_prediction * rf_confidence + xgb_prediction * xgb_confidence)
  / (rf_confidence + xgb_confidence)
)
```

## 7. Authentication and Identity Verification

The project has two authentication meanings:

1. **Normal account authentication**: username/password login.
2. **Behavioral authentication**: verifying the user's identity by typing pattern.

### 7.1 Signup / Registration

The registration route is `/register`.

Flow:

1. User submits username, email, and password.
2. The backend validates:
   - all fields are present
   - username length is between 3 and 20 characters
   - password length is at least 6 characters
   - username is unique
   - email is unique
3. The password is hashed using Werkzeug PBKDF2.
4. A new `User` row is inserted into the database.
5. The user is automatically logged in.
6. The user is redirected to `/setup-typing` to create a typing baseline.

### 7.2 Password Storage

The `User` model has:

- `id`
- `username`
- `email`
- `password_hash`
- `created_at`

Passwords are not stored directly. `User.set_password()` uses:

```text
generate_password_hash(password, method='pbkdf2:sha256', salt_length=16)
```

`User.check_password()` supports:

- modern PBKDF2 hashes
- legacy SHA256 hashes

If a legacy SHA256 hash is detected and the password is correct, the system upgrades it to PBKDF2.

### 7.3 Login

The login route is `/login`.

Flow:

1. User submits username and password.
2. The backend looks up the user by username.
3. It checks the password using `check_password()`.
4. If valid, Flask session values are set:
   - `session['user_id']`
   - `session['username']`
5. The session is marked permanent.
6. Session lifetime is set to 7 days.
7. The user is redirected to `/dashboard`.

### 7.4 Protected Routes

The `login_required` decorator protects pages and APIs.

If a user is not logged in:

- API requests return JSON `401 Authentication required`.
- Browser page requests redirect to `/login`.

Protected pages include:

- dashboard
- typing verification
- history
- profile
- model health
- model comparison
- admin
- user stats
- exports
- continuous authentication endpoints

## 8. Baseline Enrollment

After signup, the user is sent to `/setup-typing`.

The system uses baseline typing sessions to learn the user's normal typing rhythm. The constant:

```text
BASELINE_TARGET_SAMPLES = 3
```

means the app expects three baseline samples.

### 8.1 Baseline UI

The page `templates/typing_baseline.html` displays:

- a random sample text
- a typing textarea
- progress bar
- character count
- typing speed
- accuracy
- duration
- baseline round count
- quality score
- status label

The page records keydown and keyup events:

```text
{
  timestamp: Date.now(),
  key: e.key,
  type: 'keydown' or 'keyup'
}
```

Paste is blocked and recorded as a `paste` event.

### 8.2 Saving Baseline

Baseline samples are sent to `/save-baseline`.

The backend:

1. Reads `typed_text`, `sample_text`, and `keystroke_data`.
2. Calculates character-level accuracy.
3. Rejects the sample if accuracy is below `BASELINE_MIN_ACCURACY = 0.75`.
4. Extracts keystroke features.
5. Evaluates sample quality.
6. Saves a `TypingSession` row with:
   - timing features
   - `text_typed='baseline_profile'`
   - no stress confidence
   - `is_baseline=True` inside the feature blob
   - sanitized keystroke events
7. Returns updated baseline progress.
8. If fewer than three samples are complete, it sends a new random sample text.
9. If complete, the frontend redirects to the dashboard.

### 8.3 Baseline Quality Checks

`evaluate_sample_quality()` checks:

- paste detection
- minimum number of keystroke events
- minimum duration
- unrealistic typing speed
- text accuracy

Important constants:

- `QUALITY_MIN_KEYSTROKES = 8`
- `QUALITY_MIN_DURATION_MS = 800`
- `MAX_REASONABLE_TYPING_SPEED = 18.0`
- `BASELINE_MIN_ACCURACY = 0.75`

The quality score starts at 100 and subtracts penalties for suspicious or low-quality samples.

## 9. Typing Verification

Typing verification is handled by `/verify-typing`.

### 9.1 Verification UI

The page `templates/typing_verify.html` shows a random sample text and asks the logged-in user to type it.

It records:

- keydown timestamps
- keyup timestamps
- typed text
- duration
- typing speed
- accuracy

When the sample is complete, it sends the data to `/verify-typing`.

### 9.2 Backend Verification Flow

On POST `/verify-typing`, the backend:

1. Gets current user ID from the Flask session.
2. Reads typed text, sample text, and keystroke events.
3. Extracts keystroke features.
4. Evaluates sample quality.
5. Loads stress models.
6. Predicts stress using Random Forest and XGBoost.
7. Computes ensemble stress prediction.
8. Loads all previous typing sessions for that user.
9. Computes an authentication match score.
10. Decides whether the user is verified.
11. Saves the session to the database.
12. Returns verification status and session ID.

### 9.3 Authentication Match Score

The behavioral authentication score is computed by `calculate_auth_match_score()`.

It compares current features to previous sessions using weighted similarity.

Features and weights:

- `mean_hold_time`: `0.20`
- `std_hold_time`: `0.10`
- `mean_flight_time`: `0.20`
- `std_flight_time`: `0.10`
- `typing_speed`: `0.15`
- `consistency_score`: `0.15`
- `pause_frequency`: `0.10`

For each feature:

1. Compute baseline mean from previous sessions.
2. Compute baseline standard deviation.
3. Compute distance between current value and baseline mean.
4. Convert the distance into a similarity score.
5. Add weighted similarity.

The final score is scaled to 0-100.

Authentication threshold:

```text
AUTH_RETRY_THRESHOLD = 65.0
```

If:

```text
auth_match_score >= 65
```

the user is considered behaviorally verified.

If the score is below 65, or if the quality check fails, the frontend recommends retrying.

## 10. Continuous Authentication

The project includes continuous authentication, which means it periodically recomputes whether users still look legitimate based on recent typing sessions.

There are two related implementations:

- `keystroke_project/src/continuous_auth.py`
- continuous authentication functions inside `app_auth.py`

### 10.1 Anomaly Score Version

`keystroke_project/src/continuous_auth.py` computes an anomaly score:

- `0`: trusted
- `100`: anomalous

It uses z-score deviation from the user's historical feature distribution.

Features checked:

- `mean_hold_time`
- `std_hold_time`
- `mean_flight_time`
- `std_flight_time`
- `typing_speed`
- `consistency_score`
- `pause_frequency`

If the anomaly score is above 75, the user is considered anomalous.

### 10.2 App Runtime Version

Inside `app_auth.py`, continuous authentication computes a rolling match score for recent sessions:

1. Get the latest session.
2. Get previous recent sessions as baseline.
3. Compute `calculate_auth_match_score()`.
4. Store result in `ContinuousAuthStatus`.

The table stores:

- `user_id`
- `last_score`
- `is_authenticated`
- `updated_at`

There is also a background daemon thread that periodically checks every user.

Runtime environment variables:

- `KEYSTROKE_CONTINUOUS_INTERVAL`, default `60`
- `KEYSTROKE_CONTINUOUS_THRESHOLD`, default `65.0`

The API `/api/continuous_status` returns the current user's continuous authentication state.

## 11. Database Design

The app uses SQLAlchemy models in `app_auth.py`.

### 11.1 User Table

Table: `users`

Fields:

- `id`: primary key
- `username`: unique username
- `email`: unique email
- `password_hash`: hashed password
- `created_at`: account creation timestamp

Relationship:

- one user has many typing sessions

### 11.2 Typing Session Table

Table: `typing_sessions`

Fields:

- `id`
- `user_id`
- `mean_hold_time`
- `std_hold_time`
- `mean_flight_time`
- `std_flight_time`
- `typing_speed`
- `error_proxy`
- `consistency_score`
- `pause_frequency`
- `rf_prediction`
- `rf_confidence`
- `xgb_prediction`
- `xgb_confidence`
- `ensemble_prediction`
- `text_typed`
- `num_keystrokes`
- `duration_ms`
- `feature_blob`
- `created_at`

The `feature_blob` is a JSON text field that stores expanded feature data, quality information, sanitized keystroke events, baseline flags, and other details.

### 11.3 Continuous Authentication Table

Table: `continuous_auth`

Fields:

- `id`
- `user_id`
- `last_score`
- `is_authenticated`
- `updated_at`

This table stores the latest behavioral authentication status per user.

## 12. Keystroke Feature Extraction at Runtime

Runtime feature extraction is done by `calculate_keystroke_features()` in `app_auth.py`.

It normalizes events so each has:

- `timestamp`
- `key`
- `type`

It supports both:

- `timestamp`
- `time`

It supports both:

- `type`
- `event`

Events are sorted by timestamp.

### 12.1 Hold Time

Hold time is calculated from paired keydown and keyup events for the same key:

```text
hold_time = keyup_timestamp - keydown_timestamp
```

### 12.2 Flight Time

Flight time is calculated as:

```text
flight_time = next_keydown_timestamp - previous_keyup_timestamp
```

### 12.3 Fallback Behavior

If true hold or flight times cannot be calculated, the system uses intervals between consecutive timestamps as fallback. This makes the extractor robust even if some keyup events are missing.

### 12.4 Extracted Runtime Features

The runtime extractor calculates:

- `mean_hold_time`
- `median_hold_time`
- `std_hold_time`
- `var_hold_time`
- `mean_flight_time`
- `std_flight_time`
- `var_flight_time`
- `typing_speed`
- `error_proxy`
- `consistency_score`
- `pause_frequency`
- `pause_count_long`
- `longest_pause`
- `hold_entropy`
- `burst_frequency`
- `backspace_count`
- `backspace_ratio`
- `delete_count`
- `max_correction_streak`
- `digraph_th`
- `digraph_er`
- `digraph_in`
- `digraph_an`

The extended extractor in `keystroke_project/src/features_ext.py` also calculates:

- average digraph time
- average trigraph time
- common trigraph features such as `the`, `ing`, and `and`
- acceleration
- space-related timing
- shift count
- percentiles

## 13. Dashboards and Pages

### 13.1 Auth Page

Template: `templates/auth.html`

Used for registration and login. The same page switches between login and register tab states.

### 13.2 Dashboard

Route: `/dashboard`

Template: `templates/dashboard_pro.html`

Shows:

- recent sessions
- total sessions
- average typing speed
- best consistency
- regular vs stressed count
- authentication scores for sessions

### 13.3 Baseline Setup

Route: `/setup-typing`

Template: `templates/typing_baseline.html`

Used to create the initial typing profile.

### 13.4 Verification

Route: `/verify-typing`

Template: `templates/typing_verify.html`

Used to verify identity and run stress detection.

### 13.5 Analysis Results

Route: `/analysis-results`

Shows the result of a specific session, including model predictions, confidence, interpretation, and explanation.

### 13.6 History

Route: `/history`

Shows older typing sessions and trends.

### 13.7 Profile

Route: `/profile`

Shows account/profile information and likely baseline-related controls.

### 13.8 Model Health

Route: `/model-health`

Reports whether model artifacts exist, their sizes, modification dates, metrics, calibration status, and database URI.

### 13.9 Model Comparison

Route: `/model-comparison`

Compares Random Forest, XGBoost, and runtime ensemble.

### 13.10 Admin Dashboard

Route: `/admin`

Provides project-level overview:

- total users
- total sessions
- baseline sessions
- verification sessions
- stress sessions
- average auth match
- model health
- baseline target samples

## 14. API Endpoints

Important API endpoints:

- `GET /api/metrics`: all training metrics.
- `GET /api/metrics/latest`: most recent training metrics.
- `GET /api/metrics/summary`: aggregate metrics.
- `GET /api/models/status`: loaded model status.
- `GET /api/model-health`: detailed model artifact health.
- `GET /api/model-comparison`: model comparison payload.
- `GET /api/admin/overview`: admin/project summary.
- `GET /api/baseline/status`: current user's baseline progress.
- `POST /api/sample-quality`: evaluates sample quality.
- `POST /api/predict/stress`: predicts stress from feature payload.
- `POST /save-baseline`: saves baseline typing sample.
- `GET /api/session/<session_id>`: returns a session.
- `GET /api/session/<session_id>/replay`: returns sanitized replay events.
- `GET /api/user/sessions`: returns user sessions.
- `GET /api/user/stats`: returns aggregate user stats.
- `GET /api/analytics/overview`: returns timeline and peer summary.
- `GET /api/anomaly-timeline`: returns identity confidence over time.
- `GET /api/continuous_status`: returns continuous auth state.
- `GET /api/export/feature-blobs`: exports feature blobs as JSON.
- `GET /api/export/feature-blobs/csv`: exports feature blobs as CSV.

## 15. Model Outputs and Results

Current generated report:

```text
Random Forest Accuracy: 1.0000
XGBoost Accuracy:       1.0000
Best Stress Model:      XGBoost

Authentication Average Accuracy:  0.6699
Authentication Average Precision: 0.6464
Authentication Average Recall:    0.9216
```

Interpretation:

- Stress models perform perfectly on the generated-label test split.
- Authentication is more difficult because it must distinguish legitimate user samples from impostor samples.
- Authentication recall is high, meaning the system tends to accept many legitimate samples.
- Precision is lower, meaning there may be false accepts among accepted samples.

## 16. Security and Privacy Considerations

Security strengths:

- Passwords are hashed, not stored in plain text.
- PBKDF2 is used for new passwords.
- Legacy SHA256 passwords can be upgraded automatically.
- Protected routes require active sessions.
- API routes return `401` when unauthenticated.
- Paste is blocked during typing samples.
- Full raw keystroke content is sanitized for replay/debug export.

Potential concerns:

- The default production secret key is insecure if `FLASK_SECRET_KEY` is not set.
- SQLite is suitable for local/demo use but not ideal for a high-scale production deployment.
- Stress labels are synthetic/rule-generated, not clinically validated.
- Keystroke biometrics are behavioral signals and should not be treated as perfect identity proof.
- Model confidence may be overconfident without calibration.
- The app stores typed text and feature blobs, so privacy policy and retention rules would matter in a real deployment.

## 17. Testing

Tests are configured through `pytest.ini`.

Test folders:

- `keystroke_project/tests/test_features.py`
- `keystroke_project/tests/test_endpoints.py`

The tests cover:

- feature extraction returning dictionaries
- JSON serializability
- hold time calculation
- flight time calculation
- entropy
- empty input handling
- digraph extraction
- pause detection
- correction/backspace detection
- registration endpoint
- login endpoint
- save baseline endpoint
- verify typing endpoint
- continuous status endpoint
- export endpoints
- stress prediction endpoint
- protected route behavior
- database persistence

Last validation result:

```text
26 tests passed
```

## 18. Limitations and Future Improvements

Important limitations:

1. Stress labels are generated from rules, not from actual stress measurements.
2. Runtime authentication uses heuristic similarity scoring, even though trained Isolation Forest authentication models also exist.
3. Raw model probabilities may need calibration.
4. There is no external validation dataset for real-world stress detection.
5. SQLite and Flask sessions are appropriate for demo/local deployment, but production would need stronger deployment architecture.
6. Keystroke behavior can vary due to keyboard type, fatigue, injuries, device changes, and environment.
7. Authentication threshold is fixed at 65 instead of personalized per user.
8. Some feature names differ between training extraction and extended runtime extraction, so careful alignment is important.

Good future improvements:

- Add survey-based or sensor-based real stress labels.
- Use calibrated probabilities for Random Forest and XGBoost.
- Train a dedicated runtime authentication model using each user's own baseline data.
- Add per-user adaptive thresholds.
- Use database migrations with Alembic.
- Add CSRF protection for forms.
- Add stronger password policy and email verification.
- Avoid storing raw typed text unless necessary.
- Add model drift detection.
- Add device/keyboard metadata.
- Add REST API documentation.
- Add role-based admin access.

## 19. One-Paragraph Summary for Report Introduction

This project implements a keystroke dynamics system for behavioral authentication and stress detection. It captures how users type through browser keydown and keyup events, extracts timing features such as hold time, flight time, speed, pauses, and consistency, and uses those features for two tasks. For stress detection, Random Forest and XGBoost classifiers are trained on generated stress labels derived from typing variability and speed. For identity verification, the system creates a baseline typing profile for each user and compares later samples against previous sessions using a weighted similarity score. The application is built with Flask, SQLAlchemy, SQLite, scikit-learn, XGBoost, Pandas, NumPy, and JavaScript, and includes signup, login, baseline enrollment, verification, stress analysis, session history, continuous authentication, model health, exports, and analytics dashboards.

