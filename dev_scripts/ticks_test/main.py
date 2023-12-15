# Import the required libraries
from machine import Pin, SoftI2C, Timer
import sh1106
import time
import network
import ubinascii

# init OLED display
i2c = SoftI2C(scl=Pin(22), sda=Pin(21))
oled = sh1106.SH1106_I2C(128, 64, i2c, Pin(16), 0x3c)
oled.sleep(False)
oled.fill(0)
oled.text('Screen init', 0, 0)
oled.show()

scheduled_time = time.ticks_ms() + 1000
iter = 1

while True:
    if time.ticks_diff(scheduled_time, time.ticks_ms()) < 0:
        oled.fill(0)
        oled.text('Timer done: ' + str(iter), 0, 20)
        oled.show()
        scheduled_time = time.ticks_ms() + 1000
        iter += 1
    pass


