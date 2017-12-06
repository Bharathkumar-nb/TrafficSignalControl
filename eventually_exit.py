import time, socket, sys
import signal
import paho.mqtt.client as paho
import mraa
import threading

# Init LEDs
leds = []
for i in range(2,10):
    led = mraa.Gpio(i)
    leds.append(led)


class Exit(object):
    """docstring for Safety"""
    def __init__(self):
        self.car_timers = {}
        
        # setup MQTT and register MQTT callback functions
        self.mqtt_client = paho.Client()
        self.mqtt_client.on_connect = self.on_connect
        self.mqtt_client.on_message = self.on_message
        self.mqtt_client.on_disconnect = self.on_disconnect
        self.mqtt_client.on_log = self.on_log
        self.mqtt_topic = 'TrafficSignalControl/exit'
        self.mqtt_client.will_set(self.mqtt_topic, '______________Will of Exit_________________\n\n', 0, False)
        self.mqtt_client.connect('sansa.cs.uoregon.edu', '1883',keepalive=300)
        self.mqtt_client.subscribe([('TrafficSignalControl/car', 0),('TrafficSignalControl/gui', 0)])
        self.mqtt_client.loop_start()
        
        signal.signal(signal.SIGINT, self.control_c_handler)

    # Deal with control-c
    def control_c_handler(self, signum, frame):
        self.mqtt_client.disconnect()
        self.mqtt_client.loop_stop()  # waits until DISCONNECT message is sent out
        print ("Exit")
        sys.exit(0)

    # MQTT callback functions
    def on_connect(self, client, userdata, flags, rc):
        pass
    
    def on_message(self, client, userdata, msg):
        if len(msg.payload.split('.')) > 1:
            key, msg_content = msg.payload.split('.')

            if msg_content == 'Request':
                car_id,lane_id,timestamp = key.split('_')
                self.car_timers[car_id] = threading.Timer(15.0, self.timeout_handler, car_id)

            if msg_content == 'Exit':
                car_id = key
                del self.car_timers[car_id]
            

    def on_disconnect(self, client, userdata, rc):
        self.mqtt_client.loop_stop()  # waits until DISCONNECT message is sent out
        print ("Exit")
        sys.exit(0)

    def on_log(self, client, userdata, level, buf):
        pass
        #print("log: {}".format(buf)) # only semi-useful IMHO

    def timeout_handler(self, car_id):
        print('Error: Car {} has been waiting for more than 10 seconds'.format(car_id))
        self.turnOnLED(2)

    # LED functions
    def turnOnLED(self, led_no):
        leds[led_no].write(0)

    def turnOffLED(self, led_no):
        leds[led_no].write(1)


if __name__ == '__main__':
    Exit()
    while True:
        time.sleep(10)