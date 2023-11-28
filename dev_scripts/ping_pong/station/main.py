# Class station_rtls
    # Attributes:
        # self.mobileMacAddr = None
        # self.myMacAddr = None
        # self.esp_now = None
        
        # self.scl_pin
        # self.sda_pin
        # self.i2c
        # self.display
    # Methods:
        # __init__(self, mobileMacAddr, myMacAddr)
        # setup(self)
        # loop(self)
            # 1) Register station with mobile
            # 2) Recieve message from mobile
            # 3) Start sending loop
                # 1) Send message to mobile
                # 2) Wait for reply
                # 3) Display reply and measured rssi
    # private methods:
        # __display_setup(self)
        # __esp_now_setup(self)
        # __register_station(self)
        # __send_ping_msg(self)
    
# Import the required libraries
from machine import Pin, SoftI2C
import sh1106
import time
import network
import ubinascii
import espnow

# Class station_rtls
