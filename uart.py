import serial
import time
import os

# UART configuration for direct serial communication
UART_PORT = "/dev/ttyS2"  # Direct UART port
BAUDRATE = 115200

def send_ascii_command(ser, command):
    """Send ASCII command and return response"""
    ser.write((command + '\n').encode())
    time.sleep(0.1)  # Small delay for command processing
    response = ser.readline().decode().strip()
    return response

try:
    print(f"Connecting to ODrive over UART on {UART_PORT}...")
    
    # Open serial connection
    ser = serial.Serial(
        port=UART_PORT,
        baudrate=BAUDRATE,
        timeout=1,
        bytesize=serial.EIGHTBITS,
        parity=serial.PARITY_NONE,
        stopbits=serial.STOPBITS_ONE
    )
    
    print("Connected successfully!")
    
    # Test connection
    response = send_ascii_command(ser, "r vbus_voltage")
    print(f"Bus voltage: {response}")
    
    print("\nStarting sensorless control...")
    
    # Set axis0 to sensorless control
    response = send_ascii_command(ser, "w axis0.requested_state 8")  # 8 = AXIS_STATE_SENSORLESS_CONTROL
    print(f"Axis0 sensorless control: {response}")
    
    # Set axis1 to sensorless control
    response = send_ascii_command(ser, "w axis1.requested_state 8")  # 8 = AXIS_STATE_SENSORLESS_CONTROL
    print(f"Axis1 sensorless control: {response}")
    
    time.sleep(1)
    
    speed = 0.00001
    print(f"Setting velocity to {speed}")
    
    # Set velocity for axis0
    response = send_ascii_command(ser, f"w axis0.controller.input_vel {speed}")
    print(f"Axis0 velocity set: {response}")
    
    # Set velocity for axis1
    response = send_ascii_command(ser, f"w axis1.controller.input_vel {speed}")
    print(f"Axis1 velocity set: {response}")
    
    time.sleep(2)
    
    print("Stopping motors...")
    
    # Stop axis0
    response = send_ascii_command(ser, "w axis0.controller.input_vel 0")
    print(f"Axis0 stopped: {response}")
    
    # Stop axis1
    response = send_ascii_command(ser, "w axis1.controller.input_vel 0")
    print(f"Axis1 stopped: {response}")
    
    print("Returning to idle state...")
    
    # Set axis0 to idle
    response = send_ascii_command(ser, "w axis0.requested_state 1")  # 1 = AXIS_STATE_IDLE
    print(f"Axis0 idle: {response}")
    
    # Set axis1 to idle
    response = send_ascii_command(ser, "w axis1.requested_state 1")  # 1 = AXIS_STATE_IDLE
    print(f"Axis1 idle: {response}")
    
    print("Done!")
    
    # Close serial connection
    ser.close()

except Exception as e:
    print(f"Error: {e}")
    print(f"Make sure the ODrive is connected to {UART_PORT} and the port is available.")
    print("You may need to run with sudo if you don't have permission to access ttyS2")
    try:
        if 'ser' in locals():
            ser.close()
    except:
        pass
