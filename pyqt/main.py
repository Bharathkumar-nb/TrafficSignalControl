import sys, os, time
from PyQt5 import QtCore, QtGui, QtWidgets
from signal_layout import Ui_MainWindow

class TrafficSignal(QtWidgets.QMainWindow):
    """docstring for TrafficSignal"""
    def __init__(self, parent = None):
        QtWidgets.QWidget.__init__(self, parent)
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)

        # Init member variables
        self.next_car_id = 0
        self.cars = {}
        self.slots = {}
        self.slots['l1'] = [[(5,3),False], [(4,3),False]]
        self.slots['l2'] = [[(2,5),False], [(2,4),False]]
        self.slots['l3'] = [[(0,2),False], [(1,2),False]]
        self.slots['l4'] = [[(3,0),False], [(3,1),False]]
        self.CRITICAL_SECTION = [(2,2),(2,3),(3,2),(3,3)]

        # Setup callback fuctions
        self.ui.l1_right_turn.mouseReleaseEvent = self.init_car_l1_r
        self.ui.l2_right_turn.mouseReleaseEvent = self.init_car_l2_r
        self.ui.l3_right_turn.mouseReleaseEvent = self.init_car_l3_r
        self.ui.l4_right_turn.mouseReleaseEvent = self.init_car_l4_r
        self.ui.l1_straight.mouseReleaseEvent = self.init_car_l1_s
        self.ui.l2_straight.mouseReleaseEvent = self.init_car_l2_s
        self.ui.l3_straight.mouseReleaseEvent = self.init_car_l3_s
        self.ui.l4_straight.mouseReleaseEvent = self.init_car_l4_s

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
        self.init_car(src, dst, 'l1')

    def init_car_l2_s(self, event):
        src, success = self.get_src(0, 1, 'l2')
        if not success:
            return
        dst = (2,0)
        self.init_car(src, dst, 'l2')

    def init_car_l3_s(self, event):
        src, success = self.get_src(-1, 0, 'l3')
        if not success:
            return
        dst = (5,2)
        self.init_car(src, dst, 'l3')

    def init_car_l4_s(self, event):
        src, success = self.get_src(0, -1, 'l4')
        if not success:
            return
        dst = (3,5)
        self.init_car(src, dst, 'l4')

    def init_car_l1_r(self, event):
        src, success = self.get_src(1, 0, 'l1')
        if not success:
            return
        dst = (3,5)
        self.init_car(src, dst, 'l1')

    def init_car_l2_r(self, event):
        src, success = self.get_src(0, 1, 'l2')
        if not success:
            return
        dst = (0,3)
        self.init_car(src, dst, 'l2')

    def init_car_l3_r(self, event):
        src, success = self.get_src(-1, 0, 'l3')
        if not success:
            return
        dst = (2,0)
        self.init_car(src, dst, 'l3')
        
    def init_car_l4_r(self, event):
        src, success = self.get_src(0, -1, 'l4')
        if not success:
            return
        dst = (5,2)
        self.init_car(src, dst, 'l4')

    def init_car(self, src, dst, lane):
        # update UI
        imagepath = os.path.join(os.getcwd(), 'maruti.jpg')
        pixmap = QtGui.QPixmap(imagepath)
        widget = self.ui.gridLayout.itemAtPosition(src[0],src[1]).widget()
        widget.setPixmap(pixmap)
        # update dictionary
        car_id = self.next_car_id
        self.next_car_id += 1
        self.cars[car_id] = [src, dst, lane]
        # create process
        cmds = 'python Car.py {} {}'.format(car_id, lane)
        self.cross_critical_section(car_id)

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
        imagepath = os.path.join(os.getcwd(), 'maruti.jpg')
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

        # 3. sleep
        QtWidgets.QApplication.processEvents()
        time.sleep(4)

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
            while src!=dst :
                print('L2 and L4 (straight)', src, dst)
                self.move_car(src, offset_x, offset_y, lane)
                src = src[0]+offset_x, src[1]+offset_y
                if src in self.CRITICAL_SECTION:
                    entered_critical_section = True
                elif entered_critical_section and not exited_critical_section:
                    print('Exiting Critical Section')
                    exited_critical_section = True
        if src==dst:
            return

        # L1 and L3 (straight)
        if src[1]==dst[1]:
            if src[0] in [0,1]:  # L3
                offset_x = 1
            else:                # L1
                offset_x = -1
            while src!=dst :
                print('L1 and L3 (straight)', src, dst)
                self.move_car(src, offset_x, offset_y, lane)
                src = src[0]+offset_x, src[1]+offset_y
                if src in self.CRITICAL_SECTION:
                    entered_critical_section = True
                elif entered_critical_section and not exited_critical_section:
                    exited_critical_section = True
                    print('Exiting Critical Section')
        if src==dst:
            return

        # L2 and L4 (right turn)
        if src[0] in [2,3]:
            # [Proceed until right turn]
            if src[1] in [0,1]: # L4
                offset_y = 1
            else:               # L2
                offset_y = -1
            while src[1] != dst[1]:
                print('L2 and L4 (before right turn)', src, dst)
                self.move_car(src, offset_x, offset_y, lane)
                src = src[0]+offset_x, src[1]+offset_y
            # [After making right turn]
            offset_y = 0
            if dst[0] in [0,1]: # L2
                offset_x = -1
            else:               # L4
                offset_x = 1
            while src!=dst :
                print('L2 and L4 (after right turn)', src, dst)
                self.move_car(src, offset_x, offset_y, lane)
                src = src[0]+offset_x, src[1]+offset_y
                if not exited_critical_section and src not in self.CRITICAL_SECTION:
                    exited_critical_section = True
                    print('Exiting Critical Section')

        # L1 and L3 (right)
        else:
            # [Proceed until right turn]
            if src[0] in [0,1]: # L3
                offset_x = 1
            else:               # L1
                offset_x = -1
            while src[0] != dst[0]:
                print('L1 and L3 (before right turn)', src, dst)
                self.move_car(src, offset_x, offset_y, lane)
                src = src[0]+offset_x, src[1]+offset_y
            # [After making right turn]
            offset_x = 0
            if dst[1] in [0,1]: # L3
                offset_y = -1
            else:               # L1
                offset_y = 1
            while src!=dst :
                print('L1 and L3 (after right turn)', src, dst)
                self.move_car(src, offset_x, offset_y, lane)
                src = src[0]+offset_x, src[1]+offset_y
                if not exited_critical_section and src not in self.CRITICAL_SECTION:
                    exited_critical_section = True
                    print('Exiting Critical Section')




if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)
    myapp = TrafficSignal()
    myapp.show()
    sys.exit(app.exec_())