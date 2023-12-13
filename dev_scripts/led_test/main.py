from machine import Pin
import time

p19 = Pin(19, Pin.OUT)
p18 = Pin(18, Pin.OUT)
p5 = Pin(5, Pin.OUT)

# One pin is 0 and the two others are 1
while True:
    p19.value(0)
    p18.value(1)
    p5.value(1)
    time.sleep(1)
    p19.value(1)
    p18.value(0)
    p5.value(1)
    time.sleep(1)
    p19.value(1)
    p18.value(1)
    p5.value(0)
    time.sleep(1)