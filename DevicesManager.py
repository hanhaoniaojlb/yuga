# -*- coding: utf-8 -*-
import consttype
import json
from Singleton import *
from socket import *
import datetime
import time
import threading
import ConfigParser

consttype.MasterIpAddr = '192.168.1.200'
consttype.MasterPort = 60000
consttype.SlaveIpPort = 60001
consttype.UiIpAddr = '192.168.1.39'
consttype.UiPort = 60002
consttype.ConfigPath = "./config.conf"


class DeviceManager(CSingleton):
    def __init__(self):
        self.deviceList = {}
        self.msgList = []
        self.readConfig()

    def registerNewDevice(self, device):
        self.deviceList[device.name] = device

    def readConfig(self):
        cf = ConfigParser.ConfigParser()
        cf.read(consttype.ConfigPath)

        consttype.MasterIpAddr = cf.get("netconfig","master_ipaddr")
        consttype.MasterPort = int(cf.get("netconfig", "master_port"))
        consttype.SlaveIpPort = int(cf.get("netconfig", "slave_port"))
        consttype.UiPort = int(cf.get("netconfig", "ui_port"))

    def getDeviceNumbers(self):
        return len(self.deviceList)

    def initNetwork(self):
        self.udpServer = socket(AF_INET, SOCK_DGRAM)
        self.udpServer.bind((consttype.MasterIpAddr, consttype.MasterPort))
        self.threadListen = threading.Thread(target=self.udpListenTarget, name="udpListen")
        self.threadListen.setDaemon(True)
        self.threadListen.start()
        self.threadMsgHandler = threading.Thread(target=self.dealwithMsgTarget, name="msgHandler")
        self.threadMsgHandler.setDaemon(True)
        self.threadMsgHandler.start()

    def udpListenTarget(self):
        while True:
            data, ip = self.udpServer.recvfrom(1024)
            addr = ip[0]
            self.msgList.append([data, addr])

    def dealwithMsgTarget(self):
        while True:
            if len(self.msgList) > 0:
                data, addr = self.msgList.pop(0)
                #print addr
                if addr == consttype.UiIpAddr:
                    self.dealwithUiCmd(data)
                else:
                    decodeData = json.loads(data)
                    if decodeData["type"] == "heartbeat":
                        self.checkHeartbeat(addr)
                    elif decodeData["type"] == "update_status":
                        self.updateDeviceStatus(decodeData, addr)
                    elif decodeData["type"] == "setting_resp":
                        if decodeData['result'] == 'ok':
                            print u'设置参数成功'
                        else:
                            print u'设置参数失败'
                    elif decodeData["type"] == "task_control_resp":
                        if decodeData['task_type'] == 'start':
                            if decodeData['result'] == 'ok':
                                print u'任务启动成功'
                            else:
                                print u'任务启动失败'
                        elif decodeData['task_type'] == 'stop':
                            if decodeData['result'] == 'ok':
                                print u'任务停止成功'
                            else:
                                print u'任务停止失败'
            #time.sleep(0.01)

    def dealwithUiCmd(self,data):
        decodeData = json.loads(data)
        if decodeData["type"] == "setting":
            for (key, device) in self.deviceList.items():
                if device.onlineStatus == "online":
                    self.udpServer.sendto(data, (device.name, consttype.SlaveIpPort))
        elif decodeData["type"] == "query":
            target = decodeData["target"]
            self.reportDevicesStatusToUi(target)
        elif decodeData["type"] == "task_control":
            target = decodeData["target"]
            for slave in target:
                self.sendUiCmdTaskControl(slave, decodeData["task_type"], decodeData["param"])


    def sendUiCmdTaskControl(self, slave, control, param):
        paramEncode = []
        cmd = {"type": "task_control"}
        cmd["task_type"] = control
        if control == "start":
            paramEncode.append("-h " + param[0])
            paramEncode.append("-p " + param[1])
            paramEncode.append("-m " + param[2])
            paramEncode.append("-i " + param[3])
        cmd["param"] = paramEncode
        js = json.dumps(cmd, skipkeys=True)
        self.udpServer.sendto(js, (slave, consttype.SlaveIpPort))

    def reportDevicesStatusToUi(self, target):
        cmd = {"type": "query_resp"}
        devices = []

        for (key, device) in self.deviceList.items():
            if device.name in target:
                deviceInfo = {}
                deviceInfo['ip'] = device.name
                if device.status != "offline":
                    deviceInfo['status'] = device.status
                else:
                    deviceInfo['status'] = "offline"
                deviceInfo['connections'] = device.connections
                devices.append(deviceInfo)
        cmd["devices"] = devices
        js = json.dumps(cmd, skipkeys=True)
        self.udpServer.sendto(js, (consttype.UiIpAddr, consttype.UiPort))

    def checkHeartbeat(self, addr):
        if self.deviceList.has_key(addr):
            self.deviceList[addr].lastUpdateTime = datetime.datetime.now()
            if self.deviceList[addr].onlineStatus == 'offline':
                self.deviceList[addr].onlineStatus = 'online'
                print u'设备 ' + addr + 'online\r\n'
        else:
            newDevice = slaveDevice(self.udpServer, addr)

            newDevice.ip = addr
            newDevice.lastUpdateTime = datetime.datetime.now()
            self.registerNewDevice(newDevice)
            print u'新设备 ' + addr + u'注册\r\n'

    def updateDeviceStatus(self, decodeData, addr):
        if self.deviceList.has_key(addr):
            self.deviceList[addr].status = decodeData['status']
            self.deviceList[addr].desc = decodeData['desc']
            if self.deviceList[addr].status == "running":
                self.deviceList[addr].connections = int(self.deviceList[addr].desc)
        decodeData["ip"] = addr
        js = json.dumps(decodeData, skipkeys=True)
        self.udpServer.sendto(js, (consttype.UiIpAddr, consttype.UiPort))


    def showAllDevices(self):
        for device in self.deviceList:
            print u'设备'+ self.deviceList[device].name + u' ' + self.deviceList[device].onlineStatus + u'  设备状态：' +  self.deviceList[device].status +u'  desc：' +  self.deviceList[device].desc\
                  + u'  最后更新时间:' + self.deviceList[device].lastUpdateTime.strftime('%Y-%m-%d %H:%M:%S')

    def showOneDeviceStatus(self,name):
        if name in self.deviceList.keys():
            print u'设备'+self.deviceList[name].name+ u'  设备状态：' +  self.deviceList[name].status
        else:
            print u'No such devices'

    def startAllDevices(self,param):
        for device in self.deviceList:
            self.deviceList[device].startTask(param)
        print 'finish'

    def startOneDevice(self, name, param):
        if name in self.deviceList.keys():
            self.deviceList[name].startTask(param)
            print 'finish'
        else:
            print 'unknown name'

    def stopAllDevices(self):
        for device in self.deviceList:
            print self.deviceList[device].stopTask()
        print 'finish'

    def stopOneDevice(self, name):
        if name in self.deviceList.keys():
            self.deviceList[name].stopTask()
            print 'finish'
        else:
            print 'unknown name'

    def setAllMode(self, mode):
        for device in self.deviceList:
            print self.deviceList[device].setMode(mode)
        print 'finish'

    def setOneDeviceMode(self, name, mode):
        if name in self.deviceList.keys():
            self.deviceList[name].setMode(mode)
            print 'finish'
        else:
            print 'unknown name'

    def checkDeviceOnline(self):
        for (key, device) in self.deviceList.items():
            timenow = datetime.datetime.now()
            deltaSecond = (timenow - device.lastUpdateTime).seconds

            if deltaSecond > 20:
                device.onlineStatus = 'offline'
                print u'设备'+device.name + device.onlineStatus + '\r\n'


class slaveDevice(object):
    def __init__(self, udpServer, name):
        self.socket = udpServer
        self.name = name
        self.ip = ''
        self.onlineStatus  = 'online'
        self.status = 'idle'
        self.connections = 0
        self.lastUpdateTime = None
        self.desc = ''

    def startTask(self, param):
        cmd = {"type": "task_control"}
        cmd["task_type"] = "start"
        cmd["param"] = param
        js = json.dumps(cmd, skipkeys=True)
        self.socket.sendto(js,(self.ip, consttype.SlaveIpPort))

    def stopTask(self):
        cmd = {"type": "task_control"}
        cmd["task_type"] = "stop"
        cmd["param"] = ""
        js = json.dumps(cmd, skipkeys=True)
        self.socket.sendto(js, (self.ip, consttype.SlaveIpPort))

    def setMode(self, mode):
        cmd = {"type": "setting"}
        cmd["mode"] = mode
        js = json.dumps(cmd, skipkeys=True)
        self.socket.sendto(js, (self.ip, consttype.SlaveIpPort))



