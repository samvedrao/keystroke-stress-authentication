# KEYSTROKE DYNAMICS AUTHENTICATION AND STRESS DETECTION SYSTEM

## TABLE OF CONTENTS

| Chapter No | Title of Chapter | Page No |
|---|---|---|
| 1 | INTRODUCTION | 1-2 |
| 2 | LITERATURE SURVEY | 3-5 |
| 3 | SYSTEM STUDY | 6-8 |
| 4 | SYSTEM ANALYSIS | 9-11 |
| 5 | SYSTEM DESIGN | 12-18 |
| 6 | SYSTEM IMPLEMENTATION | 19-22 |
| 7 | SCREENSHOTS | 23-34 |
| 8 | SYSTEM TESTING | 35-36 |
| 9 | RESULT AND ANALYSIS | 37 |
| 10 | CONCLUSION | 38 |
| 11 | FUTURE ENHANCEMENTS | 39 |
|  | REFERENCE / BIBLIOGRAPHY | 40-41 |

## LIST OF TABLES

| Table No | Title of Table | Page No |
|---|---|---|
| 3.1 | Hardware and Software Requirements | 7 |
| 4.1 | Functional Requirements | 9 |
| 4.2 | Non-Functional Requirements | 10 |
| 5.1 | Database Tables | 17 |
| 8.1 | Test Cases | 35-36 |
| 9.1 | Model Performance Summary | 37 |

## LIST OF FIGURES

| Figure No | Title of Figure | Page No |
|---|---|---|
| 5.1 | Use Case Diagram | 12 |
| 5.2 | User Registration and Baseline Flowchart | 14 |
| 5.3 | Typing Verification Flowchart | 15 |
| 5.4 | Admin and Model Monitoring Flowchart | 16 |
| 5.5 | ER Diagram | 17 |
| 5.6 | DFD Level 1 | 18 |
| 6.1 | Architectural Diagram | 19 |
| 7.1 | Sign Up Page | 23 |
| 7.2 | Login Page | 24 |
| 7.3 | User Dashboard | 25 |
| 7.4 | Baseline Typing Setup Page | 26 |
| 7.5 | Typing Verification Page | 27 |
| 7.6 | Analysis Result Page | 28 |
| 7.7 | Session History Page | 29 |
| 7.8 | User Profile Page | 30 |
| 7.9 | Model Health Page | 31 |
| 7.10 | Model Comparison Page | 32 |
| 7.11 | Admin Dashboard Page | 33 |
| 7.12 | Feature Export / Analytics Page | 34 |

---

# CHAPTER 1: INTRODUCTION

## 1.1 Introduction

The project titled **Keystroke Dynamics Authentication and Stress Detection System** is a behavioral biometric web application that analyzes how a user types on a keyboard. Instead of only focusing on what the user types, the system studies the rhythm and timing of typing. It records events such as when a key is pressed, when it is released, how long each key is held, how much delay exists between consecutive keys, how often the user pauses, and how consistent the typing pattern is.

The project has two major objectives. The first objective is **user authentication through keystroke dynamics**. Every user has a somewhat unique typing rhythm. This rhythm can be used as an additional identity signal. The second objective is **stress detection**. A user's typing pattern may change when they are stressed, hurried, hesitant, or inconsistent. The system uses machine learning models to classify a typing sample as either low stress or high stress based on extracted keystroke features.

The system is implemented as a Flask-based web application. It includes user registration, login, baseline typing profile creation, identity verification, stress analysis, user dashboard, session history, profile management, model health monitoring, feature export, and admin overview. It also contains a machine learning pipeline that trains Random Forest and XGBoost models for stress classification and Isolation Forest models for user authentication.

## 1.2 Problem Statement

Traditional authentication systems usually depend on static credentials such as usernames and passwords. These credentials can be stolen, guessed, shared, or reused across websites. Even when a user enters the correct password, the system usually does not verify whether the person typing the password is truly the account owner.

At the same time, stress and mental state are difficult to estimate in a non-invasive way. Many stress detection systems require external sensors, questionnaires, or manual observation. Keystroke dynamics provides a lightweight and non-invasive alternative because typing data can be captured directly from normal keyboard interaction.

This project addresses the problem by developing a system that:

- authenticates users using both password-based login and typing behavior,
- creates a baseline typing profile for each user,
- compares new typing samples with previous typing sessions,
- predicts stress level from keystroke timing features,
- stores session history and analytics for later review.

