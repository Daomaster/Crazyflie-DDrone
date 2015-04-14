import time, sys
from threading import Thread


sys.path.append("../lib")
import cflib
from cflib.crazyflie import Crazyflie

import cflib.crtp
from cfclient.utils.logconfigreader import LogConfig

import logging

logging.basicConfig(level=logging.ERROR)

class Main:

    # Initial values, you can use these to set trim etc.
    roll = 0.0
    pitch = 0.0
    yawrate = 0
    thrust = 10001

    # desire asl value, it could be changed current_asl_value + 50
    d_asl = 685


    def __init__(self):
        self.crazyflie = Crazyflie()
        cflib.crtp.init_drivers(enable_debug_driver=False)

        print "Scanning interfaces for Crazyflies..."
        available = cflib.crtp.scan_interfaces()
        print "Crazyflies found: "

        for i in available:
            print i[0]

        # You may need to update this value if your Crazyradio uses a different frequency.

        link_uri = available[0][0]

        #link_uri = available[0][0]
        #self.crazyflie.open_link(link_uri)
        self.crazyflie.open_link("radio://0/80/250K")

        self.crazyflie.connected.add_callback(self._connectSetupFinished)

        #self.crazyflie.disconnected.add_callback(self._disconnected)
        self.crazyflie.connection_failed.add_callback(self._connection_failed)
        self.crazyflie.connection_lost.add_callback(self._connection_lost)



    def _connectSetupFinished(self, linkURI):
        # Keep the commands alive so the firmware kill-switch doesn't kick in.
        Thread(target=self.pulse_command).start()

        hold_flag = True


        # The definition of the logconfig can be made before connecting
        self._lg_alt = LogConfig(name="altitude", period_in_ms=10)
        self._lg_alt.add_variable("baro.asl", "float")

        # Adding the configuration cannot be done until a Crazyflie is
        # connected, since we need to check that the variables we
        # would like to log are in the TOC.
        self._cf.log.add_config(self._lg_alt)
        if self._lg_alt.valid:
            # This callback will receive the data
            self._lg_alt.data_received_cb.add_callback(self._alt_log_data)
            # This callback will be called on errors
            self._lg_alt.error_cb.add_callback(self._alt_log_error)
            # Start the logging
            self._lg_alt.start()
        else:
            print("Could not add logconfig since some variables are not in TOC")




        while 1:

            #self.crazyflie.log.


            self.thrust = int(raw_input("Set thrust (10001-60000):"))

            if self.thrust == 0:
                self.crazyflie.close_link()
                break
            elif self.thrust <= 10000:
                self.thrust = 10001
            elif self.thrust == 40000:
                # Test altitude hold flightmode
                time.sleep(10)
                #self.crazyflie.commander.send_setpoint(0, 0, 0, 0)
                time.sleep(0.05)
                self.param.set_value("flightmode.althold", "True")
                #time.sleep(10)
                #self.param.set_value("flightmode.althold", "False")
            elif self.thrust > 60000:
                self.thrust = 60000







    def _alt_log_error(self, logconf, msg):
        """Callback from the log API when an error occurs"""
        print "Error when logging %s: %s" % (logconf.name, msg)

    def _alt_log_data(self, timestamp, data, logconf):
        """Callback froma the log API when data arrives"""
        if logconf.name == "altitude":
            if not self._takeoff:
                self._start_alt = data['baro.asl']
                self._takeoff = True
            else:
                self._alt = data['baro.asl']
        print "{}".format(self._alt - self._start_alt)



    def pulse_command(self):
        self.crazyflie.commander.send_setpoint(self.roll, self.pitch, self.yawrate, self.thrust)
        time.sleep(0.1)

        # ..and go again!
        self.pulse_command()




Main()