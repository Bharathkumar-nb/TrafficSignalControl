import time, socket, sys
from datetime import datetime as dt
import paho.mqtt.client as paho
import signal
#import mraa
import threading

# leds = []
# for i in range(2,10):
#     led = mraa.Gpio(i)
#     led.dir(mraa.DIR_OUT)
#     led.write(1)
#     leds.append(led)

# constants
TH = 2
NF = 2

class Car(object):
    """docstring for Car"""
    def __init__(self, car_id, lane_id):
        self.MY_NAME = 'Car : ' + car_id
        self.car_id = car_id
        self.lane_id = lane_id
        self.timer = threading.Timer(10.0, self.timeout_handler)
        self.compatible_lane = str(((int(self.lane_id)+1)%4)+1)
        self.cnt_pmp = 0
        self.isBroadcast = False
        self.isWaiting = False
        self.isPassing = False
        self.isLast = False
        self.isDone = False
        self.ll = []
        self.hl = []

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

        signal.signal(signal.SIGINT, self.control_c_handler)

        self.broadcast_request()

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
        # print('on_message: {}'.format(msg.payload))
        # print('Before hl: {}'.format(self.hl))
        # print('Before ll: {}'.format(self.ll))
        if self.isDone:
            return
        if len(msg.payload.split('.')) > 1:
            key, msg_content = msg.payload.split('.')

            if msg_content == 'Request':
                car_id,lane_id = key.split('_')
                if (car_id != self.car_id) and ((self.isWaiting or self.isPassing) and (lane_id != self.compatible_lane or lane_id == self.lane_id)) :
                    for (k,k_l) in self.hl:
                        if (k_l == lane_id or str(((int(k_l)+1)%4)+1) == lane_id) and self.cnt_pmp<TH:
                            self.hl.append((car_id,lane_id))
                            self.cnt_pmp += 1
                            break
                    else:
                        if (self.car_id < car_id):
                            self.ll.append((car_id,lane_id))
                            print(self.car_id+'_'+self.lane_id+'_'+car_id+'_'+lane_id+'.Reject')
                            self.mqtt_client.publish(self.mqtt_topic, self.car_id+'_'+self.lane_id+'_'+car_id+'_'+lane_id+'.Reject')

            if msg_content == 'Reject':
                src,src_lane_id,dst,dst_lane_id = key.split('_')
                if self.isWaiting:
                    if dst == self.car_id:
                        self.timer.cancel()
                        self.hl.append((src,src_lane_id))
                    else:
                        if (dst,dst_lane_id) in self.hl and \
                            (self.lane_id==src_lane_id or src_lane_id==self.compatible_lane or \
                            ((src,src_lane_id) not in self.hl)):
                            self.hl.remove((dst,dst_lane_id))
                            print(self.car_id+'_'+self.lane_id+'_'+dst+'_'+dst_lane_id+'.Reject')
                            self.mqtt_client.publish(self.mqtt_topic, self.car_id+'_'+self.lane_id+'_'+dst+'_'+dst_lane_id+'.Reject')
                        
            if msg_content == 'Permit':
                src,src_lane_id = key.split('_')
                if src != self.car_id:
                    if (src,src_lane_id) in self.hl:
                        self.hl.remove((src,src_lane_id))
                        self.before_critical_section()

            if msg_content == 'Follow':
                src, src_l, flt = key.split('_')
                if src != self.car_id:
                    flt = flt.split(',')
                    flt = map(lambda x:tuple(x.split('-')), flt)
                    if (self.car_id,self.lane_id) in flt:
                        self.isPassing = True
                        if (self.car_id,self.lane_id) == flt[-1]:
                            self.isLast = True
                        self.enter_critical_section()
                    elif src_l != self.compatible_lane:
                        if (src,src_l) in self.hl:
                            self.hl.remove((src,src_l))
                        for v in flt:
                            if v in self.hl:
                                self.hl.remove(v)
                            if v in self.ll:
                                self.ll.remove(v)
                        self.hl.append(flt[-1])
        # print('After hl: {}'.format(self.hl))
        # print('After ll: {}'.format(self.ll))

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

    # Car specific functions
    def broadcast_request(self):
        print(self.car_id+'_'+self.lane_id+'.Request')
        self.mqtt_client.publish(self.mqtt_topic, self.car_id+'_'+self.lane_id+'.Request')
        self.isBroadcast = True
        self.isWaiting = True
        self.timer.start()

    def timeout_handler(self):
        print('Time out')
        self.before_critical_section()

    def before_critical_section(self):
        if self.hl == []:
            self.isPassing = True
            if len(self.ll) == 0:
                self.isLast = True
            else:    
                flt = self.car_id + '_'+self.lane_id + '_'
                n = min(len(self.ll),NF)
                i = 0
                del_indeces = []
                while i<n:
                    f, f_l = self.ll[i] 
                    if f_l == self.lane_id:
                        flt += f+'-'+f_l+','
                        del_indeces.append(i)
                    i += 1
                flt = flt[:-1]       # remove extra ','
                for i in del_indeces:
                    self.ll.pop(i)
                print(flt+'.Follow')
                self.mqtt_client.publish(self.mqtt_topic, flt+'.Follow')
            self.enter_critical_section()

    def enter_critical_section(self):
        print('Enter Critical Section')
        time.sleep(3)
        print('Exiting Critical Section')
        if self.isLast:
            print(self.car_id+'_'+self.lane_id+'.Permit')
            self.mqtt_client.publish(self.mqtt_topic, self.car_id+'_'+self.lane_id+'.Permit')
        print('Done')
        self.isDone = True


def main():
    arr = sys.argv
    if  len (arr) != 3 :
        print ('Please enter valid input, e.g. python car.py <car_id> <lane_id>')
        sys.exit(1)
    if arr[2] not in '1234' or len(arr[2]) > 1:
        print ('Please enter valid lane id between 1 to 4')
        sys.exit(1)
    Car(arr[1], arr[2])
    while True:
        time.sleep(10)

main()