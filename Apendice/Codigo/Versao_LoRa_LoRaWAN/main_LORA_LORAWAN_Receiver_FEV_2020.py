import config_lora
from sx127x import SX127x
from controller_esp32 import ESP32Controller

from ssd1306_i2c import Display

from time import sleep, sleep_ms, sleep_us
import network
from umqtt.simple import MQTTClient


# ThingSpeak Credentials:
SERVER = "mqtt.thingspeak.com"
CHANNEL_ID = "1083373"
WRITE_API_KEY = "V62MN5J6XDQXV22Q"
PUB_TIME_SEC = 30

# MQTT client object
client = MQTTClient("umqtt_client", SERVER)

# Create the MQTT topic string
topic = "channels/" + CHANNEL_ID + "/publish/" + WRITE_API_KEY

# WiFi Credentials
WiFi_SSID = "LamyS9"
WiFi_PASS = "nkzs4379"


def do_connect():
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    if not wlan.isconnected():
        print('connecting to network...')
        wlan.connect(WiFi_SSID, WiFi_PASS)
        while not wlan.isconnected():
            pass
    print('network config:', wlan.ifconfig())


def receive(lora):
    print("LoRa Receiver")

    display = Display()

    while True:
        lora.receivedPacket()

        lora.blink_led()

        try:
            payload = lora.read_payload()

            #display.show_text_wrap("{} {} RSSI: {}".format(ident, payload.decode(), lora.packetRssi()), 2)
            #print("*** Received message ***\n{}".format(payload.decode()))

            data_recived = payload.decode()
            # print(data_recived)
            split_data_recived = data_recived.split()
            # print(split_data_recived)
            ds18_temp, pH_final, discharge, tdsValue, temp_dht22, hum_dht22, total_discharge = split_data_recived

            # print(ds18_temp)
            # print(pH_final)
            # print(discharge)
            # print(tdsValue)
            # print(temp_dht22)
            # print(hum_dht22)
            # print(total_discharge)
            # # Save to file if needed
            # # with open("recived.txt", mode='a') as file:
            # #     file.write('data recived raw: {} \n'.format(payload))
            display.show_text_wrap("{} {} {} {} {} {} {} ".format(
                ds18_temp, pH_final, discharge, tdsValue, temp_dht22, hum_dht22, total_discharge), 2)

            mqtt_payload = "field1="+str(ds18_temp)+"&field2="+str(pH_final)+"&field3="+str(discharge)+"&field4="+str(
                tdsValue)+"&field5="+str(temp_dht22)+"&field6="+str(hum_dht22)+"&field7="+str(total_discharge)

            client.connect()
            client.publish(topic, mqtt_payload)
            client.disconnect()
            sleep(PUB_TIME_SEC)

        except Exception as e:
            print(e)
        #display.show_text("RSSI: {}\n".format(lora.packetRssi()), 10, 10)
        #print("with RSSI: {}\n".format(lora.packetRssi))


controller = ESP32Controller()
lora = controller.add_transceiver(SX127x(name='LoRa'),
                                  pin_id_ss=ESP32Controller.PIN_ID_FOR_LORA_SS,
                                  pin_id_RxDone=ESP32Controller.PIN_ID_FOR_LORA_DIO0)
do_connect()

receive(lora)
