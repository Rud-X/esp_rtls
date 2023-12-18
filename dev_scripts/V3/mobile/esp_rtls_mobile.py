import random
from machine import Pin, SoftI2C
import machine
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
    msg_count = 0
    old_msg_count = 0
    avg_rssi = 0
    
    # debug time
    __debug_time = 0
    __debug_level_print = 0
    
    
    # Task queue
    __taskQueue = []
    
    def __init__(self, station_list, mobile_list, debug_time = 0, debug_level_print = 0):
        self.__debug_time = debug_time
        self.__debug_level_print = debug_level_print
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
        
        self.station_rssi = {
            stationID: None
            for stationID in self.station_list.keys()
        }
        
        self.state = _STATE_0_noRequest
        
        self.LED_R = Pin(19, Pin.OUT, value=1)
        self.LED_G = Pin(18, Pin.OUT, value=1)
        self.LED_B = Pin( 5, Pin.OUT, value=1)
        
        self.display.fill(0)
        self.display.text("Mobile active", 0, 5 * self.line_height, 1)
        self.display.show()
        
        
    
    def loop(self):        
        # Print info to display
        self.__printInfoToDisplay()    
        
        # Check if there is a message in the buffer
        try:
            mac, data = self.esp_now.irecv()
        except Exception as e:
            machine.reset()
        if mac != None:
            self.handleRecievedData(mac, data)
    
    def changeLEDbyStationRSSI(self):
        # p19 => Station 1
        # p18 => Station 2
        # p05 => Station 3
        
        # Choose the station with the lowest RSSI and turn on the LED
        
        # Find the lowest RSSI
        lowestRSSI = None
        for stationID, rssi in self.station_rssi.items():
            if rssi != None:
                if lowestRSSI == None:
                    lowestRSSI = rssi
                elif rssi < lowestRSSI:
                    lowestRSSI = rssi
        
        # Turn off all LEDs
        self.LED_R.value(1)
        self.LED_G.value(1)
        self.LED_B.value(1)
        
        # Turn on the LED for the station with the lowest RSSI
        if lowestRSSI != None:
            for stationID, rssi in self.station_rssi.items():
                if rssi == lowestRSSI:
                    if stationID == 1:
                        self.LED_R.value(0)
                    elif stationID == 2:
                        self.LED_G.value(0)
                    elif stationID == 3:
                        self.LED_B.value(0)
                    else:
                        self.__print_debug("Error: Unknown stationID")
                        self.__print_debug("    stationID: " + str(stationID))
                        self.__print_debug("    rssi: " + str(rssi))
                        self.__print_debug("    lowestRSSI: " + str(lowestRSSI))
                        while True:
                            pass
        
    def handleRecievedData(self, mac, data):
        # print data
        self.__print_debug("    data: " + str(data))

        # Match first 3 bit of data with the message type
        msgType = (int(data[0]) & (0b11100000 << 0)) >> 5
        
        if msgType == self._MTID_pingMobile:
            self.__handlePingMobile(mac, data)
        else:
            self.__print_debug("Error: Unknown message type")
            self.__print_debug("    msgType: " + str(msgType))
            
            self.display.fill(0)
            self.display.text("Error:", 0, 0, 1)
            self.display.text("Unknown message type", 0, self.line_height, 1)
            self.display.text(str(msgType), 0, self.line_height * 2, 1)
            self.display.show()
    
    def __handlePingMobile(self, mac, data):
        self.__print_debug("FUNC: __handlePingMobile")
        # Read RSSI from messsage and send it back as a pong message
        rssi = abs(self.esp_now.peers_table[mac][0])
        self.__print_debug("    rssi: " + str(rssi))
        
        stationID_recieved = self.__stationidFromMac(mac)
        
        # # Dummy functionality
        # self.display.fill(0)
        # self.display.text("Ping recieved", 0, 0, 1)
        # self.display.text("rssi: " + str(rssi), 0, self.line_height, 1)
        # self.display.text("from StID: " + str(stationID_recieved), 0, self.line_height * 2, 1)
        # self.display.show()
        
        time.sleep(self.__debug_time)
        
        # Save rssi in station_rssi
        self.station_rssi[stationID_recieved] = rssi
        
        self.msg_count += 1
        
        # Create pong message
        msgType = self._MTID_pongMobile
        tokenID = (data[0] & (0b00011111 << 0)) >> 0
        msgData = (msgType & 0b111) << 5 | tokenID
        
        # Send pong message
        self.esp_now.send(mac, bytearray([msgData, rssi]),True)
        
        # Change LED by station RSSI
        self.changeLEDbyStationRSSI()
        
        self.__print_debug("    pong sent")
        
    def __printInfoToDisplay(self):
        """Print info to display"""
        # if all RSSI values are not None
        if all(rssi != None for rssi in self.station_rssi.values()) and \
            self.old_msg_count != self.msg_count:
            
            if self.avg_rssi == 0:
                self.avg_rssi = sum(self.station_rssi.values()) / len(self.station_rssi)
            # Calculate average RSSI
            new_avg_rssi = sum(self.station_rssi.values()) / len(self.station_rssi)
            
            self.avg_rssi = self.avg_rssi + (new_avg_rssi - self.avg_rssi) / self.msg_count
            
            self.old_msg_count = self.msg_count
        
        self.display.fill(0)
        self.display.text("Mobile active", 0, 0, 1)
        self.display.text("RSSI:  S1:  " + str(self.station_rssi[1]), 0, self.line_height, 1)
        self.display.text("       S2:  " + str(self.station_rssi[2]), 0, self.line_height * 2, 1)
        self.display.text("       S3:  " + str(self.station_rssi[3]), 0, self.line_height * 3, 1)
        self.display.text("       avg: " + str(self.avg_rssi), 0, self.line_height * 4, 1)
        self.display.text("msgCount:   " + str(self.msg_count), 0, self.line_height * 5, 1)
        self.display.show()
        
    def __stationidFromMac(self, mac):
        """Find the stationID from the station MAC address

        Args:
            mac (bytestring): mac address of the station

        Returns:
            bytestring: stationID
        """

        stationID = None
        for stationID, stationMAC in self.station_list.items():
            if stationMAC == mac:
                break

        if stationID == None:
            # Print "Error: Station not in station list" on the display
            self.display.fill(0)
            self.display.text("Error:", 0, 0, 1)
            self.display.text("Station not in list", 0, self.line_height, 1)
            self.display.text(self.__mac_to_string(mac), 0, self.line_height * 2, 1)
            while True:
                pass

        return stationID    
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
            self.__print_debug(
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

    def __print_debug(self, string):
        if self.__debug_level_print == 1:
            print(string)