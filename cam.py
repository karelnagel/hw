# webcam_server.py
from flask import Flask, Response, render_template_string
import cv2
import odrive
from odrive.enums import AXIS_STATE_CLOSED_LOOP_CONTROL, AXIS_STATE_IDLE
import time
import signal
import sys
import atexit
import threading
from flask import request, jsonify

app = Flask(__name__)

# Capture video from the first camera (usually /dev/video0)
camera = cv2.VideoCapture(0)

# Set camera properties for better performance
camera.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
camera.set(cv2.CAP_PROP_FPS, 15)  # Reduce FPS for better streaming

# Global variables for cleanup
odrv0 = None
axis0 = None
axis1 = None

# Global variables for status
battery_voltage = 0.0
motor_currents = [0.0, 0.0]
motor_temperatures = [0.0, 0.0]
uptime = 0
current_speed = 1.0  # Default speed

def get_battery_percentage(voltage):
    """Convert voltage to battery percentage (assuming 4S LiPo: 16.8V full, 12.6V empty)"""
    if voltage <= 12.6:
        return 0
    elif voltage >= 16.8:
        return 100
    else:
        return int(((voltage - 12.6) / (16.8 - 12.6)) * 100)

def get_battery_status():
    """Get battery and motor status from ODrive"""
    global battery_voltage, motor_currents, motor_temperatures
    try:
        if odrv0:
            battery_voltage = odrv0.vbus_voltage
            motor_currents = [axis0.motor.current_control.Iq_measured, axis1.motor.current_control.Iq_measured]
            # Note: ODrive doesn't have built-in temperature sensors, but we can monitor current as a proxy
            motor_temperatures = [abs(current) * 10 for current in motor_currents]  # Rough estimate
    except Exception as e:
        print(f"Error reading status: {e}")

def status_monitor():
    """Background thread to monitor system status"""
    global uptime
    start_time = time.time()
    while True:
        uptime = int(time.time() - start_time)
        get_battery_status()
        time.sleep(1)

def cleanup_motors():
    """Cleanup function to stop motors and return to idle state"""
    global axis0, axis1
    if axis0 and axis1:
        print("Returning to idle state...")
        try:
            axis0.requested_state = AXIS_STATE_IDLE
            axis1.requested_state = AXIS_STATE_IDLE
        except Exception as e:
            print(f"Error during cleanup: {e}")

def signal_handler(sig, frame):
    """Handle Ctrl+C and other termination signals"""
    print("\nShutting down gracefully...")
    cleanup_motors()
    sys.exit(0)

# Register signal handlers and cleanup
signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)
atexit.register(cleanup_motors)

try:
  odrv0 = odrive.find_any(timeout=3)
  axis0 = odrv0.axis0
  axis1 = odrv0.axis1

  print("\nStarting motors")
  axis0.requested_state = AXIS_STATE_CLOSED_LOOP_CONTROL
  axis1.requested_state = AXIS_STATE_CLOSED_LOOP_CONTROL
except:
  print("Odrive failed")

time.sleep(1)

def move(left, right, speed=None):
    """Move motors with specified speed"""
    global current_speed
    if speed is not None:
        current_speed = max(0.1, min(3.0, speed))  # Clamp between 0.1 and 3.0
    
    axis0.controller.input_vel = right * current_speed
    axis1.controller.input_vel = left * -1 * current_speed

# Start status monitoring thread
status_thread = threading.Thread(target=status_monitor, daemon=True)
status_thread.start()

