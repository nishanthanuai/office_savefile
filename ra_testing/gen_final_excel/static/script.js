let currentProcessId = null;
let eventSource = null;
let currentStep = null;
let stepTimer = null;

let lastFunnyMessage = "";

function runPipeline() {
    const surveyId = document.getElementById('surveyId').value.trim();


    if (!surveyId) {
        alert('Please enter a Survey ID');
        return;
    }

    if (!/^\d+$/.test(surveyId)) {
        alert('Survey ID must be numeric');
        return;
    }

    // Disable button and show status
    const runBtn = document.getElementById('runBtn');
    runBtn.disabled = true;
    runBtn.textContent = 'Running...';

    // Show sections
    document.getElementById('downloadBtn').style.display = 'none';
    document.getElementById('validationResult').style.display = 'none';
    document.getElementById('statusSection').style.display = 'block';
    document.getElementById('logsSection').style.display = 'block';
    document.getElementById('validationSection').style.display = 'none';

    // Clear previous logs
    clearLogs();

    // Start pipeline
    fetch('/run-pipeline', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ survey_id: surveyId })
    })
        .then(response => response.json())
        .then(data => {
            if (data.error) {
                alert('Error: ' + data.error);
                resetUI();
                return;
            }

            currentProcessId = data.process_id;
            updateStatus('Pipeline started, processing...');
            updateFunnyMessage("🚀 Launching master pipeline...");

            // Start streaming logs
            streamLogs(currentProcessId);
        })
        .catch(error => {
            console.error('Error:', error);
            alert('Failed to start pipeline: ' + error.message);
            resetUI();
        });
}

function streamLogs(processId) {
    // Close existing connection
    if (eventSource) {
        eventSource.close();
    }

    eventSource = new EventSource(`/stream-logs/${processId}`);

    eventSource.onmessage = function (event) {
        console.log("RAW EVENT:", event.data);
        const data = JSON.parse(event.data);

        if (data.log) {
            addLogEntry(data.log);
            detectStepFromLog(data.log);  // 👈 ADD THIS
        }
        else if (data.status === 'completed') {
            updateStatus('Pipeline completed successfully! ✅');

            // Show validation section
            document.getElementById('validationSection').style.display = 'block';

            // Use structured backend data
            if (data.api_counts) {
                displayCounts('dashboardCounts', data.api_counts);
                calculateTotal('dashboardTotal', data.api_counts);
            }

            if (data.excel_counts) {
                displayCounts('excelCounts', data.excel_counts);
                calculateTotal('excelTotal', data.excel_counts);
            }

            // Show validation result
            showValidationResult(data.validation_status === true);
            clearStepTimer();
            clearFunnyMessage();

            resetUI();
            eventSource.close();
        }
        else if (data.status === 'error') {
            updateStatus('Pipeline failed ❌');
            addLogEntry(`ERROR: ${data.message}`, 'error');
            clearStepTimer();
            clearFunnyMessage();
            resetUI();
            eventSource.close();
        }
    };

    eventSource.onerror = function (error) {
        console.error('EventSource error:', error);
        updateStatus('Connection error');
        clearFunnyMessage();
        resetUI();
        eventSource.close();
    };
}

function addLogEntry(text, type = 'info') {
    const logsContainer = document.getElementById('logsContainer');
    const entry = document.createElement('div');
    entry.className = `log-entry ${type}`;

    // Detect log level from text
    if (text.includes('ERROR') || text.includes('FAILED') || text.includes('❌')) {
        entry.className = 'log-entry error';
    } else if (text.includes('WARNING')) {
        entry.className = 'log-entry warning';
    } else if (text.includes('COMPLETED') || text.includes('✅') || text.includes('✔')) {
        entry.className = 'log-entry success';
    }

    entry.textContent = text;
    logsContainer.appendChild(entry);

    // Auto-scroll to bottom
    logsContainer.scrollTop = logsContainer.scrollHeight;
}

