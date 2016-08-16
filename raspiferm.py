import time, random, serial, os, signal, sys, math, json

debug = False
if len(sys.argv) > 1 and sys.argv[1] == "-d":
    debug = True

from multiprocessing import Process, Pipe, Queue, current_process
from Queue import Full
from datetime import datetime, date

if debug:
    from debugTools import GPIO
else:
    import RPi.GPIO as GPIO

from pid import pidpy as PIDController
import xml.etree.ElementTree as ET
from flask import Flask, render_template, request, jsonify
from subprocess import Popen, PIPE, call

global webParentConn, statusQueue, brewtime, dataHistory, paramsOuter
global xml_root, pinGPIOList

from tools import TempMonitor

app = Flask(__name__, template_folder='templates')

#Parameters that are used in the temperature control process
class Params:
    def __init__(self, cycle_time=0, pidParams=None, mode="off", deadband=0.5):

        kH,iH,dH,kC,iC,dC = (None,None,None,None,None,None)
        if pidParams:
            kH,iH,dH = pidParams[0]
            kC,iC,dC = pidParams[1]

        self.status = {
            "mode" : mode, "set_point" : 0.0,
            "cycle_time" : cycle_time, "duty_cycle" : 0.0,
            "kH" : kH or 0, "iH" : iH or 0, "dH" : dH or 0,
            "kC" : kC or 0, "iC" : iC or 0, "dC" : dC or 0,
            "deadband" : deadband
            }
    def returnDict(self):
        return self.status

# main web page
@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'GET':
        print "GET - plain"
        #render main page
        return render_template("raspiferm.html",**paramsOuter)

#post params (selectable temp sensor number)
@app.route('/postparams/', methods=['POST'])
def postparams():
    newPars = {}
    newPars["mode"] = request.form["mode"]
    newPars["deadband"] = float(request.form["deadband"])
    newPars["cycle_time"] = float(request.form["cycletime"])
    if newPars["mode"] == "manual":
        newPars["duty_cycle"] = float(request.form["dutycycle"])
    elif newPars["mode"] == "auto":
        newPars["set_point"] = float(request.form["setpoint"])
        if request.form["kH"] != '':
            newPars["kH"] = float(request.form["kH"])
            newPars["iH"] = float(request.form["iH"])
            newPars["dH"] = float(request.form["dH"])
            newPars["kC"] = float(request.form["kC"])
            newPars["iC"] = float(request.form["iC"])
            newPars["dC"] = float(request.form["dC"])

    #send to main temp control process
    #if did not receive variable key value in POST, the param class default is used
    webParentConn.send(newPars)
    return 'OK'

#post params (selectable temp sensor number)
@app.route('/gethistory/')
def gethistory():
    idxs = request.args.getlist('indx[]')

    historyFragment = []
    fxData = {"time": json.dumps(datetime.now().isoformat()), "innerTemp": 64, "outerTemp": 23, "envirTemp":45, "duty":12}
    for s, idx in enumerate(idxs):
        historyFragment.append(fxData) #dataHistory[s][int(idx)+1:]

    return jsonify(historyFragment)

#get status from RasPiBrew using firefox web browser (selectable temp sensor)
@app.route('/getstatus/') #only GET
def getstatus():
    #blocking receive - current status
    params = statusQueue.get()
    return jsonify(**params)


# Stand Alone Heat Process using GPIO
def actuatorProc(pinId, conn):
    p = current_process()
    print 'Starting actuator process:', p.name, p.pid
    if pinId == -1:
        return
    
    duty_cycle = 0
    cycle_time = 2

    ON = 1
    OFF = 0

    while (True):
        while conn.poll(): #get last
            duty_cycle, cycle_time = conn.recv()
        
        print p.name,"duty:",duty_cycle,"cycle:",cycle_time 

        if duty_cycle <= 0:
            GPIO.output(pinId, OFF)
            print p.name,"set",pinId,"as",OFF
            time.sleep(cycle_time)
        elif duty_cycle >= 100:
            GPIO.output(pinId, ON)
            print p.name,"set",pinId,"as",ON
            time.sleep(cycle_time)
        else:
            GPIO.output(pinId, ON)
            time.sleep( cycle_time * (    duty_cycle/100.0) )
            GPIO.output(pinId, OFF)
            time.sleep( cycle_time * (1.0-duty_cycle/100.0) )

