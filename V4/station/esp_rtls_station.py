import random
from machine import Pin, SoftI2C
import sh1106
import time
import network
import ubinascii
import espnow
import uctypes

# Constants:
# Message-Type-ID (MTID): byte-strings
_MTID_parseToken = const(0b001)
_MTID_ackToken = const(0b010)
_MTID_pingMobile = const(0b011)
_MTID_pongMobile = const(0b100)
_MTID_newMobile_fromStation = const(0b101)
_MTID_newMobile_fromMobile = const(0b110)
_MTID_newMobile_fromMobile_ack = const(0b111)

# States:
_STATE_0_noToken = const(0)
_STATE_1_sendACK = const(1)
_STATE_2_pingMobile = const(2)
_STATE_3_waitMobile = const(3)
_STATE_4_parseToken = const(4)
_STATE_5_waitStation = const(5)
_STATE_a_newMFromS = const(6)
_STATE_b_newMFromM = const(7)
_STATE_c_newMReg = const(9)
_STATE_d_newMSendMAck = const(10)
_STATE_e_newMParseToken = const(11)
_STATE_f_newMWaitStation = const(12)

# Transitions:
_TRANSITION_0_noToken_1_sendACK = const(0)
_TRANSITION_1_sendACK_2_pingMobile = const(1)
_TRANSITION_2_pingMobile_3_waitMobile = const(2)
_TRANSITION_3_waitMobile_4_parseToken = const(3)
_TRANSITION_4_parseToken_5_waitStation = const(4)
_TRANSITION_5_waitStation_0_noToken = const(5)
_TRANSITION_0_noToken_a_newMFromS = const(6)
_TRANSITION_0_noToken_b_newMFromM = const(7)
_TRANSITION_aORb_newM_c_newMReg = const(8)
_TRANSITION_cORd_newM_e_newMParseToken = const(9)
_TRANSITION_c_newMReg_d_newMSendMAck = const(10)
_TRANSITION_e_newMParseToken_f_newMWaitStation = const(11)
_TRANSITION_f_newMWaitStation_0_noToken = const(12)

# Timeout transition dictionary:
# State to transition
_TIMEOUT_DICT = {
    _STATE_3_waitMobile: _TRANSITION_2_pingMobile_3_waitMobile,
    _STATE_5_waitStation: _TRANSITION_4_parseToken_5_waitStation,
    _STATE_f_newMWaitStation: _TRANSITION_e_newMParseToken_f_newMWaitStation,
}


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

    # timeout timer
    __timeout_ticks = None

    def __init__(self, tokenID, mac, state, stationIDs):
        self.tokenID = tokenID
        self.mac = mac
        self.state = state
        self.RSSI = {stationID: 0 for stationID, stationMAC in stationIDs.items()}

    def updateRSSI(self, stationID, RSSI):
        """
        Update the RSSI of the mobile to a station

        Args:
            stationID   [String] => ID of the station
            RSSI        [Integer] => RSSI of the mobile to the station
        """
        self.RSSI[stationID] = RSSI

    def check_timeout(self):
        """Check if the timeout timer has expired"""
        if self.__timeout_ticks:
            return time.ticks_diff(self.__timeout_ticks, time.ticks_ms()) < 0
        else:
            return False

    def start_timeout_timer(self, timeout_ms):
        """Start the timeout timer"""
        self.__timeout_ticks = time.ticks_ms() + timeout_ms

    def stop_timeout_timer(self):
        """Stop the timeout timer"""
        self.__timeout_ticks = None


