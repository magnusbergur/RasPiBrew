import json
from datetime import datetime
from multiprocessing import Queue, Pipe, Manager
from Queue import Full

class WebServer():
    def __init__(self):
        self.statusQueue = Queue()
        self.webParentConn, self.webChildConn = Pipe()
        self.dataHistory = Manager().list()
        self.paramsOuter = {}

    def getInitParams(self):
        return self.paramsOuter

    def receiveSettings(self,form):
        newPars = {"mode":form["mode"]}
        for key,val in form:
            newPars[key] = float(val)

        self.webParentConn.send(newPars)

    def getHistory(self,indx):
        if len(self.dataHistory) <= indx: return {}
        
        historyFragment = self.dataHistory[indx:]
        H = len(historyFragment)

        dataEntries = {}
        for key,val in historyFragment[0].iteritems():
            dataEntries[key] = [None]*H

        for i,entry in enumerate(historyFragment):
            for key,val in entry.iteritems():
                dataEntries[key][i] = val

        return dataEntries

    def getStatus(self):
        return self.statusQueue.get()

    def report(self, report):
        #Report temps, cycle and duty
        while (self.statusQueue.qsize() >= 2):
            self.statusQueue.get() #remove old status
        
        timestamp = json.dumps(datetime.now().isoformat())
        #print "timestamp",timestamp
        report["time"] = timestamp
        
        self.dataHistory.append(report)

        try:
            self.statusQueue.put(report) #GET request
        except Full:
            pass

