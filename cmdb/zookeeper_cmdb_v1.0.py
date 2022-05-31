#!/usr/bin/env python
# -*- coding:utf-8 -*-
import sys
import subprocess
import platform
import os
import socket
import re
import json
import time
import collections
import traceback
import xml.etree.ElementTree as ET

ZKAGENT_VERSION = "v1.0"
OS_TYPE = platform.system()
hostname = socket.gethostname()
currtime = time.strftime('%Y-%m-%d %H:%M:%S',time.localtime(time.time()))
currtime2 = time.strftime('%Y%m%d%H%M%S',time.localtime(time.time()))

#JSONFILE = hostname + '_Zookeeper_' + currtime2 + '.json'
JSONFILE = '/tmp/enmotech/zookeeper_cmdb/' + hostname + '_Zookeeper_' + currtime2 + '.json'


def printCopyright():
	print("Zookeeper CMDB Collection Agent (%s)" % ZKAGENT_VERSION)
	sys.stdout.flush()

#get zookeeper home
def getZKHOME():
    zookeeper_list = []
    if OS_TYPE == "Linux":
        zookeeper_command = "ps -ef|grep java|grep org.apache.zookeeper.server.quorum.QuorumPeerMain|grep -v grep |grep -io '\Dzookeeper.log.dir.*' | awk '{print $1}' | awk -F '=' '{print $2}'"
        zookeepers = subprocess.Popen(zookeeper_command, shell=True, stdout=subprocess.PIPE).communicate()[0].splitlines()
        for zookeeper in zookeepers:
            zookeeper = zookeeper.decode()[:-12]
            if zookeeper not in zookeeper_list:
                zookeeper_list.append(zookeeper)
        return zookeeper_list

    elif OS_TYPE == "AIX":
        zookeeper_command = "ps -ef|grep java|grep org.apache.zookeeper.server.quorum.QuorumPeerMain|grep -v grep |grep -io '\Dzookeeper.log.dir.*' | awk '{print $1}' | awk -F '=' '{print $2}'"
        zookeepers = subprocess.Popen(zookeeper_command, shell=True, stdout=subprocess.PIPE).communicate()[0].splitlines()
        for zookeeper in zookeepers:
            zookeeper = zookeeper.decode()[:-12]
            if zookeeper not in zookeeper_list:
                zookeeper_list.append(zookeeper)
        return zookeeper_list

    elif OS_TYPE == "HP-UX":
        zookeeper_command = "ps -ef|grep java|grep org.apache.zookeeper.server.quorum.QuorumPeerMain |grep -v grep |grep -io '\Dzookeeper.log.dir.*' | awk '{print $1}' | awk -F '=' '{print $2}'"
        zookeepers = subprocess.Popen(zookeeper_command, shell=True, stdout=subprocess.PIPE).communicate()[0].splitlines()
        for zookeeper in zookeepers:
            zookeeper = zookeeper.decode()[:-12]
            if zookeeper not in zookeeper_list:
                zookeeper_list.append(zookeeper)
        return zookeeper_list
    else:
        print("ERROR! This os (%s) is not supported." % OS_TYPE)

def getHostAllIPs():
    ipstmp = list(set(socket.gethostbyname_ex(socket.gethostname())[-1]))
    ipstmp.append("localhost")
    return ipstmp


ips = getHostAllIPs()
if "127.0.0.1" in ips:
    ips.remove("127.0.0.1")
if "localhost" in ips:
    ips.remove("localhost")


def optionsMatch(express, shelloptions, default):
    outvalue = re.findall(express, shelloptions)
    if len(outvalue) > 1:
        custvalue = re.findall(express)
        if len(custvalue) > 0:
            return custvalue[0]
        else:
            return outvalue[0]
    elif len(outvalue) == 1:
        return outvalue[0]
    else:
        return default


def getCommonInfo(cmdstr):
	return subprocess.Popen(cmdstr, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE).communicate()[0].decode().replace("\n","")


def getCommonInfo02(cmdstr):
    return subprocess.Popen(cmdstr, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE).communicate()[0].decode()