HTML_PAGE = """
<!doctype html>
<html>
<head>
  <title>Orange Pi Robot Control</title>
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <style>
    * {
      margin: 0;
      padding: 0;
      box-sizing: border-box;
    }
    
    body {
      font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
      background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
      min-height: 100vh;
      padding: 20px;
    }
    
    .container {
      max-width: 1200px;
      margin: 0 auto;
      background: rgba(255, 255, 255, 0.95);
      border-radius: 20px;
      padding: 20px;
      box-shadow: 0 20px 40px rgba(0,0,0,0.1);
    }
    
    .header {
      text-align: center;
      margin-bottom: 20px;
      color: #333;
    }
    
    .video-container {
      text-align: center;
      margin-bottom: 20px;
    }
    
    .video-container img {
      max-width: 100%;
      height: auto;
      border-radius: 15px;
      box-shadow: 0 10px 30px rgba(0,0,0,0.2);
    }
    
    .status-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
      gap: 10px;
      margin-bottom: 15px;
    }
    
    .status-card {
      background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
      color: white;
      padding: 10px;
      border-radius: 10px;
      text-align: center;
      box-shadow: 0 3px 10px rgba(0,0,0,0.1);
    }
    
    .status-card > div:first-child {
      font-size: 12px;
      margin-bottom: 3px;
    }
    
    .status-value {
      font-size: 18px;
      font-weight: bold;
      margin: 3px 0;
    }
    
    .status-card > div:last-child {
      font-size: 10px;
      opacity: 0.9;
    }
    
    .battery-bar {
      width: 100%;
      height: 12px;
      background: rgba(255,255,255,0.3);
      border-radius: 6px;
      overflow: hidden;
      margin-top: 5px;
    }
    
    .battery-fill {
      height: 100%;
      background: linear-gradient(90deg, #ff4757, #ffa502, #2ed573);
      transition: width 0.3s ease;
    }
    
    .controls-section {
      display: flex;
      flex-direction: column;
      align-items: center;
      gap: 15px;
    }
    
    .keyboard-hint {
      background: rgba(102, 126, 234, 0.1);
      padding: 8px 15px;
      border-radius: 8px;
      text-align: center;
      color: #667eea;
      font-weight: 500;
      font-size: 14px;
    }
    
    .speed-control {
      background: rgba(255, 255, 255, 0.9);
      padding: 12px;
      border-radius: 12px;
      text-align: center;
      box-shadow: 0 3px 10px rgba(0,0,0,0.1);
      margin-bottom: 15px;
    }
    
    .speed-control > div:first-child {
      font-size: 14px;
      margin-bottom: 5px;
    }
    
    .speed-slider {
      width: 180px;
      height: 6px;
      border-radius: 3px;
      background: #ddd;
      outline: none;
      margin: 8px 0;
    }
    
    .speed-slider::-webkit-slider-thumb {
      appearance: none;
      width: 16px;
      height: 16px;
      border-radius: 50%;
      background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
      cursor: pointer;
      box-shadow: 0 2px 4px rgba(0,0,0,0.2);
    }
    
    .speed-slider::-moz-range-thumb {
      width: 16px;
      height: 16px;
      border-radius: 50%;
      background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
      cursor: pointer;
      border: none;
      box-shadow: 0 2px 4px rgba(0,0,0,0.2);
    }
    
    .speed-value {
      font-size: 16px;
      font-weight: bold;
      color: #667eea;
    }
    
    #joystick {
      width: 220px;
      height: 220px;
      background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
      border-radius: 50%;
      position: relative;
      touch-action: none;
      box-shadow: 0 10px 25px rgba(0,0,0,0.2);
      border: 4px solid white;
    }
    
    #stick {
      width: 60px;
      height: 60px;
      background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
      border-radius: 50%;
      position: absolute;
      left: 80px;
      top: 80px;
      touch-action: none;
      box-shadow: 0 5px 15px rgba(0,0,0,0.3);
      border: 3px solid white;
      transition: all 0.1s ease;
    }
    
    .mobile-controls {
      display: none;
      grid-template-columns: repeat(3, 1fr);
      gap: 12px;
      margin-top: 15px;
    }
    
    .mobile-btn {
      padding: 15px;
      background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
      color: white;
      border: none;
      border-radius: 12px;
      font-size: 20px;
      font-weight: bold;
      touch-action: manipulation;
      box-shadow: 0 5px 15px rgba(0,0,0,0.2);
    }
    
    .mobile-btn:active {
      transform: scale(0.95);
    }
    
    @media (max-width: 768px) {
      .container {
        padding: 12px;
        margin: 8px;
      }
      
      .status-grid {
        grid-template-columns: repeat(2, 1fr);
        gap: 8px;
      }
      
      .mobile-controls {
        display: grid;
      }
      
      #joystick {
        width: 180px;
        height: 180px;
      }
      
      #stick {
        width: 50px;
        height: 50px;
        left: 65px;
        top: 65px;
      }
      
      .speed-slider {
        width: 140px;
      }
    }
  </style>
</head>
<body>
  <div class="container">
    <div class="header">
      <h1>🤖 Orange Pi Robot Control</h1>
    </div>
    
    <div class="video-container">
      <img src="{{ url_for('video_feed') }}" alt="Robot Camera Feed" id="video-feed">
    </div>
    
    <div class="status-grid">
      <div class="status-card">
        <div>🔋 Battery</div>
        <div class="status-value" id="battery-percentage">--%</div>
        <div class="battery-bar">
          <div class="battery-fill" id="battery-fill"></div>
        </div>
        <div id="battery-voltage">--V</div>
      </div>
      
      <div class="status-card">
        <div>⚡ Current</div>
        <div class="status-value" id="motor-current">--A</div>
        <div>Motor Load</div>
      </div>
      
      <div class="status-card">
        <div>🌡️ Temperature</div>
        <div class="status-value" id="motor-temp">--°C</div>
        <div>Motor Temp</div>
      </div>
      
      <div class="status-card">
        <div>⏱️ Uptime</div>
        <div class="status-value" id="uptime">--s</div>
        <div>Running Time</div>
      </div>
    </div>
    
    <div class="speed-control">
      <div>🚀 Speed Control</div>
      <input type="range" min="0.1" max="1.5" step="0.1" value="1" class="speed-slider" id="speed-slider">
      <div class="speed-value" id="speed-value">1.0x</div>
    </div>
    
    <div class="controls-section">
      <div class="keyboard-hint">
        💡 Use arrow keys or WASD to control the robot
      </div>
      
      <div id="joystick">
        <div id="stick"></div>
      </div>
      
      <div class="mobile-controls">
        <button class="mobile-btn" data-action="forward">⬆️</button>
        <button class="mobile-btn" data-action="left">⬅️</button>
        <button class="mobile-btn" data-action="stop">⏹️</button>
        <button class="mobile-btn" data-action="right">➡️</button>
        <button class="mobile-btn" data-action="backward">⬇️</button>
      </div>
    </div>
  </div>

<script>
const stick = document.getElementById('stick');
const joystick = document.getElementById('joystick');
const mobileBtns = document.querySelectorAll('.mobile-btn');
const speedSlider = document.getElementById('speed-slider');
const speedValue = document.getElementById('speed-value');

let dragging = false;
let lastSendTime = 0;
const THROTTLE_MS = 100;
let currentX = 0;
let currentY = 0;
let currentSpeed = 1.0;

// Speed control
speedSlider.addEventListener('input', function() {
  currentSpeed = parseFloat(this.value);
  speedValue.textContent = currentSpeed.toFixed(1) + 'x';
});

// Status update function
function updateStatus() {
  fetch('/status')
    .then(res => res.json())
    .then(data => {
      document.getElementById('battery-percentage').textContent = data.battery_percentage + '%';
      document.getElementById('battery-voltage').textContent = data.battery_voltage.toFixed(1) + 'V';
      document.getElementById('battery-fill').style.width = data.battery_percentage + '%';
      document.getElementById('motor-current').textContent = data.motor_current.toFixed(2) + 'A';
      document.getElementById('motor-temp').textContent = data.motor_temp.toFixed(1) + '°C';
      document.getElementById('uptime').textContent = data.uptime + 's';
    })
    .catch(err => console.log('Status update failed:', err));
}

// Update status every 2 seconds
setInterval(updateStatus, 2000);
updateStatus(); // Initial update

// Joystick controls
joystick.addEventListener('pointerdown', e => {
  dragging = true;
  e.preventDefault();
});

document.addEventListener('pointerup', e => {
  if (dragging) {
    dragging = false;
    resetJoystick();
    sendJoystick(0, 0);
  }
});

document.addEventListener('pointermove', e => {
  if (!dragging) return;
  e.preventDefault();
  
  const rect = joystick.getBoundingClientRect();
  let x = e.clientX - rect.left - 110; // Adjusted for smaller joystick
  let y = e.clientY - rect.top - 110;

  const dist = Math.sqrt(x*x + y*y);
  const maxDist = 110; // Adjusted for smaller joystick
  if (dist > maxDist) {
    x = x * maxDist / dist;
    y = y * maxDist / dist;
  }

  stick.style.left = `${x + 110 - 30}px`; // Adjusted positioning
  stick.style.top = `${y + 110 - 30}px`;

  currentX = x / maxDist;
  currentY = -y / maxDist;
  sendJoystick(currentX, currentY);
});

function resetJoystick() {
  stick.style.left = '80px'; // Adjusted for smaller joystick
  stick.style.top = '80px';
  currentX = 0;
  currentY = 0;
}

// Keyboard controls
const keyMap = {
  'ArrowUp': [0, 1],
  'ArrowDown': [0, -1],
  'ArrowLeft': [-1, 0],
  'ArrowRight': [1, 0],
  'KeyW': [0, 1],
  'KeyS': [0, -1],
  'KeyA': [-1, 0],
  'KeyD': [1, 0]
};

// Track currently pressed keys
const pressedKeys = new Set();

document.addEventListener('keydown', e => {
  if (keyMap[e.code]) {
    e.preventDefault();
    pressedKeys.add(e.code);
    updateMovementFromKeys();
  }
});

document.addEventListener('keyup', e => {
  if (keyMap[e.code]) {
    e.preventDefault();
    pressedKeys.delete(e.code);
    updateMovementFromKeys();
  }
});

function updateMovementFromKeys() {
  let x = 0, y = 0;
  
  // Calculate combined movement from all pressed keys
  for (const key of pressedKeys) {
    const [keyX, keyY] = keyMap[key];
    x += keyX;
    y += keyY;
  }
  
  // Normalize diagonal movement to prevent faster diagonal speed
  if (x !== 0 && y !== 0) {
    x *= 0.707; // 1/√2
    y *= 0.707;
  }
  
  // Clamp to [-1, 1] range
  x = Math.max(-1, Math.min(1, x));
  y = Math.max(-1, Math.min(1, y));
  
  currentX = x;
  currentY = y;
  
  if (pressedKeys.size === 0) {
    // No keys pressed, reset joystick
    resetJoystick();
    sendJoystick(0, 0);
  } else {
    // Update joystick visual and send movement
    updateJoystickVisual(x, y);
    sendJoystick(x, y);
  }
}

function updateJoystickVisual(x, y) {
  const maxDist = 110; // Adjusted for smaller joystick
  const visualX = x * maxDist;
  const visualY = -y * maxDist;
  stick.style.left = `${visualX + 110 - 30}px`; // Adjusted positioning
  stick.style.top = `${visualY + 110 - 30}px`;
}

// Mobile button controls
mobileBtns.forEach(btn => {
  btn.addEventListener('touchstart', e => {
    e.preventDefault();
    const action = btn.dataset.action;
    let x = 0, y = 0;
    
    switch(action) {
      case 'forward': y = 1; break;
      case 'backward': y = -1; break;
      case 'left': x = -1; break;
      case 'right': x = 1; break;
      case 'stop': x = 0; y = 0; break;
    }
    
    currentX = x;
    currentY = y;
    updateJoystickVisual(x, y);
    sendJoystick(x, y);
  });
  
  btn.addEventListener('touchend', e => {
    e.preventDefault();
    resetJoystick();
    sendJoystick(0, 0);
  });
});

function sendJoystick(x, y) {
  const now = Date.now();
  // Bypass throttling for stop signals (x=0, y=0)
  if (x === 0 && y === 0) {
    lastSendTime = now;
  } else if (now - lastSendTime < THROTTLE_MS) {
    return; // Skip if not enough time has passed
  } else {
    lastSendTime = now;
  }
  
  fetch('/control', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({x, y, speed: currentSpeed})
  })
  .then(res => res.json())
  .then(data => {
    console.log("Wheel output:", data);
  })
  .catch(err => console.log('Control failed:', err));
}

// Prevent context menu on long press
document.addEventListener('contextmenu', e => e.preventDefault());
</script>
</body>
</html>
"""

