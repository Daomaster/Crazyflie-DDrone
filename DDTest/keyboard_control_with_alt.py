#!/usr/bin/python



import time
import sys
import tty
import termios
import argparse

sys.path.append("../lib")

import cflib
from cflib.crazyflie import Crazyflie

from cfclient.utils.logconfigreader import LogConfig
from cfclient.utils.logconfigreader import LogVariable
from threading import Thread, Event
from datetime import datetime

#import Gnuplot

# Global values for accelometer
accelvaluesX = []
accelvaluesY = []
accelvaluesZ = []

# Global key for threads
key = ""

# Global value for current and target altitude
current_alt = 0
target_alt = 650





class _GetchUnix:
    """
    Class to get keys from the keyboard without pressing Enter.
    """
    def __init__(self):
        pass
    def __call__(self):
        fd = sys.stdin.fileno()
        old_settings = termios.tcgetattr(fd)
        try:
            tty.setraw(sys.stdin.fileno())
            ch = sys.stdin.read(1)
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
        return ch



class KeyReaderThread(Thread):
    """
    This class is a basic thread for reading the keyboard continously
    """
    def __init__(self):
        """
        Initialize the thread
        """
        Thread.__init__(self)

    def run(self):
        """
        Read the keyboard and store the value in variable key
        """
        global key
        getch = _GetchUnix()
        key = getch()
        while key != "e":
            key = getch()
            time.sleep(0.1)



