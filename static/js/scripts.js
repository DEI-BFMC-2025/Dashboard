class LidarVisualizer {
    constructor(containerId) {
        this.container = document.getElementById(containerId);
        this.width = this.container.clientWidth;  //get from the index.html
        this.height = this.container.clientHeight;
        this.points = [];

        this.tofDistance = 0; // TOF distance in mm

        this.minDistance = 0.0; // in meters
        this.maxDistance = 0.50; // in meters
        this.scale = 6; // pixels per cm

        this.angleOffset = 90; // Adjust this value to compensate for misalignment

        //Shift center of the drawings
        this.shiftOnY = 0;
        this.shiftOnX = 100;
        // Create canvas
        this.canvas = document.createElement('canvas');
        this.canvas.width = this.width + this.shiftOnX;
        this.canvas.height = this.height;
        this.canvas.style.border = "0px solid #444";
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

    setFrontTofDistance(distance) {
        this.tofFrontDistance = Number(distance) || 0;
    }

    setLeftTofDistance(distance) {
        this.tofLeftDistance = Number(distance) || 0;
    }

    // Front TOF line drawing
// Front TOF line drawing
drawFrontTofLine() {
    const centerX = this.width / 2 + + this.shiftOnX;
    const centerY = this.height / 2 + this.shiftOnY;
    
    // Use LIDAR's range but limit to TOF's capabilities
    const minCM = this.minDistance * 100; // 10cm (matches LIDAR start)
    const maxCM = 25.5;                   // TOF's max 25.5cm

    const tofCM = this.tofFrontDistance / 10;
    const clampedCM = Math.max(minCM, Math.min(maxCM, tofCM));
    
    // Calculate position relative to LIDAR's visualization
    const positionFromCenter = (clampedCM - minCM) * this.scale;

    this.ctx.beginPath();
    this.ctx.moveTo(centerX - 30, centerY - positionFromCenter);
    this.ctx.lineTo(centerX + 30, centerY - positionFromCenter);
    this.ctx.strokeStyle = 'cyan';
    this.ctx.lineWidth = 4;
    this.ctx.stroke();
}

// Left TOF line drawing
drawLeftTofLine() {
    const centerX = this.width / 2 + this.shiftOnX;
    const centerY = this.height / 2 + this.shiftOnY;
    const minCM = this.minDistance * 100; // 10cm
    const maxCM = 25.5;                   // 25.5cm

    const tofCM = this.tofLeftDistance / 10;
    const clampedCM = Math.max(minCM, Math.min(maxCM, tofCM));
    
    // Position calculation with LIDAR alignment
    const positionFromCenter = (clampedCM - minCM) * this.scale;

    this.ctx.beginPath();
    this.ctx.moveTo(centerX - positionFromCenter, centerY - 30);
    this.ctx.lineTo(centerX - positionFromCenter, centerY + 30);
    this.ctx.strokeStyle = 'magenta';
    this.ctx.lineWidth = 4;
    this.ctx.stroke();
}

    // Draw the grid and distance rings
    // and radial lines
    drawGrid() {
        const ctx = this.ctx;

        const centerX = this.width / 2 + this.shiftOnX;
        const centerY = this.height / 2 + this.shiftOnY;

        // Draw distance rings as semicircles
        ctx.strokeStyle = 'rgba(170, 170, 170, 0.3)';
        ctx.lineWidth = 1;
        ctx.font = '14px Helvetica';
        ctx.fillStyle = 'rgba(240, 240, 240, 0.3)';

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
            const originalAngle = (angle + 90) % 360;
            const rad = originalAngle * Math.PI / 180;
                
            const endRadius = (maxCM - minCM) * this.scale;
            const endX = centerX + Math.cos(rad) * endRadius;
            const endY = centerY + Math.sin(rad) * endRadius;
                
            ctx.beginPath();
            ctx.moveTo(centerX, centerY);
            ctx.lineTo(endX, endY);
            ctx.stroke();
                
            // flip angles to match display
            angle = 360 - angle;
                
            // remap to signed labels where appropriate
            let displayAngle = angle;
            if (angle === 225) displayAngle = -135;
            else if (angle === 270) displayAngle = -90;
            else if (angle === 315) displayAngle = -45;
            
                
            // label positioning
            let textOffsetX = 0, textOffsetY = 0;
            if (angle === 45 || angle === 315) textOffsetX = -15;
            if (angle === 135 || angle === 225) textOffsetX = -5;
            if (angle === 90) textOffsetY = 2;
            if (angle === 270) textOffsetX = -5;
            if (angle === 180) textOffsetX = -25;
                
            const labelRadius = endRadius + 25;
            const labelX = centerX + Math.cos(rad) * labelRadius;
            const labelY = centerY + Math.sin(rad) * labelRadius;
                
            if (angle === 180)
                ctx.fillText(`-180° 180°`, labelX + textOffsetX, labelY + textOffsetY);
            else
                ctx.fillText(`${displayAngle}°`, labelX + textOffsetX, labelY + textOffsetY);
        });

    }

    draw() {
        this.drawGrid();
        
        //the tof lines
        if (this.tofFrontDistance) {
            this.drawFrontTofLine();
        }
        if (this.tofLeftDistance) {
            this.drawLeftTofLine();
        }

        const centerX = this.width / 2 + this.shiftOnX;
        const centerY = this.height / 2 + this.shiftOnY;

        const minCM = this.minDistance * 100;
        const maxCM = this.maxDistance * 100;

        this.points.forEach(point => {
            const distance = Math.sqrt(point.x ** 2 + point.y ** 2);

            const offsetX = (point.x / distance) * (distance - minCM) * this.scale;
            const offsetY = (point.y / distance) * (distance - minCM) * this.scale;

            const x = centerX + offsetX;
            const y = centerY + offsetY;

            // Normalize distance to a range of 0 to 1 and map to rgb values
            const ratio = (distance - 15) / (maxCM - 15); //minCM or 15 cm for better viz
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
    
    // Create and store the LIDAR instance
    const lidarVisualizer = new LidarVisualizer('lidar-container');
    
    // Pass the instance to setup
    setupEventListeners(socket, lidarVisualizer);  // Add parameter here
});

function initializeTerminal(socket) {
    const term = new Terminal();
    term.open(document.getElementById('terminal'));
    
    term.onData(data => socket.emit('terminal_input', data));
    socket.on('terminal_output', output => term.write(output));
}

function setupEventListeners(socket, lidarVisualizer) {
    // System control buttons
    document.querySelectorAll('.system-control').forEach(button => {
        button.addEventListener('click', handleSystemControl);
    });

    socket.on('metrics_update', (data) => {
        // Update metrics section
        updateMetrics(data);

        //for the lines
        if (data.TOF_FRONT !== undefined) {
            lidarVisualizer.setFrontTofDistance(data.TOF_FRONT);
        }
        if (data.TOF_LEFT !== undefined) {
            lidarVisualizer.setLeftTofDistance(data.TOF_LEFT);
        }
    });
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
        
        // On succes update button state visually  // TODO: Handle better the cases in which there is no start & stop , i.e. when we have only restart 
        if (result.success) {
            //button.classList.add('active');
            //const oppositeAction = action === 'start' ? 'stop' : 'start';
            //document.querySelector(`[data-system="${system}"][data-action="${oppositeAction}"]`)
            //    .classList.remove('active');
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
        document.getElementById('condition-tunnel').textContent       = data.CONDITIONS.TUNNEL ?? '-';
        document.getElementById('condition-car-on-path').textContent  = data.CONDITIONS.CAR_ON_PATH ?? '-';
        document.getElementById('condition-no-lane').textContent      = data.CONDITIONS.NO_LANE ?? '-';
        document.getElementById('condition-rerouting').textContent    = data.CONDITIONS.REROUTING ?? '-';
    }

    const metrics = [
        'SPEED_CMD','SPEED', 'STEER', 'DISTANCE', 
        'YAW', 'HEADING','TOF_FRONT','TOF_LEFT','HEADLIGHTS'
    ];

    metrics.forEach(metric => {
        const element = document.getElementById(metric.toLowerCase());
        if (element && data[metric] !== undefined && data[metric] !== '') {
            if (metric === 'HEADLIGHTS') {
                element.textContent = data[metric] ? 'ON' : 'OFF';
            } else {
                element.textContent = data[metric];
            }
        }

    });
}