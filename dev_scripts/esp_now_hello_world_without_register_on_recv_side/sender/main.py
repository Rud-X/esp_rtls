# Sender part of the ESP-Now Hello World example
# Description: Send a message to the reciever
    # Macaddr of reciever (esp#2): d4:d4:da:59:ed:ac
    # Message: "Hello World!"
    
# Import the required libraries
from machine import Pin, SoftI2C
import sh1106
import time
import network
import ubinascii
import espnow

# Setup the display
i2c = SoftI2C(scl=Pin(22), sda=Pin(21), freq=100000)
display = sh1106.SH1106_I2C(128, 64, i2c, None, 0x3c)
display.sleep(False)
display.fill(0)

display.text("Display setup done", 0, 0, 1)
display.show()

# A WLAN interface must be active to send()/recv()
sta = network.WLAN(network.STA_IF)
sta.active(True)

display.text("WLAN active", 0, 10, 1)
display.show()

# Setup the ESP-Now
e = espnow.ESPNow()
e.active(True)
peer = ubinascii.unhexlify('d4d4da59edac')
e.add_peer(peer)

display.text("ESPNow active", 0, 20, 1)
display.show()

# Loop and send the message every second with a counter
lineHeight = 10
n = 0
while True:
    e.send(peer, "Hello World! %d" % n)
    display.fill(0)
    display.text('Msg:', 0, 0, 1)
    display.text("Hello World! %d" % n, 0, lineHeight, 1)
    display.text('Peer:', 0, lineHeight * 2, 1)
    display.text(ubinascii.hexlify(peer), 0, lineHeight * 3, 1)
    display.show()
    n += 1
    time.sleep(1)