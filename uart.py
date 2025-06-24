import serial
import time
import os

# UART configuration for direct serial communication
UART_PORT = "/dev/ttyACM0"  # USB connection (working port)
BAUDRATE = 115200

def send_ascii_command(ser, command, delay=0.1):
    """Send ASCII command and return response"""
    ser.write((command + '\n').encode())
    if delay: time.sleep(delay)  
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
    send_ascii_command(ser, "w axis0.requested_state 5")
    send_ascii_command(ser, "w axis1.requested_state 5")
    
    time.sleep(1)
    
    speed = 0.00001
    print(f"Setting velocity to {speed}")
    send_ascii_command(ser, f"v 0 {speed}", 0)
    send_ascii_command(ser, f"v 1 {speed}", 0)
    
    time.sleep(2)
    
    print("Stopping motors...")
    
    # Stop both axes with batched commands
    send_ascii_command(ser, f"v 0 0", 0)
    send_ascii_command(ser, f"v 1 0", 0)
    
    
    send_ascii_command(ser, "w axis0.requested_state 1")  # 1 = AXIS_STATE_IDLE
    send_ascii_command(ser, "w axis1.requested_state 1")  # 1 = AXIS_STATE_IDLE

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
