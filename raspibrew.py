import time, random, serial, os, signal, sys

debug = False
if len(sys.argv) > 1 and sys.argv[1] == "-d":
    debug = True

from multiprocessing import Process, Pipe, Queue, current_process
from subprocess import Popen, PIPE, call
from Queue import Full
from datetime import datetime, date

if debug:
    from debugTools import GPIO
else:
    import RPi.GPIO as GPIO
    from subprocess import call

from pid import pidpy as PIDController
import xml.etree.ElementTree as ET
from flask import Flask, render_template, request, jsonify

global webParentConn, statusQueues, brewtime
global xml_root, template_name, pinGPIOList

from tools import TempMonitor

app = Flask(__name__, template_folder='templates')

#Parameters that are used in the temperature control process
class Params:
    def __init__(self, sensor=1, cycle_time=0, kp=0, ti=0, td=0, llim=0.0, hlim=100.0, mode="off"):
        self.status = {
            "sensor" : sensor,
            "temp" : "0",
            "mode" : mode,
            "cycle_time" : cycle_time,
            "duty_cycle" : 0.0,
            "set_point" : 0.0,
            "num_pnts_smooth" : 5,
            "k" : kp,
            "i" : ti,
            "d" : td,
            "llim" : llim,
            "hlim" : hlim
            }

    def setNew(self, temp, duty):
        self.status["temp"] = "%3.2f" % temp
        self.status["duty_cycle"] = "%3.2f" % duty

# main web page
@app.route('/', methods=['GET', 'POST'])
def index():
    freshPars = Params()
    if request.method == 'GET':
        #render main page
        return render_template(template_name, 
            mode = freshPars.status["mode"], \
            set_point = freshPars.status["set_point"], \
            duty_cycle = freshPars.status["duty_cycle"], \
            cycle_time = freshPars.status["cycle_time"], \
            k = freshPars.status["k"], \
            i = freshPars.status["i"], \
            d = freshPars.status["d"])

#post params (selectable temp sensor number)
@app.route('/postparams/<sensorNum>', methods=['POST'])
def postparams(sensorNum=None):

    print "form: ",request.form
    freshPars = Params()
    freshPars.status["mode"] = request.form["mode"]
    freshPars.status["cycle_time"] = float(request.form["cycletime"])
    if freshPars.status["mode"] == "manual":
        freshPars.status["duty_cycle"] = float(request.form["dutycycle"])
    elif freshPars.status["mode"] == "auto":
        freshPars.status["set_point"] = float(request.form["setpoint"])
        if request.form["k"] != '':
            freshPars.status["k"] = float(request.form["k"])
            freshPars.status["i"] = float(request.form["i"])
            freshPars.status["d"] = float(request.form["d"])

    #send to main temp control process
    #if did not receive variable key value in POST, the param class default is used
    sensorNum = int(sensorNum)

    webParentConn[sensorNum-1].send(freshPars.status)

    return 'OK'

#post GPIO
@app.route('/GPIO_Toggle/<GPIO_Num>/<onoff>', methods=['GET'])
def GPIO_Toggle(GPIO_Num=None, onoff=None):

    if len(pinGPIOList) >= int(GPIO_Num):
        out = {"pin" : pinGPIOList[int(GPIO_Num)-1], "status" : "off"}
        if onoff == "on":
            GPIO.output(pinGPIOList[int(GPIO_Num)-1], ON)
            out["status"] = "on"
            print "GPIO Pin #%s is toggled on" % pinGPIOList[int(GPIO_Num)-1]
        else: #off
            GPIO.output(pinGPIOList[int(GPIO_Num)-1], OFF)
            print "GPIO Pin #%s is toggled off" % pinGPIOList[int(GPIO_Num)-1]
    else:
        out = {"pin" : 0, "status" : "off"}

    return jsonify(**out)

#get status from RasPiBrew using firefox web browser (first temp sensor / backwards compatibility)
@app.route('/getstatus') #only GET
def getstatusB():
    #blocking receive - current status
    params = statusQueues[0].get()
    return jsonify(**params)

#get status from RasPiBrew using firefox web browser (selectable temp sensor)
@app.route('/getstatus/<sensorNumStr>') #only GET
def getstatus(sensorNumStr=None):
    #blocking receive - current status
    sensorNum = int(sensorNumStr)
    params = statusQueues[sensorNum-1].get()
    return jsonify(**params)

