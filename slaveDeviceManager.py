# -*- coding: utf-8 -*-
import consttype
from socket import *
import threading
import json
import time
import os 
import psutil
import serial


consttype.localIpAddr = (u'127.0.0.1', 6601)
consttype.masterIpAddr = (u'127.0.0.1', 6600)


class taskManager(object):
    def __init__(self):
        self.currentTask = ''
        self.taskStatus = 0
   
    def doNewTask(self, task):
        if self.currentTask == task and self.taskStatus == 1:
            return
        else:
            self.task = task
            self.stopTask()
            self.doTask()
            self.currentTask = task
            
    def doTask(self):
        #task jiexi        
        #os.system('')
        print 'start task'
        self.taskStatus = 1
    
    def stopTask(self):
        if self.taskStatus == 0:
            return  
        #kill process      
        os.system('')
        print 'stop task'
        self.taskStatus = 0

    def getTaskStatus(self):
        return self.taskStatus


class slaveDeviceManager(object):
    def __init__(self):
        self.msgList = []
        self.task = {}
        self.status = 'init'      # init ,dailing, ready, running
        self.m_moudle = DailMoudleManager()
        self.m_taskManager = taskManager()
        self.taskControlBit = True

    def initNetwork(self):
        self.udpServer = socket(AF_INET, SOCK_DGRAM)
        self.udpServer.bind(consttype.localIpAddr)
        self.threadListen = threading.Thread(target=self.udpListenTarget, name="udpListen")
        self.threadListen.start()
        self.threadMsgHandler = threading.Thread(target=self.dealwithMsgTarget, name="msgHandler")
        self.threadMsgHandler.start()


    def moudleMonitorWork(self, task):
        moudleStatus = 0
        disconnectTime = 0

        while self.taskControlBit:
            if moudleStatus == 0:
                if self.m_moudle.checkPort():
                    moudleStatus = 1
                    self.m_moudle.setMoudleMode()
                else:
                    self.sendUpdateStaus("no port")
            if moudleStatus == 1:
                if self.m_moudle.checkRegister():
                    moudleStatus = 2
                else:
                    self.sendUpdateStaus("not register")
            if moudleStatus == 2:
                self.m_moudle.dialPPP()
                self.status = "dailing"
                moudleStatus = 3
            if moudleStatus == 3:
                if self.m_moudle.checkPppStatus():
                    moudleStatus = 4
                elif not self.m_moudle.checkPppProcess():
                    moudleStatus = 2
                    self.sendUpdateStaus("error")
            if moudleStatus == 4:
                if self.m_moudle.checkConnectionToInternet():
                    if not self.status == "ready":
                        self.status = "ready"
                        self.sendUpdateStaus("connected")
                    self.m_taskManager.doNewTask(task)
                    self.status = "running"
                    self.sendUpdateStaus("")
                    disconnectTime = 0
                else:
                    disconnectTime += 1
                if disconnectTime == 10:
                    moudleStatus = 0
                    self.status = "reinit"
                    self.sendUpdateStaus("disconnect")
                    self.m_moudle.stopDialPPP()
                    if self.m_taskManager.getTaskStatus() == 1:
                        self.m_taskManager.stopTask()
                    ## recheck

            time.sleep(1)

    def StartTask(self, task):
        self.taskControlBit = True
        self.threadTask = threading.Thread(target=self.moudleMonitorWork, name="taskHandler", args=(task,))
        self.threadTask.start()

    def StopTask(self):
        if self.threadTask is not None and self.threadTask.is_alive():
            self.taskControlBit = False
            self.threadTask.join()
        self.m_moudle.stopDialPPP()

    def sendMsgToMaster(self, msg):
        self.udpServer.sendto(msg, consttype.masterIpAddr)

    def sendHeartbeat(self):
        heartbeat = {"type": "heartbeat"}
        js = json.dumps(heartbeat, skipkeys=True)
        self.sendMsgToMaster(js)

    def sendUpdateStaus(self, desc):
        info = {"type": "update_status"}
        info["status"] = self.status
        info["desc"] = desc
        js = json.dumps(info, skipkeys=True)
        self.sendMsgToMaster(js)

    def sendQueryResp(self,target,status):
        rsp = {"type": "query_resp"}
        rsp["target"] = target
        rsp["status"] = status
        js = json.dumps(rsp, skipkeys=True)
        #print js
        self.sendMsgToMaster(js)

    def sendSettingResp(self, result, err = ''):
        rsp = {"type": "setting_resp"}
        rsp["result"] = result
        rsp["error"] = err
        js = json.dumps(rsp, skipkeys=True)
        #print js
        self.sendMsgToMaster(js)

    def sendTaskControlResp(self, type,result):
        rsp = {"type": "task_control_resp"}
        rsp["task_type"] = type
        rsp["result"] = result
        js = json.dumps(rsp, skipkeys=True)
        #print js
        self.sendMsgToMaster(js)
    
    def udpListenTarget(self):
        while True:
            data, addr = self.udpServer.recvfrom(1024)
            self.msgList.append([data, addr])

    def dealwithMsgTarget(self):
        while True:
            if len(self.msgList) > 0:
                data, addr = self.msgList.pop(0)
                decodeData = json.loads(data)

                if decodeData["type"] == "setting":
                    mode = decodeData["mode"]
                    if self.m_taskManager.taskStatus == 1 and not self.m_moudle.mode == mode:
                        self.StopTask()
                        self.m_moudle.setMoudleMode(mode)
                        self.StartTask(self.m_moudle.currentTask)
                    else:
                        self.m_moudle.mode = 'lte'
                    self.sendSettingResp("ok")
                elif decodeData["type"] == "task_control":
                    if decodeData["task_type"] == "start":
                        param = decodeData["param"]
                        ##make task with longlong
                        task = ""
                        self.StartTask(task)
                    elif decodeData["task_type"] == "stop":
                        self.StopTask()
                elif decodeData["type"] == "query":
                    if decodeData["target"] == "task":
                        self.sendQueryResp("task", self.status)
            time.sleep(0.1)