function parseValidationResults() {
    const logsContainer = document.getElementById('logsContainer');
    const logText = logsContainer.textContent;

    // Always show validation section after completion
    document.getElementById('validationSection').style.display = 'block';

    // Try to extract counts if available
    const dashboardMatch = logText.match(/Dashboard Counts \(API\)[\s\S]*?({[\s\S]*?})/);
    const excelMatch = logText.match(/Excel Counts[\s\S]*?({[\s\S]*?})/);

    if (dashboardMatch) {
        try {
            const dashboardData = JSON.parse(dashboardMatch[1]);
            displayCounts('dashboardCounts', dashboardData);
            calculateTotal('dashboardTotal', dashboardData);
        } catch (e) {
            document.getElementById('dashboardCounts').textContent = 'Data not available';
        }
    }

    if (excelMatch) {
        try {
            const excelData = JSON.parse(excelMatch[1]);
            displayCounts('excelCounts', excelData);
            calculateTotal('excelTotal', excelData);
        } catch (e) {
            document.getElementById('excelCounts').textContent = 'Data not available';
        }
    }

    // 🔥 IMPORTANT: Validation based on status text, not JSON
    if (
        logText.includes('PIPELINE VALIDATION SUCCESSFUL') ||
        logText.includes('PIPELINE COMPLETED SUCCESSFULLY') ||
        logText.includes('Pipeline completed successfully')
    ) {
        showValidationResult(true);
    } else {
        showValidationResult(false);
    }
}

function displayCounts(elementId, data) {
    const element = document.getElementById(elementId);
    element.textContent = JSON.stringify(data, null, 2);
}

function calculateTotal(elementId, data) {

    // If backend already provided total_assets, use it
    if (data.total_assets !== undefined) {
        document.getElementById(elementId).textContent = data.total_assets;
        return;
    }

    // Otherwise calculate manually (fallback)
    let total = 0;

    function sumValues(obj) {
        for (let key in obj) {

            // Skip total fields to avoid double count
            if (key.toLowerCase().includes("total")) continue;

            if (typeof obj[key] === 'number') {
                total += obj[key];
            } else if (typeof obj[key] === 'object') {
                sumValues(obj[key]);
            }
        }
    }

    sumValues(data);
    document.getElementById(elementId).textContent = total;
}

function showValidationResult(success) {
    const resultDiv = document.getElementById('validationResult');
    const surveyId = document.getElementById('surveyId').value.trim();
    const downloadBtn = document.getElementById('downloadBtn');

    resultDiv.style.display = 'block';

    if (success) {
        resultDiv.className = 'validation-result success';
        resultDiv.textContent =
            '✅ Congratulations! All counts are correct. Dashboard and Excel counts match!';

        // Show and attach download button ONLY on success
        downloadBtn.style.display = 'block';
        downloadBtn.onclick = function () {
            window.location.href = `/download/${currentProcessId}`;
        };

        // Trigger fireworks animation
        launchFireworks();
    } else {
        resultDiv.className = 'validation-result error';
        resultDiv.textContent =
            '❌ Validation Failed. Dashboard and Excel counts do not match.';

        // Hide download button on failure
        downloadBtn.style.display = 'none';
    }
}

function clearLogs() {
    document.getElementById('logsContainer').innerHTML = '';
}

function updateStatus(text) {
    document.getElementById('statusText').textContent = text;
}