# Stand Alone Heat Process using GPIO
def heatProc(heat_pin, conn):
    p = current_process()
    print 'Starting getHeat:', p.name, p.pid
    if heat_pin == -1:
        return
    
    cycle_time = 2
    duty_cycle = 0

    GPIO.setup(heat_pin, GPIO.OUT)

    while (True):
        while (conn.poll()): #get last
            tubi = conn.recv()

            if len(tubi) == 3:
                cycle_time, duty_cycle, name = tubi
            else:
                cycle_time, duty_cycle, name = tubi[0]
        
        conn.send([cycle_time, duty_cycle])
        #print "duty_cycle ",duty_cycle,"cycle: ",cycle_time

        if cycle_time == 0:
            time.sleep(1)
            continue

        if duty_cycle == 0:
            #print "0 percent"
            GPIO.output(heat_pin, OFF)
            time.sleep(cycle_time)
        elif duty_cycle == 100:
            #print "100 percent"
            GPIO.output(heat_pin, ON)
            time.sleep(cycle_time)
        elif duty_cycle > 0:
            #print duty_cycle,"percent"
            GPIO.output(heat_pin, ON)
            time.sleep( cycle_time * (    duty_cycle/100.0) )
            GPIO.output(heat_pin, OFF)
            time.sleep( cycle_time * (1.0-duty_cycle/100.0) )

class Heater:
    def __init__(self, pinId):
        parent_conn_heat, child_conn_heat = Pipe()
        self.pheat = Process(name = "heatProc", target=heatProc, args=(pinId, child_conn_heat))
        self.pheat.daemon = True
        self.pheat.start()
        self.pipe = parent_conn_heat

    def set_new_duty_cycle(self, duty_cycle):
        self.pipe.send([duty_cycle])

    def terminate(self):
        print "Terminate heater"
        self.pheat.terminate()
        self.pheat.join()


class Controller:
    def __init__(self, name, paramsDict, tempSensor, queue, webConn):
        self.name = name
        self.paramsDict = paramsDict
        self.tempMonitor = TempMonitor(name, tempSensor, paramsDict["num_pnts_smooth"])
        self.queue = queue
        self.webConn = webConn

        self.temp = -99
        self.temp_ma = -99
        self.last_duty_time = 0

        if paramsDict["cycle_time"] > 0:
            self.pid = PIDController.pidpy(self.paramsDict["cycle_time"], self.paramsDict["k"], self.paramsDict["i"], self.paramsDict["d"])
            self.pid.setLims(self.paramsDict["llim"], self.paramsDict["hlim"])
        else:
            self.pid = None

    def get_temp(self):
        temp, temp_ma = self.tempMonitor.get_temp()
        self.temp = temp
        self.temp_ma = temp_ma
        
        return self.temp

    def get_duty(self):
        now = time.time()
        if self.paramsDict["mode"] == "off":
            self.paramsDict["duty_cycle"] = 0
        elif self.paramsDict["mode"] == "auto" and  now - self.last_duty_time > self.paramsDict["cycle_time"]:
            self.pid.newTemp(self.temp_ma)
            self.paramsDict["duty_cycle"] = self.pid.calcPID(self.paramsDict["set_point"])
            self.last_duty_time = now

        #print "get duty",self.name,"mode",self.paramsDict["mode"],"duty",self.paramsDict["duty_cycle"],"cycle",self.paramsDict["cycle_time"]
        return (self.paramsDict["cycle_time"],self.paramsDict["duty_cycle"],self.name)

    def set_lims(self, llim, hlim):
        self.pid.setLims(llim, hlim)

    def set_setpoint(self, new_setpoint):
        if self.name == "HLT" and self.paramsDict["mode"] == "auto":
            self.paramsDict["set_point"] = new_setpoint[1]

    def report(self):
        #put current status in queue
        while (self.queue.qsize() >= 2):
            self.queue.get() #remove old status
        
        self.paramsDict["temp"] = "%3.2f" % self.temp

        try:
            self.queue.put(self.paramsDict) #GET request
        except Full:
            pass

    def receiveReconfigure(self):
        while self.webConn.poll(): #POST settings - Received POST from web browser or Android device
            newParamsDict = self.webConn.recv()

            print self.name,"recieved reconf:",newParamsDict
            
            self.paramsDict["mode"] = newParamsDict["mode"]
            self.paramsDict["cycle_time"] = newParamsDict["cycle_time"]

            if self.paramsDict["mode"] == "auto":
                if self.pid:
                    self.paramsDict["k"] = newParamsDict["k"]
                    self.paramsDict["i"] = newParamsDict["i"]
                    self.paramsDict["d"] = newParamsDict["d"]
                    self.paramsDict["set_point"] = newParamsDict["set_point"]
                    self.pid.setParams(self.paramsDict["cycle_time"], self.paramsDict["k"], self.paramsDict["i"], self.paramsDict["d"])

                print self.name,"auto selected"
            if self.paramsDict["mode"] == "manual":
                self.paramsDict["duty_cycle"] = newParamsDict["duty_cycle"]
                print self.name,"manual selected, duty: ",self.paramsDict

            if self.paramsDict["mode"] == "off":
                print self.name,"off selected"

    def terminate(self):
        self.tempMonitor.terminate()
        

