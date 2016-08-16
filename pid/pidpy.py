class pidpy(object):
    def __init__(self, ts, kc, ti, td):
        self.setParams(ts, kc, ti, td)
        self.yk = 0.0
        self.setLims(0.0,100.0)
        self.xks = []
    
    def setParams(self, ts, kc, ti, td):
        self.kc = float(kc)
        self.k0 = 0.0
        self.k1 = 0.0
        if (ti == 0.0):
            self.k0 = 0.0
        else:
            self.k0 = self.kc * ts / ti
        self.k1 = self.kc * td / ts


    def setLims(self, llim, hlim):
        self.llim = llim
        self.hlim = hlim             

    def newTemp(self, xk):
        self.xks.append(xk)

    def PV_diff(self):
        if len(self.xks) < 15: return 0.0

        return (sum(self.xks[-15:-5]) - sum(self.xks[-10:]))/10

    def PV_2der(self):
        if len(self.xks) < 20: return 0.0

        return (2.0*sum(self.xks[-15:-5]) - sum(self.xks[-10:]) - sum(self.xks[-20:-10]))/10

    def calcPID(self, tset, debug=False):

        xk = self.xks[-1]

        #-----------------------------------------------------------
        # Calculate PID controller:
        # y[k] = y[k-1] + kc*(PV[k-1] - PV[k] + Ts*e[k]/Ti + Td/Ts*(2*PV[k-1] - PV[k] - PV[k-2]))
        #-----------------------------------------------------------
        pp = self.kc * self.PV_diff() # y[k] = y[k-1] + Kc*(PV[k-1] - PV[k])
        pi = self.k0 * (tset - xk)  # + Kc*Ts/Ti * e[k]
        pd = self.k1 * self.PV_2der()
        self.yk += pp + pi + pd

        if (self.yk > self.hlim):
            self.yk = self.hlim
        if (self.yk < self.llim):
            self.yk = self.llim
        
        if debug:
            strings = ["%.2f" % num for num in (xk, self.yk, pp, pi, pd)]
            strings = [string.rjust(8) for string in strings]
            print "%s %s %s %s %s" % tuple(strings)
            return self.yk, pp, pi, pd

        return self.yk

class pos_pid(object):
    def __init__(self, ts, kc, ti, td):
        self.setParams(ts, kc, ti, td)
        self.yk = 0.0
        self.setLims(0.0,100.0)
        self.xks = []
        self.pi = 0.0
    
    def setParams(self, ts, kc, ti, td):
        self.kp = float(kc)
        self.ki = ti * ts
        self.kd = td / ts

    def setLims(self, llim, hlim):
        self.llim = -100
        self.hlim = 100             

    def newTemp(self, xk):
        self.xks.append(xk)

    def PV_diff(self):
        if len(self.xks) < 15: return 0.0

        return (sum(self.xks[-15:-5]) - sum(self.xks[-10:]))/10

    def calcPID(self, tset, debug=False):

        error = tset - self.xks[-1]
        self.pp = self.kp * error

        self.pi += (self.ki * error)
        if self.pi > self.hlim:
            self.pi = self.hlim
        elif self.pi < self.llim:
            self.pi = self.llim

        self.pd = self.kd * self.PV_diff()
        self.yk = self.pp + self.pi + self.pd;

        if (self.yk > self.hlim):
            self.yk = self.hlim
        if (self.yk < self.llim):
            self.yk = self.llim

        strings = ["%.2f" % num for num in (self.xks[-1], self.yk, self.pp, self.pi, self.pd)]
        strings = [string.rjust(8) for string in strings]
        print "%s %s %s %s %s" % tuple(strings)

        if debug:
            strings = ["%.2f" % num for num in (self.xks[-1], self.yk, self.pp, self.pi, self.pd)]
            strings = [string.rjust(8) for string in strings]
            print "%s %s %s %s %s" % tuple(strings)
            return self.yk, pp, pi, pd

        return self.yk


class pidpy_simple(object):
    def __init__(self, ts, kc, ti, td):
        self.xk = 0.0

    def newTemp(self, xk):
        self.xk = xk

    def setParams(self, ts, kc, ti, td):
        pass

    def calcPID(self, tset):
        err = tset - self.xk
        yk = 100.0 * err/0.5
        if (yk > 100.0):
            yk = 100.0
        if (yk < -100.0):
            yk = -100.0
        print "yk",yk
        return yk

if __name__=="__main__":
    
    import matplotlib.pyplot as plt
    from random import gauss


    sampleTime = 1
    pid = pidpy(sampleTime,5.0,0.005,0.0)
    
    N = 400
    t = [0.25*i for i in range(N)]
    S = [60 for i in range(100)]
    S.extend([65 for i in range(200)])
    S.extend([60 for i in range(100)])
    new_temp = 40
    D = []
    T = []

    for n in range(N):
        old_temp = new_temp
        setP = S[n]
        duty = pid.calcPID(old_temp, setP)

        temp_add = 0.15*duty/100
        new_temp = old_temp + temp_add
        D.append(duty)
        T.append(new_temp)

        new_temp *= gauss(0.9997, 0.0001)
        
        print "old_temp",old_temp,"duty:",duty,"tempadd:",temp_add,"new_temp:",new_temp

    plt.subplot(2, 1, 1)
    plt.plot(t, T, label="T")
    plt.plot(t, S, label="S")
    plt.ylabel('Temperature (C)')
    plt.grid(True)
    plt.legend(fancybox=True)
    
    plt.subplot(2, 1, 2)
    plt.plot(t, D)
    plt.ylabel('Power (%)')
    plt.grid(True)
    plt.xlabel('time (min)')
    plt.show()