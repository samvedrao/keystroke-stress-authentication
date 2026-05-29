/* ============================================
   Keystroke Tracking and Analysis
   ============================================ */

const typingInput = document.getElementById('typingInput');
const analyzeBtn = document.getElementById('analyzeBtn');
const resetBtn = document.getElementById('resetBtn');
const statsBox = document.getElementById('statsBox');
const resultsSection = document.getElementById('resultsSection');
const errorBox = document.getElementById('errorBox');

// Keystroke tracking data
let keystrokeData = {
    holdTimes: [],      // Time each key is held down
    flightTimes: [],    // Time between key releases and next key press
    keyDownTimes: {},   // Track when each key was pressed
    lastKeyUpTime: null,
    startTime: null,
    keyCount: 0
};

// Initialize
typingInput.addEventListener('keydown', handleKeyDown);
typingInput.addEventListener('keyup', handleKeyUp);
analyzeBtn.addEventListener('click', analyzePattern);
resetBtn.addEventListener('click', resetTracking);

function handleKeyDown(e) {
    if (!keystrokeData.startTime) {
        keystrokeData.startTime = Date.now();
    }

    const key = e.key;
    
    // Record key down time
    keystrokeData.keyDownTimes[key] = Date.now();

    // Calculate flight time if this is not first key
    if (keystrokeData.lastKeyUpTime !== null) {
        const flightTime = keystrokeData.keyDownTimes[key] - keystrokeData.lastKeyUpTime;
        if (flightTime > 0) {
            keystrokeData.flightTimes.push(flightTime);
        }
    }
}

function handleKeyUp(e) {
    const key = e.key;
    
    // Calculate hold time
    if (keystrokeData.keyDownTimes[key]) {
        const holdTime = Date.now() - keystrokeData.keyDownTimes[key];
        keystrokeData.holdTimes.push(holdTime);
        keystrokeData.keyCount++;
        keystrokeData.lastKeyUpTime = Date.now();
    }

    // Update stats in real-time
    updateLiveStats();
    
    // Enable analyze button if enough data
    if (keystrokeData.keyCount >= 5) {
        analyzeBtn.disabled = false;
    }
}

function updateLiveStats() {
    statsBox.style.display = 'block';

    // Key count
    document.getElementById('keyCount').textContent = keystrokeData.keyCount;

    // Typing time
    if (keystrokeData.startTime) {
        const elapsed = (Date.now() - keystrokeData.startTime) / 1000;
        document.getElementById('typingTime').textContent = elapsed.toFixed(1) + 's';
    }

    // Typing speed (keys per second)
    if (keystrokeData.startTime) {
        const elapsed = (Date.now() - keystrokeData.startTime) / 1000;
        const speed = (keystrokeData.keyCount / elapsed).toFixed(2);
        document.getElementById('typingSpeed').textContent = speed + ' keys/s';
    }

    // Hold time statistics
    if (keystrokeData.holdTimes.length > 0) {
        const meanHold = getMean(keystrokeData.holdTimes);
        const stdHold = getStdDev(keystrokeData.holdTimes);
        
        document.getElementById('meanHold').textContent = meanHold.toFixed(1) + 'ms';
        document.getElementById('stdHold').textContent = stdHold.toFixed(1) + 'ms';

        // Consistency (inverse of variation)
        const consistency = meanHold > 0 ? 
            Math.max(0, Math.min(100, (1 - (stdHold / meanHold)) * 100)) : 0;
        document.getElementById('consistency').textContent = consistency.toFixed(1) + '%';
    }

    // Flight time statistics
    if (keystrokeData.flightTimes.length > 0) {
        const meanFlight = getMean(keystrokeData.flightTimes);
        document.getElementById('meanFlight').textContent = meanFlight.toFixed(1) + 'ms';
    }

    // Pause count (hold times > 1.5x mean)
    if (keystrokeData.holdTimes.length > 0) {
        const meanHold = getMean(keystrokeData.holdTimes);
        const pauseCount = keystrokeData.holdTimes.filter(h => h > meanHold * 1.5).length;
        document.getElementById('pauseCount').textContent = pauseCount;
    }
}