# Main Temperature Control Process
def tempControlProc(HLTController, MLTController, BKController, heater):
    p = current_process()
    print 'Starting main:', p.name, p.pid

    #overwrite log file for new data log
    log_name = "brew-"+ str(date.today()) + ".csv"
    ff = open(log_name, "ab")
    ff.write("New brew started!\n")
    ff.close()
    last_iter = brewtime
    while (True):
        time.sleep(1)
        now = time.time()
        #print "new iteration took: %.2f s" % (now - last_iter)
        last_iter = now

        temp_hlt = HLTController.get_temp()
        temp_mlt = MLTController.get_temp()
        temp_bk  = BKController.get_temp()

        duty_mlt = MLTController.get_duty()
        HLTController.set_setpoint(duty_mlt)
        duty_hlt = HLTController.get_duty()
        heater.set_new_duty_cycle(duty_hlt)

        logdata(log_name, temp_hlt, temp_mlt, temp_bk, duty_hlt, duty_mlt)

        #put current status in queue
        HLTController.report()
        MLTController.report()
        BKController.report()
 
        HLTController.receiveReconfigure()
        MLTController.receiveReconfigure()


def logdata(log_name, temp_hlt, temp_mlt, temp_bk, duty_hlt, duty_mlt):
    time_now = datetime.now()
    print "%s Temp HLT: %3.2f C, MLT: %3.2f C, BK: %3.2f C, Duty MLT: %3.2f C, Duty HLT: %3.1f%%" % (time_now.isoformat(' '), temp_hlt, temp_mlt, temp_bk, duty_mlt[1], duty_hlt[1])
    
    f = open(log_name, "ab")
    f.write("%s;%3.3f;%3.3f;%3.3f;%3.3f;%3.3f\n" % (time_now.isoformat(' '), temp_hlt, temp_mlt, temp_bk, duty_hlt[1], duty_mlt[1]))
    f.close()

def webProc():
    import logging
    log = logging.getLogger('werkzeug')
    log.setLevel(logging.ERROR)

    p = current_process()
    print 'Starting web:', p.name, p.pid
    app.debug = False
    app.run(use_reloader=False, host='0.0.0.0', port=5000, use_debugger=True, threaded=True)

if __name__ == '__main__':

    brewtime = time.time()
    #os.chdir("/var/www/RasPiBrew")
    
    default_handler = signal.getsignal(signal.SIGINT)
    signal.signal(signal.SIGINT, signal.SIG_IGN)

    if not debug:
        call(["modprobe", "w1-gpio"])
        call(["modprobe", "w1-therm"])
        call(["modprobe", "i2c-bcm2708"])
        call(["modprobe", "i2c-dev"])

    # Retrieve root element from config.xml for parsing
    tree = ET.parse('configBrew.xml')
    xml_root = tree.getroot()
    template_name = xml_root.find('Template').text.strip()

    gpioNumberingScheme = xml_root.find('GPIO_pin_numbering_scheme').text.strip()
    if gpioNumberingScheme == "BOARD":
        GPIO.setmode(GPIO.BOARD)
    else:
        GPIO.setmode(GPIO.BCM)

    gpioInverted = xml_root.find('GPIO_Inverted').text.strip()
    if gpioInverted == "0":
        ON = 1
        OFF = 0
    else:
        ON = 0
        OFF = 1

    heatPin=-1
    for pin in xml_root.iter('Heat_Pin'):
        heatPin = int(pin.text.strip())

    GPIO.setwarnings(False)
    pinGPIOList=[]
    for pin in xml_root.iter('GPIO_Pin'):
        pinNum = int(pin.text.strip())
        pinGPIOList.append(pinNum)
        GPIO.setup(pinNum, GPIO.OUT)

    paramsHLT = Params(1, 5, 150, 58, 2, 0.0, 100.0)  #Cycle time, kP, kI, KD, llim, hlim
    paramsMLT = Params(2, 30, 150, 58, 2, 60.0, 72.0) #Cycle time, kP, kI, KD, llim, hlim
    paramsBK  = Params(3)

    tempSensors = [sensor.text.strip() for sensor in xml_root.iter('Temp_Sensor_Id')]
    while len(tempSensors) < 3:
        tempSensors.append(None)

    statusQueues = [Queue(2), Queue(2), Queue(2)]
    webParentConn, webChildConn = zip(Pipe(), Pipe(), Pipe())

    HLTControl = Controller("HLT", paramsHLT.status, tempSensors[0], statusQueues[0], webChildConn[0])
    MLTControl = Controller("MLT", paramsMLT.status, tempSensors[1], statusQueues[1], webChildConn[1])
    BKControl  = Controller("BK",  paramsBK.status,  tempSensors[2], statusQueues[2], webChildConn[2])
    heater = Heater(heatPin)

    mainProcess = Process(name = "MainControl", target=tempControlProc, args=(HLTControl, MLTControl, BKControl, heater))
    mainProcess.start()

    webProcess = Process(name = "WebProcess", target=webProc)
    webProcess.start()

    signal.signal(signal.SIGINT, default_handler)

    try:
        while (True):
            time.sleep(60)
            
    except KeyboardInterrupt:
        print 'Interrupted'
        HLTControl.terminate()
        MLTControl.terminate()
        BKControl.terminate()
        heater.terminate()
        mainProcess.terminate()
        webProcess.terminate()
        GPIO.setwarnings(False)
        GPIO.cleanup()