class DailMoudleManager(object):
    def __init__(self):
        self.mode = 'lte'
        self.status = 'idle'
        self.atPort = '/dev/ttyUSB0'
        self.timeout = 1

    def setMoudleMode(self, mode='default'):
        if not self.status == 'idle':
            self.stopDialPPP()
        if not mode == 'default':
            self.mode = mode
        if self.mode == 'lte':
            self.serialCom.write('AT^MODECONFIG=38\r\n')
            self.mode = mode
        elif self.mode == 'wcdma':
            self.serialCom.write('AT^MODECONFIG=14\r\n')
            self.mode = mode

    def checkPort(self):
        tmp = os.popen('ls /dev/ttyUSB*').readlines()
        if len(tmp) == 3:
            self.atPort = tmp[0].strip('\n')
            self.serialCom = serial.Serial(self.atPort, 115200)
            self.serialCom.timeout = 1

            return True
        else:
            return False

    def checkRegister(self):
        self.serialCom.write('AT^SYSINFO\r\n')
        time.sleep(0.5)
        resp = self.serialCom.readlines()
        for info in resp:
            if "SYSINFO" in info:
                if info.split(',')[0][-1] == '2':
                    return True
                else:
                    return False
        return False

    def checkPppStatus(self):
        ifInfos = psutil.net_if_addrs()
        if 'ppp0' in ifInfos.keys():
            return True
        else:
            return False

    def checkPppProcess(self):
        tmp = os.popen('ps -A | grep pppd').readline()
        if not tmp =="":
            return True
        else:
            return False

    def checkConnectionToInternet(self):
        tmp = os.popen('ping -c 3 -i 0.5 114.114.114.114 | grep \'0 received\' | wc -l').readline()
        if tmp != '0\n':
            return False
        else:
            return True

    def dialPPP(self):
        os.system('./yuga.lte-pppd&')
        self.status = 'dialing'
        time.sleep(2) 
        
    def stopDialPPP(self):
        os.system('killall pppd')
        time.sleep(2)
        self.status = 'idle' 


slaveDevice = slaveDeviceManager()
slaveDevice.initNetwork()
while True:
    slaveDevice.sendHeartbeat()    
    time.sleep(3)