## 1.3 Objectives

The main objectives of the project are:

- To develop a secure user registration and login system.
- To capture real-time keystroke events from the browser.
- To extract meaningful timing features from raw typing data.
- To create a baseline typing profile for each user.
- To verify user identity using behavioral typing similarity.
- To detect stress level using trained machine learning models.
- To store typing sessions and model predictions in a database.
- To provide dashboards for users and administrators.
- To provide model health, model comparison, analytics, and export features.

## 1.4 Scope of the Project

The scope of the project includes both machine learning and web application development. The system is designed for demonstration, academic, and experimental use. It can be used to show how behavioral biometrics can improve authentication and how typing patterns can be analyzed for psychological or behavioral signals.

The system supports:

- account creation,
- password hashing,
- login and logout,
- typing baseline enrollment,
- typing verification,
- stress prediction,
- continuous authentication scoring,
- user session history,
- model performance display,
- feature export,
- admin statistics.

The project does not claim to be a medically certified stress diagnosis system. The stress labels are generated using a rule-based formula from typing variability and speed. Therefore, the stress prediction should be treated as behavioral stress estimation, not clinical stress measurement.

## 1.5 Existing System

In many existing systems, authentication is based only on username and password. Once the password is entered correctly, the user is considered authenticated. Such systems usually do not analyze behavior after login. If the password is stolen, an attacker may gain access.

Stress detection systems often require:

- wearable sensors,
- heart rate monitors,
- skin conductance sensors,
- camera-based expression analysis,
- manual questionnaires.

These systems may be expensive, intrusive, or inconvenient. In contrast, keystroke-based analysis can be performed silently while the user types.

## 1.6 Proposed System

The proposed system combines password authentication with keystroke dynamics. After registration, the user creates a baseline profile by typing multiple random sample texts. Later, during verification, the system compares the new typing sample against the user's stored typing history.

The system also sends extracted typing features to trained stress classification models. Random Forest and XGBoost models classify the sample as low stress or high stress. The final result is stored in the database and shown to the user through dashboards and result pages.

---

# CHAPTER 2: LITERATURE SURVEY

## 2.1 Behavioral Biometrics

Behavioral biometrics refers to identifying or verifying a person based on patterns of behavior rather than physical traits. Examples include voice rhythm, gait, mouse movement, touchscreen gestures, and keyboard typing patterns. Unlike fingerprints or iris scans, behavioral biometrics can be captured during normal interaction with a system.

Keystroke dynamics is one of the oldest and most practical forms of behavioral biometrics. It analyzes how users type, including timing between keys, duration of key presses, rhythm, speed, and error behavior.

## 2.2 Keystroke Dynamics

Keystroke dynamics is based on the idea that each person has a unique typing rhythm. Even if two users type the same text, their key press durations and transition timings may differ. These differences can be converted into numerical features and used for classification or anomaly detection.

Common keystroke features include:

- **Dwell time / hold time**: Time between key press and key release.
- **Flight time**: Time between releasing one key and pressing the next key.
- **Down-down latency**: Time between pressing one key and pressing the next key.
- **Up-up latency**: Time between releasing one key and releasing the next key.
- **Typing speed**: Number of characters or keys typed per second.
- **Pause frequency**: Number of long pauses in a typing sample.
- **Error/correction behavior**: Backspace or delete frequency.

## 2.3 Keystroke Authentication

Keystroke authentication can be static or dynamic.

Static keystroke authentication usually asks users to type a fixed text such as a password. The system learns the user's rhythm for that fixed phrase.

Dynamic keystroke authentication works with free text or changing prompts. This project uses prompted sample text for baseline and verification. The prompts are not passwords; they are used to capture natural typing behavior.

Authentication can be performed using:

- statistical distance,
- similarity scoring,
- one-class classifiers,
- anomaly detection,
- supervised classifiers.

This project uses two approaches. The training pipeline trains per-user Isolation Forest models, while the runtime application uses a weighted similarity score based on previous user sessions.

## 2.4 Stress Detection from Typing Behavior

Stress can influence typing behavior. A stressed user may type faster or slower than usual, pause more often, make more corrections, or show higher timing variability. Keystroke-based stress detection attempts to estimate stress level using these behavioral changes.

