import odrive
import time
from odrive.enums import *


def dump_axis_errors(axis, axis_name):
    print(f"{axis_name} error: {axis.error}")
    print(f"  motor error: {axis.motor.error}")
    print(f"  encoder error: {axis.encoder.error}")
    print(f"  controller error: {axis.controller.error}")


def wait_for_calibration(axis):
    print(f"Waiting for {axis.requested_state}")
    while axis.current_state != AXIS_STATE_IDLE:
        time.sleep(0.1)
    print("Done!")


def save_and_reboot(odrv0):
    try:
        odrv0.save_configuration()
        odrv0.reboot()
    except:
        print("reboot")


def config(odrv0, axis, axis_name):
    print(f"\n--- Testing {axis_name} (with hall sensors, bypass motor cal) ---")
    # Clear errors
    axis.error = 0
    axis.motor.error = 0
    axis.encoder.error = 0
    axis.controller.error = 0

    axis.motor.config.pole_pairs = 15
    axis.motor.config.resistance_calib_max_voltage = 4
    axis.motor.config.requested_current_range = 25  # Requires config save and reboot
    axis.motor.config.current_control_bandwidth = 100
    axis.motor.config.torque_constant = 8.27 / 16

    axis.encoder.config.mode = ENCODER_MODE_HALL
    axis.encoder.config.cpr = 90
    axis.encoder.config.calib_scan_distance = 150

    axis.encoder.config.bandwidth = 100
    axis.controller.config.pos_gain = 1
    axis.controller.config.vel_gain = (
        0.02 * axis.motor.config.torque_constant * axis.encoder.config.cpr
    )
    axis.controller.config.vel_integrator_gain = (
        0.1 * axis.motor.config.torque_constant * axis.encoder.config.cpr
    )
    axis.controller.config.vel_limit = 10
    axis.controller.config.control_mode = CONTROL_MODE_VELOCITY_CONTROL

    # Skip motor calibration
    axis.motor.config.phase_resistance = 0.15
    axis.motor.config.phase_inductance = 0.00015
    axis.motor.config.pre_calibrated = True


def calibrate(odrv0, axis, axis_name):
    axis.requested_state = AXIS_STATE_ENCODER_HALL_POLARITY_CALIBRATION
    wait_for_calibration(axis)

    axis.requested_state = AXIS_STATE_ENCODER_OFFSET_CALIBRATION
    wait_for_calibration(axis)

    axis.encoder.config.pre_calibrated = True

    dump_axis_errors(axis, axis_name)

    if axis.error != 0:
        print(f"{axis_name} encoder calibration failed!")
        return

    print("Hall sensor calibration successful! Entering closed loop control...")


odrv0 = odrive.find_any()
try:
    odrv0.erase_configuration()
except:
    print("erased")


odrv0 = odrive.find_any()
odrv0.config.enable_uart = True
odrv0.config.uart_baudrate = 115200

odrv0 = odrive.find_any()
config(odrv0, odrv0.axis0, "axis0")
save_and_reboot(odrv0)
odrv0 = odrive.find_any()
calibrate(odrv0, odrv0.axis0, "axis0")
save_and_reboot(odrv0)

odrv0 = odrive.find_any()
config(odrv0, odrv0.axis1, "axis1")
save_and_reboot(odrv0)
odrv0 = odrive.find_any()
calibrate(odrv0, odrv0.axis1, "axis1")
save_and_reboot(odrv0)
