import random
from machine import Pin, SoftI2C
import sh1106
import time
import network
import ubinascii
import espnow
import uctypes

# Constants
# States:
_STATE_0_noRequest = const(0)
_STATE_1_Request = const(1)

# Transistions
_TRANSITION_0_noRequest_to_1_Request = const(0)
_TRANSITION_1_Request_to_0_noRequest = const(1)

class esp_rtls_mobile:
    _MTID_pingMobile = 0b011
    _MTID_pongMobile = 0b100
    
    # Attributes:
    sta = None
    scl_pin = const(22)
    sda_pin = const(21)
    i2c = None
    line_height = const(10)
    
    # Task queue
    __taskQueue = []
    
    def __init__(self, station_list, mobile_list):
        self.__display_setup()
        self.__esp_now_setup()
        self.station_list = {  # Add the station to the station list
            stationID: ubinascii.unhexlify(stationMAC)
            for stationID, stationMAC in station_list.items()
        }
        self.mac = network.WLAN(network.STA_IF).config("mac")
        self.mobile_list_raw = mobile_list
        self.mobile_ID = self.__mobileidFromMac(self.mac)
        self.__esp_now_add_stations()
        
        self.state = _STATE_0_noRequest
        
        self.display.fill(0)
        self.display.text("Mobile active", 0, 5 * self.line_height, 1)
        self.display.show()
        
        
    
    def loop(self):        
        # Check if there is a message in the buffer
        mac, data = self.esp_now.recv()
        if mac != None:
            self.handleRecievedData(mac, data)
    
    def handleRecievedData(self, mac, data):
        # print data
        print("    data: " + str(data))

        # Match first 3 bit of data with the message type
        msgType = (int(data[0]) & (0b11100000 << 0)) >> 5
        
        if msgType == self._MTID_pingMobile:
            self.__handlePingMobile(mac, data)
        else:
            print("Error: Unknown message type")
            print("    msgType: " + str(msgType))
            
            self.display.fill(0)
            self.display.text("Error:", 0, 0, 1)
            self.display.text("Unknown message type", 0, self.line_height, 1)
            self.display.text(str(msgType), 0, self.line_height * 2, 1)
            self.display.show()
    
    def __handlePingMobile(self, mac, data):
        print("FUNC: __handlePingMobile")
        # Read RSSI from messsage and send it back as a pong message
        rssi = abs(self.esp_now.peers_table[mac][0])
        print("    rssi: " + str(rssi))
        
        # Dummy functionality
        self.display.fill(0)
        self.display.text("Ping recieved", 0, 0, 1)
        self.display.text("rssi: " + str(rssi), 0, self.line_height, 1)
        self.display.text("from " + self.__mac_to_string(mac), 0, self.line_height * 2, 1)
        self.display.show()
        
        time.sleep(1)
        
        
        # Create pong message
        msgType = self._MTID_pongMobile
        tokenID = (data[0] & (0b00011111 << 0)) >> 0
        msgData = (msgType & 0b111) << 5 | tokenID
        
        # Send pong message
        self.esp_now.send(mac, bytearray([msgData, rssi]),1)
        print("    pong sent")
        
    def __printInfoToDisplay(self):
        """Print info to display"""
        self.display.fill(0)
        self.display.text("Mobile active", 0, 0, 1)
        self.display.text("MobileID: " + str(self.mobile_ID), 0, self.line_height, 1)
        self.display.text("MAC: " + self.__mac_to_string(self.mac), 0, self.line_height * 2, 1)
        self.display.text("State: " + str(self.state), 0, self.line_height * 3, 1)
        self.display.show()
        
        
    def __mobileidFromMac(self, mac):
        """Find the mobileID from the mobile MAC address

        Args:
            mac (bytestring): mac address of the mobile

        Returns:
            bytestring: mobileID
        """

        mobileID = None
        for mobileID, mobileMAC in self.mobile_list_raw.items():
            if mobileMAC == mac:
                break

        if mobileID == None:
            # Print "Error: Station not in station list" on the display
            self.display.fill(0)
            self.display.text("Error:", 0, 0, 1)
            self.display.text("Station not in list", 0, self.line_height, 1)
            self.display.text(self.__mac_to_string(mac), 0, self.line_height * 2, 1)
            while True:
                pass

        return mobileID
    
    def __display_setup(self):
        """Setup sh1106 display"""
        self.i2c = SoftI2C(scl=Pin(self.scl_pin), sda=Pin(self.sda_pin), freq=100000)
        self.display = sh1106.SH1106_I2C(128, 64, self.i2c, None, 0x3C)
        self.display.sleep(False)
        self.display.fill(0)

        self.display.text("Display active", 0, 0, 1)
        self.display.show()

    def __esp_now_setup(self):
        """Setup ESP-Now"""

        # A WLAN interface must be active to send()/recv()
        self.sta = network.WLAN(network.STA_IF)
        self.sta.active(True)

        # Setup the ESP-Now
        self.esp_now = espnow.ESPNow()
        self.esp_now.active(True)

        self.display.text("ESPNow active", 0, 10, 1)
        self.display.show()
        
    def __esp_now_add_stations(self):
        """Add other stations to the ESP-Now"""

        for stationID, stationMAC in self.station_list.items():
            self.esp_now.add_peer(stationMAC)
            print(
                "Added station "
                + str(stationID)
                + " to ESP-Now - MAC: "
                + str(stationMAC)
            )
        
    def __mac_to_string(self, mac):
        """Convert MAC address to string"""

        return ubinascii.hexlify(mac, ":").decode().replace(":", "")

    def __string_to_mac(self, string):
        """Convert string to MAC address"""

        return ubinascii.unhexlify(string.replace(":", ""))
