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

KAFKAAGENT_VERSION = "v1.2"
OS_TYPE = platform.system()
hostname = socket.gethostname()
currtime = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time()))
currtime2 = time.strftime('%Y%m%d%H%M%S', time.localtime(time.time()))
JSONFILE = '/tmp/enmotech/kafka_cmdb/' + hostname + '_Kafka_' + currtime2 + '.json'


def getKafkaHome():
    kafka_list = []
    if OS_TYPE == "Linux":
        kafka_command = "ps -ef|grep java|grep kafka|grep 'Dkafka.logs.dir='|grep -v grep|awk -F 'Dkafka.logs.dir=' '{print $2}'|awk '{print $1}'"
        kafkas = subprocess.Popen(kafka_command, shell=True, stdout=subprocess.PIPE).communicate()[0].splitlines()
        for kafka in kafkas:
            kafka = kafka.decode()[:-12]
            if kafka not in kafka_list:
                kafka_list.append(kafka)
        return kafka_list

    elif OS_TYPE == "AIX":
        kafka_command = "ps -ef|grep java|grep kafka|grep 'Dkafka.logs.dir='|grep -v grep|awk -F 'Dkafka.logs.dir=' '{print $2}'|awk '{print $1}'"
        kafkas = subprocess.Popen(kafka_command, shell=True, stdout=subprocess.PIPE).communicate()[0].splitlines()
        for kafka in kafkas:
            kafka = kafka.decode()[:-12]
            if kafka not in kafka_list:
                kafka_list.append(kafka)
        return kafka_list

    elif OS_TYPE == "HP-UX":
        kafka_command = "ps -ef|grep java|grep kafka|grep 'Dkafka.logs.dir='|grep -v grep|awk -F 'Dkafka.logs.dir=' '{print $2}'|awk '{print $1}'"
        kafkas = subprocess.Popen(kafka_command, shell=True, stdout=subprocess.PIPE).communicate()[0].splitlines()
        for kafka in kafkas:
            kafka = kafka.decode()[:-12]
            if kafka not in kafka_list:
                kafka_list.append(kafka)
        return kafka_list
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
    return subprocess.Popen(cmdstr, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE).communicate()[
        0].decode().strip()


def getServerInfo(cmdstr):
    return subprocess.Popen(cmdstr, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE).communicate()[
        0].decode().replace("\n","")


def getConfigInfo(cmdstr):
    return subprocess.Popen(cmdstr, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE).communicate()[
        0].decode().replace("\n","")

def getConfigInfo1(cmdstr):
    return subprocess.Popen(cmdstr, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE).communicate()[
        0].decode()

