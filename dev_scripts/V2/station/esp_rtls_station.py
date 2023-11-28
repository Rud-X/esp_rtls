import random
from machine import Pin, SoftI2C
import sh1106
import time
import network
import ubinascii
import espnow
import uctypes

# Constants:
# States:
_STATE_0_noToken = const(0)
_STATE_1_pingMobile = const(1)
_STATE_2_waitMobile = const(2)
_STATE_3_parseToken = const(3)
_STATE_4_waitStation = const(4)

# Transitions:
_TRANSITION_noToken_pingMobile = const(0)
_TRANSITION_pingMobile_waitMobile = const(1)
_TRANSITION_waitMobile_pingMobile = const(2)
_TRANSITION_waitMobile_parseToken = const(3)
_TRANSITION_parseToken_waitStation = const(4)
_TRANSITION_waitStation_parseToken = const(5)
_TRANSITION_parseToken_noToken = const(6)

# Message structure:
# bitnr:    | 0 | 1 | 2 | 3 | 4 | 5 | 6 | 7 |  8-15 | 16-23 |
#           | msgType   | TokenID           | RSSI1 | RSSI2 |

# Message-Type-ID (MTID): byte-strings
_MTID_parseToken = const(0b001)
_MTID_ackToken = const(0b010)
_MTID_pingMobile = const(0b011)
_MTID_pongMobile = const(0b100)


class esp_rtls_station_mobile_info:
    """
    Description: Class that holds the information of a mobile

    Attributes:
    - tokenID     [String] => ID of the token.
    - mac         [MAC address] => MAC address of the mobile.
    - state       [Integer] => State of the mobile.
    - RSSI        [Dictionary] => RSSI of the mobile to the different stations.

    Methods:
    - updateRSSI(stationID, RSSI) => Update the RSSI of the mobile to a station.
    """

    def __init__(self, tokenID, mac, state, stationIDs):
        self.tokenID = tokenID
        self.mac = mac
        self.state = state
        self.RSSI = {stationID: None for stationID, stationMAC in stationIDs.items()}

    def updateRSSI(self, stationID, RSSI):
        """
        Update the RSSI of the mobile to a station

        Args:
            stationID   [String] => ID of the station
            RSSI        [Integer] => RSSI of the mobile to the station
        """
        self.RSSI[stationID] = RSSI


class esp_rtls_station:
    # Attributes:
    sta = None
    scl_pin = const(22)
    sda_pin = const(21)
    i2c = None
    line_height = const(10)
    mobile_list = {}

    def __init__(self, station_list, mobile_list, mobile_token):
        # Setup the display and the ESP-Now
        self.__display_setup()
        self.__esp_now_setup()

        # Add the station to the station list
        self.station_list = {
            stationID: ubinascii.unhexlify(stationMAC)
            for stationID, stationMAC in station_list.items()
        }
        self.mac = network.WLAN(network.STA_IF).config("mac")
        self.__checkIfStationInList(self.mac)
        self.__esp_now_add_other_stations()

        # Add the mobiles to the mobile list
        for MobileTokenID, MobileMAC in mobile_list.items():
            setState = _STATE_0_noToken

            if MobileTokenID == mobile_token:
                setState = _STATE_1_pingMobile

            self.mobile_list[MobileTokenID] = esp_rtls_station_mobile_info(
                MobileTokenID,
                ubinascii.unhexlify(MobileMAC),
                setState,
                self.station_list,
            )

    def handleRecievedData(self, mac, data):
        # Match first 3 bit of data with the message type
        msgType = (data[0] & 0b11100000) >> 5

        match msgType:
            case _MTID_parseToken:
                self.__handleRecievedParseToken(mac, data)
            case _MTID_ackToken:
                self.__handleRecievedAckToken(mac, data)
            case _MTID_pongMobile:
                self.__handleRecievedPongMobile(mac, data)
            case _:
                # Print "Error: Unknown message type" on the display
                self.display.fill(0)
                self.display.text("Error:", 0, 0, 1)
                self.display.text("Unknown message type", 0, self.line_height, 1)
                self.display.text(self.__mac_to_string(mac), 0, self.line_height * 2, 1)
                self.display.show()
                while True:
                    pass

    # Handler methods:
    def __handleRecievedParseToken(self, mac, data):
        # Isolate the tokenID
        tokenID = (data[0] & 0b00011111) >> 0

        # Get stationID from mac
        stationID = self.__stationidFromMac(mac)

        # send ackToken to the station
        msgType = _MTID_ackToken
        msgTokenID = tokenID
        msgData = uctypes.UINT8 | (msgType << 5 | msgTokenID)

        self.esp_now.send(mac, msgData, 1)
        
        # Update the RSSI of the mobile to the station
        self.mobile_list[tokenID].updateRSSI(stationID, (data[1]+data[2])>>1)
        
        # If the mobile is in noToken change to pingMobile
        if self.mobile_list[tokenID].state == _STATE_0_noToken:
            self.mobile_list[tokenID].state = _STATE_1_pingMobile
        else:
            # Print "Error: Mobile not in noToken state" on the display
            self.display.fill(0)
            self.display.text("Error:", 0, 0, 1)
            self.display.text("Mobile not in noToken state", 0, self.line_height, 1)
            self.display.text(self.__mac_to_string(mac), 0, self.line_height * 2, 1)
            self.display.text("tokenID: " + str(tokenID), 0, self.line_height * 3, 1)
            self.display.show()
            while True:
                pass
        
        self.__do_STATE_1_pingMobile(tokenID)
        
    
    def __handleRecievedAckToken(self, mac, data):
        # Isolate the tokenID
        tokenID = data[0] & 0b00011111
        
        # Get stationID from mac
        stationiD = self.__stationidFromMac(mac)
        
        # Change state to noToken
        self.mobile_list[tokenID].state = _STATE_0_noToken

    def __handleRecievedPongMobile(self, mac, data):
        pass
    
    # State methods:
    def __do_STATE_1_pingMobile(self, tokenID):
        # Get the mobile MAC address
        mobileMAC = self.mobile_list[tokenID].mac

        # Send pingMobile to the mobile
        msgType = _MTID_pingMobile
        msgTokenID = tokenID
        msgData = uctypes.UINT8 | (msgType << 5 | msgTokenID)

        self.esp_now.send(mobileMAC, msgData, 1)

        # Change state to waitMobile
        self.mobile_list[tokenID].state = _STATE_2_waitMobile

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

    # Private methods:
    def __checkIfStationInList(self, station_mac):
        """Description: Check if the station is in the station list"""
        if station_mac not in self.station_list.values():
            # Print "Error: Station not in station list" on the display
            self.display.fill(0)
            self.display.text("Error:", 0, 0, 1)
            self.display.text("Station not in list", 0, self.line_height, 1)
            self.display.text(
                self.__mac_to_string(station_mac), 0, self.line_height * 2, 1
            )  # [String] => MAC address of the station itself), 0, self.line_height * 2, 1)
            self.display.show()
            while True:
                pass

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

    def __esp_now_add_other_stations(self):
        """Add other stations to the ESP-Now"""

        for stationID, stationMAC in self.station_list.items():
            if stationMAC != self.mac:
                self.esp_now.add_peer(stationMAC)

    def __mac_to_string(self, mac):
        """Convert MAC address to string"""

        return ubinascii.hexlify(mac, ":").decode().replace(":", "")

    def __string_to_mac(self, string):
        """Convert string to MAC address"""

        return ubinascii.unhexlify(string.replace(":", ""))