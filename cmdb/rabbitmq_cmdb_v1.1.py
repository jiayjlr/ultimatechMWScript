#!/usr/bin/env python
# -*- coding:utf-8 -*-
# python3

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
from multiprocessing import cpu_count

RMQAGENT_VERSION = "v1.1"
OS_TYPE = platform.system()
hostname = socket.gethostname()
currtime = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time()))
currtime2 = time.strftime('%Y%m%d%H%M%S', time.localtime(time.time()))
JSONFILE = '/tmp/enmotech/rmq_cmdb/' + hostname + '_rmq_' + currtime2 + '.json'


def getRMQHome():
    rmq_list = []
    if OS_TYPE == "Linux":
        rmq_command = "ps -ef|grep rabbit|grep -v grep|grep -v rabbitmq-server|awk '{print $2}'"
        rmqs = subprocess.Popen(rmq_command, shell=True, stdout=subprocess.PIPE).communicate()[0].splitlines()
        for rmq in rmqs:
            rmq = rmq.decode()[:-12]
            if rmq not in rmq_list:
                rmq_list.append(rmq)
        return rmq_list

    elif OS_TYPE == "AIX":
        if OS_TYPE == "Linux":
            rmq_command = "ps -ef|grep rabbit|grep -v grep|grep -v rabbitmq-server|awk '{print $2}'"
            rmqs = subprocess.Popen(rmq_command, shell=True, stdout=subprocess.PIPE).communicate()[0].splitlines()
            for rmq in rmqs:
                rmq = rmq.decode()[:-12]
                if rmq not in rmq_list:
                    rmq_list.append(rmq)
            return rmq_list

    elif OS_TYPE == "HP-UX":
        if OS_TYPE == "Linux":
            rmq_command = "ps -efx|grep rabbit|grep -v grep|grep -v rabbitmq-server|awk '{print $2}'"
            rmqs = subprocess.Popen(rmq_command, shell=True, stdout=subprocess.PIPE).communicate()[0].splitlines()
            for rmq in rmqs:
                rmq = rmq.decode()[:-12]
                if rmq not in rmq_list:
                    rmq_list.append(rmq)
            return rmq_list
    else:
        print(("ERROR! This os (%s) is not supported." % OS_TYPE))


def getHostAllIPs():
    ipstmp = list(set(socket.gethostbyname_ex(socket.gethostname())[-1]))
    ipstmp.append("localhost")
    return ipstmp


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


def getOSInfo(cmdstr):
    return subprocess.Popen(cmdstr, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE).communicate()[0].decode().strip()


def getServerInfo(cmdstr):
    return subprocess.Popen(cmdstr, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE).communicate()[0].decode().replace("\n","")


def getConfigInfo(cmdstr):
    return subprocess.Popen(cmdstr, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE).communicate()[0].decode().replace("\n","")

def getConfigInfo1(cmdstr):
    return subprocess.Popen(cmdstr, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE).communicate()[0].decode()

