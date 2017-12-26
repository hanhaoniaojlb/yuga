# -*- coding: utf-8 -*-
from DevicesManager import *
import time
import threading

class interactive(threading.Thread):
    def __init__(self):
        threading.Thread.__init__(self)

    def run(self):
        while True:
            print '>>'
            cmd = raw_input()
            if cmd == "help":
                self.echoHelp()
            elif cmd == "devices":
                DeviceManager().showAllDevices()
            elif cmd.find("status") == 0:
                if len(cmd.split(' '))  > 1:
                    device = cmd.split(' ')[1]
                    DeviceManager().showOneDeviceStatus(device)
                else:
                    print "Error device name"
            elif cmd.find("startall") == 0:
                detail = cmd.split(' ')
                param = []
                if len(detail) > 1:
                    param = detail[1:len(detail)]
                DeviceManager().startAllDevices(param)
            elif cmd.find("start") == 0:
                detail = cmd.split(' ')
                if len(detail) >= 2:
                    name = detail[1]
                    param = []
                    if len(detail) > 2:
                        param = detail[2:len(detail)]
                    DeviceManager().startOneDevice(name, param)
            elif cmd.find("stopall") == 0:
                DeviceManager().stopAllDevices()
            elif cmd.find("stop") == 0:
                detail = cmd.split(' ')
                if len(detail) > 1:
                    name = detail[1]
                    DeviceManager().stopOneDevice(name)
            elif cmd.find("setmodeall") == 0:
                detail = cmd.split(' ')
                if len(detail) > 1:
                    mode = detail[1]
                    DeviceManager().setAllMode(mode)
            elif cmd.find("setmode") == 0:
                detail = cmd.split(' ')
                if len(detail) >= 2:
                    name = detail[1]
                    mode = detail[2]
                    DeviceManager().setOneDeviceMode(name, mode)
            else:
                print 'Unknown Cmd'
        time.sleep(0.5)

    def echoHelp(self):
        print "devices                          :----- show all devices"
        print "status [device name]             :----- show some device status"
        print "start [device name] [param]      :----- start one device Task"
        print "startall [param]                 :----- start all devices Task"
        print "stop [device name]               :----- stop one device task "
        print "stopall                          :----- stop All devices Task"
        print "setmodeall [mode]                :----- set moudle work mode"
        print "setmode [device name] [mode]     :----- set moudle work mode"

if __name__ == '__main__':
    try:

        DeviceManager().initNetwork()
        ia = interactive()
        ia.setDaemon(True)
        ia.start()
        while True:
            DeviceManager().checkDeviceOnline()
            time.sleep(2)
    except Exception, exc:
        print exc
