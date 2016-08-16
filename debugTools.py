import math, time

class GPIO(object):
    OUT = "OUT"
    IN  = "IN"
    BOARD = "BOARD"
    BCM = "BCM"

    @staticmethod
    def setup(pinNr, direction):
    	print "GPIO setup pin",pinNr,"as",direction

    @staticmethod
    def setmode(mode):
    	print "GPIO set mode:",mode

    @staticmethod
    def output(pinNr, output):
        print "GPIO pin",pinNr,"output:",output

    @staticmethod
    def setwarnings(boolVal):
        print "GPIO set warnings",boolVal

    @staticmethod
    def cleanup():
        print "GPIO cleanup"

PIPE = "PIPE"

class Popen(object):
    def __init__(self,path,stdout):
        #print "Initialise Popen at:",path
        return

    def communicate(self):
        temp_C = (math.sin(time.time()/100)+1)*2+16;
        temp_str = "           YES temp=%s" % (temp_C*1000)
        return (temp_str,None)

    def kill(self):
        return