The project calculates a stress score from normalized timing features. Higher hold-time variability, higher flight-time variability, higher error proxy, and lower typing speed contribute to a higher stress score. These generated labels are then used to train machine learning classifiers.

## 2.5 Machine Learning Models Used in Related Work

Machine learning is commonly used in keystroke dynamics because the relationship between typing behavior and identity or stress is not purely linear.

Common models include:

- k-Nearest Neighbors,
- Support Vector Machines,
- Random Forest,
- Gradient Boosting,
- Neural Networks,
- Isolation Forest,
- One-Class SVM.

This project uses:

- Random Forest for stress classification,
- XGBoost for stress classification,
- Isolation Forest for authentication model training,
- weighted statistical similarity for runtime behavioral verification.

## 2.6 Summary of Literature Survey

The literature supports the idea that typing behavior can be used as a behavioral biometric. Keystroke dynamics is low-cost, non-invasive, and easy to capture through normal keyboard events. It is suitable for additional authentication and behavioral analysis. However, it is affected by environment, device, mood, fatigue, and typing context. Therefore, keystroke authentication is best used as an additional signal rather than the only security mechanism.

---

# CHAPTER 3: SYSTEM STUDY

## 3.1 Feasibility Study

The feasibility study examines whether the proposed system is practical from technical, operational, and economic perspectives.

### 3.1.1 Technical Feasibility

The system is technically feasible because all required tools are available as open-source technologies. Flask provides a lightweight backend framework. JavaScript can capture browser keystroke events. SQLite provides a simple local database. scikit-learn and XGBoost support model training and prediction.

The required machine learning models are already trained and stored in the `outputs/models/` directory. The application can load these models using joblib and use them during runtime.

### 3.1.2 Operational Feasibility

The system is operationally feasible because the user interaction is simple. Users register, type sample text, and view analysis results. The typing task is natural and does not require special hardware.

### 3.1.3 Economic Feasibility

The project is economically feasible because it uses free and open-source tools. No special biometric device, sensor, or paid cloud service is required.

## 3.2 Hardware Requirements

| Requirement | Specification |
|---|---|
| Processor | Intel i3 or above |
| RAM | 4 GB minimum, 8 GB recommended |
| Storage | 1 GB free space minimum |
| Input Device | Standard keyboard |
| Display | Standard monitor or laptop screen |

## 3.3 Software Requirements

| Requirement | Specification |
|---|---|
| Operating System | Windows / Linux / macOS |
| Programming Language | Python |
| Web Framework | Flask |
| Database | SQLite |
| Frontend | HTML, CSS, JavaScript |
| ML Libraries | scikit-learn, XGBoost |
| Data Libraries | Pandas, NumPy |
| Visualization | Matplotlib, Seaborn |
| Testing | Pytest |

## 3.4 Dataset Study

The project uses the CMU keystroke dataset and additional free-text user information datasets.

The CMU dataset contains 20,400 rows and includes subject/session data with hold, flight, and down-down timing features. The free-text datasets contain email, full name, and phone typing records.

Dataset files:

- `DSL-StrongPasswordData.csv`
- `email_userInformation.csv`
- `fullname_userInformation.csv`
- `phone_userInformation.csv`
- `content.csv`

## 3.5 Module Study

The project modules are:

- User account module
- Password authentication module
- Baseline typing module
- Typing verification module
- Feature extraction module
- Stress prediction module
- Behavioral authentication module
- Continuous authentication module
- Dashboard and analytics module
- Model health and comparison module
- Export module
- Testing module

---

# CHAPTER 4: SYSTEM ANALYSIS

## 4.1 Requirement Analysis

System analysis identifies what the system must do and how it should behave. The project has functional and non-functional requirements.

## 4.2 Functional Requirements

| Requirement No | Requirement |
|---|---|
| FR1 | The system shall allow users to register with username, email, and password. |
| FR2 | The system shall securely hash user passwords. |
| FR3 | The system shall allow users to log in and log out. |
| FR4 | The system shall require logged-in users for protected pages and APIs. |
| FR5 | The system shall capture keydown and keyup events during typing. |
| FR6 | The system shall block paste during baseline and verification. |
| FR7 | The system shall extract keystroke timing features. |
| FR8 | The system shall allow users to create baseline typing profiles. |
| FR9 | The system shall verify identity using previous typing sessions. |
| FR10 | The system shall predict stress using Random Forest and XGBoost. |
| FR11 | The system shall store typing sessions and prediction results. |
| FR12 | The system shall show dashboard, history, and analysis results. |
| FR13 | The system shall provide model health and model comparison pages. |
| FR14 | The system shall allow feature data export in JSON and CSV. |

