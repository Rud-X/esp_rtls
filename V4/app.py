"""
Read 3 distances from COM port and do trilateration to get the position of the mobile => Plot the position on the map dynamically

Description:
- COM port: COM3
- Baudrate: 115200
- 3 distances: d1, d2, d3
    - In format: (d1,d2,d3)
- max distance: 128
"""

import serial
import matplotlib.pyplot as plt
import numpy as np
import math

# Global variables
ser = serial.Serial('COM3', 115200)
ser.flushInput()
x1 = 0
y1 = 0
x2 = 0
y2 = 0
x3 = 0
y3 = 0
x = 0
y = 0
d1 = 0
d2 = 0
d3 = 0
max_distance = 128
fig = plt.figure()
ax = fig.add_subplot(111)
ax.set_xlim([0, 100])
ax.set_ylim([0, 100])
ax.set_aspect('equal')
ax.grid()

# Functions
def get_distance(rssi, rssi_at_1_meter=60, n=2.0):
    distance = 10 ** (((-rssi_at_1_meter) - (-rssi)) / (10 * n))
    
    return distance

def calc_anchor_position(x1,y1, d_1_2, d_1_3, d_2_3):
    x2 = x1 - d_2_3/2
    x3 = x1 + d_2_3/2
    y2 = y1 - math.sqrt(d_1_2**2 - x2**2)
    y3 = y1 - math.sqrt(d_1_3**2 - x3**2)
    return x2, y2, x3, y3

def get_position(x1, y1, x2, y2, x3, y3, d1, d2, d3):
    
    A = 2 * x2 - 2 * x1
    B = 2 * y2 - 2 * y1
    C = d1 ** 2 - d2 ** 2 - x1 ** 2 + x2 ** 2 - y1 ** 2 + y2 ** 2
    D = 2 * x3 - 2 * x2
    E = 2 * y3 - 2 * y2
    F = d2 ** 2 - d3 ** 2 - x2 ** 2 + x3 ** 2 - y2 ** 2 + y3 ** 2
    x = (C * E - F * B) / (E * A - B * D)
    y = (C * D - A * F) / (B * D - A * E)
    return x, y, d1, d2, d3

def plot_position(x, y, x1, y1, x2, y2, x3, y3, d1, d2, d3):
    # draw the circles of the radius from the three anchors
        # With dotted line
    circle1 = plt.Circle((x1, y1), d1, color='r', fill=False, linestyle='--')
    circle2 = plt.Circle((x2, y2), d2, color='g', fill=False, linestyle='--')
    circle3 = plt.Circle((x3, y3), d3, color='b', fill=False, linestyle='--')
    
    ax.add_artist(circle1)
    ax.add_artist(circle2)
    ax.add_artist(circle3)
    
    ax.scatter(x, y, c='black', marker='o')
    ax.scatter(x1, y1, c='r', marker='o')
    ax.scatter(x2, y2, c='g', marker='o')
    ax.scatter(x3, y3, c='b', marker='o')
    plt.pause(0.05)
    
def clear_plot(x1, y1, x2, y2, x3, y3):
    ax.clear()
    # Calculate minimum and maximum of x and y
    min_x = min(x1, x2, x3)
    max_x = max(x1, x2, x3)
    min_y = min(y1, y2, y3)
    max_y = max(y1, y2, y3)
    ax.set_xlim([min_x -abs(min_x/2), max_x + abs(min_x/2)])
    ax.set_ylim([min_y -abs(min_y/2), max_y + abs(min_x/2)])
    ax.set_aspect('equal')
    ax.grid()
    
def swap_position_of_2_anchors(x1, y1, x2, y2):
    x1, x2 = x2, x1
    y1, y2 = y2, y1
    return x1, y1, x2, y2

# Moving average filter
def moving_average_filter(d, d_last):
    d_filtered = (d + d_last) / 2
    return d_filtered

# Moving average on 3 distances
def moving_average_on_3_distances(d1, d2, d3, d_1_last, d_2_last, d_3_last):
    d1_filtered = moving_average_filter(d1, d_1_last)
    d2_filtered = moving_average_filter(d2, d_2_last)
    d3_filtered = moving_average_filter(d3, d_3_last)
    return d1_filtered, d2_filtered, d3_filtered
    
x1 = 0
y1 = 0

d_1_last = 0
d_2_last = 0
d_3_last = 0

x2, y2, x3, y3 = calc_anchor_position(x1, y1, 6, 6, 6)
# Main
while True:
    ser_bytes = ser.readline()
    decoded_bytes = ser_bytes[0:len(ser_bytes)-2].decode("utf-8")
    print(decoded_bytes)
    if decoded_bytes != "":
        decoded_bytes = decoded_bytes[1:-1]
        d1, d2, d3 = decoded_bytes.split(",")
        d1 = get_distance(int(d1),58,2.5)
        d2 = get_distance(int(d2),58,2.5)
        d3 = get_distance(int(d3),58,2.5)
        d1, d2, d3 = moving_average_on_3_distances(d1, d2, d3, d_1_last, d_2_last, d_3_last)
        d_1_last, d_2_last, d_3_last = d1, d2, d3
        print("d1 = ", d1)
        print("d2 = ", d2)
        print("d3 = ", d3)
        if d1 != 0 and d2 != 0 and d3 != 0:
            x, y, d1, d2, d3 = get_position(x1, y1, x2, y2, x3, y3, d1, d2, d3)
            print("x = ", x)
            print("y = ", y)
            plot_position(x, y, x1, y1, x2, y2, x3, y3, d1, d2, d3)
            clear_plot(x1, y1, x2, y2, x3, y3)
#     try:
#         ser_bytes = ser.readline()
#         decoded_bytes = ser_bytes[0:len(ser_bytes)-2].decode("utf-8")
#         print(decoded_bytes)
#         if decoded_bytes != "":
#             d1, d2, d3 = decoded_bytes.split(",")
#             d1 = get_distance(int(d1))
#             d2 = get_distance(int(d2))
#             d3 = get_distance(int(d3))
#             print("d1 = ", d1)
#             print("d2 = ", d2)
#             print("d3 = ", d3)
#             if d1 != 0 and d2 != 0 and d3 != 0:
#                 x, y = get_position(x1, y1, x2, y2, x3, y3, d1, d2, d3)
#                 print("x = ", x)
#                 print("y = ", y)
#                 plot_position(x, y)
#                 clear_plot()
#     except:
#         print("Keyboard Interrupt")
#         break
    
# Close serial port
ser.close()

# References:
# https://stackoverflow.com/questions/29317262/realtime-plotting-with-matplotlib-and-arduino-data

