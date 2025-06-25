import odrive
from odrive.enums import *
import time


try:
    odrv0 = odrive.find_any()
    axis0 = odrv0.axis0
    axis1 = odrv0.axis1

    print("\nStarting sensorless control...")
    axis0.requested_state = AXIS_STATE_CLOSED_LOOP_CONTROL
    axis1.requested_state = AXIS_STATE_CLOSED_LOOP_CONTROL

    time.sleep(1)
    
    speed = 0.3

    def move(left,right):
        axis0.controller.input_vel = right * speed
        axis1.controller.input_vel = left * -1 * speed
        time.sleep(2)

    # move(left=1, right=1)
    # move(left=1,right=-1)
    move(left=-1,right=-1)

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