## 4.3 Non-Functional Requirements

| Requirement No | Requirement |
|---|---|
| NFR1 | The system should be easy to use. |
| NFR2 | The system should respond quickly during typing verification. |
| NFR3 | Passwords should not be stored in plain text. |
| NFR4 | The system should handle invalid or incomplete typing data safely. |
| NFR5 | The system should be maintainable and modular. |
| NFR6 | The system should provide useful diagnostics for model availability. |
| NFR7 | The system should protect API routes from unauthenticated access. |

## 4.4 Input Analysis

Inputs include:

- username,
- email,
- password,
- typed text,
- sample prompt text,
- raw keystroke events,
- timestamp values,
- session requests,
- API requests.

## 4.5 Output Analysis

Outputs include:

- login/register responses,
- baseline status,
- typing quality score,
- authentication match score,
- stress prediction label,
- Random Forest confidence,
- XGBoost confidence,
- ensemble prediction,
- dashboard statistics,
- exported feature data,
- model health status.

## 4.6 Data Flow Summary

The user types in the browser. JavaScript captures raw events and sends them to Flask. Flask extracts features, loads models, predicts stress, calculates authentication match, stores the result in SQLite, and returns JSON or renders templates.

---

# CHAPTER 5: SYSTEM DESIGN

## 5.1 System Design Overview

System design describes the structure of the application, database, data flow, and interaction between modules. The system follows a web-based client-server architecture.

The browser acts as the client. It displays templates and captures keystroke data. The Flask backend acts as the server. It performs authentication, feature extraction, database operations, model prediction, and analytics.

## 5.2 Use Case Diagram

**Figure 5.1 Use Case Diagram**

Actors:

- Guest user
- Registered user
- Admin/system monitor

Use cases:

- Register account
- Login
- Create baseline profile
- Verify typing identity
- View stress result
- View dashboard
- View history
- Export features
- Check model health
- View admin overview

Text representation:

```text
Guest User
  -> Register
  -> Login

Registered User
  -> Setup Typing Baseline
  -> Verify Typing
  -> View Analysis Result
  -> View Dashboard
  -> View History
  -> View Profile
  -> Export Feature Data

Admin/System Monitor
  -> View Admin Overview
  -> View Model Health
  -> View Model Comparison
```

## 5.3 User Registration and Baseline Flowchart

**Figure 5.2 User Registration and Baseline Flowchart**

```text
Start
  |
Open Register Page
  |
Enter Username, Email, Password
  |
Validate Inputs
  |
Check Username and Email Availability
  |
Hash Password using PBKDF2
  |
Create User Record
  |
Create Flask Session
  |
Redirect to Baseline Setup
  |
Display Random Sample Text
  |
Capture Keydown and Keyup Events
  |
Submit Baseline Sample
  |
Check Accuracy and Quality
  |
Extract Keystroke Features
  |
Save Baseline Session
  |
Are 3 Samples Complete?
  | Yes -> Redirect to Dashboard
  | No  -> Show Next Sample
End
```

## 5.4 Typing Verification Flowchart

**Figure 5.3 Typing Verification Flowchart**

```text
Start
  |
User Opens Verification Page
  |
System Shows Random Sample Text
  |
User Types Sample
  |
Browser Captures Key Events
  |
Submit Typing Data
  |
Backend Extracts Features
  |
Evaluate Sample Quality
  |
Load Stress Models
  |
Predict Stress using Random Forest
  |
Predict Stress using XGBoost
  |
Calculate Ensemble Result
  |
Compare Current Features with User History
  |
Calculate Auth Match Score
  |
Save Typing Session
  |
Score >= 65 and Quality Good?
  | Yes -> Identity Verified
  | No  -> Retry Recommended
  |
Show Analysis Result
End
```

## 5.5 Admin and Model Monitoring Flowchart

**Figure 5.4 Admin and Model Monitoring Flowchart**

