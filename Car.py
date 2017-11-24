import time, socket, sys
from datetime import datetime as dt
import paho.mqtt.client as paho
import signal
import mraa

leds = []
for i in range(2,10):
    led = mraa.Gpio(i)
    led.dir(mraa.DIR_OUT)
    led.write(1)
    leds.append(led)

class Car(object):
    """docstring for Car"""
    def __init__(self, car_id, lane_id, direction):
        self.MY_NAME = 'Car : ' + car_id
        self.car_id = car_id
        self.lane_id = lane_id
        self.direction = direction

        self.mqtt_client = paho.Client()
        self.mqtt_client.on_connect = self.on_connect
        self.mqtt_client.on_message = self.on_message
        self.mqtt_client.on_disconnect = self.on_disconnect
        self.mqtt_client.on_log = self.on_log
        self.mqtt_topic = 'TrafficSignalControl/' + 'car'
        self.mqtt_client.will_set(self.mqtt_topic, '______________Will of '+self.MY_NAME+' _________________\n\n', 0, False)
        self.mqtt_client.connect('sansa.cs.uoregon.edu', '1883',keepalive=300)
        self.mqtt_client.subscribe('TrafficSignalControl/' + 'car')
        self.mqtt_client.loop_start()
        self.isBroadcast = False
        self.isWaiting = False
        self.isPassing = False

        signal.signal(signal.SIGINT, self.control_c_handler)
        signal.signal(signal.SIGALRM, self.enter_critical_section)

        self.broadcast_request()
        self.ll = []
        self.hl = []

    def broadcast_request(self):
        print(self.car_id+'_'+self.lane_id+'.Request')
        self.mqtt_client.publish(self.mqtt_topic, self.car_id+'_'+self.lane_id+'.Request')
        self.isBroadcast = True
        self.isWaiting = True
        signal.alarm(10)

  

    # Deal with control-c
    def control_c_handler(self, signum, frame):
        self.mqtt_client.disconnect()
        self.mqtt_client.loop_stop()  # waits until DISCONNECT message is sent out
        print ("Exit")
        sys.exit(0)
        
    def on_connect(self, client, userdata, flags, rc):
        pass
    
    def on_message(self, client, userdata, msg):
        if len(msg.payload.split('.')) > 1:
            key, msg_content = msg.payload.split('.')

            if msg_content == 'Request':
                car_id,lane_id = key.split('_')
                # missing part

                if car_id == self.car_id and (self.isWaiting or self.isPassing) :
                    self.ll.append(car_id)
                    print(self.car_id+'_'+car_id+'.Reject')
                    self.mqtt_client.publish(self.mqtt_topic, self.car_id+'_'+car_id+'.Reject')

            if msg_content == 'Reject':
                src,dest = key.split('_')
                if self.isWaiting:
                    if dest == self.car_id:
                        self.hl.append(src)
                    else:
                        # check preemption
                        pass
            if msg_content == 'Permit':
                src = key
                if src != self.car_id:
                    self.hl.remove(src)
                    if self.hl == []:
                        self.isPassing = True
                        self.enter_critical_section()


    def enter_critical_section(self):
        time.sleep(3)
        print(self.car_id+'.Permit')
        self.mqtt_client.publish(self.mqtt_topic, self.car_id+'.Permit')
        




            


    def on_disconnect(self, client, userdata, rc):
        pass

    def on_log(self, client, userdata, level, buf):
        pass
        #print("log: {}".format(buf)) # only semi-useful IMHO

    # LED functions
    def turnOnLED(self):
        led_idx = int(self.led_no)
        leds[led_idx].write(0)

    def turnOffLED(self):
        led_idx = int(self.led_no)
        leds[led_idx].write(1)

    def blinkLED(self):
        for x in xrange(0,30):
            self.turnOnLED()
            time.sleep(0.1)
            self.turnOffLED()
            time.sleep(0.1)


def main():
    arr = sys.argv
    if  len (arr) != 4 :
        print ('Please enter valid input, e.g. python car.py <car_id> <lane_id> <[0,1](straight,right)>')
        sys.exit(1)
    if arr[2] not in '1234' or len(arr[2]) > 1:
        print ('Please enter valid led number between 1 to 4')
        sys.exit(1)
    Car(arr[1], arr[2], arr[3])
    while True:
        time.sleep(10)

main()