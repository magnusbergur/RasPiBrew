import matplotlib.pyplot as plt
from random import gauss
from math import fmod

from scipy.optimize import differential_evolution

from pid import pidpy

class Pot(object):
    def __init__(self, setP, Kc, Ti, Td):
        self.duty = 0.0
        self.setP = setP
        self.tempHistory = []
        self.dutyHistory = []
        self.setPHistory = []
        self.pHistory = []
        self.iHistory = []
        self.dHistory = []

        self.pid = pidpy.pidpy(5, Kc, Ti, Td) #849.53, 38.261, 9.5653
    
    def tick(self, temp, evaluate):
        self.tempHistory.append(temp)
        self.dutyHistory.append(self.duty)
        self.setPHistory.append(self.setP)

        self.pid.newTemp(temp)

        if evaluate:
            self.duty,pp,pi,pd = self.pid.calcPID(self.setP, True)

            self.pHistory.append(pp)
            self.iHistory.append(pi)
            self.dHistory.append(pd)

    def plot(self):

        I = len(self.tempHistory)
        t = range(I)

        plt.subplot(5, 1, 1)
        plt.plot(t, self.tempHistory, label="T")
        plt.plot(t, self.setPHistory, label="S")
        plt.ylabel('Temperature (C)')
        plt.grid(True)
        plt.legend(fancybox=True, bbox_to_anchor=(0., 1.02, 1., .102), loc=3,
           ncol=2, mode="expand", borderaxespad=0.)
        
        plt.subplot(5, 1, 5)
        plt.plot(t, self.dutyHistory)
        plt.ylabel('Power (%)')
        plt.grid(True)
        plt.xlabel('time (s)')

        I2 = len(self.pHistory)
        t2 = range(I2)

        plt.subplot(5, 1, 3)
        plt.plot(t2, self.pHistory)
        plt.ylabel('P')
        plt.grid(True)
        plt.xlabel('time (show)')

        plt.subplot(5, 1, 4)
        plt.plot(t2, self.iHistory)
        plt.grid(True)
        plt.ylabel('I')
        plt.xlabel('time (s)')

        plt.subplot(5, 1, 2)
        plt.plot(t2, self.dHistory)
        plt.grid(True)
        plt.ylabel('D')
        plt.xlabel('time (s)')

        plt.show()

def simul(pars):
    initTemp = 60.0
    power = 3500.0
    volume = 100.0
    setP = 60.0
    sqError = 0.0

    HLT = Pot(setP, pars[0], pars[1], pars[2])
    temp = initTemp
    sysHeat = (power/(4186*volume))/100.0
    for i in range(3600):

        evaluate = False
        if fmod(i,5) == 0:
            evaluate = True

        HLT.tick(temp, evaluate)
        temp *= gauss(0.99997, 0.0001)
        if i >= 19:
            temp += HLT.dutyHistory[i-19]*sysHeat
        sqError += (temp - setP)**2.0

    return sqError

if __name__=="__main__":
    
    initTemp = 60
    power = 3500
    volume = 100
    setP = 60
                    #224.25831831   68.3469701    12.01606341 # 193.65386931 ,  98.65292469 ,  22.74942745
    HLT = Pot(setP,  200 ,  70 ,  20)

    #f = open("temps1.txt","r")
    #raw = f.read()
    #f.close()
    #tempLog = raw.split('\n')
    #tempLog = [float(t) for t in tempLog]

    temp = initTemp
    for i in range(3600):
        #if i > 1000:
        #   HLT.setP = 70
        #elif i > 3000:
        #    HLT.setP = 60

        #temp = tempLog[i]
        evaluate = False
        if fmod(i,5) == 0:
            evaluate = True
        HLT.tick(temp, evaluate)

        temp *= gauss(0.99997, 0.0001)
        if i >= 19:
            temp += (HLT.dutyHistory[i-19]/100.0)*power/(4186*volume)


    HLT.plot()
