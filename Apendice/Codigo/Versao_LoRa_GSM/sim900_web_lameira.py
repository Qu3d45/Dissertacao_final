# Adapted from Sandro Ormeno in https://github.com/sandroormeno/sim800L/blob/master/pi_SIM800.py
# Board: ESP32 - WROOM or WROVER with SIM900
# Manuel Lameira, 02/2020

from machine import UART
from time import sleep

ua = UART(2, 19200, rxbuf=1000, timeout=1)


def sim900_responde():
    while True:
        response = ua.readline()
        print response
        if "OK" in response:
            break


def gsm_http(url_and_readings):
    # Inicial handshake
    ua.write('AT\r')
    sim900_responde()

    # configure bearer profile 1
    ua.write('AT+SAPBR=3,1,"Contype","GPRS"\r')
    sim900_responde()

    ua.write('AT+SAPBR=3,1,"APN","CMNET"\r')
    sim900_responde()

    # To open GPRS context
    ua.write('AT+SAPBR=1,1\r')
    sim900_responde()

    # Init http service
    ua.write('AT+HTTPINIT\r')
    sim900_responde()

    # Set parameters for HTTP session
    ua.write('AT+HTTPPARA="CID",1\r')
    sim900_responde()

    ua.write('AT+HTTPPARA="URL","{}"\r').format(url_and_readings)
    sim900_responde()

    # Session start
    ua.write('AT+HTTPACTION=0\r')
    sim900_responde()
    # Wait for response
    sleep(4)

    # Terminate http service
    ua.write('AT+HTTPTERM\r')
    sim900_responde()

    # To close a GPRS context
    ua.write('AT+SAPBR=0,1\r')
    sim900_responde()