function analyzePattern() {
    if (keystrokeData.keyCount < 5) {
        showError('Please type at least 5 keys to analyze');
        return;
    }

    // Extract features
    const features = extractFeatures();

    if (!features) {
        showError('Unable to extract features. Please type more.');
        return;
    }

    // Show loading
    resultsSection.style.display = 'block';
    resultsSection.innerHTML = '<h3>🎯 Stress Level Analysis</h3><p style="text-align: center; padding: 2rem;">Analyzing your keystroke pattern...</p>';

    // Send to backend
    fetch('/api/predict/stress', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(features)
    })
    .then(response => response.json())
    .then(result => {
        if (result.error) {
            showError('Error: ' + result.error);
            return;
        }
        displayResults(features, result);
    })
    .catch(error => {
        console.error('Error:', error);
        showError('Error analyzing keystroke pattern: ' + error.message);
    });
}

function extractFeatures() {
    if (keystrokeData.holdTimes.length === 0) return null;

    const meanHold = getMean(keystrokeData.holdTimes);
    const stdHold = getStdDev(keystrokeData.holdTimes);
    
    const meanFlight = keystrokeData.flightTimes.length > 0 ? 
        getMean(keystrokeData.flightTimes) : 0;
    const stdFlight = keystrokeData.flightTimes.length > 0 ? 
        getStdDev(keystrokeData.flightTimes) : 0;

    const elapsed = (Date.now() - keystrokeData.startTime) / 1000;
    const typingSpeed = elapsed > 0 ? keystrokeData.keyCount / elapsed : 0;

    // Error proxy (coefficient of variation)
    const errorProxy = meanHold > 0 ? (stdHold / meanHold) : 0;

    // Consistency score
    const consistencyScore = Math.max(0, Math.min(1, 1 - errorProxy));

    // Pause frequency
    const pauseFrequency = keystrokeData.holdTimes.filter(
        h => h > meanHold * 1.5
    ).length;

    // Mean DD time (approximated from flight time)
    const meanDdTime = meanFlight > 0 ? meanFlight : 0.1;

    return {
        mean_hold_time: meanHold,
        std_hold_time: stdHold,
        mean_flight_time: meanFlight,
        std_flight_time: stdFlight,
        typing_speed: typingSpeed > 0 ? 1.0 / (meanDdTime / 1000) : 0,
        error_proxy: errorProxy,
        consistency_score: consistencyScore,
        pause_frequency: pauseFrequency
    };
}

function displayResults(features, prediction) {
    const rfPred = prediction.random_forest;
    const xgbPred = prediction.xgboost;

    // Determine overall stress
    const overallStress = (rfPred.confidence + xgbPred.confidence) / 2;
    const isHighStress = overallStress >= 0.5;

    const stressBadgeHtml = `
        <span class="stress-badge ${isHighStress ? 'high' : 'low'}">
            ${isHighStress ? '🔴 High Stress' : '🟢 Low Stress'}
        </span>
    `;

    const rfResultHtml = `
        <p><strong>Prediction:</strong> ${rfPred.label}</p>
        <p><strong>Confidence:</strong> ${(rfPred.confidence * 100).toFixed(1)}%</p>
        <div class="confidence-bar">
            <div class="confidence-fill" style="width: ${rfPred.confidence * 100}%"></div>
        </div>
    `;

    const xgbResultHtml = `
        <p><strong>Prediction:</strong> ${xgbPred.label}</p>
        <p><strong>Confidence:</strong> ${(xgbPred.confidence * 100).toFixed(1)}%</p>
        <div class="confidence-bar">
            <div class="confidence-fill" style="width: ${xgbPred.confidence * 100}%"></div>
        </div>
    `;

    const metricsHtml = `
        <div class="metric-row">
            <span class="metric-label">Mean Hold Time (Dwell):</span>
            <span class="metric-value">${features.mean_hold_time.toFixed(1)} ms</span>
        </div>
        <div class="metric-row">
            <span class="metric-label">Std Hold Time:</span>
            <span class="metric-value">${features.std_hold_time.toFixed(1)} ms</span>
        </div>
        <div class="metric-row">
            <span class="metric-label">Mean Flight Time:</span>
            <span class="metric-value">${features.mean_flight_time.toFixed(1)} ms</span>
        </div>
        <div class="metric-row">
            <span class="metric-label">Std Flight Time:</span>
            <span class="metric-value">${features.std_flight_time.toFixed(1)} ms</span>
        </div>
        <div class="metric-row">
            <span class="metric-label">Typing Speed:</span>
            <span class="metric-value">${features.typing_speed.toFixed(2)} keys/s</span>
        </div>
        <div class="metric-row">
            <span class="metric-label">Error Proxy (Variability):</span>
            <span class="metric-value">${features.error_proxy.toFixed(3)}</span>
        </div>
        <div class="metric-row">
            <span class="metric-label">Consistency Score:</span>
            <span class="metric-value">${(features.consistency_score * 100).toFixed(1)}%</span>
        </div>
        <div class="metric-row">
            <span class="metric-label">Pause Frequency:</span>
            <span class="metric-value">${features.pause_frequency}</span>
        </div>
    `;

    const interpretation = generateInterpretation(features, isHighStress);

    resultsSection.innerHTML = `
        <h3>🎯 Stress Level Analysis</h3>
        
        <div class="prediction-card stress-large">
            <div class="prediction-header">
                <h4>💪 Overall Stress Level</h4>
                ${stressBadgeHtml}
            </div>
            <div class="models-grid">
                <div class="model-result">
                    <h5>🤖 Random Forest</h5>
                    <div class="model-result-content">
                        ${rfResultHtml}
                    </div>
                </div>
                <div class="model-result">
                    <h5>🚀 XGBoost</h5>
                    <div class="model-result-content">
                        ${xgbResultHtml}
                    </div>
                </div>
            </div>
        </div>

        <div class="metrics-detail">
            <h4>📈 Detailed Keystroke Metrics</h4>
            <div class="metrics-table">
                ${metricsHtml}
            </div>
        </div>

        <div class="interpretation-box">
            ${interpretation}
        </div>
    `;

    errorBox.style.display = 'none';
}

