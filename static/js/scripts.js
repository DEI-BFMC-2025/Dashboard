document.addEventListener('DOMContentLoaded', () => {
    const socket = io();
    initializeTerminal(socket);
    setupEventListeners(socket);
});

function initializeTerminal(socket) {
    const term = new Terminal();
    term.open(document.getElementById('terminal'));
    
    term.onData(data => socket.emit('terminal_input', data));
    socket.on('terminal_output', output => term.write(output));
}

function setupEventListeners(socket) {
    document.querySelectorAll('button').forEach(button => {
        button.addEventListener('click', handleButtonClick);
    });

    socket.on('metrics_update', updateMetrics);
}

function handleButtonClick(event) {
    const action = event.target.textContent.trim();
    const scriptMap = {
        'Start Script': 'start_script',
        'Stop Script': 'stop_script',
        'Test Script': 'test_script',
        'IMU Script': 'imu_script',
        'GPS Script': 'gps_script'
    };

    if (scriptMap[action]) {
        runSSH(scriptMap[action]);
    } else if (action === 'Run Custom Script') {
        runCustomScript();
    } else if (action === 'Stop Custom Script') {
        stopCustomScript();
    }
}

async function runSSH(script) {
    try {
        const response = await fetch(`/${script}`, { method: 'POST' });
        const result = await response.json();
        alert(result.message);
    } catch (error) {
        alert('Error running script: ' + error);
    }
}

async function runCustomScript() {
    const script = document.getElementById('custom-script').value;
    if (!script) {
        alert('Please enter a script');
        return;
    }
    try {
        const response = await fetch('/run_custom_script', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ script })
        });
        const result = await response.json();
        alert(result.message);
    } catch (error) {
        alert('Error running custom script: ' + error);
    }
}

async function stopCustomScript() {
    try {
        const response = await fetch('/stop_custom_script', { method: 'POST' });
        const result = await response.json();
        alert(result.message);
    } catch (error) {
        alert('Error stopping custom script: ' + error);
    }
}

function updateMetrics(data) {
    document.getElementById('state').textContent = data.STATE || '-';
    document.getElementById('prev-event').textContent = data.PREV_EVENT || '-';
    document.getElementById('next-event').textContent = data.UPCOMING_EVENT || '-';

    const routinesContainer = document.getElementById('routines');
    routinesContainer.innerHTML = data.ROUTINES?.join(', ') || '-';

    if (data.CONDITIONS) {
        document.getElementById('condition-highway').textContent      = data.CONDITIONS.HIGHWAY ?? '-';
        document.getElementById('condition-can-overtake').textContent = data.CONDITIONS.CAN_OVERTAKE ?? '-';
        document.getElementById('condition-trust-gps').textContent    = data.CONDITIONS.TRUST_GPS ?? '-';
        document.getElementById('condition-car-on-path').textContent  = data.CONDITIONS.CAR_ON_PATH ?? '-';
        document.getElementById('condition-no-lane').textContent      = data.CONDITIONS.NO_LANE ?? '-';
        document.getElementById('condition-rerouting').textContent    = data.CONDITIONS.REROUTING ?? '-';
    }

    const metrics = [
        'SPEED', 'STEER', 'DISTANCE', 
        'SONAR_L', 'SONAR_R', 'SONAR_C', 
        'YAW', 'HEADING'
    ];

    metrics.forEach(metric => {
        const element = document.getElementById(metric.toLowerCase());
        if (element && data[metric] !== undefined && data[metric] !== '') {
            element.textContent = data[metric];
        }
    });
}