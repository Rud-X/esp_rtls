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
_STATE_1_sendACK = const(1)
_STATE_2_pingMobile = const(2)
_STATE_3_waitMobile = const(3)
_STATE_4_parseToken = const(4)
_STATE_5_waitStation = const(5)

# Transitions:
_TRANSITION_0_noToken_1_sendACK = const(0)
_TRANSITION_1_sendACK_2_pingMobile = const(1)
_TRANSITION_2_pingMobile_3_waitMobile = const(2)
_TRANSITION_3_waitMobile_4_parseToken = const(3)
_TRANSITION_4_parseToken_5_waitStation = const(4)
_TRANSITION_5_waitStation_0_noToken = const(5)


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
    
    # Task queue
    __taskQueue = []

    def __init__(self, station_list, mobile_list, mobile_token):
        self.__display_setup()
        self.__esp_now_setup()
        self.station_list = {  # Add the station to the station list
            stationID: ubinascii.unhexlify(stationMAC)
            for stationID, stationMAC in station_list.items()
        }
        self.mac = network.WLAN(network.STA_IF).config("mac")
        self.__checkIfStationInList(self.mac)
        self.stationID = self.__stationidFromMac(self.mac)
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
            time.sleep(2)

            TokenID = 0b00001
            macNextStation = self.station_list[((self.stationID ) % len(self.station_list)) + 1]
            rssi1 = 40
            
            self.__do_STATE_4_parseToken(macNextStation, TokenID, rssi1)

            print("    Message send")

        

        self.__printStateLastLine("init DONE")

    def loop(self):
        """Description: Loop of the station"""
        
        # Print token id and state to display
        self.printInfoToDisplay()
        
        # Check if there is something in the task queue
        if self.__taskQueue != []:
            [taskID, TokenID] = self.__taskQueue.pop(0)
            
            if taskID == _TRANSITION_0_noToken_1_sendACK:
                print("TRANSITION_0_noToken_1_sendACK")
            
            elif taskID == _TRANSITION_1_sendACK_2_pingMobile:
                print("TRANSITION_1_sendACK_2_pingMobile")
            
            elif taskID == _TRANSITION_2_pingMobile_3_waitMobile:
                print("TRANSITION_2_pingMobile_3_waitMobile")
            
            elif taskID == _TRANSITION_3_waitMobile_4_parseToken:
                print("TRANSITION_3_waitMobile_4_parseToken")
                
            elif taskID == _TRANSITION_4_parseToken_5_waitStation:
                print("TRANSITION_4_parseToken_5_waitStation")
                
            elif taskID == _TRANSITION_5_waitStation_0_noToken:
                print("TRANSITION_5_waitStation_0_noToken")
                
            else:
                print("Error: TaskID not in task list")
                
        # Check if there is a message => no timeout
        mac, data = self.esp_now.recv(0)
        if mac != None:
            self.handleRecievedData(mac, data)
    
    def printInfoToDisplay(self):
        self.display.fill(0)
        self.display.text("TokenID: " + str(self.mobile_list[1].tokenID), 0, 0, 1)
        self.display.text("State: " + str(self.mobile_list[1].state), 0, self.line_height, 1)
        # self.display.text("RSSI: S1: " + str(self.mobile_list[1].RSSI[1]), 0, 2 * self.line_height, 1)
        # self.display.text("      S2: " + str(self.mobile_list[1].RSSI[2]), 0, 3 * self.line_height, 1)
        # self.display.text("      S3: " + str(self.mobile_list[1].RSSI[3]), 0, 4 * self.line_height, 1)
        self.display.show()

    def handleRecievedData(self, mac, data):
        # Convert data (string) to byte array
        print("    data: " + str(data))

        # Match first 3 bit of data with the message type
        msgType = (int(data[0]) & (0b11100000 << 0)) >> 5

        if msgType == self._MTID_parseToken:
            self.__handleRecievedParseToken(mac, data)
        elif msgType == self._MTID_ackToken:
            self.__handleRecievedAckToken(mac, data)

    # Handler methods:
    def __handleRecievedParseToken(self, mac, data):
        print("\nFUNC: handleRecievedParseToken")
        time.sleep(1)

        # Isolate tokenID, msgType and rssi1 from the data
        tokenID = (data[0] & (0b00011111 << 0)) >> 0
        msgType = (data[0] & (0b11100000 << 0)) >> 5
        rssi1 = data[1]
        
        print("    msgType: " + str(msgType))
        print("    tokenID: " + str(tokenID))
        print("    rssi1:   " + str(rssi1))
        
        # # Update state
        # self.mobile_list[tokenID].state = _STATE_3_parseToken
        
        self.__do_STATE_1_sendAck(mac, tokenID)
        
        # pingMobile
        self.__do_STATE_2_pingMobile(tokenID)
        
        # waitMobile
        self.__do_STATE_3_waitMobile(tokenID)

        # Parse token
        rssi1 = 42
        self.__do_STATE_4_parseToken(mac, tokenID, rssi1)
    
    def __handleRecievedAckToken(self, mac, data):
        print("\nFUNC: handleRecievedAckToken")

        # Isolate tokenID, msgType and rssi1 from the data
        tokenID = (data[0] & (0b00011111 << 0)) >> 0
        msgType = (data[0] & (0b11100000 << 0)) >> 5
        
        print("    msgType: " + str(msgType))
        print("    tokenID: " + str(tokenID))
        
        # Update state
        self.mobile_list[tokenID].state = _STATE_0_noToken
        self.printInfoToDisplay()
        
    def __handleRecievedPongMobile(self, mac, data):
        pass

    # State methods:
    def __do_STATE_1_sendAck(self, mac, tokenID):
        print("\nFUNC: send_ackToken")
        
        # Update state
        self.mobile_list[tokenID].state = _STATE_1_sendACK
        
        # Dummy state functionality
        self.printInfoToDisplay()
        time.sleep(1)
        
        # Send ackToken back to the station
        msgType = self._MTID_ackToken
        msgTokenID = tokenID
        msgData = (msgType & 0b111) << 5 | msgTokenID
        
        self.esp_now.send(mac, bytearray([msgData]), False)
        
        # Update state to pingMobile
        self.mobile_list[tokenID].state = _STATE_2_pingMobile
        
    def __do_STATE_2_pingMobile(self, tokenID):
        print("\nFUNC: do_STATE_1_pingMobile")
        
        # Update state
        self.mobile_list[tokenID].state = _STATE_2_pingMobile
        
        # Dummy state functionality
        self.printInfoToDisplay()
        time.sleep(1)
        
    def __do_STATE_3_waitMobile(self, tokenID):
        print("\nFUNC: do_STATE_2_waitMobile")
        
        # Update state
        self.mobile_list[tokenID].state = _STATE_3_waitMobile
        
        # Dummy state functionality
        self.printInfoToDisplay()
        time.sleep(1)
    
    def __do_STATE_4_parseToken(self, mac, tokenID, rssi1):
        print("\nFUNC: do_STATE_3_parseToken")
        
        # Update state
        self.mobile_list[tokenID].state = _STATE_4_parseToken
        
        # Send Parse Token back to the station  (for testing)
        msgType = self._MTID_parseToken
        msgTokenID = tokenID
        msgData = (msgType & 0b111) << 5 | msgTokenID
        macNextStation = self.station_list[((self.stationID ) % len(self.station_list)) + 1]

        print("    Token send")
        print("        Msg send: " + str(msgData))
        print("        Token send length = " + str(len(bytearray([msgData]))))

        # Wait for 1 second
        self.printInfoToDisplay()
        time.sleep(1)

        # Send token
        self.esp_now.send(macNextStation, bytearray([msgData, rssi1]), 1)
        
        # Update state
        self.mobile_list[tokenID].state = _STATE_5_waitStation
        
        
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

    def __printStateLastLine(self, state, with_clear=True):
        if with_clear: self.display.fill(0)
        self.display.text("State: " + str(state), 0, 5 * self.line_height, 1)
        self.display.show()

    def __printFunctionNameSecondLastLine(self, func, with_clear=True):
        if with_clear: self.display.fill(0)
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