def parseCI(rmq_homes):
    global username, state
    for rmq_home in rmq_homes:
        # rmq server info
        rmq_prod_name = "Rabbitmq"
        rmq_home = getServerInfo("rabbitmq-diagnostics  -q status|grep 'Enabled plugin file'|awk -F ':' '{print $NF}'|awk -F 'etc' '{print $1}'")
        rmq_prod_version = getServerInfo("rabbitmq-diagnostics -q status|grep  'RabbitMQ version'|awk -F ':' '{print $NF}'")
        rmq_prod_logpath = getServerInfo("rabbitmq-diagnostics -q status|sed -n /'Log file(s)'/,/'Alarms'/p|grep -v 'Log file(s)'|grep -v 'Alarms'|grep -v '^$'")[3:]
        rmq_ip_addr = subprocess.Popen("ip addr show |grep 'state UP' -A 2| grep 'inet ' |grep -v 127.0.0. |head -1|cut -d ' ' -f6|cut -d/ -f1", shell=True, stdout=subprocess.PIPE).communicate()[0].decode().replace("\n","")
        rmq_run_user = getServerInfo("ps -ef|grep rabbit|grep -v grep|grep -v rabbitmq-server|grep -v daemon|awk -F ' ' '{print $1}'").replace("\n","")
        command1 = "ls -lrt %s|grep -v total|grep sbin |awk -F ' ' '{print $4}'" %rmq_home
        command2 = "ls -lrt %s|grep -v total|grep sbin |awk -F ' ' '{print $3}'" %rmq_home
        rmq_username =getServerInfo(command1)
        rmq_groupname = getServerInfo(command2)
        rmq_serverproperties = getServerInfo("rabbitmq-diagnostics -q status|sed -n /'Config files'/,/'Log file(s)'/p|grep -vi 'Config files'|grep -vi 'Log file(s)'|grep -v ^$|awk -F ' ' '{print $NF}'")
        rmq_serverproperties1 = getServerInfo("rabbitmq-diagnostics -q status|sed -n /'Config files'/,/'Log file(s)'/p|grep -vi 'Config files'|grep -vi 'Log file(s)'|grep -v ^$|awk -F ' ' '{print $NF}'|wc -l")
        rmq_start_script = rmq_home + '/sbin/rabbitmq-server '
        rmq_stop_script = rmq_home + '/sbin/rabbitmqctl'
        rmq_runflag = getOSInfo("netstat -anpt |grep rmq_port")
        if rmq_runflag != ' ':
            rmq_runflag = 'Y'
        else:
            rmq_runflag = 'N'

        if OS_TYPE == "HP-UX":
            state = getServerInfo("ps -efx|grep rabbit|grep -v grep|grep -v rabbitmq-server")
            if len(state) > 0:
                state = "start"
            else:
                state = "No rmq Process"
        else:
            state = getServerInfo("ps -ef|grep rabbit|grep -v grep|grep -v rabbitmq-server")
            if len(state) > 0:
                state = "start"
            else:
                state = "No rmq Process"
        rmq_pid = getServerInfo("ps -ef|grep rabbit|grep -v grep|grep -v rabbitmq-server|grep -v daemon|awk -F ' ' '{print $2}'")
        command3 = "ps -eo pid,lstart|grep %s" %rmq_pid
        rmq_creattime = getServerInfo(command3)[7:]

        # rmq config info
        if rmq_serverproperties1 == 1:
            rmqconfigfileinfocommand = "cat %s |grep -v '#' | grep -v '^$' " % rmq_serverproperties
            rmqconfigfileoutput = getConfigInfo1(rmqconfigfileinfocommand)
            listeners = optionsMatch("listeners.tcp.local=(.*)\S*", rmqconfigfileoutput, "127.0.0.1:5672")
            rmq_port = optionsMatch("listeners.tcp.default=(.*)\S*", rmqconfigfileoutput, "5672")
            num_acceptors_tcp = optionsMatch("num_acceptors.tcp=(.*)\S*", rmqconfigfileoutput, "10")
            num_acceptors_ssl = optionsMatch("num_acceptors.ssl=(.*)\S*", rmqconfigfileoutput, "10")
            ssl_handshake_timeout = optionsMatch("handshake_timeout=(.*)\S*", rmqconfigfileoutput, "10000")
            vm_memory_high_watermark = optionsMatch("vm_memory_high_watermark.relative=(.*)\S*", rmqconfigfileoutput,
                                                    "0.4")
            vm_memory_calculation_strategy = optionsMatch("vm_memory_calculation_strategy=(.*)\S*", rmqconfigfileoutput,
                                                          "rss")
            vm_memory_high_watermark_paging_ratio = optionsMatch("vm_memory_high_watermark_paging_ratio=(.*)\S*",
                                                                 rmqconfigfileoutput, "0.5")
            disk_free_limit = optionsMatch("disk_free_limit.absolute=(.*)\S*", rmqconfigfileoutput, "50m")
            log_file_level = optionsMatch("log.file.level=(.*)\S*", rmqconfigfileoutput, "info")
            channel_max = optionsMatch("channel_max=(.*)\S*", rmqconfigfileoutput, "128")
            queue_index_embed_msgs_below = optionsMatch("queue_index_embed_msgs_below=(.*)\S*", rmqconfigfileoutput,
                                                        "4kb")
        else:
            listeners = "127.0.0.1:5672"
            rmq_port = "5672"
            num_acceptors_tcp = "10"
            num_acceptors_ssl = "10"
            ssl_handshake_timeout = "10000"
            vm_memory_high_watermark = "0.4"
            vm_memory_calculation_strategy = "rss"
            vm_memory_high_watermark_paging_ratio = "0.5"
            disk_free_limit = "50m"
            log_file_level = "info"
            channel_max = "128"
            queue_index_embed_msgs_below = "4kb"

        # rmq server info
        rmqtoserver.append(
            {
                "rmq_prod_name": rmq_prod_name,
                "rmq_home": rmq_home,
                "rmq_prod_version": rmq_prod_version,
                "rmq_prod_logpath": rmq_prod_logpath,
                "rmq_ip_addr": rmq_ip_addr,
                "rmq_run_user":rmq_run_user,
                "rmq_username": rmq_username,
                "rmq_groupname": rmq_groupname,
                "rmq_port": rmq_port,
                "rmq_serverproperties": rmq_serverproperties,
                "rmq_start_script": rmq_start_script,
                "rmq_stop_script": rmq_stop_script,
                "rmq_runflag": rmq_runflag,
                "rmq_creattime": rmq_creattime
            }
        )

        # rmq config info
        rmqtoconfig.append(
            {
                "listeners": listeners,
                "num_acceptors_tcp": num_acceptors_tcp,
                "num_acceptors_ssl": num_acceptors_ssl,
                "ssl_handshake_timeout": ssl_handshake_timeout,
                "vm_memory_high_watermark": vm_memory_high_watermark,
                "vm_memory_calculation_strategy": vm_memory_calculation_strategy,
                "vm_memory_high_watermark_paging_ratio": vm_memory_high_watermark_paging_ratio,
                "disk_free_limit": disk_free_limit,
                "log_file_level": log_file_level,
                "channel_max": channel_max,
                "queue_index_embed_msgs_below": queue_index_embed_msgs_below
            }
        )


