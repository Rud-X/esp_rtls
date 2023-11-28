from machine import Pin, SoftI2C
import sh1106
import time
import uctypes

i2c = SoftI2C(scl=Pin(22), sda=Pin(21), freq=100000)
display = sh1106.SH1106_I2C(128, 64, i2c, None, 0x3c)
display.sleep(False)
display.fill(0)

lineHeight = 10

data = 0b01100100

data_msg_Type = (data & 0b11100000) >> 5

msg_type = const(0b011)
msgTokenID = const(0b00010)

test_val = (data_msg_Type == msg_type)

# Display a counter and increment every second (remember to update display)
n = 0
while True:
    display.fill(0)
    display.text('Count:   %d' % (n), 0, 0, 1)
    display.text('Test val:', 0, lineHeight, 1)
    display.text(str(test_val), 0, lineHeight * 2, 1)
    display.show()
    time.sleep(1)