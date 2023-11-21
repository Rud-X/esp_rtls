# Reciever part of the ESP-Now return rssi
# Description: Recieve a message from the sender and display it on the OLED display
    # Macaddr of sender (esp#1): 08:b6:1f:88:85:dc
    # Recieve RSSI in data from sender and print it
    # Send RSSI back to sender
    
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

display.text("ESPNow active", 0, 20, 1)
display.show()

# Recieve and display the message in loop
    # Also read peers_table and display latest entry
senderMac = ubinascii.unhexlify('08b61f8885dc')
e.add_peer(senderMac)
lineHeight = 10
while True:
    host, msg = e.recv()
    if msg:
        display.fill(0)
        display.text('Msg:', 0, 0, 1)
        display.text(msg, 0, lineHeight, 1)
        display.text('Peer:', 0, lineHeight * 2, 1)
        display.text(ubinascii.hexlify(host), 0, lineHeight * 3, 1)
        display.text('rssi =', 0, lineHeight * 4, 1)
        display.text(str(e.peers_table[senderMac][0]), 7*8, lineHeight * 4, 1)
        display.text('Sending...', 0, lineHeight * 5, 1)
        display.show()
        
        # Send RSSI back to sender
        e.send(senderMac, str(e.peers_table[senderMac][0]))
    
    

