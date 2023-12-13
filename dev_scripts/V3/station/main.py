
from esp_rtls_station import *


# List of stations
    # 1 => 08:b6:1f:88:85:dc => DevNr 1
    # 2 => d4:d4:da:59:ed:ac => DevNr 2
    # 3 => 58:bf:25:09:5e:50 => DevNr 3
list_of_stations = {1:'08b61f8885dc', 2:'d4d4da59edac', 3:'58bf25095e50'}
# list_of_stations = {1:'08b61f8885dc', 2:'d4d4da59edac'}


# List of mobiles
    # 1 => 0b0001 ; d4:d4:da:5a:92:a0 => DevNr 4
    # 2 => 0b0010 ; 24:d7:eb:32:6c:34 => DevNr 5
list_of_mobiles = {1: 'd4d4da5a92a0', 2: '24d7eb326c34'}

# Create the station
station = esp_rtls_station(list_of_stations, list_of_mobiles, 1)

# Loop
while True:
    station.loop()
    
    