class Actuator:
    def __init__(self, heatPinId, coolPinId):
        self.processes = dict()
        self.pipes = dict()

        self.getActuatorProcess("heatProcess", heatPinId)
        self.getActuatorProcess("coolProcess", coolPinId)

    def getActuatorProcess(self, processName, pinId):
        parent_conn, child_conn = Pipe()
        self.processes[processName] = Process(name = processName, target=actuatorProc, args=(pinId, child_conn))
        self.processes[processName].daemon = True
        self.processes[processName].start()
        self.pipes[processName] = parent_conn

    def set_new_duty_and_cycle(self, duty, cycle):
        if duty > 0:
            self.pipes["heatProcess"].send((duty,cycle))
            self.pipes["coolProcess"].send((   0,cycle))
        else:
            self.pipes["heatProcess"].send((    0,cycle))
            self.pipes["coolProcess"].send((-duty,cycle))

    def terminate(self):
        print "Terminate actuator"
        for p in self.processes:
            self.processes[p].terminate()
            self.processes[p].join()

    def is_alive(self):
        alive = True
        for p in self.processes:
            if not self.processes[p].is_alive():
                alive = False

        return alive
            
class Controller:
    def __init__(self, name, params):
        self.name = name
        self.params = params
        
        self.last_duty_time = 0

        if params["cycle_time"] > 0:
            print name,"setting pids"
            self.pidH = PIDController.pidpy_simple(self.params["cycle_time"], self.params["kH"], self.params["iH"], self.params["dH"])
            self.pidC = PIDController.pidpy_simple(self.params["cycle_time"], self.params["kC"], self.params["iC"], self.params["dC"])

    def get_duty_from_pid(self, temp):
        error = temp - self.params["set_point"]
        if math.fabs(error) >= self.params["deadband"]:
            return 0

        if error > 0:
            self.pidC.newTemp(temp) 
            duty =  self.pidC.calcPID(self.params["set_point"]) 
        else:
            self.pidH.newTemp(temp) 
            duty = -self.pidH.calcPID(self.params["set_point"])
        return duty

    def get_duty_and_cycle(self, temp):
        now = time.time()
        if self.params["mode"] == "off":
            self.params["duty_cycle"] = 0
        elif self.params["mode"] == "auto" and now - self.last_duty_time > 5:#self.params["cycle_time"]:
            self.params["duty_cycle"] = self.get_duty_from_pid(temp)
            self.last_duty_time = now

        #print "get duty",self.name,"mode",self.params["mode"],"duty",self.params["duty_cycle"]
        return self.params["duty_cycle"],self.params["cycle_time"],self.params["set_point"]

    def receiveReconfigure(self, newparams):
        print self.name,"recieved reconf:",newparams
    
        self.params = newparams

        if self.params["mode"] == "auto":
            if self.pidH:
                self.pidH.setParams(self.params["cycle_time"], self.params["kH"], self.params["iH"], self.params["dH"])
                self.pidC.setParams(self.params["cycle_time"], self.params["kC"], self.params["iC"], self.params["dC"])

        print self.name,self.params["mode"],"selected"

    def terminate(self):
        self.tempMonitor.terminate()

    def is_alive(self):
        return self.tempMonitor.is_alive()
        
