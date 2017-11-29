import sys, os, time
import functools
import socket
import signal
import paho.mqtt.client as paho
import subprocess
from datetime import datetime as dt
from PyQt5 import QtCore, QtGui, QtWidgets
from signal_layout import Ui_MainWindow
from Car import Car
import thread

class TrafficSignal(QtWidgets.QMainWindow):
    """docstring for TrafficSignal"""
    def __init__(self, parent = None):
        QtWidgets.QWidget.__init__(self, parent)
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)

        # Init member variables
        self.next_car_id = '1'
        self.cars = {}
        self.slots = {}
        self.slots['l1'] = [[(5,3),False], [(4,3),False]]
        self.slots['l2'] = [[(2,5),False], [(2,4),False]]
        self.slots['l3'] = [[(0,2),False], [(1,2),False]]
        self.slots['l4'] = [[(3,0),False], [(3,1),False]]
        self.CRITICAL_SECTION = [(2,2),(2,3),(3,2),(3,3)]
        # car_direction is used for images
        self.car_direction = {(-1,0):'up', (1,0):'down', (0,-1):'left', (0,1):'right'}

        # Setup callback fuctions
        self.ui.l1_right_turn.mouseReleaseEvent = self.init_car_l1_r
        self.ui.l2_right_turn.mouseReleaseEvent = self.init_car_l2_r
        self.ui.l3_right_turn.mouseReleaseEvent = self.init_car_l3_r
        self.ui.l4_right_turn.mouseReleaseEvent = self.init_car_l4_r
        self.ui.l1_straight.mouseReleaseEvent = self.init_car_l1_s
        self.ui.l2_straight.mouseReleaseEvent = self.init_car_l2_s
        self.ui.l3_straight.mouseReleaseEvent = self.init_car_l3_s
        self.ui.l4_straight.mouseReleaseEvent = self.init_car_l4_s

        # setup MQTT and register MQTT callback functions
        self.mqtt_client = paho.Client()
        self.mqtt_client.on_connect = self.on_connect
        self.mqtt_client.on_message = self.on_message
        self.mqtt_client.on_disconnect = self.on_disconnect
        self.mqtt_client.on_log = self.on_log
        self.mqtt_topic = 'TrafficSignalControl/' + 'gui'
        self.mqtt_client.will_set(self.mqtt_topic, '______________Will of GUI _________________\n\n', 0, False)
        self.mqtt_client.connect('sansa.cs.uoregon.edu', '1883',keepalive=300)
        self.mqtt_client.subscribe('TrafficSignalControl/' + 'car')
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
            car_id, msg_content = msg.payload.split('.')
            if msg_content == 'Enter':
                print('Received: {}'.format(msg.payload))
                thread.start_new_thread(self.cross_critical_section, (car_id,))

    def on_disconnect(self, client, userdata, rc):
        self.mqtt_client.loop_stop()  # waits until DISCONNECT message is sent out
        print ("Exit")
        sys.exit(0)

    def on_log(self, client, userdata, level, buf):
        pass
        #print("log: {}".format(buf)) # only semi-useful IMHO

    def get_src(self, offset_x, offset_y, lane):
        x, y = 0, 0
        index = -1
        success = True
        for i in range(len(self.slots[lane])):
            slot, isOccupied = self.slots[lane][i]
            if not isOccupied:
                x, y = slot
                index = i
        if (x,y)==(0,0):
            success = False
        else:
            self.slots[lane][index][1] = True
        return ((x,y), success)

    def init_car_l1_s(self, event):
        src, success = self.get_src(1, 0, 'l1')
        if not success:
            return
        dst = (0,3)
        self.init_car(src, dst, 'l1','up')

    def init_car_l2_s(self, event):
        src, success = self.get_src(0, 1, 'l2')
        if not success:
            return
        dst = (2,0)
        self.init_car(src, dst, 'l2', 'left')

    def init_car_l3_s(self, event):
        src, success = self.get_src(-1, 0, 'l3')
        if not success:
            return
        dst = (5,2)
        self.init_car(src, dst, 'l3', 'down')

    def init_car_l4_s(self, event):
        src, success = self.get_src(0, -1, 'l4')
        if not success:
            return
        dst = (3,5)
        self.init_car(src, dst, 'l4', 'right')

    def init_car_l1_r(self, event):
        src, success = self.get_src(1, 0, 'l1')
        if not success:
            return
        dst = (3,5)
        self.init_car(src, dst, 'l1', 'up')

    def init_car_l2_r(self, event):
        src, success = self.get_src(0, 1, 'l2')
        if not success:
            return
        dst = (0,3)
        self.init_car(src, dst, 'l2', 'left')

    def init_car_l3_r(self, event):
        src, success = self.get_src(-1, 0, 'l3')
        if not success:
            return
        dst = (2,0)
        self.init_car(src, dst, 'l3', 'down')
        
    def init_car_l4_r(self, event):
        src, success = self.get_src(0, -1, 'l4')
        if not success:
            return
        dst = (5,2)
        self.init_car(src, dst, 'l4', 'right')

    def init_car(self, src, dst, lane, direction):
        # update UI
        imagepath = os.path.join(os.getcwd(), 'images', direction+'.jpg')
        pixmap = QtGui.QPixmap(imagepath)
        widget = self.ui.gridLayout.itemAtPosition(src[0],src[1]).widget()
        widget.setPixmap(pixmap)
        # update dictionary
        car_id = self.next_car_id
        self.next_car_id = str(int(self.next_car_id)+1)
        self.cars[car_id] = [src, dst, lane]
        # create process
        print('Starting Car:{} Lane:{}'.format(car_id, lane[-1]))
        thread.start_new_thread(self.start_car, (car_id, lane[-1]))

    def start_car(self, car_id, lane):
        car = Car(car_id, lane)
        while not car.isDone:
            time.sleep(10)
        print('Terminating thread. Car:{} Lane:{}'.format(car_id, lane))       

    ### Functions to update GUI after receiving Enter message
    ### These functions are run in seperate threads

    def delete_slot(self, pos, lane):
        for i in range(len(self.slots[lane])):
            slot, isOccupied = self.slots[lane][i]
            if slot == pos:
                self.slots[lane][i][1] = False
                break

    def add_slot(self, pos, lane):
        for i in range(len(self.slots[lane])):
            slot, isOccupied = self.slots[lane][i]
            if slot == pos:
                self.slots[lane][i][1] = True
                break

    def move_car(self, src, offset_x, offset_y, lane):
        # update UI
        direction = self.car_direction[(offset_x, offset_y)]
        imagepath = os.path.join(os.getcwd(), 'images', direction+'.jpg')
        # 1. Clear image in current cell
        x, y = src[0],src[1]
        pixmap = QtGui.QPixmap('')
        widget = self.ui.gridLayout.itemAtPosition(x, y).widget()
        widget.setPixmap(pixmap)
        # Make slots available to other cars
        self.delete_slot((x,y), lane)
        
        # 2. Set image in next cell
        pixmap = QtGui.QPixmap(imagepath)
        next_x, next_y = x+offset_x, y+offset_y

        widget = self.ui.gridLayout.itemAtPosition(next_x, next_y).widget()
        widget.setPixmap(pixmap)
        # Occupy the next slot
        self.add_slot((next_x, next_y), lane)

    def clear_car(self, pos, car_id):
        pixmap = QtGui.QPixmap('')
        widget = self.ui.gridLayout.itemAtPosition(pos[0], pos[1]).widget()
        widget.setPixmap(pixmap)

    def straight(self, car_id, offset_x, offset_y, entered_critical_section, exited_critical_section):
        src, dst, lane = self.cars[car_id]
        if src == dst:
            time.sleep(1)
            self.clear_car(dst, car_id)
            return
        self.move_car(src, offset_x, offset_y, lane)
        self.cars[car_id][0] = (src[0]+offset_x, src[1]+offset_y)
        if src in self.CRITICAL_SECTION:
            entered_critical_section = True
        elif entered_critical_section and not exited_critical_section:
            print('Exiting Critical Section')
            print(car_id+'.Exit')
            self.mqtt_client.publish(self.mqtt_topic, car_id+'.Exit')
            exited_critical_section = True
        time.sleep(1)
        self.straight(car_id, offset_x, offset_y, entered_critical_section, exited_critical_section)    

    def right_phase1(self, car_id, offset_x, offset_y, index):
        src, dst, lane = self.cars[car_id]
        if src[index] != dst[index]:
            self.move_car(src, offset_x, offset_y, lane)
            self.cars[car_id][0] = (src[0]+offset_x, src[1]+offset_y)
            time.sleep(1)
            self.right_phase1(car_id, offset_x, offset_y, index)
        else:
            # Phase 1 is done. Move straight from now on
            offset_x, offset_y = 0, 0
            entered_critical_section = True
            exited_critical_section = False
            index = 0 if index==1 else 1
            if dst[index] in [0,1]:
                if index == 0:
                    offset_x = -1
                else:
                    offset_y = -1
            else:
                if index == 0:
                    offset_x = 1
                else:
                    offset_y = 1
            self.straight(car_id, offset_x, offset_y, entered_critical_section, exited_critical_section)

    def cross_critical_section(self, car_id):
        src, dst, lane = self.cars[car_id]
        offset_x, offset_y = 0, 0
        entered_critical_section = False
        exited_critical_section = False

        # L2 and L4 (straight)
        if src[0]==dst[0]:
            if src[1] in [0,1]:  # L4
                offset_y = 1
            else:                # L2
                offset_y = -1
            time.sleep(1)
            self.straight(car_id, offset_x, offset_y, entered_critical_section, exited_critical_section)

        # L1 and L3 (straight)
        elif src[1]==dst[1]:
            if src[0] in [0,1]:  # L3
                offset_x = 1
            else:                # L1
                offset_x = -1
            time.sleep(1)
            self.straight(car_id, offset_x, offset_y, entered_critical_section, exited_critical_section)

        # L2 and L4 (right turn)
        elif src[0] in [2,3]:
            # [Proceed until right turn]
            if src[1] in [0,1]: # L4
                offset_y = 1
            else:               # L2
                offset_y = -1
            time.sleep(1)
            self.right_phase1(car_id, offset_x, offset_y, 1)
        # L1 and L3 (right)
        else:
            # [Proceed until right turn]
            if src[0] in [0,1]: # L3
                offset_x = 1
            else:               # L1
                offset_x = -1
            time.sleep(1)
            self.right_phase1(car_id, offset_x, offset_y, 0)

if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)
    myapp = TrafficSignal()
    myapp.show()
    sys.exit(app.exec_())