function generateInterpretation(features, isHighStress) {
    let html = '<h4>📊 Analysis & Interpretation</h4>';

    if (isHighStress) {
        html += '<p><strong style="color: #e74c3c;">⚠️ Elevated Stress Detected:</strong></p>';
        html += '<ul>';
        
        if (features.error_proxy > 0.3) {
            html += '<li>High typing variability - inconsistent key press patterns</li>';
        }
        if (features.pause_frequency > 2) {
            html += '<li>Frequent long pauses detected - possible hesitation or deliberation</li>';
        }
        if (features.std_hold_time > features.mean_hold_time * 0.4) {
            html += '<li>Variable hold times - suggests uncertain or tense typing</li>';
        }
        if (features.typing_speed < 3) {
            html += '<li>Below-average typing speed - may indicate stress or careful typing</li>';
        }
        
        html += '</ul>';
        html += '<p><strong>Recommendation:</strong> Consider taking a break or practicing relaxation techniques.</p>';
    } else {
        html += '<p><strong style="color: #2ecc71;">✓ Normal Stress Level:</strong></p>';
        html += '<ul>';
        
        if (features.consistency_score > 0.8) {
            html += '<li>Consistent typing patterns - indicates comfortable typing</li>';
        }
        if (features.typing_speed > 5) {
            html += '<li>Good typing speed - suggests confidence and comfort</li>';
        }
        if (features.error_proxy < 0.2) {
            html += '<li>Low typing variability - stable and predictable patterns</li>';
        }
        
        html += '</ul>';
        html += '<p><strong>Status:</strong> Your typing patterns indicate a relaxed and comfortable state.</p>';
    }

    return html;
}

function resetTracking() {
    keystrokeData = {
        holdTimes: [],
        flightTimes: [],
        keyDownTimes: {},
        lastKeyUpTime: null,
        startTime: null,
        keyCount: 0
    };

    typingInput.value = '';
    statsBox.style.display = 'none';
    resultsSection.style.display = 'none';
    errorBox.style.display = 'none';
    analyzeBtn.disabled = true;
}

function showError(message) {
    errorBox.style.display = 'block';
    errorBox.innerHTML = `<h4>❌ Error</h4><p>${message}</p>`;
    resultsSection.style.display = 'none';
}

function getMean(arr) {
    if (arr.length === 0) return 0;
    return arr.reduce((a, b) => a + b, 0) / arr.length;
}

function getStdDev(arr) {
    if (arr.length === 0) return 0;
    const mean = getMean(arr);
    const variance = arr.reduce((sum, val) => sum + Math.pow(val - mean, 2), 0) / arr.length;
    return Math.sqrt(variance);
}

// Hide results on initial load
resultsSection.style.display = 'none';
errorBox.style.display = 'none';
