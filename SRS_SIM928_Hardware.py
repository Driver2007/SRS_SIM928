### written on python 2.7

PARITY = 'N'
STOPBITS = 1
BYTESIZE = 8
XONXOFF  = False
RTSCTS   = True
TIMEOUT = 0.1 # in seconds when reading from the device
SENDTERMSTR = '\r\n'
RESPONSETERMSTR = '\r\n'  # used to distinguish whether the received characters form a complete response

import serial
import time

class SRS_SIM928_Hardware:
    def __init__(self):
        self.baudrate = None
        self.devfile  = None
        self.serial = None
        self.connected = False
        self.conn_callbacks = []
        self.busy = False
        self.info_ident = ""
        self.battery_state = (-1,-1,-1)
        self.battery_state_str = ("unknown", "unknown", "unknown")
        self.battery_state_desc = {-1: "unknown", 0 : "", 1 : "in use", 2 : "charging", 3 : "ready/standby"}
        
    
    def connect(self, devfile, baudrate=None):
        if self.connected:
            return
        self.devfile = devfile
        self.baudrate = 9600 if baudrate==None else baudrate
        self.serial = serial.Serial(self.devfile, baudrate=self.baudrate, 
                                    parity=PARITY, stopbits=STOPBITS, 
                                    bytesize=BYTESIZE, timeout=TIMEOUT, 
                                    xonxoff=XONXOFF, rtscts=RTSCTS)
        if not self.serial.isOpen():
            print("Error while connecting.")
            return False
        else:
            self.connected = True
            print("Connected.")
            for c in self.conn_callbacks:
                c(True)
            return True
        
    def disconnect(self):
        if not self.serial.isOpen():
            return
        self.serial.close()
        self.connected = False
        for c in self.conn_callbacks:
            c(False)
    
    def read_ident(self):
        self.info_ident = self.send_and_receive("*IDN?")
        return str(self.info_ident).strip()
        
    def read_battery_state(self):
        answer = self.send_and_receive("BATS?")
        tokens = answer.split(',')
        try:
            self.battery_state = (int(tokens[0]), int(tokens[1]), int(tokens[2]))
            self.battery_state_str = (self.battery_state_desc[self.battery_state[0]],
                                      self.battery_state_desc[self.battery_state[1]],
                                      "ok" if self.battery_state[2]==0 else "battery service needed")
            return self.battery_state
        except:
            return (-1,-1,-1)

    def read_output_on(self):
        answer = self.send_and_receive("EXON?")
        try:
            output_state = int(answer)
            return output_state
        except:
            return -1
        
    def write_output_on(self, on_state=True):
        if on_state:
            self.send("OPON")
        else:
            self.send("OPOF")
    
    def read_volt(self):
        answer = self.send_and_receive("VOLT?")
        try:
            return float(answer)
        except ValueError:
            print("Got non-float voltage value from device: ", answer)
            return None
    
    def write_volt(self, volt):
        try:
            volt = float(volt)
        except:
            return
        if volt>20.0:
            volt = 20.0
        if volt<-20.0:
            volt = -20.0
        self.send("VOLT {v:5.3f}".format(v=volt))
        
    def clear_status(self):
        self.send("*CLS")
    
    def write_bat_charge_override(self):
        self.send("BCOR")
    
    def read_battery_info(self, parameter=0):
        """ allowed parameter values are 0 = PNUM (Battery pack part number)
                                         1 = SERIAL (Battery pack serial number)
                                         2 = MAXCY (Design life, number of charge cycles)
                                         3 = CYCLES (number of charge cycles used)
                                         4 = PDATE (Battery pack production date (YYYY-MM-DD))
        """
        try:
            parameter = int(parameter)
        except:
            return
        if parameter < 0 or parameter > 4:
            return
        answer = self.send_and_receive("BIDN? " + str(parameter))
        return str(answer).strip()
    
    def add_connection_listener(self, callback):
        self.conn_callbacks.append(callback)

    def send(self, sendstr):
        self.send_and_receive(sendstr, receive=False)

    def send_and_receive(self, sendstr, receive=True, maxtries=10):
        if not self.serial or not self.serial.isOpen():
            return ""
        while (self.busy):
            time.sleep(0.02)
        self.busy = True
        try:
            #print("sending ", sendstr)
            s=sendstr.strip('\n\r')+SENDTERMSTR
            #s = bytes(s, "utf-8")   # needed only in python3 (?)
            self.serial.write(s)
            if not receive:
                return None
            #time.sleep(0.1)
            responsebuf = ""
            loops = 0
            while not responsebuf.endswith(RESPONSETERMSTR) and loops < maxtries:
                buf = self.serial.read(10000) # insecure, should receive until line ending!
                responsebuf += buf.decode('utf-8')
                #print("received " + str(len(buf)) + " bytes.")
                loops = loops + 1
            #print("received ", responsebuf)
            return responsebuf
        except:
            self.busy = False
            raise
        finally:
            self.busy = False
        