# parse zk info
def parseCI(zkhomes):
    global username,state
    for zkhome in zkhomes:
        if OS_TYPE == "HP-UX":
            java_path = subprocess.Popen("ps -efx|grep %s|grep java|grep -v grep |awk '{print $9}'" % zkhome, shell=True,stdout=subprocess.PIPE).communicate()[0].decode().split("/bin")[0]
        elif OS_TYPE == "AIX":
            java_path = subprocess.Popen("ps -ef|grep %s|grep java|grep -v grep |awk '{print $9}'" % zkhome, shell=True,stdout=subprocess.PIPE).communicate()[0].decode().split("/bin")[0]
        else:
            java_path = subprocess.Popen("ps -ef|grep %s|grep java|grep -v grep |awk '{print $8}'" % zkhome, shell=True,stdout=subprocess.PIPE).communicate()[0].decode().split("/bin")[0]


        if java_path == 'java\n':
            ### get openjdk install path
            whichjava = subprocess.Popen("which %s" % java_path, shell=True, stdout=subprocess.PIPE).communicate()[0].decode()
            if whichjava == '/usr/bin/java\n':
                java_path=os.path.realpath('/usr/bin/java').split("/jre")[0]
            else:
                java_path = os.path.realpath(whichjava).split("/bin")[0]
            (status, javainfo) = subprocess.getstatusoutput('java -version')
            JAVA_VERSION = re.findall("version (.*)\s", javainfo)

        else:
            os.environ['JAVA_HOME'] = java_path
            (status, javainfo) = subprocess.getstatusoutput(java_path + '/bin/java -version')
            JAVA_VERSION = re.findall("version (.*)\s", javainfo)


        JAVA_NUM=float(eval(JAVA_VERSION[0])[0:3])
        #print(JAVA_NUM)

        if javainfo.find("IBM J9") >= 0:
            if javainfo.find("ppc64-64") >= 0:
                runbit = "64"
            else:
                runbit = "32"
            vendor = "IBM JDK"
        elif javainfo.find("jinteg") >= 0:
            if javainfo.find("64-Bit") >= 0:
                runbit = "64"
            else:
                runbit = "32"
            vendor = "HP JDK"
        elif javainfo.find("OpenJDK") >= 0:
            if javainfo.find("64-Bit") >= 0:
                runbit = "64"
            else:
                runbit = "32"
            vendor = "OpenJDK"
        else:
            if javainfo.find("64-Bit") >= 0:
                runbit = "64"
            else:
                runbit = "32"
            vendor = "Oracle JDK"
        # use zkserver.sh print-cmd  get zk info
        (status, zkserverprintcmdinfo) = subprocess.getstatusoutput(zkhome + '/bin/zkServer.sh print-cmd')

        maxheap = optionsMatch("-Xmx(.+?[mMgG])\S*", zkserverprintcmdinfo, "")
        minheap = optionsMatch("-Xms(.+?[mMgG])\S*", zkserverprintcmdinfo, "")

        if JAVA_NUM >= 1.8:
            gcpolicy = optionsMatch("(-XX:\+UseSerialGC|-XX:\+UseParallelGC|-XX:\+UseConMarkSweepGC|-XX:\+UseG1GC|-Xgcpolicy:\S*)",zkserverprintcmdinfo, "")
            zkjvm.append(
                {
                    "zkhome": zkhome,
                    "javahome": java_path,
                    "maxheap": maxheap,
                    "minheap": minheap,
                    "gcpolicy": gcpolicy,
                    "runbit": runbit,
                    "javaversion": eval(JAVA_VERSION[0]),  # use eval remove ""
                    "vendor": vendor
                }
            )
        else:
            maxperm = optionsMatch("-XX:MaxPermSize=(.+?[mMgG])\S*", zkserverprintcmdinfo, "")
            minperm = optionsMatch("-XX:MinPermSize=(.+?[mMgG])\S*", zkserverprintcmdinfo, "")
            gcpolicy = optionsMatch("(-XX:\+UseSerialGC|-XX:\+UseParallelGC|-XX:\+UseConMarkSweepGC|-XX:\+UseG1GC|-Xgcpolicy:\S*)",zkserverprintcmdinfo, "")
            zkjvm.append(
                {
                    "zkhome": zkhome,
                    "javahome": java_path,
                    "maxheap": maxheap,
                    "minheap": minheap,
                    "maxperm": maxperm,
                    "minperm": minperm,
                    "gcpolicy": gcpolicy,
                    "runbit": runbit,
                    "javaversion": eval(JAVA_VERSION[0]),  # use eval remove ""
                    "vendor": vendor
                }
            )

        # use zkserver.sh version  get zk version
        (status, zkserverversion) = subprocess.getstatusoutput(zkhome + '/bin/zkServer.sh version')
        zkprodname = optionsMatch("Apache ZooKeeper", zkserverversion, "")

        zkversion = optionsMatch("version \S*",zkserverversion,"")[8: ]
        #print(zkversion)

        zkrunusercommand = "ps -ef|grep java| grep org.apache.zookeeper.server.quorum.QuorumPeerMain |grep %s| grep -v grep | awk '{print $1}'" %zkhome
        zkrunuser = getCommonInfo(zkrunusercommand)
        zkusercommand = "ls -lrt %s|grep -v total|grep bin |awk -F ' ' '{print $3}'" % zkhome
        zkgroupcommand = "ls -lrt %s|grep -v total|grep bin |awk -F ' ' '{print $4}'" %zkhome
        zkuser = getCommonInfo(zkusercommand)
        zkgroup = getCommonInfo(zkgroupcommand)

        '''
        zkgroupIDcommand = "cat /etc/passwd |grep %s | awk -F ':' '{print $4}'  " %zkuser
        zkgroupIDoutput = getCommonInfo(zkgroupIDcommand)
        zkgroupcommand = "cat /etc/group | grep %s | awk -F ':' '{print $1}'" %zkgroupIDoutput
        zkgroup = getCommonInfo(zkgroupcommand)
        '''

        zkconfigfile = optionsMatch("Using config: (.*)\S*", zkserverprintcmdinfo, "")
        #print(zkconfigfile)
        zkstartscript=zkhome+'/bin/zkServer.sh'
        zkstopscript=zkhome+'/bin/zkServer.sh'

        zkconfigfileinfocommand = "cat %s |grep -v '#' | grep -v '^$' " %zkconfigfile
        zkconfigfileoutput = getCommonInfo02(zkconfigfileinfocommand)
        #print(zkconfigfileoutput)
        zktickTime = optionsMatch("tickTime=(.*)\S*", zkconfigfileoutput, "2000")
        zkinitLimit = optionsMatch("initLimit=(.*)\S*",zkconfigfileoutput,"10")
        zksyncLimit = optionsMatch("syncLimit=(.*)\S*", zkconfigfileoutput, "10")
        zkdataDir = optionsMatch("dataDir=(.*)\S*", zkconfigfileoutput, "")
        zkmaxClientCnxns = optionsMatch("zkmaxClientCnxns=(.*)\S*", zkconfigfileoutput, "60")
        zkautopurge_snapRetainCount = optionsMatch("autopurge.snapRetainCount=(.*)\S*", zkconfigfileoutput, "3")
        zkautopurge_purgeInterval = optionsMatch("autopurge.purgeInterval=(.*)\S*", zkconfigfileoutput, "3")

        (status, zkserverversion) = subprocess.getstatusoutput(zkhome + '/bin/zkServer.sh status')
        zkmode = optionsMatch("Mode: (.*)\S*", zkserverversion, "")
        if zkmode == 'standalone':
            zkclientPort = optionsMatch("clientPort=(.*)\S*", zkconfigfileoutput, "2181")
            # zkconfig json
            zkConfig.append(
                {
                    "zkhome": zkhome,
                    "zktickTime": zktickTime,
                    "zkinitLimit": zkinitLimit,
                    "zksyncLimit": zksyncLimit,
                    "zkdataDir": zkdataDir,
                    "zkmaxClientCnxns": zkmaxClientCnxns,
                    "zkautopurge.snapRetainCount": zkautopurge_snapRetainCount,
                    "zkautopurge.purgeInterval": zkautopurge_purgeInterval,
                    "zkmode": zkmode,
                    "zkport": zkclientPort
                }
            )
        else:
            zkmyidcommand = "cat %s/myid" %zkdataDir
            zkmyid = getCommonInfo(zkmyidcommand)
            zkclientPort = optionsMatch("clientPort=(.*)\S*", zkconfigfileoutput, "")
            #print(len(zkclientPort))

            if len(zkclientPort) ==0 :
                serverregstr = "server.%s" % zkmyid
                zkserverport = optionsMatch("%s=(.*)\S*" % serverregstr, zkconfigfileoutput, "")
                stsport = zkserverport.split(";")[0].split(":")[1]
                stsvoteport = zkserverport.split(";")[0].split(":")[2]
                zkclientPort = zkserverport.split(";")[1]
                zkport = zkclientPort +',' +stsport +','+ stsvoteport
                zkConfig.append(
                    {
                        "zkhome": zkhome,
                        "zktickTime": zktickTime,
                        "zkinitLimit": zkinitLimit,
                        "zksyncLimit": zksyncLimit,
                        "zkdataDir": zkdataDir,
                        "zkmaxClientCnxns": zkmaxClientCnxns,
                        "zkautopurge.snapRetainCount": zkautopurge_snapRetainCount,
                        "zkautopurge.purgeInterval": zkautopurge_purgeInterval,
                        "zkmode": zkmode,
                        "zkmyid": zkmyid,
                        "zkport": zkport
                    }
                )
            else:
                serverregstr = "server.%s" % zkmyid
                zkserverport = optionsMatch("%s=(.*)\S*" % serverregstr, zkconfigfileoutput, "")
                stsport = zkserverport.split(":")[1]
                stsvoteport = zkserverport.split(":")[2]
                zkport = zkclientPort + ',' + stsport + ',' + stsvoteport
                # zkconfig json
                zkConfig.append(
                    {
                        "zkhome": zkhome,
                        "zktickTime": zktickTime,
                        "zkinitLimit": zkinitLimit,
                        "zksyncLimit": zksyncLimit,
                        "zkdataDir": zkdataDir,
                        "zkmaxClientCnxns": zkmaxClientCnxns,
                        "zkautopurge.snapRetainCount": zkautopurge_snapRetainCount,
                        "zkautopurge.purgeInterval": zkautopurge_purgeInterval,
                        "zkmode": zkmode,
                        "zkmyid": zkmyid,
                        "zkport": zkport
                    }
                )

        #zkproduct json
        zkProduct.append({
            "zkhome": zkhome,
            "zkprodname": zkprodname,
            "zkversion": zkversion,
            "zkrunuser": zkrunuser,
            "zkuser": zkuser,
            "zkgroup": zkgroup,
            "zkconfigfile": zkconfigfile,
            "zkstartscript": zkstartscript,
            "zkstopscript": zkstopscript
        })





