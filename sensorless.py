import odrive
from odrive.enums import *
import time

# Import specific enums to avoid linter errors
from odrive.enums import (
    MOTOR_TYPE_PMSM_VOLTAGE_CONTROL,  # Changed for sensorless control in this ODrive version
    ENCODER_MODE_HALL,
    CONTROL_MODE_VELOCITY_CONTROL,
    AXIS_STATE_IDLE,
    AXIS_STATE_SENSORLESS_CONTROL,
)


def dump_axis_errors(axis, axis_name):
    print(f"{axis_name} error: {axis.error}")
    print(f"  motor error: {axis.motor.error}")
    print(f"  encoder error: {axis.encoder.error}")
    print(f"  controller error: {axis.controller.error}")


def get():
    odrv0 = odrive.find_any()
    axis = odrv0.axis1
    return odrv0, axis


def wait_for_calibration(axis):
    """Wait for calibration to complete"""
    print("Waiting for calibration to complete...")
    while axis.current_state != AXIS_STATE_IDLE:
        time.sleep(0.1)
    print("Calibration complete!")


def setup_axis(odrv0, axis, axis_name):
    print(f"\n--- Testing {axis_name} (sensorless control, bypass all calibration) ---")
    # Clear errors
    axis.error = 0
    axis.motor.error = 0
    axis.encoder.error = 0
    axis.controller.error = 0

    # Configure motor for 6.5" hoverboard hub motors - BYPASS CALIBRATION
    axis.motor.config.pole_pairs = 10  # Typical for hoverboard motors
    axis.motor.config.motor_type = MOTOR_TYPE_PMSM_VOLTAGE_CONTROL  # Changed for sensorless control
    axis.motor.config.current_lim = 10
    axis.motor.config.requested_current_range = 20
    axis.motor.config.calibration_current = 5
    axis.motor.config.phase_resistance = 0.15  # Manual value for hoverboard motors
    axis.motor.config.phase_inductance = 0.00015  # Manual value for hoverboard motors
    axis.motor.config.pre_calibrated = True

    # For sensorless control, we don't need encoder configuration
    # But we'll keep it minimal in case we switch back to encoder mode
    axis.encoder.config.mode = ENCODER_MODE_HALL
    axis.encoder.config.cpr = 60  # 6 hall sensors * 10 pole pairs
    axis.encoder.config.bandwidth = 1000
    axis.encoder.config.pre_calibrated = True

    # Controller config for sensorless control
    axis.controller.config.control_mode = CONTROL_MODE_VELOCITY_CONTROL
    axis.controller.config.vel_limit = 15
    axis.controller.config.vel_limit_tolerance = 1.2
    axis.controller.config.vel_gain = 0.16
    axis.controller.config.vel_integrator_gain = 0.32

    # Disable all startup sequences
    axis.config.startup_motor_calibration = False
    axis.config.startup_encoder_offset_calibration = False
    axis.config.startup_closed_loop_control = False
    axis.config.startup_sensorless_control = False


def check_axis_state(axis, axis_name, expected_state):
    """Check if axis is in expected state"""
    if axis.current_state != expected_state:
        print(f"ERROR: {axis_name} is in state {axis.current_state}, expected {expected_state}")
        dump_axis_errors(axis, axis_name)
        return False
    return True


# Main logic
try:
    odrv0 = odrive.find_any()
    axis0 = odrv0.axis0
    axis1 = odrv0.axis1

    setup_axis(odrv0, axis0, "axis0")
    setup_axis(odrv0, axis1, "axis1")

    print("\nStarting sensorless control...")
    axis0.requested_state = AXIS_STATE_SENSORLESS_CONTROL
    axis1.requested_state = AXIS_STATE_SENSORLESS_CONTROL

    time.sleep(1)


    speed = 0.00001
    print(f"Setting velocity to {speed}")
    axis0.controller.input_vel = speed
    axis1.controller.input_vel = speed

    time.sleep(10)

    print("Stopping motors...")
    axis0.controller.input_vel = 0
    axis1.controller.input_vel = 0

    print("Returning to idle state...")
    axis0.requested_state = AXIS_STATE_IDLE
    axis1.requested_state = AXIS_STATE_IDLE

    print("Done!")

except Exception as e:
    print(f"Error: {e}")
    try:
        axis0.requested_state = AXIS_STATE_IDLE
        axis1.requested_state = AXIS_STATE_IDLE
    except:
        pass
