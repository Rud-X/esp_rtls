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

iter_timer = 0

# def callback function
    # Print to the OLED display
def tick(timer):
    global iter_timer
    oled.fill(0)
    oled.text('Timer tick', 0, 0)
    oled.text(str(iter_timer), 0, 10)
    oled.show()
    iter_timer += 1

# init timer 0 in periodic mode, with a period of 1s
tim = Timer(0)
tim.init(period=1000, mode=Timer.PERIODIC, callback=tick)

while True:
    if iter_timer == 5:
        # adjust timer to period = 2s
        tim.init(period=2000, mode=Timer.PERIODIC, callback=tick)
        iter_timer += 1
    pass