# generate json
def buildCIJSON():
    zookeepercijson = collections.OrderedDict()
    zookeeper_jvm = []
    zookeeper_config = []
    zookeeper_product = []
    for jvm in zkjvm:
        JAVA_NUM = float(jvm["javaversion"][0:3])

        ### get java_num  if java_num >= 1.8 don't set maxperm minperm parameter
        if JAVA_NUM >= 1.8:
            zookeeper_jvm.append(collections.OrderedDict([
                ("zkhome", jvm["zkhome"]),
                ("javahome", jvm["javahome"]),
                ("maxheap", jvm["maxheap"]),
                ("minheap", jvm["minheap"]),
                ("gcpolicy", jvm["gcpolicy"]),
                ("javaversion", jvm["javaversion"]),
                ("runbit", jvm["runbit"]),
                ("vendor", jvm["vendor"])
            ]))
        else:
            zookeeper_jvm.append(collections.OrderedDict([
                ("zkhome", jvm["zkhome"]),
                ("javahome", jvm["javahome"]),
                ("maxheap", jvm["maxheap"]),
                ("minheap", jvm["minheap"]),
                ("maxperm", jvm["maxperm"]),
                ("minperm", jvm["minperm"]),
                ("gcpolicy", jvm["gcpolicy"]),
                ("runbit", jvm["runbit"]),
                ("javaversion", jvm["javaversion"]),
                ("vendor", jvm["vendor"])
            ]))


    for config in zkConfig:
        zkmode = config["zkmode"]
        if zkmode == 'standalone':
            zookeeper_config.append(collections.OrderedDict([
            ("zkhome", config["zkhome"]),
            ("zktickTime",config["zktickTime"]),
            ("zkinitLimit", config["zkinitLimit"]),
            ("zksyncLimit", config["zksyncLimit"]),
            ("zkdataDir", config["zkdataDir"]),
            ("zkmaxClientCnxns", config["zkmaxClientCnxns"]),
            ("zkautopurge.snapRetainCount",config["zkautopurge.snapRetainCount"]),
            ("zkautopurge.purgeInterval", config["zkautopurge.purgeInterval"]),
            ("zkmode",config["zkmode"]),
            ("zkport", config["zkport"])
            ]))
        else:
            zookeeper_config.append(collections.OrderedDict([
            ("zkhome", config["zkhome"]),
            ("zktickTime",config["zktickTime"]),
            ("zkinitLimit", config["zkinitLimit"]),
            ("zksyncLimit", config["zksyncLimit"]),
            ("zkdataDir", config["zkdataDir"]),
            ("zkmaxClientCnxns", config["zkmaxClientCnxns"]),
            ("zkautopurge.snapRetainCount",config["zkautopurge.snapRetainCount"]),
            ("zkautopurge.purgeInterval", config["zkautopurge.purgeInterval"]),
            ("zkmode",config["zkmode"]),
            ("zkmyid", config["zkmyid"]),
            ("zkport", config["zkport"])
            ]))





    for product in zkProduct:
        zookeeper_product.append(collections.OrderedDict([
            ("zkhome",product["zkhome"]),
            ("zkprodname",product["zkprodname"]),
            ("zkversion",product["zkversion"]),
            ("zkrunuser", product["zkrunuser"]),
            ("zkuser",product["zkuser"]),
            ("zkgroup",product["zkgroup"]),
            ("zkconfigfile",product["zkconfigfile"]),
            ("zkstartscript",product["zkstartscript"]),
            ("zkstopscript",product["zkstopscript"])
        ]))

    zookeepercijson.update(hostname=hostname)
    zookeepercijson.update(ipaddress=":".join(ips))
    zookeepercijson.update(zookeeper_product=zookeeper_product)
    zookeepercijson.update(zookeeper_jvm=zookeeper_jvm)
    zookeepercijson.update(zookeeper_config=zookeeper_config)
    zookeepercijson.update(collection_time=currtime)


    os.system("mkdir -p /tmp/enmotech/zookeeper_cmdb")
    with open(JSONFILE, "w") as f:
         json.dump(zookeepercijson, f)


if __name__ == '__main__':

    zkjvm = []
    zkProduct = []
    zkConfig = []

    if sys.version[:1] == '3':
        try:
            printCopyright()

            zkprocessCountCommand="ps -ef|grep java| grep org.apache.zookeeper.server.quorum.QuorumPeerMain |grep -v grep | wc -l"
            zkprocessoutput = getCommonInfo(zkprocessCountCommand)
            if eval(zkprocessoutput) == 0:
                print("no zookeeper process")
                sys.exit(0)

            zkhomes = getZKHOME()
            parseCI(zkhomes)
            buildCIJSON()
        except Exception as e:
            print("error! Execute failed ,message : ")
            print("%s" % e.format_exc())
        sys.exit(0)
    else:
        exit("only support python3,current python version is %s" % sys.version[:5])