```text
Start
  |
Admin Opens Model Health/Admin Page
  |
System Checks Model Files
  |
Read Model Sizes and Modified Dates
  |
Read Latest Metrics
  |
Check Database Status
  |
Calculate User and Session Counts
  |
Calculate Average Auth Match
  |
Display Admin Overview
End
```

## 5.6 ER Diagram

**Figure 5.5 ER Diagram**

Entities:

```text
User
  user_id PK
  username
  email
  password_hash
  created_at

TypingSession
  session_id PK
  user_id FK
  mean_hold_time
  std_hold_time
  mean_flight_time
  std_flight_time
  typing_speed
  error_proxy
  consistency_score
  pause_frequency
  rf_prediction
  rf_confidence
  xgb_prediction
  xgb_confidence
  ensemble_prediction
  text_typed
  num_keystrokes
  duration_ms
  feature_blob
  created_at

ContinuousAuthStatus
  id PK
  user_id FK
  last_score
  is_authenticated
  updated_at
```

Relationship:

```text
User 1 -------- many TypingSession
User 1 -------- 1 ContinuousAuthStatus
```

## 5.7 DFD Level 1

**Figure 5.6 DFD Level 1**

```text
User
  -> Registration/Login Process
  -> Typing Capture Process
  -> Verification Process

Registration/Login Process
  -> User Database

Typing Capture Process
  -> Feature Extraction Process

Feature Extraction Process
  -> Stress Prediction Process
  -> Authentication Matching Process

Stress Prediction Process
  -> Model Files
  -> Typing Session Database

Authentication Matching Process
  -> Typing Session Database
  -> Continuous Auth Database

Dashboard/Analytics Process
  -> User Database
  -> Typing Session Database
  -> User Interface
```

## 5.8 Database Table Design

| Table Name | Purpose |
|---|---|
| users | Stores user account credentials and metadata. |
| typing_sessions | Stores typing features, stress predictions, and session details. |
| continuous_auth | Stores latest continuous authentication score and status. |

---

# CHAPTER 6: SYSTEM IMPLEMENTATION

## 6.1 Architecture

**Figure 6.1 Architectural Diagram**

```text
Browser Frontend
  HTML / CSS / JavaScript
  Keydown / Keyup Capture
          |
          v
Flask Backend
  Routes
  Session Management
  Feature Extraction
  Quality Checking
  Authentication Scoring
  Stress Prediction
          |
          v
Machine Learning Models
  Random Forest
  XGBoost
  Isolation Forest artifacts
          |
          v
SQLite Database
  users
  typing_sessions
  continuous_auth
          |
          v
Dashboards / APIs / Reports
```

## 6.2 User Registration Implementation

Registration is implemented in `app_auth.py` through the `/register` route. The route accepts GET and POST requests. On GET, it displays the authentication page. On POST, it validates the submitted form, checks whether the username or email already exists, hashes the password, creates a user, commits the user to the database, creates a session, and redirects the user to baseline typing setup.

## 6.3 Login Implementation

Login is implemented through the `/login` route. It checks username and password, verifies the password hash, creates a Flask session, marks it permanent, and redirects the user to the dashboard.

## 6.4 Password Hashing Implementation

The `User` model uses Werkzeug password hashing. Passwords are hashed using PBKDF2 SHA-256 with a salt length of 16. The system also supports old SHA256 hashes and upgrades them when the correct password is entered.

## 6.5 Baseline Typing Implementation

The baseline page captures keydown and keyup events. It sends the typed text, sample text, and keystroke event list to `/save-baseline`.

The backend checks:

- sample accuracy,
- paste detection,
- minimum keystroke count,
- minimum duration,
- reasonable typing speed.

Then it extracts features and stores the sample as a baseline session.

## 6.6 Feature Extraction Implementation

Feature extraction converts raw events into numerical values.

Main extracted features:

- mean hold time,
- standard deviation of hold time,
- mean flight time,
- standard deviation of flight time,
- typing speed,
- error proxy,
- consistency score,
- pause frequency,
- entropy,
- correction count,
- digraph timing.

These features are used by both authentication and stress detection.

## 6.7 Stress Detection Implementation

Stress detection uses two trained models:

- Random Forest,
- XGBoost.

The backend loads the models using joblib. During prediction, it creates an input vector using eight core features:

```text
mean_hold_time
std_hold_time
mean_flight_time
std_flight_time
typing_speed
error_proxy
consistency_score
pause_frequency
```

