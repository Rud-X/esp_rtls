
from esp_rtls_station import *

# List of stations
    # 1 => 08:b6:1f:88:85:dc
    # 2 => d4:d4:da:59:ed:ac
    # 3 => 58:bf:25:09:5e:50
list_of_stations = {1:'08b61f8885dc', 2:'d4d4da59edac', 3:'58bf25095e50'}

# List of mobiles
    # 1 => 0b0001 ; 01:23:45:67:89:ab
    # 2 => 0b0010 ; 12:34:56:78:9a:bc
list_of_mobiles = {'0001': '0123456789ab', '0010': '123456789abc'}

# Create the station
station = esp_rtls_station(list_of_stations, list_of_mobiles, '0001')

# Loop
while True:
    time.sleep(1)