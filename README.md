# esp_rtls
A project exploring the use of ESP-MCU's as hardware for a RTLS, using either ESP-NOW or BLE

## Current Version
> The current version is: V4

Main functionality: 
- 3 Stations and (tested upto) 2 mobiles
- Dynamic registration of mobiles
- Estimation using RSSI and simple trilateration

## How to use
> This section will cover how to setup and use the system, the steps are chronologicaly ordered.
>
> Note that the how to use is made for windows, but the steps are similar for other OS's.

### Hardware
- Minimum 4 NodeMCU ESP32 developmentboards (optionally other ESP32 boards)
  - With SH1106 OLED display (partly optional)
- Power supply for the ESP's

### Flashing the ESP's
Use AMPY to flash the ESP's

Example for ESP on COM3:

```bash
pip install esptool
esptool.py --port COM3 erase_flash
esptool.py --chip esp32 --port COM3 write_flash -z 0x1000 esp32-20180511-v1.9.4.bin
```

### Installing the software

#### Stations
For 3 of the ESP's, the stations, the following steps are to be done:

Adjust the MAC-addresses for the stations (`list_of_stations`) in `V4/station/main.py` to the MAC-addresses of the ESP's used for the stations. (the `list_of_mobiles` in `V4/station/main.py` is optional)

Starting from the root of the project:
```bash
cd V4/station
ampy -p COM3 -d 2 put main.py
ampy -p COM3 -d 2 put esp_rtls_station.py
```

The delay `-d 2` shouldn't be necessary, but is the only way to make it work for me, it has to do with the time it takes for the ESP to boot up.

#### Mobiles
For the remaining ESP's, the mobiles, the following steps are to be done:

Just as with the stations: Adjust the MAC-addresses for the stations (`list_of_stations`) in `V4/station/main.py` to the MAC-addresses of the ESP's used for the stations. (the `list_of_mobiles` in `V4/station/main.py` is optional). It is only necessary to set the MAC-addresses for the station with number 1, the rest will be discovered dynamically.

Starting from the root of the project:
```bash
cd V4/mobile
ampy -p COM3 -d 2 put main.py
ampy -p COM3 -d 2 put esp_rtls_mobile.py
```

### Running the system without app
1. Power on the stations
2. Power on the mobiles

### Running the system with app
1. Power on all other stations than 1 (called station 1)
2. Plug station 1 into the computer
3. Adjust `V4/app.py` to the correct COM port
4. Make sure that the `__debug_level_print` in `V4/esp_rtls_station.py` is set to `1`
   1. At least for the station plugged into the computer
5. Run `V4/app.py`
6. Power on the mobiles