Both models return a prediction and confidence. The final ensemble result is calculated using confidence-weighted voting.

## 6.8 Authentication Matching Implementation

Behavioral authentication uses previous sessions as the user's baseline. The current typing features are compared with historical feature means and standard deviations. A weighted similarity score is calculated. If the score is at least 65, the system considers the typing behavior verified.

## 6.9 Continuous Authentication Implementation

Continuous authentication periodically checks user typing sessions in the background. It computes a rolling authentication score and stores the latest score in the `continuous_auth` table.

## 6.10 Dashboard and Analytics Implementation

The dashboard displays:

- total sessions,
- average speed,
- best consistency,
- regular/stressed count,
- recent session list,
- authentication scores.

Analytics APIs provide timeline data, peer summaries, and anomaly timeline data.

---

# CHAPTER 7: SCREENSHOTS

This chapter should contain screenshots from the running application. The following screenshot list is adapted to this project.

## 7.1 Sign Up Page

Shows the registration form where a new user enters username, email, and password.

## 7.2 Login Page

Shows the login form where an existing user enters username and password.

## 7.3 User Dashboard

Shows user statistics, recent sessions, stress count, and typing performance overview.

## 7.4 Baseline Typing Setup Page

Shows the random sample text, typing area, progress bar, accuracy, speed, and baseline progress.

## 7.5 Typing Verification Page

Shows the verification challenge where the user types a random sample for identity verification and stress analysis.

## 7.6 Analysis Result Page

Shows the stress prediction, model confidence, authentication match score, and interpretation.

## 7.7 Session History Page

Shows previous typing sessions with timestamps, stress labels, and typing statistics.

## 7.8 User Profile Page

Shows user account details and profile-related actions.

## 7.9 Model Health Page

Shows whether model files exist, model sizes, calibration status, and latest metrics.

## 7.10 Model Comparison Page

Compares Random Forest, XGBoost, and ensemble model behavior.

## 7.11 Admin Dashboard Page

Shows total users, sessions, baseline sessions, verification sessions, stress sessions, and average authentication match.

## 7.12 Feature Export / Analytics Page

Shows exported feature data, charts, or analytics output from user sessions.

---

# CHAPTER 8: SYSTEM TESTING

## 8.1 Introduction

Testing ensures that the system works according to requirements. The project uses Pytest for automated testing. The test suite checks feature extraction, endpoint behavior, authentication protection, stress prediction, database persistence, and export routes.

## 8.2 Test Cases

| Test Case ID | Test Case | Input | Expected Output | Status |
|---|---|---|---|---|
| TC01 | Register page loads | GET `/register` | Page response or redirect | Pass |
| TC02 | User registration | username, email, password | New user created | Pass |
| TC03 | Login page loads | GET `/login` | Page response or redirect | Pass |
| TC04 | Valid login | correct username/password | User logged in | Pass |
| TC05 | Save baseline | typing sample and keystrokes | Baseline session saved | Pass |
| TC06 | Verify typing | typing sample and keystrokes | Verification response | Pass |
| TC07 | Continuous status | logged-in user | JSON status returned | Pass |
| TC08 | Export feature blobs | logged-in user | JSON export response | Pass |
| TC09 | Export feature CSV | logged-in user | CSV response or valid error | Pass |
| TC10 | Stress prediction | keystroke feature payload | Prediction JSON | Pass |
| TC11 | Protected API without login | unauthenticated request | 401 response | Pass |
| TC12 | Feature extraction | raw keydown/keyup events | Feature dictionary | Pass |
| TC13 | Empty keystroke data | empty list | Default feature dictionary | Pass |
| TC14 | Pause detection | long interval sample | Pause feature calculated | Pass |
| TC15 | Backspace detection | sample with Backspace | Correction feature calculated | Pass |

## 8.3 Test Result

The current automated test result is:

```text
26 tests passed
```

Warnings were observed for default production secret key, SQLAlchemy legacy usage, and scikit-learn model version mismatch. These are warnings, not test failures.

---

# CHAPTER 9: RESULT AND ANALYSIS

## 9.1 Model Results

The generated report in `outputs/stress_auth_report.txt` contains the following results:

