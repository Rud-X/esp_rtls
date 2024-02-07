from machine import Pin, SoftI2C
import sh1106
import time
import ubinascii

i2c = SoftI2C(scl=Pin(22), sda=Pin(21), freq=100000)
display = sh1106.SH1106_I2C(128, 64, i2c, None, 0x3c)
display.sleep(False)
display.fill(0)

lineHeight = 10

mac = 'd4d4da5a92a0'
print("mac = ", mac)
print("mac unhexlify = ", ubinascii.unhexlify(mac))


# Display a counter and increment every second (remember to update display)
n = 0
while True:
    display.fill(0)
    display.text('Count:   %d' % n, 0, 0, 1)  
    
    # Display the mac address in byte array
    mac_byte_array = ubinascii.unhexlify(mac)
    display.text('Mac:', 0, lineHeight * 3, 1)
    display.text(mac_byte_array, 0, lineHeight * 4, 1)
    display.show()
    n += 1
    time.sleep(1)