/* ============================================
   Keystroke Dynamics Dashboard JavaScript
   ============================================ */

// Load model status on page load
document.addEventListener('DOMContentLoaded', function() {
    loadModelStatus();
    loadUsers();
});

// ============================================
// Model Status
// ============================================

function loadModelStatus() {
    fetch('/api/models/status')
        .then(response => response.json())
        .then(data => {
            const statusDiv = document.getElementById('modelStatus');
            if (!statusDiv) return;

            statusDiv.innerHTML = `
                <div class="status-card">
                    <h3>🤖 Random Forest</h3>
                    <div class="status-badge ${data.stress_random_forest ? 'active' : 'inactive'}">
                        ${data.stress_random_forest ? '✓ Loaded' : '✗ Not Loaded'}
                    </div>
                </div>
                <div class="status-card">
                    <h3>🚀 XGBoost</h3>
                    <div class="status-badge ${data.stress_xgboost ? 'active' : 'inactive'}">
                        ${data.stress_xgboost ? '✓ Loaded' : '✗ Not Loaded'}
                    </div>
                </div>
                <div class="status-card">
                    <h3>🔐 Authentication</h3>
                    <div class="status-badge ${data.auth_models ? 'active' : 'inactive'}">
                        ${data.auth_models ? '✓ Loaded' : '✗ Not Loaded'}
                    </div>
                    ${data.num_users > 0 ? `<div style="margin-top: 0.5rem; font-size: 0.9rem;">${data.num_users} users</div>` : ''}
                </div>
            `;
        })
        .catch(error => {
            console.error('Error loading model status:', error);
            const statusDiv = document.getElementById('modelStatus');
            if (statusDiv) {
                statusDiv.innerHTML = '<div class="status-card"><h3>Error loading status</h3></div>';
            }
        });
}

// ============================================
// Load Users
// ============================================

function loadUsers() {
    const userSelect = document.getElementById('userSelect');
    if (!userSelect) return;

    fetch('/api/users')
        .then(response => response.json())
        .then(data => {
            userSelect.innerHTML = '<option value="">Select a user...</option>';
            data.forEach(user => {
                const option = document.createElement('option');
                option.value = user;
                option.textContent = user;
                userSelect.appendChild(option);
            });
        })
        .catch(error => {
            console.error('Error loading users:', error);
            userSelect.innerHTML = '<option value="">Error loading users</option>';
        });
}

// ============================================
// Stress Prediction
// ============================================

function predictStress(e) {
    e.preventDefault();

    const form = e.target;
    const formData = new FormData(form);
    const data = Object.fromEntries(formData);

    // Convert to numbers
    Object.keys(data).forEach(key => {
        data[key] = parseFloat(data[key]);
    });

    fetch('/api/predict/stress', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(data)
    })
    .then(response => response.json())
    .then(result => {
        const resultDiv = document.getElementById('stressResult');
        
        if (result.error) {
            resultDiv.className = 'result-box show error';
            resultDiv.innerHTML = `<h4>Error</h4><p>${result.error}</p>`;
            return;
        }

        const rfLabel = result.random_forest.label === 'High Stress' ? 'high-stress' : 'low-stress';
        const xgbLabel = result.xgboost.label === 'High Stress' ? 'high-stress' : 'low-stress';

        resultDiv.className = 'result-box show success';
        resultDiv.innerHTML = `
            <h4>Stress Prediction Results</h4>
            <div class="result-content">
                <div class="result-item">
                    <span class="result-label">Random Forest:</span>
                    <span class="result-value">${(result.random_forest.confidence * 100).toFixed(2)}%</span>
                </div>
                <div>
                    <span class="prediction-label ${rfLabel}">${result.random_forest.label}</span>
                </div>
                
                <div class="result-item" style="margin-top: 1rem;">
                    <span class="result-label">XGBoost:</span>
                    <span class="result-value">${(result.xgboost.confidence * 100).toFixed(2)}%</span>
                </div>
                <div>
                    <span class="prediction-label ${xgbLabel}">${result.xgboost.label}</span>
                </div>
            </div>
        `;
    })
    .catch(error => {
        console.error('Error:', error);
        const resultDiv = document.getElementById('stressResult');
        resultDiv.className = 'result-box show error';
        resultDiv.innerHTML = `<h4>Error</h4><p>${error.message}</p>`;
    });
}

// ============================================
// Authentication Prediction
// ============================================

function predictAuth(e) {
    e.preventDefault();

    const form = e.target;
    const formData = new FormData(form);
    const userId = formData.get('user_id');
    
    const data = {
        mean_hold_time: parseFloat(formData.get('mean_hold_time')),
        std_hold_time: parseFloat(formData.get('std_hold_time')),
        mean_flight_time: parseFloat(formData.get('mean_flight_time')),
        std_flight_time: parseFloat(formData.get('std_flight_time')),
        typing_speed: parseFloat(formData.get('typing_speed')),
        error_proxy: parseFloat(formData.get('error_proxy')),
        consistency_score: parseFloat(formData.get('consistency_score')),
        pause_frequency: parseFloat(formData.get('pause_frequency'))
    };

    if (!userId) {
        const resultDiv = document.getElementById('authResult');
        resultDiv.className = 'result-box show error';
        resultDiv.innerHTML = '<h4>Error</h4><p>Please select a user</p>';
        return;
    }

    fetch(`/api/predict/auth/${userId}`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(data)
    })
    .then(response => response.json())
    .then(result => {
        const resultDiv = document.getElementById('authResult');
        
        if (result.error) {
            resultDiv.className = 'result-box show error';
            resultDiv.innerHTML = `<h4>Error</h4><p>${result.error}</p>`;
            return;
        }

        const authLabel = result.is_legitimate ? 'legitimate' : 'impostor';
        const confidence = result.is_legitimate ? 
            'Patterns match user profile' : 
            'Patterns DO NOT match user profile';

        resultDiv.className = 'result-box show success';
        resultDiv.innerHTML = `
            <h4>Authentication Result for User ${result.user_id}</h4>
            <div class="result-content">
                <div class="result-item">
                    <span class="result-label">Status:</span>
                    <span class="result-value">${result.is_legitimate ? '✓ Authenticated' : '✗ Rejected'}</span>
                </div>
                <div>
                    <span class="prediction-label ${authLabel}">${result.label}</span>
                </div>
                <div class="result-item" style="margin-top: 1rem;">
                    <span class="result-label">Analysis:</span>
                    <span>${confidence}</span>
                </div>
            </div>
        `;
    })
    .catch(error => {
        console.error('Error:', error);
        const resultDiv = document.getElementById('authResult');
        resultDiv.className = 'result-box show error';
        resultDiv.innerHTML = `<h4>Error</h4><p>${error.message}</p>`;
    });
}

// ============================================
// Auto-refresh status periodically
// ============================================

setInterval(function() {
    loadModelStatus();
}, 30000); // Refresh every 30 seconds