| Model / Task | Metric | Value |
|---|---:|---:|
| Random Forest Stress Classifier | Accuracy | 1.0000 |
| XGBoost Stress Classifier | Accuracy | 1.0000 |
| Best Stress Model | Selected Model | XGBoost |
| Authentication Models | Average Accuracy | 0.6699 |
| Authentication Models | Average Precision | 0.6464 |
| Authentication Models | Average Recall | 0.9216 |

## 9.2 Analysis of Stress Detection

Both Random Forest and XGBoost achieved 100% accuracy on the generated-label test split. This indicates that the models learned the relationship between timing features and the generated stress labels very well.

However, the stress labels are not externally measured clinical labels. They are generated from keystroke variability, error proxy, and typing speed. Therefore, the result proves that the models can learn the defined stress scoring logic, but it does not prove clinical stress detection accuracy.

## 9.3 Analysis of Authentication

Authentication achieved approximately 67% average accuracy and 92% recall. High recall means the system is good at accepting genuine users. Lower precision means some impostor-like samples may also be accepted. This is common in behavioral biometric systems because user behavior can vary across sessions.

The authentication score is useful as an additional security layer, not as the only authentication factor.

## 9.4 Overall Result

The project successfully demonstrates:

- secure account authentication,
- keystroke capture,
- baseline enrollment,
- behavioral identity verification,
- stress prediction,
- session storage,
- dashboard analytics,
- model monitoring,
- automated testing.

---

# CHAPTER 10: CONCLUSION

The Keystroke Dynamics Authentication and Stress Detection System successfully demonstrates how keyboard typing behavior can be used for both behavioral authentication and stress analysis. The project combines web development, database management, machine learning, and real-time browser event capture.

The system allows users to register, log in, create a baseline typing profile, verify identity through typing, and receive stress analysis results. The machine learning pipeline trains Random Forest and XGBoost models for stress classification and Isolation Forest models for user authentication. Runtime verification compares current typing behavior with previous sessions and calculates an authentication match score.

The project is useful as an academic demonstration of behavioral biometrics. It shows that keystroke features such as hold time, flight time, typing speed, consistency, and pause frequency can provide meaningful behavioral signals. At the same time, the project also shows the limitations of such systems, especially the need for real stress labels and stronger production security.

---

# CHAPTER 11: FUTURE ENHANCEMENTS

Future enhancements include:

- Use real stress labels from questionnaires, heart rate, or controlled experiments.
- Add calibrated stress model probabilities.
- Train personalized authentication models using each user's baseline data.
- Add adaptive per-user authentication thresholds.
- Add email verification during signup.
- Add password reset functionality.
- Add CSRF protection for form submissions.
- Add role-based admin login.
- Use PostgreSQL or MySQL instead of SQLite for production.
- Add Alembic database migrations.
- Avoid storing raw typed text unless required.
- Add device and keyboard metadata.
- Add model drift detection.
- Add more advanced models such as LSTM, Transformer, or One-Class SVM.
- Improve UI charts for stress and authentication trends.
- Add downloadable PDF report generation.

---

# REFERENCE / BIBLIOGRAPHY

1. Flask Documentation. "Flask Web Development Framework." https://flask.palletsprojects.com/
2. SQLAlchemy Documentation. "SQLAlchemy ORM." https://docs.sqlalchemy.org/
3. scikit-learn Documentation. "Machine Learning in Python." https://scikit-learn.org/
4. XGBoost Documentation. "XGBoost Python Package." https://xgboost.readthedocs.io/
5. Pandas Documentation. "Python Data Analysis Library." https://pandas.pydata.org/
6. NumPy Documentation. "Scientific Computing with Python." https://numpy.org/
7. Matplotlib Documentation. "Visualization with Python." https://matplotlib.org/
8. Seaborn Documentation. "Statistical Data Visualization." https://seaborn.pydata.org/
9. CMU Keystroke Dynamics Dataset, DSL Strong Password Dataset.
10. Killourhy, K. S., and Maxion, R. A. "Comparing anomaly-detection algorithms for keystroke dynamics." IEEE/IFIP International Conference on Dependable Systems and Networks, 2009.
11. Monrose, F., and Rubin, A. D. "Authentication via keystroke dynamics." ACM Conference on Computer and Communications Security, 1997.
12. Project source files: `app_auth.py`, `main.py`, `src/features.py`, `src/model_stress.py`, `src/model_auth.py`, `src/stress_labels.py`, `keystroke_project/src/continuous_auth.py`.

