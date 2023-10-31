# main.py -- put your code here!
from machine import Pin, I2C
import sh1106

i2c = I2C(scl=Pin(22), sda=Pin(21), freq=400000)
display = sh1106.SH1106_I2C(128, 64, i2c, None, 0x3c)
display.sleep(False)
display.fill(0)
display.text('Testing dum dum', 0, 0, 1)
display.text('Nu i terminalen', 0, 30, 1)
display.show()