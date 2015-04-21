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

import Gnuplot

# Global values for accelometer
accelvaluesX = []
accelvaluesY = []
accelvaluesZ = []

# Global key for threads
key = ""

# Global value for current and target altitude
current_alt = 0
alt_init = 0.8
alt_inc = 1
target_alt = 0
hold_mode = False






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
    This class is a basic thread for reading the keyboard
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
        Initialize the quad copter
        """
        # Log file for Accelerometer
        self.f1 = open('Accelerometer_log.txt', 'w')
        # Log file for Pitch Roll Yaw
        self.f2 = open('Stabalizer_log.txt', 'w')
        # Log file for altitude
        self.f3 = open('Barometer_log.txt', 'w')

        # write data into the log files
        self.f1.write('Accelerometer log\n {date} {acc.x} {acc.y} {acc.z}\n')
        self.f2.write('Stabilizer log\n{date} {Roll} {Pitch} {Yaw} {Thrust}\n')
        self.f3.write('Barometer log\n {data} {ASL}\n')

        # get the Unix time
        self.starttime = time.time() * 1000.0
        self.date = time.time() * 1000.0 - self.starttime

        # Initialize the crazyflie and get the drivers ready
        self.crazyflie = cflib.crazyflie.Crazyflie()
        print 'Initializing drivers'
        cflib.crtp.init_drivers()

        # Start scanning available devices
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
        self.logBaro = LogConfig("Baro", 200)
        self.logBaro.add_variable("baro.aslLong", "float")
        self.crazyflie.log.add_config(self.logBaro)
        if  self.logBaro.valid:
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

        # Start another thread and doing control function call
        print "log for debugging: before start increasing_step"

        # Thread(target=self.increasing_step).start()
        # Thread(target=self.recursive_step).start()

        Thread(target=self.init_alt).start()




    def print_baro_data(self, ident, data, logconfig):
        # Output the Barometer data

        #logging.info("Id={0}, Barometer: asl={1:.4f}".format(ident, data["baro.aslLong"]))

        # Get the Current altitude and put it in the global var
        global current_alt
        current_alt = data["baro.aslLong"]

        # The Target Altitude = Current + init
        global target_alt
        global alt_init
        # Use a temp var to hold the value of target
        target = round(current_alt) + alt_init
        # if the target did not initialized then initialize it
        if target_alt == 0:
            target_alt = target

        # system output the time and the altitude, each id represents a time slice in Unix
        date = time.time() * 1000.0 - self.starttime
        sys.stdout.write('Id={0}, Baro: baro.aslLong{1:.4f}\r\n'.format(ident, data["baro.aslLong"]))
        self.f3.write('{} {}\n'.format(date, data["baro.aslLong"]))

        pass

    def print_stab_data(self, ident, data, logconfig):
        # Output the stablizer data (roll pith yaw)

        sys.stdout.write('Id={0}, Stabilizer: Roll={1:.2f}, Pitch={2:.2f}, Yaw={3:.2f}, Thrust={4:.2f}\r'.format(ident, data["stabilizer.roll"], data["stabilizer.pitch"], data["stabilizer.yaw"], data["stabilizer.thrust"]))
        # print('Id={0}, Stabilizer: Roll={1:.2f}, Pitch={2:.2f}, Yaw={3:.2f}, Thrust={4:.2f}\r'.format(ident, data["stabilizer.roll"], data["stabilizer.pitch"], data["stabilizer.yaw"], data["stabilizer.thrust"]))
        self.f2.write('{} {} {} {} {}\n'.format(self.date, data["stabilizer.roll"], data["stabilizer.pitch"], data["stabilizer.roll"], data["stabilizer.pitch"], data["stabilizer.yaw"], data["stabilizer.thrust"]))


    def print_accel_data(self, ident, data, logconfig):
        # Output the accelerometer data

        # global variables that holds x,y,z value
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

    def init_alt(self):

        #global current_alt
        global target_alt
        global current_alt


        current_temp = current_alt
        target_temp = target_alt
        if current_temp != 0:
            print "- current_temp" + str(current_temp)
            print "- target_temp" + str(target_temp)

        # If the current = target then hold the altitude by using the build-in function althold
        if round(current_temp, 1) == target_temp:
            if current_temp != 0:
                sys.stdout.write("Now, current and target altitude is same, Let's hover!\r\n")
            self.crazyflie.param.set_value("flightmode.althold", "True")
        #the althold will last 4 second and then we set the thrust to 32767 which is the value that will hover
            self.crazyflie.commander.send_setpoint(0, 0, 0, 32767)

            return self.init_alt()

        # If the current < target the thrust up gain altitude
        # round function change float value to int
        elif round(current_temp, 3) < target_temp:
            sys.stdout.write("Current alt is lower than target value, Let's go up!\r\n")
            self.crazyflie.commander.send_setpoint(0, 0, 0, 45000)
            #for bandwidth reason, the command need to be delayed
            time.sleep(0.2)

            return self.init_alt()

        # If the current > target the thrust down lose altitude
        elif round(current_temp, 3) > target_temp:
            sys.stdout.write("Current alt is higher than target value, Let's go down!\r\n")
            self.crazyflie.commander.send_setpoint(0, 0, 0, 32000)
            #for bandwidth reason, the command need to be delayed
            time.sleep(0.2)

            return self.init_alt()






    # Start the program
TestFlight()
