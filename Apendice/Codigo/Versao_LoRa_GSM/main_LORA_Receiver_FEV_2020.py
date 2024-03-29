# Manuel Lameira
# Licence under MIT
# code for ESP32 with MicroPython

# DTH22 --> ESP32
# ---------------
# GND   --> GND
# VCC   --> 5v or 3.3v
# DAT   --> digitalPin 4

# DS18X20 --> ESP32
# -----------------
# VCC --> 5V or 3.3V with resistor
# GND --> GND
# DAT --> digitalPin 5

# ph  --> ESP32
# -----------------
# VCC --> 5V or 3.3V with resistor
# GND --> GND
# DAT --> digitalPin 25

# TDS --> ESP32
# --------------------
# VCC --> 5.5V or 3.3V
# A   --> Analog Pin 35
# GND --> GND

# SR04  --> ESP32
# --------------------
# VCC   --> 5V or 3.3V ATENCION: on 3.3V the range decresses
# Trig  --> DigitalPin 27
# Echo  --> DigitalPin 26
# GND   --> GND
# Speed of Sound = 343 m/s in dry air at 20ºC

from machine import Pin, I2C, time_pulse_us, deepsleep
from time import sleep, sleep_ms, sleep_us
from onewire import OneWire
from ds18x20 import DS18X20

import dht

import DS1307

from sim900_web_lameira import gsm_http

import config_lora
from sx127x import SX127x
from controller_esp32 import ESP32Controller


def Average(lst):
    # function to get average of a list
    return sum(lst) / len(lst)


def ReadPH(voltage, temp):
    # Calibration of probe
    # PH4502 with 5V --> pH 4 acidVoltage = 1.432V and pH 7 (pot calibration) neutralVoltage = 2.5V
    # with voltage divider --> pH 4 = 0.944V and pH 7 = 1.652V
    acidVoltage = 0.9440
    neutralVoltage = 1.6520

    if temp >= 25:
        temp_correction = 0.003 * (temp - 25)
    else:
        temp_correction = -0.003 * (temp - 25)

    slope = (7.0 - 4.0) / (- (acidVoltage - neutralVoltage) / 3.0)
    phValue = (slope * (voltage - neutralVoltage) /
               3.0) + temp_correction

    round(phValue, 2)
    return phValue


def ReadTDS(voltage, temp):
    # Temperature compensation to 25 °C reference value
    comp_Coefficente = 1 + 0.02 * (temp - 25)

    # compensated electrical conductivity
    comp_Voltage = voltage / comp_Coefficente

    # convert voltage value to tds value
    tds_value = ((133.42 * comp_Voltage**3) - (255.86 *
                                               comp_Voltage**2) + (857.39 * comp_Voltage)) * 0.5

    return tds_value


def receive(lora):

    while True:

        lora.receivedPacket()

        lora.blink_led()

        try:
            payload = lora.read_payload()

            return payload

        except Exception as e:
            print(e)


controller = ESP32Controller()
lora = controller.add_transceiver(SX127x(name='LoRa'),
                                  pin_id_ss=ESP32Controller.PIN_ID_FOR_LORA_SS,
                                  pin_id_RxDone=ESP32Controller.PIN_ID_FOR_LORA_DIO0)


#####----- RTC -----#####
i2c = I2C(sda=Pin(21), scl=Pin(22))
ds = DS1307.DS1307(i2c)

date_init = ds.DateTime()


#####----- LoRa -----#####

controller = ESP32Controller()
lora = controller.add_transceiver(SX127x(
    name='LoRa'), pin_id_ss=ESP32Controller.PIN_ID_FOR_LORA_SS, pin_id_RxDone=ESP32Controller.PIN_ID_FOR_LORA_DIO0)


#####----- DS18X20 -----#####
ds18_pin = Pin(5)
ds18_sensor = DS18X20(OneWire(ds18_pin))

addrs = ds18_sensor.scan()
addr = addrs.pop()

ds_read = ds18_sensor.convert_temp()
sleep_ms(750)
ds18_temp = ds18_sensor.read_temp(addr)
# ds18_temp_print = str('%3.2f C  DS18X20' %temp_ds)


#####----- ph -----#####
pH = ADC(Pin(25))
pH.atten(ADC.ATTN_11DB)  # Reading range: 3.3V


buf_ph = []
sample_ph = range(10)

for i in sample_ph:
    buf_ph.append(pH.read())
    sleep(2)

avgValue_ph = Average(buf_ph)
phVoltage = (avgValue_ph / (4095/3.3))

pH_final = ReadPH(phVoltage, ds18_temp)
# print(pH_final, "ph")


#####----- TDS -----#####
tds = ADC(Pin(35))
tds.atten(ADC.ATTN_11DB)  # Reading range: 3.3V


buf_tds = []
sample_tds = range(5)

for i in sample_tds:
    buf_tds.append(tds.read())
    sleep(1)

avgValue_tds = Average(buf_tds)
tdsVoltage = (avgValue_tds * (3.3/4095))  # read the voltage in mV

tdsValue = round(ReadTDS(tdsVoltage, ds18_temp), 3)
# print(tdsValue, " ppm")


#####----- DHT22 -----#####
dht_sensor = dht.DHT22(Pin(4))

temp_dht22 = ReadDHT22temp(dht_sensor)
#temp_conv = str('%3.2f C  DHT22' %temp_dht22)
hum_dht22 = ReadDHT22hum(dht_sensor)
#hum_conv = str('%3.2f %%' %hum_dht22)


#####----- Water flow HC-SR04 -----#####
trig = Pin(27, Pin.OUT)
echo = Pin(26, Pin.IN)

timeout_us = 25000  # no need to wait more then sensor's range limit (4,00 m)

sensor_hight = 150

trig.value(1)
sleep_us(10)
trig.value(0)

duration = time_pulse_us(echo, 1, timeout_us)

if duration < 0:
    print("Out of range")
else:
    # To calculate the distance we get the pulse_time and divide it by 2
    # (the pulse walk the distance twice)
    # the sound speed on air (343.2 m/s), that It's equivalent to
    # 0.034320 cm/us that is 1cm each 29.1us

    # Calculate the Speed of Sound in M/S
    sound_comp = 331.4 + (0.606 * temp_dht22) + (0.0124 * hum_dht22)

    distance = (duration / 2) * 0.000343

    water_hight = sensor_hight - distance

    discharge = (0.209763317*(water_hight**(5/3))) / \
        ((water_hight + 0.918486862)**(2/3))
    print(discharge, " m3/s")

    total_discharge = discharge*(300)


emissor1 = receive(lora)

#  Implentar split aos dados


#####----- Thingspeak -----#####
url_gateway = "https://api.thingspeak.com/update?api_key=IL9VIMCHEXM9H3W4&field1={}&field2={}&field3={}&field4={}&field5={}&field6={}&field7={}".format(
    ds18_temp, pH_final, discharge, tdsValue, temp_dht22, hum_dht22, total_discharge)

gsm_http(url_gateway)

url_emissor = "https://api.thingspeak.com/update?api_key=2IDFEOWYZCNDP7YW&field1={}&field2={}&field3={}&field4={}&field5={}&field6={}&field7={}".format(
    ds18_temp, pH_final, discharge, tdsValue, temp_dht22, hum_dht22, total_discharge)

gsm_http(url_emissor)
