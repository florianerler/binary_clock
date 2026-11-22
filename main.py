"""
Binary Clock
========================================================================
Author:   Florian Erler
Started:  2026-11-21
Version:  0.2
Platform: MicroPython on ESP32

Description
------------------------------------------------------------------------
Self-built binary clock. Shows hours, minutes and seconds in true binary
(no BCD) on 17 LEDs.
Planned features:
  - rolling light at startup as a wiring check
  - WLAN connection and time via NTP, converted to local time (CET/CEST)
  - hourly chime with the buzzer, but not during the quiet hours at night

Hardware
-------------------------------------------------------------------------
  - 1x ESP32 DevKit
  - 17x LED  (hours: 5, minutes: 6, seconds: 6)
  - 1x SN74HC595N shift register (seconds LEDs)
  - 1x passive buzzer

Contents
-------------------------------------------------------------------------
  1. Imports
  2. Pins and lists
  3. Functions
  4. Main program

Source
-------------------------------------------------------------------------
Based on "Python Der Grundkurs" (Rheinwerk), written in German.

Changelog
-------------------------------------------------------------------------
2026-11-21  v0.0    added:  -imports
                            -pin objects
                            -pin lists
                            -function_test

2026-11-22  v0.1    added:  -write_bits
                            -shift_register
                            -show_seconds (mirrored and shifted seconds)

2026-11-22  v0.2    added:  -clock loop without internet (h/m/s counter
                             with overflow 60 -> 0 and 24 -> 0)
                            -display of hours, minutes and seconds on the LEDs
                            -connect_wifi
                            -main() with rolling light at startup and wifi connection buildup


"""

# imports:
from machine import Pin
import time
import network
from network import STA_IF
from secrets import ssid, pw


# pin objects:
hour_1 = Pin(4, Pin.OUT)
hour_2 = Pin(16, Pin.OUT)
hour_4 = Pin(17, Pin.OUT)
hour_8 = Pin(18, Pin.OUT)
hour_16 = Pin(19, Pin.OUT)
min_1 = Pin(14, Pin.OUT)
min_2 = Pin(27, Pin.OUT)
min_4 = Pin(26, Pin.OUT)
min_8 = Pin(25, Pin.OUT)
min_16 = Pin(33, Pin.OUT)
min_32 = Pin(32, Pin.OUT)
SER = Pin(23, Pin.OUT)
SRCLK = Pin(21, Pin.OUT)
RCLK = Pin(22, Pin.OUT)

# wlan:
wlan = network.WLAN(STA_IF)

# h_ind: hour indicator led output list:
h_ind = [hour_1, hour_2, hour_4, hour_8, hour_16]

# m_ind: minutes indicator led output list:
m_ind = [min_1, min_2, min_4, min_8, min_16, min_32]

# new combined list for rolling leds for function test:
led_rolling = h_ind + m_ind

def function_test(led):
    """
    Switch one LED on and off again, used as the wiring test.

    led: Pin object (output) of the LED to flash

    Called once for every LED in led_rolling at startup, so the LEDs
    light up one after the other. Returns nothing.
    """
    led.on()
    time.sleep(0.3)
    led.off()
    time.sleep(0.3)

def write_bits(value, pin_lst):
    """
    Write a number in binary to a list of output pins.

    value:   non-negative integer to display; bits beyond the length
             of pin_lst are ignored
    pin_lst: list of Pin objects (outputs), index 0 is the least significant
             bit (value 1), index 1 is value 2, index 2 is value 4, ...
    Returns nothing.
    """
    pin_count = len(pin_lst)
    for i in range(pin_count):
        bit = (value >> i) & 1
        pin_lst[i].value(bit)

def shift_register(byte_value):
    """
    Shift one byte into the 74HC595 shift register and latch it to the outputs.

    byte_value: integer 0..255; bit n of the byte ends up on output Qn
                (bit 0 -> Q0, ..., bit 7 -> Q7)

    The bits are shifted in starting with bit 7, so the first bit pushed
    ends up on Q7. The outputs only change once, when RCLK is pulsed at the end.
    Returns nothing.
    """
    SRCLK.value(0)
    RCLK.value(0)
    for i in range(7, -1, -1):
        extracted_bit = (byte_value >> i) & 1
        SER.value(extracted_bit)
        SRCLK.value(1)
        SRCLK.value(0)
    RCLK.value(1)
    RCLK.value(0)

def show_seconds(sec_value):
    """
    Show the seconds in binary on the six LEDs connected to the shift register.

    sec_value: integer 0..63 (seconds are 0..59); bit j of the value has the
               weight 2**j and is shown on output Q(6 - j)

    The seconds LEDs are wired to Q1..Q6 in reversed order: value 1 is on Q6,
    value 32 is on Q1. The bits are therefore mirrored and shifted by one
    position before the byte is passed to shift_register(). Q0 and Q7 stay 0.
    Returns nothing.
    """
    byte = 0
    for j in range(5, -1, -1):
        bit = (sec_value >> j) & 1
        m = 6 - j
        if bit == 1:
            byte |= 1 << m
    shift_register(byte)

def connect_wifi():
    """
    Connect to the WLAN with the credentials from secrets.py.

    Switches the station interface on, starts the connection once and then
    checks once per second whether it is established, for at most 10 tries.

    Returns True if connected, False if the time limit was reached.
    The caller decides what to do when the connection fails.
    """
    wlan.active(True)
    wlan.connect(ssid, pw)
    tries = 0
    while wlan.isconnected() == False and tries < 10:
        time.sleep(1)
        tries += 1
    return wlan.isconnected()

def main():
    """
    Run the binary clock.

    1. Rolling light over all 11 directly connected LEDs (wiring test).
    2. Count hours, minutes and seconds starting at 0:00:00, once per second,
       with overflow 60 -> 0 and 24 -> 0.
    3. Show hours and minutes with write_bits() and the seconds with
       show_seconds() after every step.

    Runs forever, does not return. Time source is the internal counter for now,
    NTP and local time follow later.
    """
    iterator = map(function_test, led_rolling)
    for _ in iterator:
        pass

    connect_wifi()

    starting_hour = 0
    starting_minute = 0
    starting_second = 0

    while True:
        print(starting_hour, starting_minute, starting_second)
        time.sleep(1)
        starting_second = starting_second + 1
        if starting_second > 59:
            starting_second = 0
            starting_minute = starting_minute + 1
        if starting_minute > 59:
            starting_minute = 0
            starting_hour = starting_hour + 1
        if starting_hour > 23:
            starting_hour = 0
        write_bits(starting_hour, h_ind)
        write_bits(starting_minute, m_ind)
        show_seconds(starting_second)


if __name__ == '__main__':
    main()