# Main Temperature Control Process
def tempControlProc(tempMonitors, outerController, actuator, statusQueue, webConn):
    p = current_process()
    print 'Starting main:', p.name, p.pid

    #overwrite log file for new data log
    log_name = "ferm-"+ str(date.today()) + ".csv"
    ff = open(log_name, "wb")
    ff.close()
    last_iter = brewtime

    while (True):
        time.sleep(1)
        now = time.time()
        #print "new iteration took: %.2f s" % (now - last_iter)
        last_iter = now

        innerTemp,outerTemp,envirTemp = [tempMonitor.get_temp()[1] for tempMonitor in tempMonitors]

        duty,cycle,innerSet = outerController.get_duty_and_cycle(outerTemp)
        actuator.set_new_duty_and_cycle(duty,cycle)

        logdata(log_name, innerTemp, outerTemp, envirTemp, duty)

        #Report temps, cycle and duty
        while (statusQueue.qsize() >= 2):
            statusQueue.get() #remove old status
        
        timestamp = json.dumps(datetime.now().isoformat())
        print "timestamp",timestamp
        report = {"time": timestamp, "innerTemp": innerTemp, "outerTemp": outerTemp, "envirTemp":envirTemp, "duty":duty, "innerSetpoint":innerSet}
        dataHistory.append(report)
        try:
            statusQueue.put(report) #GET request
        except Full:
            pass

        #Fetch new parameters
        while webConn.poll(): #POST settings - Received POST from web browser or Android device
            newparams = self.webConn.recv()
            outerController.receiveReconfigure(newparams)

def webProc():
    import logging
    log = logging.getLogger('werkzeug')
    log.setLevel(logging.ERROR)

    p = current_process()
    print 'Starting web:', p.name, p.pid
    app.debug = False
    app.run(use_reloader=False, host='0.0.0.0', port=5000, threaded=True, use_debugger=False)

def logdata(log_name, temp_inner, temp_outer, temp_envir, duty):
    time_now = datetime.now()
    print "%s  Temp inner: %3.2f C, outer: %3.2f C, environm: %3.2f C, duty: %3.1f%%" % (time_now.isoformat(' '), temp_inner, temp_outer, temp_envir, duty)

    f = open(log_name, "ab")
    f.write("%s;%3.3f;%3.3f;%3.3f;%3.3f\n" % (time_now.isoformat(' '), temp_inner, temp_outer, temp_envir, duty))
    f.close()

if __name__ == '__main__':
    brewtime = time.time()
    #os.chdir("/var/www/RasPiBrew")
    dataHistory = []

    default_handler = signal.getsignal(signal.SIGINT)
    signal.signal(signal.SIGINT, signal.SIG_IGN)

    if not debug:
        call(["modprobe", "w1-gpio"])
        call(["modprobe", "w1-therm"])
        call(["modprobe", "i2c-bcm2708"])
        call(["modprobe", "i2c-dev"])

    # Retrieve root element from config.xml for parsing
    tree = ET.parse('configFerm.xml')
    xml_root = tree.getroot()

    GPIO.setmode(GPIO.BOARD)
    heatPin=-1
    for pin in xml_root.iter('Heat_Pin'):
        heatPin = int(pin.text.strip())
        GPIO.setup(heatPin, GPIO.OUT)
        GPIO.output(heatPin, OFF)
    coolPin=-1
    for pin in xml_root.iter('Cool_Pin'):
        coolPin = int(pin.text.strip())
        GPIO.setup(coolPin, GPIO.OUT)
        GPIO.output(coolPin, OFF)

    sensor_names = ("Inner","Outer","Environment")
    sensor_ids = [sensor.text.strip() for sensor in xml_root.iter('Temp_Sensor_Id')]
    while len(sensor_ids) < 3:
        sensor_ids.append(None)
    
    tempMonitors = [TempMonitor(sensor_names[s], sensor_ids[s], 5) for s in range(3)]
    statusQueue = Queue()
    webParentConn, webChildConn = Pipe()

    paramsOuter = Params(30, ((100,0,0), (100,0,0)), deadband=0.1).returnDict()  #Cycle time, kP, kI, KD, llim, hlim, dead
    outerControl = Controller("Outer", paramsOuter)
    actuator = Actuator(heatPin, coolPin)

    mainProcess = Process(name = "MainControl", target=tempControlProc, args=(tempMonitors, outerControl, actuator, statusQueue, webChildConn))
    mainProcess.start()

    webProcess = Process(name = "WebProcess", target=webProc)
    webProcess.start()

    signal.signal(signal.SIGINT, default_handler)

    try:
        while (True):
            time.sleep(60)

    except KeyboardInterrupt:
        print 'Interrupted'
        innerControl.terminate()
        outerControl.terminate()
        envirControl.terminate()
        actuator.terminate()
        mainProcess.terminate()
        webProcess.terminate()
        GPIO.setwarnings(False)
        GPIO.cleanup()
