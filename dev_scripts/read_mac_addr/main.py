# Description: Display the MAC address of the ESP32 on the OLED display
    # 1. Get the MAC address
    # 2. Display the MAC address on the OLED display
    # 3. Update the display every second and count a counter to show that the program is still running
    
# Import the required libraries
from machine import Pin, SoftI2C
import sh1106
import time
import network
import ubinascii


# Setup the display
i2c = SoftI2C(scl=Pin(22), sda=Pin(21), freq=100000)
display = sh1106.SH1106_I2C(128, 64, i2c, None, 0x3c)
display.sleep(False)
display.fill(0)

# Get the MAC address
mac = ubinascii.hexlify(network.WLAN(network.STA_IF).config('mac'),':').decode() 
print('MAC address: %s' % mac)

# Display the MAC address on the OLED display
    # Split into 2 lines
# Update the display every second and count a counter to show that the program is still running
lineHeight = 10
n = 0
maxCharsPerLine = 16
while True:
    display.fill(0)
    display.text('MAC:', 0, 0, 1)
    display.text(mac[0:8], 0, lineHeight, 1)
    display.text(mac[9:], 0, lineHeight * 2, 1)
    display.text('Count:   %d' % n, 0, lineHeight * 3, 1)  
    display.show()
    n += 1
    time.sleep(1)