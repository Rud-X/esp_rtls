# Class mobile_rtls 
    # Attributes:
        # self.stations => list of station mac addresses
        # self.myMacAddr => own mac address
        # self.esp_now => esp_now object
        
        # self.scl_pin => constant pin for i2c scl
        # self.sda_pin => constant pin for i2c sda
        # self.i2c => i2c object
        # self.display => display object
    # Methods:
        # __init__(self, myMacAddr)
        # setup(self)
        # loop(self)
            # 1) Recieve message from sender
                # Message = ping_msg
                # 1) If sender is in station list
                # 2) Read rssi from message
                # 3) Send pong_msg back to sender with rssi
                # Message = registerStation_msg
                # 1) Add station to station list
    # private methods:
        # __display_setup(self)
        # __esp_now_setup(self)
        # __add_station(self, stationMacAddr)
        # __send_pong_msg(self, stationMacAddr)

# Import the required libraries
from machine import Pin, SoftI2C
import sh1106
import time
import network
import ubinascii
import espnow
    
# Class mobile_rtls
class mobile_rtls:
    # Attributes:
    stations = []
    myMacAddr = None
    esp_now = None
    sta = None
    
    scl_pin = const(22)
    sda_pin = const(21)
    i2c = None
    display = None
    
    ping_msg = const("ping")
    registerStation_msg = const("regSt")
    
    # Methods:
    # __init__(self, myMacAddr, scl_pin, sda_pin)
    def __init__(self, myMacAddr):
        self.myMacAddr = myMacAddr
        
        self.setup()
        
    # setup(self)
    def setup(self):
        self.__display_setup()
        self.__esp_now_setup()
        pass
        
    # loop(self)
    def loop(self):
        # 1) Recieve message from sender
        host, msg = self.esp_now.recv()
        if msg:
            if msg == ping_msg:
                if host in self.stations:
                    self.__send_pong_msg(host)
                    
            # Message = registerStation_msg
            elif registerStation_msg in msg:
                # 1) Add station to station list
                self.__add_station(host)
    
    # private methods:
    # __display_setup(self)
    def __display_setup(self):
        # Setup the display
        self.i2c = SoftI2C(scl=Pin(self.scl_pin), sda=Pin(self.sda_pin), freq=100000)
        self.display = sh1106.SH1106_I2C(128, 64, self.i2c, None, 0x3c)
        self.display.sleep(False)
        self.display.fill(0)
        
        self.display.text("Display active", 0, 0, 1)
        self.display.show()
    
    # __esp_now_setup(self)
    def __esp_now_setup(self):
        # A WLAN interface must be active to send()/recv()
        self.sta = network.WLAN(network.STA_IF)
        self.sta.active(True)
        
        # Setup the ESP-Now
        self.esp_now = espnow.ESPNow()
        self.esp_now.active(True)
        
        self.display.text("ESPNow active", 0, 10, 1)
        self.display.show()
        
    # __add_station(self, stationMacAddr)
    def __add_station(self, stationMacAddr):
        # Add station to station list
        self.stations.append(stationMacAddr)
        
        self.esp_now.add_peer(ubinascii.unhexlify(stationMacAddr))
        
        self.display.text("Station added", 0, 20, 1)
        self.display.show()
    
    # __send_pong_msg(self, stationMacAddr)
    def __send_pong_msg(self, stationMacAddr):
        # Send pong_msg back to sender with rssi
        self.esp_now.send(stationMacAddr, str(self.esp_now.peers_table[stationMacAddr][0]))
        
        self.display.text("Pong sent", 0, 30, 1)
        self.display.show()
                

# Main program
# Create an instance of the mobile_rtls class
myMacAddr = ubinascii.unhexlify('d4d4da59edac')
my_rtls = mobile_rtls(myMacAddr)