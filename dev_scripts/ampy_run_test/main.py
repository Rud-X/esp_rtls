# Description: Test printing to the terminal
    # on the ESP32 with micropython
    
# Import modules
from machine import Pin, SoftI2C
import sh1106
import time

i2c = SoftI2C(scl=Pin(22), sda=Pin(21), freq=100000)
display = sh1106.SH1106_I2C(128, 64, i2c, None, 0x3c)
display.sleep(False)
display.fill(0)

lineHeight = 10

print("Hello World!")

# Loop with count
for i in range(10):
    display.fill(0)
    display.text('Count: %d' % i, 0, 0, 1)
    display.show()
    print("Count: ", i)
    time.sleep(1)