def generate_frames():
    while True:
        success, frame = camera.read()
        if not success:
            break
        else:
            # Encode frame as JPEG
            ret, buffer = cv2.imencode('.jpg', frame)
            frame = buffer.tobytes()

            # Yield the frame as a multipart HTTP response
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')

@app.route('/')
def index():
    return render_template_string(HTML_PAGE)

@app.route('/video_feed')
def video_feed():
    return Response(generate_frames(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/status')
def status():
    """Return system status including battery level"""
    battery_percentage = get_battery_percentage(battery_voltage)
    motor_current = max(abs(current) for current in motor_currents) if motor_currents else 0
    motor_temp = max(motor_temperatures) if motor_temperatures else 0
    
    return {
        'battery_voltage': battery_voltage,
        'battery_percentage': battery_percentage,
        'motor_current': motor_current,
        'motor_temp': motor_temp,
        'uptime': uptime
    }

@app.route('/control', methods=['POST'])
def control():
    data = request.get_json()
    x = data.get('x', 0)   # horizontal (-1 to 1)
    y = data.get('y', 0)   # vertical (-1 to 1)
    speed = data.get('speed', 1.0)  # speed multiplier (0.1 to 3.0)

    # Map joystick input to differential drive wheel speeds
    left = y + x
    right = y - x

    # Clamp to [-1, 1]
    left = max(-1, min(1, left))
    right = max(-1, min(1, right))

    move(left=left, right=right, speed=speed)
    print(f"{left=}, {right=}, speed={speed}")

    return jsonify(left=left, right=right, speed=speed)

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000, debug=False)