class TestFlight:

    def __init__(self):
        """
        Initialize the quadcopter
        """
        self.f1 = open('Accelerometer_log.txt', 'w')
        self.f2 = open('Stabalizer_log.txt', 'w')
        self.f3 = open('Barometer_log.txt', 'w')


        self.f1.write('Accelerometer log\n {date} {acc.x} {acc.y} {acc.z}\n')
        self.f2.write('Stabilizer log\n{date} {Roll} {Pitch} {Yaw} {Thrust}\n')
        self.f3.write('Barometer log\n {data} {ASL}\n')


        self.starttime = time.time()*1000.0
        self.date = time.time()*1000.0 - self.starttime

        self.crazyflie = cflib.crazyflie.Crazyflie()
        print 'Initializing drivers'
        cflib.crtp.init_drivers()

        print 'Searching for available devices'
        available = cflib.crtp.scan_interfaces()

        radio = False
        for i in available:
            # Connect to the first device of the type 'radio'
            if 'radio' in i[0]:
                radio = True
                dev = i[0]
                print 'Connecting to interface with URI [{0}] and name {1}'.format(i[0], i[1])
                self.crazyflie.open_link("radio://0/80/250K")
                ## radio://0/80/250K is most well connected radio frequency
                # Heungseok Park, 4.9.2015
                #self.crazyflie.open_link(dev)

                break

        if not radio:
            print 'No quadcopter detected. Try to connect again.'
            exit(-1)

        # Set up the callback when connected
        self.crazyflie.connected.add_callback(self.connectSetupFinished)


    def connectSetupFinished(self, linkURI):
        """
        Set the loggers
        """

        """
        # Log stabilizer
        self.logStab = LogConfig("Stabalizer", 200)
        self.logStab.add_variable("stabilizer.roll", "float")
        self.logStab.add_variable("stabilizer.pitch", "float")
        self.logStab.add_variable("stabilizer.yaw", "float")
        self.logStab.add_variable("stabilizer.thrust", "uint16_t")

        self.crazyflie.log.add_config(self.logStab)

        if self.logStab.valid:
            self.logStab.data_received_cb.add_callback(self.print_stab_data)
            self.logStab.start()
        else:
            print 'Could not setup log configuration for stabilizer after connection!'

        """

        # Log barometer
        # we use only barometer value(ASL Value) to control altitude
        # Heungseok Park, 4.9.2015

        self.logBaro = LogConfig("Baro", 200)
        self.logBaro.add_variable("baro.aslLong", "float")

        self.crazyflie.log.add_config(self.logBaro)
        if self.logBaro.valid:
            self.logBaro.data_received_cb.add_callback(self.print_baro_data)
            self.logBaro.start()
        else:
            print 'Could not setup log configuration for barometer after connection!'




        """
        # Log Accelerometer
        self.logAccel = LogConfig("Accel",200)
        self.logAccel.add_variable("acc.x", "float")
        self.logAccel.add_variable("acc.y", "float")
        self.logAccel.add_variable("acc.z", "float")

        self.crazyflie.log.add_config(self.logAccel)

        if self.logAccel.valid:
            self.logAccel.data_received_cb.add_callback(self.print_accel_data)
            self.logAccel.start()
        else:
            print 'Could not setup log configuration for accelerometer after connection!'

        """

        print "log for debugging: before start increasing_step"
        Thread(target=self.increasing_step).start()






    def print_baro_data(self, ident, data, logconfig):
        # function to log CF's barometer data.

        #logging.info("Id={0}, Barometer: asl={1:.4f}".format(ident, data["baro.aslLong"]))
        # global
        global current_alt
        current_alt = data["baro.aslLong"]

        date = time.time()*1000.0 - self.starttime
        sys.stdout.write('Id={0}, Baro: baro.aslLong{1:.4f}\r\n'.format(ident, data["baro.aslLong"]))
        self.f3.write('{} {}\n'.format(date, data["baro.aslLong"]))

        pass

    def print_stab_data(self, ident, data, logconfig):
        sys.stdout.write('Id={0}, Stabilizer: Roll={1:.2f}, Pitch={2:.2f}, Yaw={3:.2f}, Thrust={4:.2f}\r'.format(ident, data["stabilizer.roll"], data["stabilizer.pitch"], data["stabilizer.yaw"], data["stabilizer.thrust"]))
        #print('Id={0}, Stabilizer: Roll={1:.2f}, Pitch={2:.2f}, Yaw={3:.2f}, Thrust={4:.2f}\r'.format(ident, data["stabilizer.roll"], data["stabilizer.pitch"], data["stabilizer.yaw"], data["stabilizer.thrust"]))
        self.f2.write('{} {} {} {} {}\n'.format(self.date, data["stabilizer.roll"], data["stabilizer.pitch"], data["stabilizer.roll"], data["stabilizer.pitch"], data["stabilizer.yaw"], data["stabilizer.thrust"]))


    def print_accel_data(self, ident, data, logconfig):
        global accelvaluesX
        global accelvaluesY
        global accelvaluesZ
        sys.stdout.write('Id={0}, Accelerometer: x={1:.2f}, y={2:.2f}, z={3:.2f}\r".format(ident, data["acc.x"], data["acc.y"], data["acc.z"]))')
        #print("Id={0}, Accelerometer: x={1:.2f}, y={2:.2f}, z={3:.2f}\n".format(ident, data["acc.x"], data["acc.y"], data["acc.z"]))

        self.f1.write('{} {} {} {}\n'.format(self.date, data["acc.x"], data["acc.y"], data["acc.z"]))

        #sys.stdout.write("Id={0}, Accelerometer: x={1:.2f}, y={2:.2f}, z={3:.2f}\r".format(ident, data["acc.x"], data["acc.y"], data["acc.z"]))
        #date = time.time()*1000.0 - self.starttime

        #small_array = []
        #small_array.append(date)
        #small_array.append(data["acc.x"])
        #small_array.append(data["acc.y"])
        #small_array.append(data["acc.z"])


        #accelvaluesX.append(small_array_x)
        #print(accelvaluesX)
        #print(accelvaluesY)
        #print(accelvaluesZ)



    def recursive_step(self, data):

        ## CF's recursive function call to hover itself
        ## 2015.10.4
        ## Heungseok Park.

        global current_alt
        global target_alt
        current_alt = data["baro.aslLong"]

        if(current_alt < target_alt):
            sys.stdout.write("Current alt is lower than target value, Let's go up!\r\n")
            self.crazyflie.commander.send_setpoint(0, 0, 0, 40000)
            return self.recursive_step(data)

        elif(current_alt > target_alt):
            sys.stdout.write("Currnet alt is higher than target value, Let's go down!\r\n")
            self.crazyflie.commander.send_setpoint(0, 0, 0, 30000)
            return self.recursive_step(data)

        elif(current_alt == target_alt):
            sys.stdout.write("Now, current and target altitude is same, Let's hover!\r\n")
            self.crazyflie.param.set_value("flightmode.althold", "False")
            return



    def increasing_step(self):

        # If you use global var, you need to modify global copy
        global key
        global accelvaluesX
        global accelvaluesY
        global accelvaluesZ
        global current_alt

        print(current_alt) # now, this will print 0

        # (blades start to rotate after 10000)

        start_alt = 640



        start_thrust = 21000
        min_thrust = 10000
        max_thrust = 60000
        thrust_increment = 3000

        flag = True



        start_roll = 0
        roll_increment = 30
        min_roll = -50
        max_roll = 50

        start_pitch = 0
        pitch_increment = 30
        min_pitch = -50
        max_pitch = 50

        start_yaw = 0
        yaw_increment = 30
        min_yaw = -200
        max_yaw = 200
        stop_moving_count = 0

        pitch = start_pitch
        roll = start_roll
        thrust = start_thrust
        yaw = start_yaw

        #unlock the thrust protection
        self.crazyflie.commander.send_setpoint(0,0,0,0)

        # Start the keyread thread
        keyreader = KeyReaderThread()
        keyreader.start()

        sys.stdout.write('\r\nCrazyflie Status\r\n')
        sys.stdout.write('================\r\n')
        sys.stdout.write("Use 'w' and 's' for the thrust, 'a' and 'd' for yaw, 'i' and 'k' for pitch and 'j' and 'l' for roll. Stop flying with 'q'. Exit with 'e'.\r\n")


        while key != "e":
            if key == 'q':
                thrust = 0
                pitch = 0
                roll = 0
                yaw = 0
                #g = Gnuplot.Gnuplot(debug=1)
                #g.title('A simple example') # (optional)
                #g('set data style line') # give gnuplot an arbitrary command
                # Plot a list of (x, y) pairs (tuples or a numpy array would
                # also be OK):
                #g.plot(accelvaluesX)


            elif key == 'w' and (thrust + thrust_increment <= max_thrust):
                thrust += thrust_increment
            elif key == 's' and (thrust - thrust_increment >= min_roll):
                thrust -= thrust_increment
            elif key == 'd' and (yaw + yaw_increment <= max_yaw):
                yaw += yaw_increment
                stop_moving_count = 0
            elif key == 'a' and (yaw - yaw_increment >= min_yaw):
                yaw -= yaw_increment
                stop_moving_count = 0
            elif key == 'l' and (roll + roll_increment <= max_roll):
                roll += roll_increment
                stop_moving_count = 0
            elif key == 'j' and (roll - roll_increment >= min_roll):
                roll -= roll_increment
                stop_moving_count = 0
            elif key == 'i' and (pitch + pitch_increment <= max_pitch):
                pitch += pitch_increment
                stop_moving_count = 0
            elif key == 'k' and (pitch - pitch_increment >= min_pitch):
                pitch -= pitch_increment
                stop_moving_count = 0
            elif key == 'h':
                ## 'h' is altitude hold mode, but did not working now
                if flag == True:
                    self.crazyflie.param.set_value("flightmode.althold", "True")
                    sys.stdout.write("althold mode\r\n")
                    flag = False
                else:
                    self.crazyflie.param.set_value("flightmode.althold", "False")
                    sys.stdout.write("standard mode\r\n")
                    flag = True

            elif key == 'x':
                # state. is x press or not?
                # read the barometer and remember
                # bar
                pass
            elif key == "":
                # The controls are not being touch, get back to zero roll, pitch and yaw
                if stop_moving_count >= 40:
                    pitch = 0
                    roll = 0
                    yaw = 0
                else:
                    stop_moving_count += 1
            else:
                pass
            key = ""
            self.crazyflie.commander.send_setpoint(roll, pitch, yaw, thrust)


        self.crazyflie.commander.send_setpoint(0,0,0,0)
        # Make sure that the last packet leaves before the link is closed
        # since the message queue is not flushed before closing
        self.crazyflie.close_link()

# X,Y accelerometer stabilization
# Store the x,y values


TestFlight()
