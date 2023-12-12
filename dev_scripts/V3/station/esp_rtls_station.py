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
    # Constants:
    # Message-Type-ID (MTID): byte-strings
    _MTID_parseToken = 0b001
    _MTID_ackToken = 0b010
    _MTID_pingMobile = 0b011
    _MTID_pongMobile = 0b100

    # Attributes:
    sta = None
    scl_pin = const(22)
    sda_pin = const(21)
    i2c = None
    line_height = const(10)
    mobile_list = {}

    def __init__(self, station_list, mobile_list, mobile_token):
        self.__display_setup()
        self.__esp_now_setup()
        self.station_list = {  # Add the station to the station list
            stationID: ubinascii.unhexlify(stationMAC)
            for stationID, stationMAC in station_list.items()
        }
        self.mac = network.WLAN(network.STA_IF).config("mac")
        self.stationID = self.__stationidFromMac(self.mac)
        self.__checkIfStationInList(self.mac)
        self.__esp_now_add_other_stations()
        
        # Add Mobile with tokenID 0b0001
        self.mobile_list[mobile_token] = esp_rtls_station_mobile_info(
            mobile_token,
            ubinascii.unhexlify(mobile_list[mobile_token]),
            _STATE_0_noToken,
            self.station_list,
        )

        # If this is station 1, send parseToken to station 2
        if self.stationID == 1:
            print("BEGIN: send parseToken to station 2")
            self.mobile_list[mobile_token].state = _STATE_3_parseToken
            self.__printStateLastLine(self.mobile_list[mobile_token].state)

            # Send message to station 2
            msgType = self._MTID_parseToken
            msgTokenID = 0b00001
            mac = self.station_list[2]

            msgData = msgType << 5 | msgTokenID
            rssi1 = 40

            msgData_send = bytearray([msgData, rssi1])

            print("    station_list[2]: " + str(self.station_list[2]))
            print("    msgData: " + str(msgData))
            print("    msgData type: " + str(type(msgData)))
            print("    msgData_send: " + str(msgData_send))
            print("    msgData_send data: " + str(msgData_send[0]))
            print("    msgData length: " + str(len(msgData_send)))

            self.esp_now.send(mac, msgData_send, False)
            
            self.mobile_list[mobile_token].state = _STATE_0_noToken
            self.__printStateLastLine(self.mobile_list[mobile_token].state)

            print("    Message send")

        

        self.__printStateLastLine("init DONE")

    def loop(self):
        """Description: Loop of the station"""

        # Print debug loop counter (count up every time called) on the display
        # If my mac address is the first in the station list, print "I am station 1" on the display on the second line
        self.display.fill(0)
        if self.stationID == 1:
            self.display.text("I am station 1", 0, self.line_height * 2, 1)
        self.display.text("Loop: " + str(random.randint(0, 100)), 0, 0, 1)
        self.display.show()

        # Check if there is a message => no timeout
        mac, data = self.esp_now.recv(0)
        if mac != None:
            print("Message recieved")
            self.handleRecievedData(mac, data)

    def handleRecievedData(self, mac, data):
        self.__printFunctionNameSecondLastLine("handleRecievedData")

        # Convert data (string) to byte array
        print("data: " + str(data))

        # Match first 3 bit of data with the message type
        msgType = (int(data[0]) & (0b11100000 << 0)) >> 5
        print("msgType: " + str(msgType))

        if msgType == self._MTID_parseToken:
            self.__handleRecievedParseToken(mac, data)

    # Handler methods:
    def __handleRecievedParseToken(self, mac, data):
        self.__printFunctionNameSecondLastLine("handleRecievedParseToken")

        # Isolate tokenID, msgType and rssi1 from the data
        tokenID = (data[0] & (0b00011111 << 0)) >> 0
        msgType = (data[0] & (0b11100000 << 0)) >> 5
        rssi1 = data[1]

        self.display.text("msgType: " + str(msgType), 0, 1 * self.line_height, 1)
        self.display.text("TokenID: " + str(tokenID), 0, 2 * self.line_height, 1)
        self.display.text("rssi1: " + str(rssi1), 0, 3 * self.line_height, 1)

        self.display.show()
        
        # Update state
        self.mobile_list[tokenID].state = _STATE_3_parseToken
        self.__printStateLastLine(self.mobile_list[tokenID].state)

        # wait for 1 second
        time.sleep(1)

        # Send Parse Token back to the station  (for testing)
        msgType = self._MTID_parseToken
        msgTokenID = tokenID
        msgData = (msgType & 0b111) << 5 | msgTokenID
        rssi1 = 42

        self.esp_now.send(mac, bytearray([msgData, rssi1]), 1)

        self.display.fill(0)
        self.display.text("Token send: " + str(tokenID), 0, 5 * self.line_height, 1)
        self.display.show()
        print("Token send")
        print("   Msg send: " + str(msgData))
        print("   Token send length = " + str(len(bytearray([msgData]))))
        
        # Update state
        self.mobile_list[tokenID].state = _STATE_0_noToken
        self.__printStateLastLine(self.mobile_list[tokenID].state)

    # Private methods:
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

    def __printStateLastLine(self, state):
        self.display.fill(0)
        self.display.text("State: " + str(state), 0, 5 * self.line_height, 1)
        self.display.show()

    def __printFunctionNameSecondLastLine(self, func):
        self.display.fill(0)
        self.display.text("Func: " + func, 0, 4 * self.line_height, 1)
        self.display.show()

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
