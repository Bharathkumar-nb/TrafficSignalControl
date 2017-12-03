import sys, os, time, math
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
import matplotlib.pyplot as plt
import matplotlib.animation as animation

class Monitor(object):
    """docstring for Monitor"""
    def __init__(self):

        # Realtime graph variables init
        self.x_axis_cars_in_CS = []
        self.y_axis_cars_in_CS = []
        self.y_axis_waiting_time = []
        self.x_axis_waiting_time = []
        self.counter_1 = 0
        self.counter_2 = 0
        self.cars = {}
        self.WINDOW = 20

        # setup MQTT and register MQTT callback functions
        self.mqtt_client = paho.Client()
        self.mqtt_client.on_connect = self.on_connect
        self.mqtt_client.on_message = self.on_message
        self.mqtt_client.on_disconnect = self.on_disconnect
        self.mqtt_client.on_log = self.on_log
        self.mqtt_topic = 'TrafficSignalControl/' + 'monitor'
        self.mqtt_client.will_set(self.mqtt_topic, '______________Will of GUI _________________\n\n', 0, False)
        self.mqtt_client.connect('sansa.cs.uoregon.edu', '1883',keepalive=300)
        self.mqtt_client.subscribe([('TrafficSignalControl/gui', 0), ('TrafficSignalControl/car', 0)])
        self.mqtt_client.loop_start()

        self.init_graph()

    # MQTT callback functions
    def on_connect(self, client, userdata, flags, rc):
        pass
    
    def on_message(self, client, userdata, msg):
        if len(msg.payload.split('.')) > 1:
            key, msg_content = msg.payload.split('.')
            if msg_content == 'Count':
                car_count = key
                if len(self.x_axis_cars_in_CS)>self.WINDOW:
                    self.x_axis_cars_in_CS.pop(0)
                    self.y_axis_cars_in_CS.pop(0)
                self.x_axis_cars_in_CS.append(self.counter_1)
                self.y_axis_cars_in_CS.append(int(car_count))
                self.counter_1 += 1
            if msg_content == 'Request':
                car_id,lane_id,timestamp = key.split('_')
                self.cars[car_id] = [self.counter_2, -1, 0]
            if msg_content == 'Enter':
                car_id = key
                self.cars[car_id][1] = self.counter_2
            if msg_content == 'Exit':
                car_id = key
                print(car_id, self.cars)
                self.cars[car_id][2] = self.counter_2
                


    def on_disconnect(self, client, userdata, rc):
        self.mqtt_client.loop_stop()  # waits until DISCONNECT message is sent out
        print ("Exit")
        sys.exit(0)

    def on_log(self, client, userdata, level, buf):
        pass
        #print("log: {}".format(buf)) # only semi-useful IMHO

    def update_avg_waiting_time(self, frameno, ax1, y_0, y_1):
        self.counter_2 += 1
        total = 0
        count = 0
        for (s,e,i) in self.cars.values():
            if e>0:
                total += e-s
                count += 1
        if len(self.x_axis_waiting_time)>self.WINDOW:
            self.x_axis_waiting_time.pop(0)
            self.y_axis_waiting_time.pop(0)
        self.x_axis_waiting_time.append(self.counter_1)
        self.y_axis_waiting_time.append(total/count if count>0 else 0)

        for key in self.cars.keys():
            exit_time = self.cars[key][2]
            if self.counter_2 - exit_time > (5*self.WINDOW):
                print('del', key)
                del self.cars[key]
        self.animate(frameno, ax1, self.x_axis_waiting_time, self.y_axis_waiting_time, y_0, y_1)


    # Graph Functions
    def animate(self, frameno, ax1, x_axis, y_axis, y_0, y_1):
        start = 0
        end = self.WINDOW
        if len(x_axis)>0:
            start = x_axis[0]
            end = max(end, x_axis[-1])
        ax1.set_xticks([i for i in range(start, end+1)])
        ax1.set_yticks([i for i in range(y_0, y_1+1)])
        ax1.set_xlim([start, end])
        ax1.set_ylim([y_0, y_1])
        # ax = plt.gca()
        # ax.autoscale(False)
        ax1.autoscale(False)
        ax1.plot(x_axis, y_axis, '-')


    def init_graph(self):
        fig = plt.figure(figsize=(8,8))
        ax1 = fig.add_subplot(211)
        ax1.set_xlabel('Time')
        ax1.set_ylabel('No of Cars in CS', color='g')

        ax2 = fig.add_subplot(212)        
        ax2.set_xlabel('Time')
        ax2.set_ylabel('Avg wait time', color='b')

        ani1 = animation.FuncAnimation(fig, self.update_avg_waiting_time,  fargs=(ax2, 0, 10), blit=False, interval=1000, repeat=True)
        ani2 = animation.FuncAnimation(fig, self.animate,  fargs=(ax1, self.x_axis_cars_in_CS, self.y_axis_cars_in_CS, 0, 5), blit=False, interval=1000, repeat=True)

        ax1.autoscale(False)
        ax2.autoscale(False)
        plt.show()


if __name__ == '__main__':
    monitor = Monitor()
    # while True:
    #     time.sleep()