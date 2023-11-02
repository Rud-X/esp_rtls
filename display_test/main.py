# main.py -- put your code here!
from machine import Pin, I2C, SoftI2C
#from sh1106 import *
import sh1106
import time

#i2c = I2C(scl=Pin(22), sda=Pin(21), freq=400000)
i2c = SoftI2C(scl=Pin(22), sda=Pin(21), freq=100000)
display = sh1106.SH1106_I2C(128, 64, i2c, None, 0x3c)
display.sleep(False)
display.fill(0)

lineHeight = 10

# Display a counter and increment every second (remember to update display)
n = 0
while True:
    display.fill(0)
    display.text('Count:   %d' % n, 0, 0, 1)  
    for i in range(0, 5):
        display.text('Line %d' % (i+1), 0, lineHeight * (i + 1), 1)
    display.show()
    n += 1
    time.sleep(1)