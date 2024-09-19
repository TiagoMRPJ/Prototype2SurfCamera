#!/bin/bash

# Define the serial device you want to check
SERIAL_DEVICE="/dev/ttyUSB0"

# Loop until the serial device is available
while [ ! -e $SERIAL_DEVICE ]; do
    echo "Waiting for serial device $SERIAL_DEVICE to be available..."
    sleep 1
done

SERIAL_DEVICE="/dev/ttyUSB1"

# Loop until the serial device is available
while [ ! -e $SERIAL_DEVICE ]; do
    echo "Waiting for serial device $SERIAL_DEVICE to be available..."
    sleep 1
done

SERIAL_DEVICE="/dev/ttyUSB2"

# Loop until the serial device is available
while [ ! -e $SERIAL_DEVICE ]; do
    echo "Waiting for serial device $SERIAL_DEVICE to be available..."
    sleep 1
done

sleep 5

echo "Serial devices are now available. Running main.py..."
python /home/IDMind/Documents/Prototype2SurfCamera/main.py