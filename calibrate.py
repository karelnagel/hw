import odrive
from odrive.enums import *
import time

# Import specific enums to avoid linter errors
from odrive.enums import (
    MOTOR_TYPE_PMSM_CURRENT_CONTROL,
    ENCODER_MODE_HALL,
    CONTROL_MODE_VELOCITY_CONTROL,
    AXIS_STATE_MOTOR_CALIBRATION,
    AXIS_STATE_ENCODER_OFFSET_CALIBRATION,
    AXIS_STATE_CLOSED_LOOP_CONTROL,
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


def setup_and_test_axis(odrv0, axis, axis_name):
    print(f"\n--- Testing {axis_name} (with hall sensors, bypass motor cal) ---")
    # Clear errors
    axis.error = 0
    axis.motor.error = 0
    axis.encoder.error = 0
    axis.controller.error = 0

    # Configure motor for 6.5" hoverboard hub motors - BYPASS CALIBRATION
    axis.motor.config.pole_pairs = 10  # Typical for hoverboard motors
    axis.motor.config.motor_type = MOTOR_TYPE_PMSM_CURRENT_CONTROL
    axis.motor.config.current_lim = 10
    axis.motor.config.requested_current_range = 20
    axis.motor.config.calibration_current = 5
    axis.motor.config.phase_resistance = 0.15  # Manual value for hoverboard motors
    axis.motor.config.phase_inductance = 0.00015  # Manual value for hoverboard motors
    axis.motor.config.pre_calibrated = True  # Skip motor calibration

    # Configure encoder for hall sensors
    axis.encoder.config.mode = ENCODER_MODE_HALL
    axis.encoder.config.cpr = 60  # 6 hall sensors * 10 pole pairs
    axis.encoder.config.bandwidth = 1000
    axis.encoder.config.pre_calibrated = False  # Allow hall sensor calibration

    # Controller config
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

    print("Skipping motor calibration (using manual parameters)...")
    print("Starting encoder (hall sensor) calibration...")
    axis.requested_state = AXIS_STATE_ENCODER_OFFSET_CALIBRATION
    wait_for_calibration(axis)
    dump_axis_errors(axis, axis_name)

    if axis.error != 0:
        print(f"{axis_name} encoder calibration failed!")
        return

    print("Hall sensor calibration successful! Entering closed loop control...")
    axis.requested_state = AXIS_STATE_CLOSED_LOOP_CONTROL
    time.sleep(1)
    if axis.current_state == AXIS_STATE_CLOSED_LOOP_CONTROL:
        print("Successfully entered closed loop control!")
        print("Setting velocity to 1 turn/sec...")
        axis.controller.input_vel = 1
        print("Wheels should now be spinning!")
        try:
            for _ in range(10):
                print(f"Target velocity: {axis.controller.input_vel:.2f} turns/sec")
                print(f"Actual velocity: {axis.encoder.vel_estimate:.2f} turns/sec")
                print(f"Position: {axis.encoder.pos_estimate:.2f} turns")
                time.sleep(1)
        except KeyboardInterrupt:
            print("\nStopping...")
        axis.controller.input_vel = 0
        axis.requested_state = AXIS_STATE_IDLE
    else:
        print("Failed to enter closed loop control!")
        dump_axis_errors(axis, axis_name)


# Main logic
odrv0 = odrive.find_any()
setup_and_test_axis(odrv0, odrv0.axis0, "axis0")
odrv0 = odrive.find_any()
setup_and_test_axis(odrv0, odrv0.axis1, "axis1")