def parseCI(kafka_homes):
    global username, state,JAVA_NUM
    for kafka_home in kafka_homes:
        if OS_TYPE == "HP-UX":
            java_path = \
                subprocess.Popen("ps -efx|grep %s|grep java|grep -v grep |awk '{print $9}'" % kafka_home, shell=True,
                                 stdout=subprocess.PIPE).communicate()[0].decode().split("bin")[0]
        elif OS_TYPE == "AIX":
            java_path = \
                subprocess.Popen("ps -ef|grep %s|grep java|grep -v grep |awk '{print $9}'" % kafka_home, shell=True,
                                 stdout=subprocess.PIPE).communicate()[0].decode().split("bin")[0]
        else:
            java_path = \
                subprocess.Popen("ps -ef|grep %s|grep java|grep -v grep |awk '{print $8}'" % kafka_home, shell=True,
                                 stdout=subprocess.PIPE).communicate()[0].decode().split("bin")[0]


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
        #os.environ['JAVA_HOME'] = java_path
        #(status, javainfo) = subprocess.getstatusoutput(java_path + '/bin/java -version')
        #JAVA_VERSION = re.findall("java version (.*)\s", javainfo)
        if javainfo.find("1.8") >= 0:
            JAVA_NUM = 1.8
        else:
            JAVA_NUM = 1.7
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

        # use ps -ef  get kafka jvm info
        (status, kafkajvminfo) = subprocess.getstatusoutput('ps -ef|grep java|grep kafka.Kafka|grep %s|grep -v grep' %kafka_home)
        maxheap = optionsMatch("-Xmx(.+?[mMgG])\S*", kafkajvminfo, "")
        minheap = optionsMatch("-Xms(.+?[mMgG])\S*", kafkajvminfo, "")

        if JAVA_NUM >= 1.8:
            maxmate = optionsMatch("-XX:MaxMetaspaceSize=(.+?[mMgG])\S*", kafkajvminfo, "20m")
            minmate = optionsMatch("-XX:MetaspaceSize=(.+?[mMgG])\S*", kafkajvminfo, "20m")
        else:
            maxperm = optionsMatch("-XX:MaxPermSize=(.+?[mMgG])\S*", kafkajvminfo, "48m")
            minperm = optionsMatch("-XX:MinPermSize=(.+?[mMgG])\S*", kafkajvminfo, "48m")

        gcpolicy = optionsMatch(
            "(-XX:\+UseSerialGC|-XX:\+UseParallelGC|-XX:\+UseConMarkSweepGC|-XX:\+UseG1GC|-Xgcpolicy:\S*)",
            kafkajvminfo, "")

        # kafka server info
        kafka_prod_name = "Kafka"
        #kafka_home = subprocess.Popen("find / -name kafka -type d", shell=True, stdout=subprocess.PIPE).communicate()[0].decode().replace("\n","")
        kafka_prod_version = subprocess.Popen("ps -ef|grep kafka.Kafka|grep %s|grep -v grep|awk -F '/libs/kafka_' '{print $NF}'|awk -F '-sources' '{print $1}'" % kafka_home, shell=True, stdout=subprocess.PIPE).communicate()[0].decode().replace("\n","")
        kafka_prod_logpath = subprocess.Popen("ps -ef|grep java|grep kafka| grep %s |grep 'Dkafka.logs.dir='|grep -v grep|awk -F 'Dkafka.logs.dir=' '{print $2}'|awk '{print $1}'" % kafka_home, shell=True, stdout=subprocess.PIPE).communicate()[0].decode().replace("\n","")
        kafka_ip_addr = subprocess.Popen("ip addr show |grep 'state UP' -A 2| grep 'inet ' |grep -v 127.0.0. |head -1|cut -d ' ' -f6|cut -d/ -f1", shell=True, stdout=subprocess.PIPE).communicate()[0].decode().replace("\n","")
        kafka_run_user = getServerInfo("ps -ef|grep java| grep %s|grep kafka.Kafka|grep -v grep|awk '{print $1}'" % kafka_home).replace("\n","")
        command1 = "ls -lrt %s|grep -v total|grep bin |awk -F ' ' '{print $4}'" %kafka_home
        command31 = "ls -lrt %s|grep -v total|grep bin |awk -F ' ' '{print $3}'" %kafka_home
        kafka_username =getServerInfo(command31)
        kafka_groupname = getServerInfo(command1)
        kafka_serverproperties = kafka_home + getServerInfo("ps -ef|grep java|grep kafka.Kafka| grep %s|grep -v grep |awk -F 'kafka.Kafka' '{print $NF}'" %kafka_home)[3:]
        command2 = "cat %s|grep listeners=PLAINTEXT|grep -v ^#|awk -F ':' '{print $NF}'" %kafka_serverproperties
        kafka_port = getServerInfo(command2)
        kafka_start_script = kafka_home + '/bin/kafka-server-start.sh '
        kafka_stop_script = kafka_home + '/bin/kafka-server-stop.sh'
        kafka_runflag = getOSInfo("netstat -anpt |grep kafka_port")
        if kafka_runflag != ' ':
            kafka_runflag = 'Y'
        else:
            kafka_runflag = 'N'

        if OS_TYPE == "HP-UX":
            state = getServerInfo("ps -efx |grep 'kafka.Kafka'| grep %s |grep -v grep |grep java|awk '{print $NF}'" %kafka_home)
            if len(state) > 0:
                state = "start"
            else:
                state = "No Kafka Process"
        else:
            state = getServerInfo("ps -ef |grep 'kafka.Kafka'  | grep %s|grep -v grep |grep java|awk '{print $NF}'" %kafka_home)
            if len(state) > 0:
                state = "start"
            else:
                state = "No Kafka Process"
        kafka_pid = getServerInfo("ps -ef|grep java|grep kafka.Kafka |grep %s|grep -v grep |awk -F ' ' '{print $2}'" %kafka_home)
        command3 = "ps -eo pid,lstart|grep %s" %kafka_pid
        kafka_creattime = getServerInfo(command3)[7:]

        # kafka config info

        kafkaconfigfileinfocommand = "cat %s |grep -v '#' | grep -v '^$' " %kafka_serverproperties
        kafkaconfigfileoutput = getConfigInfo1(kafkaconfigfileinfocommand)
        broker_id = optionsMatch("broker.id=(.*)\S*", kafkaconfigfileoutput, "0")
        listeners = optionsMatch("listeners=(.*)\S*", kafkaconfigfileoutput, "PLAINTEXT://localhost:9092")
        num_network_threads = optionsMatch("num.network.threads=(.*)\S*", kafkaconfigfileoutput, "3")
        num_io_threads = optionsMatch("num.io.threads=(.*)\S*", kafkaconfigfileoutput, "8")
        socket_send_buffer_bytes = optionsMatch("socket.send.buffer.bytes=(.*)\S*", kafkaconfigfileoutput, "102400")
        socket_receive_buffer_bytes = optionsMatch("socket.receive.buffer.bytes=(.*)\S*", kafkaconfigfileoutput, "102400")
        socket_request_max_bytes = optionsMatch("socket.request.max.bytes=(.*)\S*", kafkaconfigfileoutput, "104857600")
        log_dirs = optionsMatch("log.dirs=(.*)\S*", kafkaconfigfileoutput, "/tmp/kafka-log")
        num_partitions = optionsMatch("num.partitions=(.*)\S*", kafkaconfigfileoutput, "1")
        num_recovery_threads_per_data_dir = optionsMatch("num.recovery.threads.per.data.dir=(.*)\S*", kafkaconfigfileoutput, "1")
        offsets_topic_replication_factor = optionsMatch("offsets.topic.replication.factor=(.*)\S*", kafkaconfigfileoutput, "3")
        transaction_state_log_replication_factor = optionsMatch("transaction.state.log.replication.factor=(.*)\S*", kafkaconfigfileoutput, "1")
        transaction_state_log_min_isr = optionsMatch("transaction.state.log.min.isr=(.*)\S*", kafkaconfigfileoutput, "1")
        log_retention_hours = optionsMatch("log.retention.hours=(.*)\S*", kafkaconfigfileoutput, "168")
        log_segment_bytes = optionsMatch("log.segment.bytes=(.*)\S*", kafkaconfigfileoutput, "1073741824")
        log_retention_check_interval_ms = optionsMatch("log.retention.check.interval.ms=(.*)\S*", kafkaconfigfileoutput, "300000")
        zookeeper_connect = optionsMatch("zookeeper.connect=(.*)\S*", kafkaconfigfileoutput, "localhost:2181")
        zookeeper_connection_timeout_ms = optionsMatch("zookeeper.connection.timeout.ms=(.*)\S*", kafkaconfigfileoutput, "18000")
        group_initial_rebalance_delay_ms = optionsMatch("group.initial.rebalance.delay.ms=(.*)\S*", kafkaconfigfileoutput, "0")

        if JAVA_NUM >= 1.8:
            kafkatojvm.append(
                {
                    "javahome": java_path,
                    "maxheap": maxheap,
                    "minheap": minheap,
                    "maxmate": maxmate,
                    "minmate": minmate,
                    "gcpolicy": gcpolicy,
                    "runbit": runbit,
                    "javaversion": eval(JAVA_VERSION[0]),  # use eval remove ""
                    "vendor": vendor
                }
            )
        else:
            kafkatojvm.append(
                {
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
        # kafka server info
        kafkatoserver.append(
            {
                "kafka_prod_name": kafka_prod_name,
                "kafka_home": kafka_home,
                "kafka_prod_version": kafka_prod_version,
                "kafka_prod_logpath": kafka_prod_logpath,
                "kafka_ip_addr": kafka_ip_addr,
                "kafka_run_user":kafka_run_user,
                "kafka_username": kafka_username,
                "kafka_groupname": kafka_groupname,
                "kafka_port": kafka_port,
                "kafka_serverproperties": kafka_serverproperties,
                "kafka_start_script": kafka_start_script,
                "kafka_stop_script": kafka_stop_script,
                "kafka_runflag": kafka_runflag,
                "kafka_creattime": kafka_creattime
            }
        )

        # kafka config info
        kafkatoconfig.append(
            {
                "broker_id": broker_id,
                "listeners": listeners,
                "num_network_threads": num_network_threads,
                "num_io_threads": num_io_threads,
                "socket_send_buffer_bytes": socket_send_buffer_bytes,
                "socket_receive_buffer_bytes": socket_receive_buffer_bytes,
                "socket_request_max_bytes": socket_request_max_bytes,
                "log_dirs": log_dirs,
                "num_partitions": num_partitions,
                "num_recovery_threads_per_data_dir": num_recovery_threads_per_data_dir,
                "offsets_topic_replication_factor": offsets_topic_replication_factor,
                "transaction_state_log_replication_factor": transaction_state_log_replication_factor,
                "transaction_state_log_min_isr": transaction_state_log_min_isr,
                "log_retention_hours": log_retention_hours,
                "log_segment_bytes": log_segment_bytes,
                "log_retention_check_interval_ms": log_retention_check_interval_ms,
                "zookeeper_connect": zookeeper_connect,
                "zookeeper_connection_timeout_ms": zookeeper_connection_timeout_ms,
                "group_initial_rebalance_delay_ms": group_initial_rebalance_delay_ms,
            }
        )


def buildCIJSON():
    kafkacijson = collections.OrderedDict()
    kafka_jvm = []
    kafka_server = []
    kafka_config = []

    for jvm in kafkatojvm:
        if JAVA_NUM >= 1.8:
            kafka_jvm.append(collections.OrderedDict([
                ("javahome", jvm["javahome"]),
                ("maxheap", jvm["maxheap"]),
                ("minheap", jvm["minheap"]),
                ("maxmate", jvm["maxmate"]),
                ("minmate", jvm["minmate"]),
                ("gcpolicy", jvm["gcpolicy"]),
                ("javaversion", jvm["javaversion"]),
                ("runbit", jvm["runbit"]),
                ("vendor", jvm["vendor"])
            ]))
        else:
            kafka_jvm.append(collections.OrderedDict([
                ("javahome", jvm["javahome"]),
                ("maxheap", jvm["maxheap"]),
                ("minheap", jvm["minheap"]),
                ("maxperm", jvm["maxperm"]),
                ("minperm", jvm["minperm"]),
                ("gcpolicy", jvm["gcpolicy"]),
                ("javaversion", jvm["javaversion"]),
                ("runbit", jvm["runbit"]),
                ("vendor", jvm["vendor"])
            ]))

    for config in kafkatoconfig:
        kafka_config.append(collections.OrderedDict([
            ("broker_id", config["broker_id"]),
            ("listeners", config["listeners"]),
            ("num_network_threads", config["num_network_threads"]),
            ("num_io_threads", config["num_io_threads"]),
            ("socket_send_buffer_bytes", config["socket_send_buffer_bytes"]),
            ("socket_receive_buffer_bytes", config["socket_receive_buffer_bytes"]),
            ("socket_request_max_bytes", config["socket_request_max_bytes"]),
            ("log_dirs", config["log_dirs"]),
            ("num_partitions", config["num_partitions"]),
            ("num_recovery_threads_per_data_dir", config["num_recovery_threads_per_data_dir"]),
            ("offsets_topic_replication_factor", config["offsets_topic_replication_factor"]),
            ("transaction_state_log_replication_factor", config["transaction_state_log_replication_factor"]),
            ("transaction_state_log_min_isr", config["transaction_state_log_min_isr"]),
            ("log_retention_hours", config["log_retention_hours"]),
            ("log_segment_bytes", config["log_segment_bytes"]),
            ("log_retention_check_interval_ms", config["log_retention_check_interval_ms"]),
            ("zookeeper_connect", config["zookeeper_connect"]),
            ("zookeeper_connection_timeout_ms", config["zookeeper_connection_timeout_ms"]),
            ("group_initial_rebalance_delay_ms", config["group_initial_rebalance_delay_ms"]),
        ]))

    for server in kafkatoserver:
        kafka_server.append(collections.OrderedDict([
            ("kafka_prod_name", server["kafka_prod_name"]),
            ("kafka_home", server["kafka_home"]),
            ("kafka_prod_version", server["kafka_prod_version"]),
            ("kafka_prod_logpath", server["kafka_prod_logpath"]),
            ("kafka_ip_addr", server["kafka_ip_addr"]),
            ("kafka_run_user", server["kafka_run_user"]),
            ("kafka_username", server["kafka_username"]),
            ("kafka_groupname", server["kafka_groupname"]),
            ("kafka_port", server["kafka_port"]),
            ("kafka_serverproperties", server["kafka_serverproperties"]),
            ("kafka_start_script", server["kafka_start_script"]),
            ("kafka_stop_script", server["kafka_stop_script"]),
            ("kafka_runflag", server["kafka_runflag"]),
            ("kafka_creattime", server["kafka_creattime"])
        ]))

    kafkacijson.update(kafka_server=kafka_server)
    kafkacijson.update(kafka_jvm=kafka_jvm)
    kafkacijson.update(kafka_config=kafka_config)
    kafkacijson.update(collection_time=currtime)

    if state != "start":
        print("No Kafka Process")
        exit()
    else:
        os.system("mkdir -p /tmp/enmotech/kafka_cmdb")
        with open(JSONFILE, "w") as f:
            json.dump(kafkacijson, f)


if __name__ == "__main__":
    kafkaprocessCountCommand = "ps -ef|grep java|grep kafka.Kafka |grep -v grep| wc -l"
    kafkaprocessoutput = getConfigInfo1(kafkaprocessCountCommand)
    if eval(kafkaprocessoutput) == 0:
        print("no kafka process")
        sys.exit(0)

    kafkatojvm = []
    kafkatoserver = []
    kafkatoconfig = []
    os.system("rm -rf " + JSONFILE)

    if sys.version[:1] == '3':
        try:
            kafka_homes = getKafkaHome()
            parseCI(kafka_homes)
            buildCIJSON()
        except Exception as e:
            print("error! Execute failed ,message : ")
            print(("%s" % traceback.format_exc()))
        sys.exit(0)
    else:
        exit("only support python3,current python version is %s" % sys.version[:5])
