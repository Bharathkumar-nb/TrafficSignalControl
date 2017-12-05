import time, socket, sys
import paho.mqtt.client as paho
import threading

# constants
TH = 2
NF = 2
        
# t = None

class Car(object):
    """docstring for Car"""
    def __init__(self, car_id, lane_id):
        self.MY_NAME = 'Car : ' + car_id
        self.car_id = car_id
        self.lane_id = lane_id
        self.timer = threading.Timer(5.0, self.timeout_handler)
        self.compatible_lane = str(((int(self.lane_id)+1)%4)+1)
        self.cnt_pmp = 0
        self.isBroadcast = False
        self.isWaiting = False
        self.isPassing = False
        self.isLast = False
        self.isDone = False
        self.ll = []
        self.hl = []
        self.timestamp = str(int(time.time()*100))
        

        # setup MQTT and register MQTT callback functions
        self.mqtt_client = paho.Client()
        self.mqtt_client.on_connect = self.on_connect
        self.mqtt_client.on_message = self.on_message
        self.mqtt_client.on_disconnect = self.on_disconnect
        self.mqtt_client.on_log = self.on_log
        self.mqtt_topic = 'TrafficSignalControl/' + 'car'
        self.mqtt_client.will_set(self.mqtt_topic, '______________Will of '+self.MY_NAME+' _________________\n\n', 0, False)
        self.mqtt_client.connect('sansa.cs.uoregon.edu', '1883',keepalive=300)
        self.mqtt_client.subscribe('TrafficSignalControl/#')
        self.mqtt_client.loop_start()

        self.broadcast_request()
    
    # MQTT callback functions
    def on_connect(self, client, userdata, flags, rc):
        pass
    
    def on_message(self, client, userdata, msg):
        # print('on_message {}: {}'.format(self.car_id, msg.payload))
        print('Car: {} Before hl: {}'.format(self.car_id, self.hl))
        print('Car: {} Before ll: {}'.format(self.car_id, self.ll))
        if self.isDone:
            return
        if len(msg.payload.split('.')) > 1:
            key, msg_content = msg.payload.split('.')

            if msg_content == 'Request':
                car_id,lane_id,timestamp = key.split('_')
                if (car_id != self.car_id) and ((self.isWaiting or self.isPassing) and (lane_id != self.compatible_lane or lane_id == self.lane_id)) :
                    for (k,k_l) in self.hl:
                        if (k_l == lane_id or str(((int(k_l)+1)%4)+1) == lane_id) and self.cnt_pmp<TH:
                            self.hl.append((car_id,lane_id))
                            self.cnt_pmp += 1
                            break
                    else:
                        #if (self.car_id < car_id and (self.isPassing and self.isLast)):
                        #if (self.car_id < car_id):
                        if (self.timestamp < timestamp and ((self.isPassing and self.isLast) or self.isWaiting)):
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
                print(key)
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

            if msg_content == 'Exit':
                car_id = key
                if self.car_id == car_id:
                    print('Exiting Critical Section')
                    if self.isLast:
                        print(self.car_id+'_'+self.lane_id+'.Permit')
                        self.mqtt_client.publish(self.mqtt_topic, self.car_id+'_'+self.lane_id+'.Permit')
                    print('Done')
                    self.mqtt_client.disconnect()
                    
        print('Car: {} After hl: {}'.format(self.car_id, self.hl))
        print('Car: {} After ll: {}'.format(self.car_id, self.ll))

    def on_disconnect(self, client, userdata, rc):
        print('Disconnecting')
        self.isDone = True
        self.mqtt_client.loop_stop()

    def on_log(self, client, userdata, level, buf):
        pass
        #print("log: {}".format(buf)) # only semi-useful IMHO

    # Car specific functions
    def broadcast_request(self):
        print(self.car_id+'_'+self.lane_id+'_'+self.timestamp+'.Request')
        self.mqtt_client.publish(self.mqtt_topic, self.car_id+'_'+self.lane_id+'_'+self.timestamp+'.Request')
        self.isBroadcast = True
        self.isWaiting = True
        self.timer.start()

    def timeout_handler(self):
        print('Time out')
        self.before_critical_section()

    def before_critical_section(self):
        #print(self.car_id, self.hl)
        if self.hl == []:
            self.isPassing = True
            n = min(len(self.ll),NF)
            flt = self.car_id + '_'+self.lane_id + '_'
            i = 0
            del_indeces = []
            while i<n:
                f, f_l = self.ll[i] 
                if f_l == self.lane_id:
                    flt += f+'-'+f_l+','
                    del_indeces.append(i)
                i += 1
            flt = flt[:-1]       # remove extra ','
            if len(del_indeces)==0:
                self.isLast = True
            else:
                for i in del_indeces:
                    self.ll.pop(i)
                print(flt+'.Follow')
                self.mqtt_client.publish(self.mqtt_topic, flt+'.Follow')
            self.enter_critical_section()

    def enter_critical_section(self):
    	self.isWaiting = False
        print('Enter Critical Section')
        print(self.car_id+'.Enter')
        self.mqtt_client.publish(self.mqtt_topic, self.car_id+'.Enter')