def buildCIJSON():
    rmqcijson = collections.OrderedDict()
    rmq_server = []
    rmq_config = []


    for config in rmqtoconfig:
        rmq_config.append(collections.OrderedDict([
            ("listeners", config["listeners"]),
            ("num_acceptors_tcp", config["num_acceptors_tcp"]),
            ("num_acceptors_ssl", config["num_acceptors_ssl"]),
            ("ssl_handshake_timeout", config["ssl_handshake_timeout"]),
            ("vm_memory_high_watermark", config["vm_memory_high_watermark"]),
            ("vm_memory_calculation_strategy", config["vm_memory_calculation_strategy"]),
            ("vm_memory_high_watermark_paging_ratio", config["vm_memory_high_watermark_paging_ratio"]),
            ("disk_free_limit", config["disk_free_limit"]),
            ("log_file_level", config["log_file_level"]),
            ("channel_max", config["channel_max"]),
            ("queue_index_embed_msgs_below", config["queue_index_embed_msgs_below"])
        ]))

    for server in rmqtoserver:
        rmq_server.append(collections.OrderedDict([
            ("rmq_prod_name", server["rmq_prod_name"]),
            ("rmq_home", server["rmq_home"]),
            ("rmq_prod_version", server["rmq_prod_version"]),
            ("rmq_prod_logpath", server["rmq_prod_logpath"]),
            ("rmq_ip_addr", server["rmq_ip_addr"]),
            ("rmq_run_user", server["rmq_run_user"]),
            ("rmq_username", server["rmq_username"]),
            ("rmq_groupname", server["rmq_groupname"]),
            ("rmq_port", server["rmq_port"]),
            ("rmq_serverproperties", server["rmq_serverproperties"]),
            ("rmq_start_script", server["rmq_start_script"]),
            ("rmq_stop_script", server["rmq_stop_script"]),
            ("rmq_runflag", server["rmq_runflag"]),
            ("rmq_creattime", server["rmq_creattime"])
        ]))

    rmqcijson.update(rmq_server=rmq_server)
    rmqcijson.update(rmq_config=rmq_config)
    rmqcijson.update(collection_time=currtime)

    if state != "start":
        print("No rmq Process")
        exit()
    else:
        os.system("mkdir -p /tmp/enmotech/rmq_cmdb")
        with open(JSONFILE, "w") as f:
            json.dump(rmqcijson, f)

if __name__ == "__main__":
    rmqprocessCountCommand = "ps -ef|grep rabbit|grep -v grep|grep -v rabbitmq-server|grep -v daemon | wc -l"
    rmqprocessoutput = getConfigInfo(rmqprocessCountCommand)
    if eval(rmqprocessoutput) == 0:
        print("no rabbitmq process")
        sys.exit(0)

    rmqtoserver = []
    rmqtoconfig = []
    os.system("rm -rf " + JSONFILE)
    if sys.version[:1] == '3':
        try:
            rmq_homes = getRMQHome()
            parseCI(rmq_homes)
            buildCIJSON()
        except Exception as e:
            print("error! Execute failed ,message : ")
            print(("%s" % traceback.format_exc()))
        sys.exit(0)
    else:
        exit("only support python3,current python version is %s" % sys.version[:5])
