import sys, time
from multiprocessing import Process, Pipe, current_process

debug = False
if len(sys.argv) > 1 and sys.argv[1] == "-d":
    debug = True

if debug:
    from debugTools import GPIO
    from debugTools import Popen, PIPE
else:
    import RPi.GPIO as GPIO
    from subprocess import Popen, PIPE, call

# Retrieve temperature from DS18B20 temperature sensor
def tempData1Wire(temp_sensor_id):

    if not temp_sensor_id:
        return -99

    pipe = Popen(["cat","/sys/bus/w1/devices/w1_bus_master1/" + temp_sensor_id + "/w1_slave"], stdout=PIPE)
    result = pipe.communicate()[0]
    try:
        if (result.split('\n')[0].split(' ')[11] == "YES"):
            temp_C = float(result.split("=")[-1])/1000 # temp in Celcius
        else:
            temp_C = -99 #bad temp reading
    except IndexError:
        temp_C = -99 #bad temp reading
    
    return temp_C

# Stand Alone Get Temperature Process
def getTempProc(conn, name, temp_sensor_id, num_pnts_smooth):
    p = current_process()
    print 'Starting getTemp:', p.name, p.pid

    temp_ma_list = []
    while (True):
        time.sleep(.2) #.2+~.83 = ~1.03 seconds
        temp = tempData1Wire(temp_sensor_id)

        if temp == -99:
            #print "Bad Temp Reading ("+name+") - retry"
            continue

        if temp == 85 and temp_ma + 5 < 85:
            continue

        temp_ma_list.append(temp)
        while (len(temp_ma_list) > num_pnts_smooth):
            temp_ma_list.pop(0) #remove oldest elements in list

        temp_ma = sum(temp_ma_list) / len(temp_ma_list)
        conn.send((temp, temp_ma))


class TempMonitor:
    def __init__(self, name, sensor_id, num_pnts_smooth):
        parent_conn, child_conn = Pipe()
        self.ptemp = Process(name = "getTemp_"+name, target=getTempProc, args=(child_conn, name, sensor_id, num_pnts_smooth))
        self.ptemp.daemon = True
        self.ptemp.start()

        self.name = name
        self.pipe = parent_conn

        self.temps = (-99,-99)

    def get_temp(self):
        while self.pipe.poll(): #Poll Get Temperature Process Pipe
            self.temps = self.pipe.recv() #non blocking receive from Get Temperature Process

        return self.temps

    def terminate(self):
        print "Terminate tempmonitor ",self.name
        self.ptemp.terminate()
        self.ptemp.join()

    def is_alive(self):
        return self.ptemp.is_alive()