function resetUI() {
    const runBtn = document.getElementById('runBtn');
    runBtn.disabled = false;
    runBtn.textContent = 'Run Pipeline';
}
function detectStepFromLog(logLine) {

    // Detect main step start
    const startMatch = logLine.match(/STARTING STEP\s*:\s*(.*)/);
    if (startMatch) {
        const stepName = startMatch[1].trim();
        currentStep = stepName;
        handleStepStart(stepName);
        return;
    }

    // Detect step completion
    const doneMatch = logLine.match(/COMPLETED STEP\s*:\s*(.*)/);
    if (doneMatch) {
        const stepName = doneMatch[1].trim();
        handleStepComplete(stepName);
        return;
    }

    // Sub-stage detections
    if (logLine.includes("[DOWNLOAD] Stage started")) {
        updateFunnyMessage("🛰️ Downloading excels from outerspace...");
    }

    if (logLine.includes("Running MCW_final module")) {
        updateFunnyMessage("⛏️ Extracting MCW counts like gold mining...");
    }

    if (logLine.includes("Processing MCW folder")) {
        updateFunnyMessage("� Sorting through the digital filing cabinet...");
    }

    if (logLine.includes("VALIDATOR STARTED")) {
        updateFunnyMessage("📡 Calling Einstein for validation...");
    }

    if (logLine.includes("FINAL VALIDATION STARTED")) {
        updateFunnyMessage("⚖️ Comparing dashboard vs Excel in multiverse...");
    }

    if (logLine.includes("🎉 VALIDATION PASSED")) {
        updateFunnyMessage("🎉 Universe aligned. Validation successful!");
    }
}
function handleStepStart(stepName) {

    const messages = {
        "D_A Download": "🚀 Initiating download engines...",
        "final_colour_format": "🎨 Formatting the rainbows into cells...",
        "dp1 asset mapping": "🧠 Mapping assets with quantum AI...",
        "allasset update": "🔄 Syncing the master database...",
        "validator api counts": "📡 Fetching dashboard truth...",
        "xlsx validator": "📊 Counting Excel atoms carefully...",
        "final validator compare": "⚖️ Running final comparison engine..."
    };

    for (let key in messages) {
        if (stepName.includes(key)) {
            updateFunnyMessage(messages[key]);
            startStepTimer();
            break;
        }
    }
}

function handleStepComplete(stepName) {

    updateFunnyMessage(`✅ ${stepName} completed. Moving to next...`);
    clearStepTimer();
}
function startStepTimer() {

    clearStepTimer();

    stepTimer = setTimeout(() => {
        updateFunnyMessage("🤯 This step is taking longer than expected... digging deeper...");
    }, 9000);
}

function clearStepTimer() {
    if (stepTimer) {
        clearTimeout(stepTimer);
        stepTimer = null;
    }
}
function updateFunnyMessage(message) {

    if (message === lastFunnyMessage) return;
    lastFunnyMessage = message;

    const bar = document.getElementById('funnyMessageBar');
    const text = document.getElementById('funnyTextInline');

    if (!bar.classList.contains('show')) {
        bar.classList.add('show');
    }

    bar.classList.add('fade');

    setTimeout(() => {
        text.textContent = message;
        bar.classList.remove('fade');
    }, 250);
}

function clearFunnyMessage() {
    const bar = document.getElementById('funnyMessageBar');
    bar.classList.remove('show');
}

function launchFireworks() {
    // Check if confetti script is loaded
    if (typeof confetti !== 'undefined') {
        const duration = 3000;
        const animationEnd = Date.now() + duration;
        const defaults = { startVelocity: 30, spread: 360, ticks: 60, zIndex: 0 };

        function randomInRange(min, max) {
            return Math.random() * (max - min) + min;
        }

        const interval = setInterval(function () {
            const timeLeft = animationEnd - Date.now();

            if (timeLeft <= 0) {
                return clearInterval(interval);
            }

            const particleCount = 50 * (timeLeft / duration);

            // since particles fall down, start a bit higher than random
            confetti(Object.assign({}, defaults, { particleCount, origin: { x: randomInRange(0.1, 0.3), y: Math.random() - 0.2 } }));
            confetti(Object.assign({}, defaults, { particleCount, origin: { x: randomInRange(0.7, 0.9), y: Math.random() - 0.2 } }));
        }, 250);

        updateFunnyMessage("🎉 CONGRATULATIONS! Pipeline Mastered! 🎆");
    }
}

// Handle page unload
window.addEventListener('beforeunload', function () {
    if (eventSource) {
        eventSource.close();
    }
});
