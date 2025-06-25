# webcam_server.py
from flask import Flask, Response, render_template_string
import cv2

app = Flask(__name__)

# Capture video from the first camera (usually /dev/video0)
camera = cv2.VideoCapture(0)

HTML_PAGE = """
<!doctype html>
<html>
<head>
  <title>Orange Pi Webcam</title>
  <style>
    #joystick {
      width: 200px;
      height: 200px;
      background: #ddd;
      border-radius: 50%;
      position: relative;
      touch-action: none;
      margin-top: 20px;
    }
    #stick {
      width: 60px;
      height: 60px;
      background: #333;
      border-radius: 50%;
      position: absolute;
      left: 70px;
      top: 70px;
      touch-action: none;
    }
  </style>
</head>
<body>
  <h1>Live Webcam Stream</h1>
  <img src="{{ url_for('video_feed') }}" width="640" height="480"><br>
  <div id="joystick">
    <div id="stick"></div>
  </div>

<script>
const stick = document.getElementById('stick');
const joystick = document.getElementById('joystick');

let dragging = false;
let lastSendTime = 0;
const THROTTLE_MS = 100;

joystick.addEventListener('pointerdown', e => {
  dragging = true;
});

document.addEventListener('pointerup', e => {
  dragging = false;
  stick.style.left = '70px';
  stick.style.top = '70px';
  sendJoystick(0, 0);
});

document.addEventListener('pointermove', e => {
  if (!dragging) return;
  const rect = joystick.getBoundingClientRect();
  let x = e.clientX - rect.left - 100;
  let y = e.clientY - rect.top - 100;

  const dist = Math.sqrt(x*x + y*y);
  const maxDist = 100;
  if (dist > maxDist) {
    x = x * maxDist / dist;
    y = y * maxDist / dist;
  }

  stick.style.left = `${x + 100 - 30}px`;
  stick.style.top = `${y + 100 - 30}px`;

  // Normalize to [-1, 1]
  sendJoystick(x / maxDist, -y / maxDist); // invert Y
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
    body: JSON.stringify({x, y})
  })
  .then(res => res.json())
  .then(data => {
    console.log("Wheel output:", data);
  });
}
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
from flask import request, jsonify

@app.route('/control', methods=['POST'])
def control():
    data = request.get_json()
    x = data.get('x', 0)   # horizontal (-1 to 1)
    y = data.get('y', 0)   # vertical (-1 to 1)

    # Map joystick input to differential drive wheel speeds
    left = y + x
    right = y - x

    # Clamp to [-1, 1]
    left = max(-1, min(1, left))
    right = max(-1, min(1, right))
    print(f"{left=}, {right=}")

    return jsonify(left=left, right=right)
if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000, debug=False)