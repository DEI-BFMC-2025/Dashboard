class LidarVisualizer {
    constructor(containerId) {
        this.container = document.getElementById(containerId);
        this.width = 400;
        this.height = 400;
        this.points = [];

        this.minDistance = 0.10; // in meters
        this.maxDistance = 0.35; // in meters
        this.scale = 6; // pixels per cm

        this.angleOffset = 90; // Adjust this value to compensate for misalignment

        // Create canvas
        this.canvas = document.createElement('canvas');
        this.canvas.width = this.width;
        this.canvas.height = this.height;
        this.canvas.style.border = "1px solid #444";
        this.container.appendChild(this.canvas);
        this.ctx = this.canvas.getContext('2d');

        // Connect to WebSocket
        this.socket = io('/lidar');
        this.socket.on('lidar_update', (data) => {
            // debugging
            // console.log("Raw LIDAR data:", data);

            this.points = data.points
                //if needed to filter
                .filter(point => {
                    // Filter based on the provided distance in meters
                    return point.distance >= this.minDistance && point.distance <= this.maxDistance;
                })
                .map(point => {
                    // Convert polar coordinates (angle, distance) to Cartesian (x, y) in meters
                    const adjustedAngle = point.angle + this.angleOffset;
                    const angleRad = (adjustedAngle * Math.PI) / 180; //deg to rad
                    const x = -point.distance * Math.cos(angleRad);
                    const y = point.distance * Math.sin(angleRad);
                    
                    // Convert to centimeters for visualization
                    return {
                        x: x * 100,
                        y: y * 100
                    };
                });

            this.draw();
        });

        this.drawGrid();
    }

    // Draw the grid and distance rings
    // and radial lines
    drawGrid() {
        const ctx = this.ctx;
        ctx.fillStyle = '#111';
        ctx.fillRect(0, 0, this.width, this.height);

        const centerX = this.width / 2;
        const centerY = this.height / 2;

        // Draw robot center
        ctx.fillStyle = 'rgba(0, 255, 42, 0.4)';
        ctx.beginPath();
        ctx.arc(centerX, centerY, 6, 0, Math.PI * 2);
        ctx.fill();

        // Draw distance rings as semicircles
        ctx.strokeStyle = 'rgba(255, 255, 255, 0.3)';
        ctx.lineWidth = 1;
        ctx.font = '10px Arial';
        ctx.fillStyle = 'white';

        const minCM = this.minDistance * 100;
        const maxCM = this.maxDistance * 100;

        for (let dist = minCM; dist <= maxCM; dist += 5) {
            const radius = (dist - minCM) * this.scale;
            ctx.beginPath();
            // Draw semicircle from 135° (3π/4) to 405° (9π/4) in original coordinates
            ctx.arc(centerX, centerY, radius, 3*Math.PI/4, 9*Math.PI/4);
            ctx.stroke();

            if (dist !== minCM )  {
                // Label positioned at 270° (bottom) in original coordinates (right side in rotated view)
                const labelAngle = 3*Math.PI/2; // 270° in original coordinates
                const labelX = centerX + Math.cos(labelAngle) * (radius + 10);
                const labelY = centerY + Math.sin(labelAngle) * (radius + 10);
                ctx.fillText(`${(dist)}cm`, labelX - 15, labelY + 5);
            }
        }

        // Radial lines at 45° increments in ROTATED coordinates
        ctx.strokeStyle = 'rgba(255, 255, 255, 0.2)';
        const angles = [45, 90, 135, 180, 225, 270, 315];
        
        angles.forEach(angle => {
            // Convert to original coordinate system angles
            const originalAngle = (angle + 90) % 360;
            const rad = originalAngle * Math.PI / 180;

            const endRadius = (maxCM - minCM) * this.scale;
            const endX = centerX + Math.cos(rad) * endRadius;
            const endY = centerY + Math.sin(rad) * endRadius;

            ctx.beginPath();
            ctx.moveTo(centerX, centerY);
            ctx.lineTo(endX, endY);
            ctx.stroke();

            // flippe the angles, find the labbeling issue/bug in the future
            angle = 360 - angle;

            // label positioning
            let textOffsetX = 0, textOffsetY = 0;
            if (angle === 45 || angle === 315) textOffsetX = -15;
            if (angle === 135 || angle === 225) textOffsetX = -5;
            if (angle === 90) textOffsetY = 2;
            if (angle === 270) textOffsetX = -5;
            if (angle === 180) textOffsetX = -10;

            // label in rotated coordinates
            const labelRadius = endRadius + 25;
            const labelX = centerX + Math.cos(rad) * labelRadius;
            const labelY = centerY + Math.sin(rad) * labelRadius;
            
            ctx.fillText(`${angle}°`, labelX + textOffsetX, labelY + textOffsetY);  //FLIPED THE LABELS
        });
    }

    draw() {
        this.drawGrid();

        const centerX = this.width / 2;
        const centerY = this.height / 2;

        const minCM = this.minDistance * 100;
        const maxCM = this.maxDistance * 100;

        this.points.forEach(point => {
            const distance = Math.sqrt(point.x ** 2 + point.y ** 2);

            const offsetX = (point.x / distance) * (distance - minCM) * this.scale;
            const offsetY = (point.y / distance) * (distance - minCM) * this.scale;

            const x = centerX + offsetX;
            const y = centerY + offsetY;

            // Normalize distance to a range of 0 to 1 and map to rgb values
            const ratio = (distance - minCM) / (maxCM - minCM);
            const r = Math.min(255, Math.floor(255 * (1 - ratio)));
            const g = Math.min(255, Math.floor(255 * ratio));
            const b = 0;

            this.ctx.fillStyle = `rgb(${r}, ${g}, ${b})`;
            this.ctx.beginPath();
            this.ctx.arc(x, y, 4, 0, Math.PI * 2);
            this.ctx.fill();
        });
        // debugging
        //console.log(`Rendering ${this.points.length} points`);
    }
}


// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    const socket = io();
    initializeTerminal(socket);
    setupEventListeners(socket);
    // Add this line to initialize LIDAR visualizer
    new LidarVisualizer('lidar-container');
});

function initializeTerminal(socket) {
    const term = new Terminal();
    term.open(document.getElementById('terminal'));
    
    term.onData(data => socket.emit('terminal_input', data));
    socket.on('terminal_output', output => term.write(output));
}

function setupEventListeners(socket) {
    // System control buttons
    document.querySelectorAll('.system-control').forEach(button => {
        button.addEventListener('click', handleSystemControl);
    });

    socket.on('metrics_update', updateMetrics);
}

async function handleSystemControl(event) {
    const button = event.target;
    const system = button.dataset.system;
    const action = button.dataset.action;
    
    try {
        const response = await fetch(`/control/${system}/${action}`, { 
            method: 'POST' 
        });
        const result = await response.json();
        
        // Update button state visually
        if (result.success) {
            button.classList.add('active');
            const oppositeAction = action === 'start' ? 'stop' : 'start';
            document.querySelector(`[data-system="${system}"][data-action="${oppositeAction}"]`)
                .classList.remove('active');
        } else {
            // Only show alert for failures
            alert(`Failed to ${action} ${system}: ${result.message}`);
        }
    } catch (error) {
        alert('Error: ' + error.message);
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