class esp_rtls_station:

    # Attributes:
    sta = None
    scl_pin = const(22)
    sda_pin = const(21)
    i2c = None
    line_height = const(10)
    mobile_list = {}

    # Task queue
    __taskQueue = []

    # debug attributes:
    __debug_time = 0
    __debug_level_print = 2
        # 0: no print
        # 1: location print
        # 2: debug print

    def __init__(self, station_list, mobile_list, mobile_token):
        self.__print_debug("BEGIN: init")
        self.__print_debug("    debug_time: " + str(self.__debug_time))
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

        self.__printStateLastLine("init DONE")

    def loop(self):
        """Description: Loop of the station"""

        # Print token id and state to display
        if self.mobile_list != {}:
            tokenID = list(self.mobile_list.keys())[0]
            self.__printInfoToDisplay(tokenID)

        # Check if there is something in the task queue
        if self.__taskQueue != []:
            self.__print_debug("\nTASK QUEUE: " + str(self.__taskQueue))
            [taskID, mac, task_data] = self.__taskQueue.pop()
            task_data = bytes(task_data)
            # Isloate tokenID from data
            TokenID = (task_data[0] & (0b00011111 << 0)) >> 0

            if taskID == _TRANSITION_0_noToken_1_sendACK:
                self.__print_debug("TRANSITION_0_noToken_1_sendACK")
                self.__do_STATE_0_noToken(mac, task_data)
                self.mobile_list[TokenID].state = _STATE_1_sendACK

                self.__taskQueue.append([_TRANSITION_1_sendACK_2_pingMobile, mac, task_data])

            elif taskID == _TRANSITION_1_sendACK_2_pingMobile:
                self.__print_debug("TRANSITION_1_sendACK_2_pingMobile")
                self.__do_STATE_1_sendAck(mac, TokenID)
                self.mobile_list[TokenID].state = _STATE_2_pingMobile

                self.__taskQueue.append(
                    [_TRANSITION_2_pingMobile_3_waitMobile, mac, task_data]
                )

            elif taskID == _TRANSITION_2_pingMobile_3_waitMobile:
                self.__print_debug("TRANSITION_2_pingMobile_3_waitMobile")
                self.__do_STATE_2_pingMobile(TokenID)
                self.mobile_list[TokenID].start_timeout_timer(1000)
                self.mobile_list[TokenID].state = _STATE_3_waitMobile

                # # Dummy functionality
                # self.__taskQueue.append(
                #     [_TRANSITION_3_waitMobile_4_parseToken, mac, data]
                # )

            elif taskID == _TRANSITION_3_waitMobile_4_parseToken:
                self.__print_debug("TRANSITION_3_waitMobile_4_parseToken")
                self.__print_debug("    Data: " + str(task_data))
                self.__print_debug("    len(data): " + str(len(task_data)))
                self.__do_STATE_3_waitMobile(mac, task_data, TokenID)
                self.mobile_list[TokenID].stop_timeout_timer()
                self.mobile_list[TokenID].state = _STATE_4_parseToken

                # Append task to task queue without trailing zeros on task_data
                self.__taskQueue.append(
                    [
                        _TRANSITION_4_parseToken_5_waitStation,
                        mac,
                        task_data,
                    ]
                )
                
            elif taskID == _TRANSITION_4_parseToken_5_waitStation:
                self.__print_debug("TRANSITION_4_parseToken_5_waitStation")
                self.__do_STATE_4_parseToken(TokenID)
                self.mobile_list[TokenID].start_timeout_timer(1000)
                self.mobile_list[TokenID].state = _STATE_5_waitStation

            elif taskID == _TRANSITION_5_waitStation_0_noToken:
                self.__print_debug("TRANSITION_5_waitStation_0_noToken")
                self.__do_STATE_5_waitStation(task_data)
                self.mobile_list[TokenID].stop_timeout_timer()
                self.mobile_list[TokenID].state = _STATE_0_noToken

                # print location
                self.__print_location()
                
            elif taskID == _TRANSITION_0_noToken_a_newMFromS:
                self.__print_debug("TRANSITION_0_noToken_a_newMobileFromStation")
                alreadyRegistered = self.__do_STATE_a_newMFromS(mac, task_data)
                
                if not alreadyRegistered: # if not registered => register
                    self.__print_debug("    Not registered: register")
                    # Not possible to register mobile before registration
                    #self.mobile_list[TokenID].state = _STATE_c_newMReg
                    self.__taskQueue.append([_TRANSITION_aORb_newM_c_newMReg, mac, task_data])
                else: # if registered => ping mobile
                    self.__print_debug("    Registered: ping mobile")
                    self.mobile_list[TokenID].state = _STATE_2_pingMobile
                    self.__taskQueue.append([_TRANSITION_2_pingMobile_3_waitMobile, mac, task_data])
                pass
            
            elif taskID == _TRANSITION_0_noToken_b_newMFromM:
                self.__print_debug("TRANSITION_0_noToken_b_newMobileFromMobile")
                alreadyRegistered = self.__do_STATE_b_newMFromM(mac, task_data)
                
                if not alreadyRegistered:
                    self.__print_debug("    Not registered: register")
                    self.__taskQueue.append([_TRANSITION_aORb_newM_c_newMReg, mac, task_data])
                else:
                    self.__print_debug("    Registered: send ack to mobile")
                    self.__taskQueue.append([_TRANSITION_c_newMReg_d_newMSendMAck, mac, task_data])
                    self.mobile_list[TokenID].state = _STATE_d_newMSendMAck
                pass
            
            elif taskID == _TRANSITION_aORb_newM_c_newMReg:
                self.__print_debug("TRANSITION_aORb_newM_c_newMReg")
                fromNewMfromM = self.__do_STATE_c_newMobileRegister(mac, task_data)
                
                if fromNewMfromM:
                    self.__print_debug("    From newMfromM: send ack to mobile")
                    self.__taskQueue.append([_TRANSITION_c_newMReg_d_newMSendMAck, mac, task_data])
                    self.mobile_list[TokenID].state = _STATE_d_newMSendMAck
                else:
                    self.__print_debug("    From newMfromS: parse token")
                    self.__taskQueue.append([_TRANSITION_cORd_newM_e_newMParseToken, mac, task_data])
                    self.mobile_list[TokenID].state = _STATE_e_newMParseToken
                pass
            
            elif taskID == _TRANSITION_c_newMReg_d_newMSendMAck:
                self.__print_debug("TRANSITION_c_newMReg_d_newMSendMAck")
                self.__do_STATE_d_newMSendMAck(mac, task_data)
                
                self.__taskQueue.append([_TRANSITION_cORd_newM_e_newMParseToken, mac, task_data])
                self.mobile_list[TokenID].state = _STATE_e_newMParseToken
                pass
            
            elif taskID == _TRANSITION_cORd_newM_e_newMParseToken:
                self.__print_debug("TRANSITION_cORd_newM_e_newMParseToken")
                self.__taskQueue.append([_TRANSITION_e_newMParseToken_f_newMWaitStation, mac, task_data])
                self.mobile_list[TokenID].state = _STATE_f_newMWaitStation
                pass
            
            elif taskID == _TRANSITION_e_newMParseToken_f_newMWaitStation:
                self.__print_debug("TRANSITION_e_newMParseToken_f_newMWaitStation")
                self.__do_STATE_e_newMParseToken(mac, task_data)
                self.mobile_list[TokenID].start_timeout_timer(1000)
                self.mobile_list[TokenID].state = _STATE_f_newMWaitStation
                pass
            
            elif taskID == _TRANSITION_f_newMWaitStation_0_noToken:
                self.__print_debug("TRANSITION_f_newMWaitStation_0_noToken")
                self.__do_STATE_f_newMWaitStation(task_data)
                self.mobile_list[TokenID].stop_timeout_timer()
                self.mobile_list[TokenID].state = _STATE_0_noToken
                pass
            
            else:
                self.__print_debug("Error: TaskID not in task list")

        # Check mobiles for timeout
        for mobile in self.mobile_list.values():
            if mobile.check_timeout() and mobile.state in _TIMEOUT_DICT:
                self.__print_debug("Timeout: " + str(mobile.tokenID))

                # print to display
                self.display.fill(0)
                self.display.text("Timeout: " + str(mobile.tokenID), 0, 0, 1)
                self.display.show()

                msgData = mobile.tokenID & 0b11111
                self.__taskQueue.append(
                    [_TIMEOUT_DICT[mobile.state], mobile.mac, bytearray([msgData])]
                )
                mobile.stop_timeout_timer()

        # Check if there is a message => no timeout
        mac, recv_data = self.esp_now.irecv(0)
        if mac != None:
            self.handleRecievedData(mac, recv_data)

    def handleRecievedData(self, mac, data):
        # print data
        self.__print_debug("    data: " + str(data))

        # Match first 3 bit of data with the message type
        msgType = (int(data[0]) & (0b11100000 << 0)) >> 5

        if msgType == _MTID_parseToken:
            self.__taskQueue.append([_TRANSITION_0_noToken_1_sendACK, mac, data])
        elif msgType == _MTID_ackToken:
            self.__taskQueue.append([_TRANSITION_5_waitStation_0_noToken, mac, data])
        elif msgType == _MTID_pongMobile:
            self.__taskQueue.append([_TRANSITION_3_waitMobile_4_parseToken, mac, data])
        elif msgType == _MTID_newMobile_fromStation:
            self.__taskQueue.append([_TRANSITION_0_noToken_a_newMFromS, mac, data])
        elif msgType == _MTID_newMobile_fromMobile:
            self.__taskQueue.append([_TRANSITION_0_noToken_b_newMFromM, mac, data])
        else:
            self.__print_debug("Error: Message type not in message type list")

    # State methods:
    def __do_STATE_0_noToken(self, mac, data):
        self.__print_debug("\nFUNC: __do_STATE_0_noToken")
        time.sleep(self.__debug_time)

        # Isolate tokenID, msgType and rssi1 from the data
        tokenID = (data[0] & (0b00011111 << 0)) >> 0
        msgType = (data[0] & (0b11100000 << 0)) >> 5
        rssi_recv_past = data[1]
        rssi_recv_past_past = data[2]

        self.__print_debug("    msgType:   " + str(msgType))
        self.__print_debug("    tokenID:   " + str(tokenID))
        self.__print_debug("    rssi_recv_past:      " + str(rssi_recv_past))
        self.__print_debug("    rssi_recv_past_past: " + str(rssi_recv_past_past))

        # Save RSSI from the past station
        stationID_recieved = self.__stationidFromMac(mac)
        stationID_past = ((self.stationID - 2) % len(self.station_list)) + 1
        stationID_past_past = ((self.stationID - 3) % len(self.station_list)) + 1

        # check if the stationID_recieved is the stationID_past => If not => Error
        if stationID_recieved != stationID_past:
            # print error
            self.__print_debug("Error: StationID_recieved != StationID_past")
            # Display error
            self.display.fill(0)
            self.display.text("Error:", 0, 0, 1)
            self.display.text(
                "StationID_recieved != StationID_past", 0, self.line_height, 1
            )
            self.display.text(
                "recv: " + str(stationID_recieved), 0, self.line_height * 2, 1
            )
            self.display.text(
                "past: " + str(stationID_past), 0, self.line_height * 3, 1
            )
            self.display.show()
            while True:
                pass

        self.mobile_list[tokenID].updateRSSI(stationID_past, rssi_recv_past)

        # Save RSSI from the past past station
        self.mobile_list[tokenID].updateRSSI(stationID_past_past, rssi_recv_past_past)

    def __do_STATE_1_sendAck(self, mac, tokenID):
        self.__print_debug("\nFUNC: __do_STATE_1_sendAck")

        # Dummy state functionality
        time.sleep(self.__debug_time)

        # Send ackToken back to the station
        msgType = _MTID_ackToken
        msgTokenID = tokenID
        msgData = (msgType & 0b111) << 5 | msgTokenID

        self.esp_now.send(mac, bytearray([msgData]), True)

    def __do_STATE_2_pingMobile(self, tokenID):
        self.__print_debug("\nFUNC: do_STATE_2_pingMobile")

        # Dummy state functionality
        time.sleep(self.__debug_time)

        # send ping to mobile
        msgType = _MTID_pingMobile
        msgTokenID = tokenID
        msgData = (msgType & 0b111) << 5 | msgTokenID
        
        self.__print_debug("    mac: " + str(self.mobile_list[tokenID].mac))

        self.esp_now.send(self.mobile_list[tokenID].mac, bytearray([msgData]), True)

    def __do_STATE_3_waitMobile(self, mac, data, tokenID):
        self.__print_debug("\nFUNC: do_STATE_3_waitMobile")

        # Dummy state functionality
        time.sleep(self.__debug_time)

        #     # Save RSSI of the mobile to the my station
        # self.mobile_list[tokenID].updateRSSI(
        #     self.stationID, self.stationID * 10 + random.randint(0, 9)
        # )

        # Extract RSSI from pong message
        rssi_mobile_2_station = abs(self.esp_now.peers_table[mac][0])  # type: ignore
        self.__print_debug("    rssi_mobile_2_station: " + str(rssi_mobile_2_station))

        # Extract RSSI from data
        rssi_station_2_mobile = data[1]
        self.__print_debug("    rssi_station_2_mobile: " + str(rssi_station_2_mobile))

        # Average RSSI and save it
        rssi_avg = round((rssi_mobile_2_station + rssi_station_2_mobile) / 2)
        self.__print_debug("    rssi_avg: " + str(rssi_avg))
        self.mobile_list[tokenID].updateRSSI(self.stationID, rssi_avg)

    def __do_STATE_4_parseToken(self, tokenID):
        self.__print_debug("\nFUNC: do_STATE_4_parseToken")

        # Send Parse Token back to the station  (for testing)
        msgType = _MTID_parseToken
        msgTokenID = tokenID
        msgData = (msgType & 0b111) << 5 | msgTokenID
        macNextStation = self.station_list[
            ((self.stationID) % len(self.station_list)) + 1
        ]
        my_rssi = self.mobile_list[tokenID].RSSI[self.stationID]

        # Get RSSI of the mobile to the previous station
        stationID_past = ((self.stationID - 2) % len(self.station_list)) + 1
        past_rssi = self.mobile_list[tokenID].RSSI[stationID_past]

        self.__print_debug("    Token send")
        self.__print_debug("        Msg send: " + str(msgData))
        self.__print_debug(
            "        Token send length = " + str(len(bytearray([msgData])))
        )
        self.__print_debug("        my_rssi: " + str(my_rssi))

        # Wait for 1 second
        time.sleep(self.__debug_time)

        # Send token
        self.esp_now.send(
            macNextStation, bytearray([msgData, my_rssi, past_rssi]), True
        )

    def __do_STATE_5_waitStation(self, data):
        self.__print_debug("\nFUNC: do_STATE_5_waitStation")

        # Isolate tokenID, msgType and rssi1 from the data
        tokenID = (data[0] & (0b00011111 << 0)) >> 0
        msgType = (data[0] & (0b11100000 << 0)) >> 5

        self.__print_debug("    msgType: " + str(msgType))
        self.__print_debug("    tokenID: " + str(tokenID))

    def __do_STATE_a_newMFromS(self, mac, data):
        self.__print_debug("\nFUNC: do_STATE_a_newMobileFromStation")
        
        # Isolate tokenID
        tokenID = (data[0] & (0b00011111 << 0)) >> 0
        
        # Send ack to station
        self.__do_STATE_1_sendAck(mac, tokenID)
        
        # Check if mobile is already registered
            # By checking if tokenID is already in mobile_list
        isAlreadyRegistered = tokenID in self.mobile_list.keys()

        return isAlreadyRegistered
    
    def __do_STATE_b_newMFromM(self, mac, task_data):
        self.__print_debug("\nFUNC: do_STATE_b_newMobileFromMobile")
        
        # Isolate tokenID
        tokenID = (task_data[0] & (0b00011111 << 0)) >> 0
        
        # Search for mobile in mobile_list
        return tokenID in self.mobile_list.keys()
    
    def __do_STATE_c_newMobileRegister(self, mac, data):
        self.__print_debug("\nFUNC: do_STATE_c_newMobileRegister")
    
        # Isolate tokenID
        tokenID = (data[0] & (0b00011111 << 0)) >> 0
        
        # Isolate mac
            # mac is the last 6 bytes of data
        mobile_mac = data[-6:]
        
        # Add mobile to mobile_list
        self.mobile_list[tokenID] = esp_rtls_station_mobile_info(
            tokenID,
            mobile_mac,
            _STATE_0_noToken,
            self.station_list,
        )
        
        print("Register Mobile: " + str(tokenID) + " - " + str(mobile_mac))
        
        # Add mobile to ESP-Now
        self.esp_now.add_peer(mobile_mac)
        
        # # if mac is equal to mac_mobile => send ack to mobile
        # if mac == mobile_mac:
        #     self.__print_debug("    mac == mobile_mac: send ack to mobile")
        #     # Send ack to mobile
        #     msgType = _MTID_newMobile_fromMobile_ack
        #     msgTokenID = tokenID
        #     msgData = (msgType & 0b111) << 5 | msgTokenID
        #     self.esp_now.send(mac, bytearray([msgData]), True)
        
        if mac == mobile_mac:
            fromNewMfromM = True
        else:
            fromNewMfromM = False
            
        return fromNewMfromM     

    def __do_STATE_d_newMSendMAck(self, mac, data):
        self.__print_debug("\nFUNC: do_STATE_d_newMSendMAck")    
    
        # Isolate tokenID
        tokenID = (data[0] & (0b00011111 << 0)) >> 0
        
        # Isolate mac
            # mac is the last 6 bytes of data
        mobile_mac = data[-6:]
        
        # if mac is equal to mac_mobile => send ack to mobile
        if mac == mobile_mac:
            self.__print_debug("    mac == mobile_mac: send ack to mobile")
            # Send ack to mobile
            msgType = _MTID_newMobile_fromMobile_ack
            msgTokenID = tokenID
            msgData = (msgType & 0b111) << 5 | msgTokenID
            self.esp_now.send(mac, bytearray([msgData]), True)
    
    def __do_STATE_e_newMParseToken(self, mac, data):
        self.__print_debug("\nFUNC: do_STATE_e_newMParseToken")
        
        # Isolate tokenID
        tokenID = (data[0] & (0b00011111 << 0)) >> 0
        
        # Isolate mac
            # mac is the last 6 bytes of data
        mobile_mac = data[-6:]
        
        # Parse token to next station
        self.__print_debug("    Parse token to next station")
        msgType = _MTID_newMobile_fromStation
        msgTokenID = tokenID
        msgData = (msgType & 0b111) << 5 | msgTokenID
        macNextStation = self.station_list[
            ((self.stationID) % len(self.station_list)) + 1
        ]
        
        # Send token
        msgData = bytearray([msgData]) + mobile_mac
        self.esp_now.send(
            macNextStation, msgData, True
        )
        
        self.__print_debug("    Token send")
        pass
    
    def __do_STATE_f_newMWaitStation(self, data):
        self.__print_debug("\nFUNC: do_STATE_f_newMWaitStation")
        
        # Isolate tokenID, msgType
        tokenID = (data[0] & (0b00011111 << 0)) >> 0
        msgType = (data[0] & (0b11100000 << 0)) >> 5

        self.__print_debug("    msgType: " + str(msgType))
        self.__print_debug("    tokenID: " + str(tokenID))
        
        pass

    # Private methods:
    def __printInfoToDisplay(self, tokenID):
        # Find position of the mobile in the mobile list
        mobile_position = None
        for position, mobile in self.mobile_list.items():
            if mobile.tokenID == tokenID:
                mobile_position = position
                break
        
        # Print info to display
        
        self.display.fill(0)
        self.display.text("TokenID: " + str(self.mobile_list[mobile_position].tokenID), 0, 0, 1)
        self.display.text(
            "State: " + str(self.mobile_list[mobile_position].state), 0, self.line_height, 1
        )
        self.display.text(
            "RSSI: S1: " + str(self.mobile_list[mobile_position].RSSI[1]), 0, 2 * self.line_height, 1
        )
        self.display.text(
            "      S2: " + str(self.mobile_list[mobile_position].RSSI[2]), 0, 3 * self.line_height, 1
        )
        self.display.text(
            "      S3: " + str(self.mobile_list[mobile_position].RSSI[3]), 0, 4 * self.line_height, 1
        )
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

    def __printStateLastLine(self, state, with_clear=True):
        if with_clear:
            self.display.fill(0)
        self.display.text("State: " + str(state), 0, 5 * self.line_height, 1)
        self.display.show()

    def __printFunctionNameSecondLastLine(self, func, with_clear=True):
        if with_clear:
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

    def __esp_now_add_mobiles(self):
        """Add mobiles to the ESP-Now"""

        for mobile in self.mobile_list.values():
            self.esp_now.add_peer(mobile.mac)
            self.__print_debug(
                "Added mobile "
                + str(mobile.tokenID)
                + " to ESP-Now - MAC: "
                + str(mobile.mac)
            )

    def __esp_now_add_other_stations(self):
        """Add other stations to the ESP-Now"""

        for stationID, stationMAC in self.station_list.items():
            if stationMAC != self.mac:
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

    def __print_location(self):
        """
        Print the rssi to the mobile from the different stations to the terminal

        Description:
            - only if debug_level_print = 1
            - As a list of 3 values (rssi1, rssi2, rssi3)
        """

        if self.__debug_level_print == 1:
            print(
                "("
                + str(self.mobile_list[1].RSSI[1])
                + ", "
                + str(self.mobile_list[1].RSSI[2])
                + ", "
                + str(self.mobile_list[1].RSSI[3])
                + ")"
            )

    def __print_debug(self, string):
        if self.__debug_level_print == 2:
            print(string)
