from multiprocessing import Process, Pipe, Queue, current_process
from Queue import Full
from subprocess import Popen, PIPE, call
from datetime import datetime
import time, random, serial, os, signal

def tempControlProc(child_conn):
    while (True):

        val = 5
        while child_conn.poll(): #Poll Heat Process Pipe
            val = child_conn.recv() #non blocking receive from Heat Process
            print "recv"

        print "val",val

        time.sleep(2)


if __name__ == '__main__':

    parent_conn, child_conn = Pipe()
    p = Process(name = "tempControlProc", target=tempControlProc, args=(child_conn,))
    p.start()

    time.sleep(10)

    parent_conn.send(6)
    print "sent"

    time.sleep(80)
     

