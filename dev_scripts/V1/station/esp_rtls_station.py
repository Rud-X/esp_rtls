import random
from machine import Pin, SoftI2C
import sh1106
import time
import network
import ubinascii
import espnow




class esp_rtls_station():
    
    # Attributes:
        # Ordered list of stations and their MAC addresses
            # Including latest rssi from every mobile in list of mobiles
        # Ordered list of mobiles, their MAC adresses and their tokens
        # Current token
            # Token format: 0b????
    
    # Methods:
        # Parse Current token to the station after this one in the list
        # Ping mobile corresponding to current token => Dummy for now
            # return rssi
            
    # Attributes:
    sta = None
    scl_pin = const(22)
    sda_pin = const(21)
    #Display = None
    i2c = None
    line_height = const(10)
        
    def __init__(self, station_list, mobile_list, mobile_token):
        self.__display_setup()
        self.__esp_now_setup()
        # unhexlified MAC addresses of the stations in the network
        self.station_list   = [ubinascii.unhexlify(station) for station in station_list]
        self.mobile_list    = mobile_list       # [dictionary 4 bit number to string] => Token to MAC address of mobiles
        self.current_token  = mobile_token      # [String] => Token of the mobile that is currently being pinged
        self.mac            = network.WLAN(network.STA_IF).config('mac')  # [String] => MAC address of the station itself   

        if self.mac not in self.station_list:
            # Print "Error: Station not in station list" on the display
            self.display.fill(0)
            self.display.text("Error:", 0, 0, 1)
            self.display.text("Station not in list", 0, self.line_height, 1)
            self.display.text(ubinascii.hexlify(self.mac,':').decode().replace(':',''), 0, self.line_height*2,1)   # [String] => MAC address of the station itself), 0, self.line_height * 2, 1)
            self.display.show()
            while True: pass
            
        self.__esp_now_add_other_stations()
        
    def ping(self):
        # Ping the mobile corresponding to the current token
        # Return the rssi of the ping
        
        # Dummy for now: Random number between 0 and 100
            # Print "Function called: \n ping() \n Token: \n token \n RSSI: \n rssi" on the display
        random_rssi = random.randint(0, 100)
        self.display.fill(0)
        self.display.text("Function called:", 0, 0, 1)
        self.display.text("ping()", 0, self.line_height, 1)
        self.display.text("Token:", 0, self.line_height * 2, 1)
        if self.current_token == None:
            self.display.text("None", 0, self.line_height * 3, 1)
        else:
            self.display.text(self.current_token, 0, self.line_height * 3, 1)
            self.display.text("RSSI:", 0, self.line_height * 4, 1)
            self.display.text(str(random_rssi), 0, self.line_height * 5, 1)
        self.display.show()
        return random_rssi

    def parse_token(self):
        index = (self.station_list.index(self.mac) + 1) % len(self.station_list)
        
        self.display.fill(0)
        self.display.text("Function called:", 0, 0, 1)
        self.display.text("parse_token()", 0, self.line_height, 1)
        self.display.text("Token:", 0, self.line_height * 2, 1)
        if self.current_token == None:
            self.display.text("None", 0, self.line_height * 3, 1)
        else:
            self.display.text(self.current_token, 0, self.line_height * 3, 1)
            self.display.text("Next station:", 0, self.line_height * 4, 1)
            self.display.text(self.__mac_to_string(self.station_list[index]), 0, self.line_height * 5, 1)
        self.display.show()
        
        # Send the token to the next station in the list
        if self.current_token != None:
            self.esp_now.send(self.station_list[index], ('t' + self.current_token))
            
            self.current_token = None
        

        return
    
    def wait_for_token(self):
        # Wait for token from previous station
        # Return the token
        self.display.fill(0)
        self.display.text("Function called:", 0, 0, 1)
        self.display.text("wait_for_token()", 0, self.line_height, 1)
        self.display.show()
        
        # Wait for token from previous station
        while True:
            host, msg = self.esp_now.recv()
            if msg:
                self.display.text(("msg:" + msg.decode('utf-8')), 0, self.line_height * 2, 1)
                self.display.show()
                if msg[0] == ord('t'): # Because msg is a byte-string
                    self.current_token = msg[1:].decode('utf-8')
                    self.display.text("Token:", 0, self.line_height * 3, 1)
                    self.display.text(self.current_token, 0, self.line_height * 4, 1)
                    self.display.show()
                    break
        return self.current_token
    
    # Private methods:
    def __display_setup(self):
        # Setup the display
        self.i2c = SoftI2C(scl=Pin(self.scl_pin), sda=Pin(self.sda_pin), freq=100000)
        self.display = sh1106.SH1106_I2C(128, 64, self.i2c, None, 0x3c)
        self.display.sleep(False)
        self.display.fill(0)
        
        self.display.text("Display active", 0, 0, 1)
        self.display.show()
        
    def __esp_now_setup(self):
        # A WLAN interface must be active to send()/recv()
        self.sta = network.WLAN(network.STA_IF)
        self.sta.active(True)
        
        # Setup the ESP-Now
        self.esp_now = espnow.ESPNow()
        self.esp_now.active(True)
        
        self.display.text("ESPNow active", 0, 10, 1)
        self.display.show()
    
    def __esp_now_add_other_stations(self):
        for station in self.station_list:
            if station != self.mac:
                self.esp_now.add_peer(station)
                
    def __mac_to_string(self, mac):
        return ubinascii.hexlify(mac,':').decode().replace(':','')
    
    
    
        
        