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

ELASTICSEARCH_VERSION = "v1.0"
OS_TYPE = platform.system()
hostname = socket.gethostname()
currtime = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time()))
currtime2 = time.strftime('%Y%m%d%H%M%S', time.localtime(time.time()))

# JSONFILE = hostname + '_elasticsearch_' + currtime2 + '.json'
JSONFILE = '/tmp/enmotech/es_cmdb/' + hostname + '_elasticsearch_' + currtime2 + '.json'


def printCopyright():
    print("elasticsearch CMDB Collection Agent (%s)" % ELASTICSEARCH_VERSION)
    sys.stdout.flush()

# get elasticsearch home
def getEsHOME():
    elasticsearch_list = []
    if OS_TYPE == "Linux":
        elasticsearch_command = "ps -ef | grep elasticsearch | grep -v grep | grep -o 'Des.path.home=.*' | awk '{print $1}'| awk -F'=' '{print $NF}'"
        elasticsearchs = subprocess.Popen(elasticsearch_command, shell=True, stdout=subprocess.PIPE).communicate()[0].splitlines()
        for elasticsearch in elasticsearchs:
            elasticsearch = elasticsearch.decode()
            if elasticsearch not in elasticsearch_list:
                elasticsearch_list.append(elasticsearch)
        return elasticsearch_list

    elif OS_TYPE == "AIX":
        elasticsearch_command = "ps -ef | grep elasticsearch | grep -v grep | grep -o 'Des.path.home=.*' | awk -F' ' '{print $1}'| awk -F'=' '{print $NF}'"
        elasticsearchs = subprocess.Popen(elasticsearch_command, shell=True, stdout=subprocess.PIPE).communicate()[0].splitlines()
        for elasticsearch in elasticsearchs:
            elasticsearch = elasticsearch.decode()
            if elasticsearch not in elasticsearch_list:
                elasticsearch_list.append(elasticsearch)
        return elasticsearch_list

    elif OS_TYPE == "HP-UX":
        elasticsearch_command = "ps -ef | grep elasticsearch | grep -v grep | grep -o 'Des.path.home=.*' | awk -F' ' '{print $1}'| awk -F'=' '{print $NF}'"
        elasticsearchs = subprocess.Popen(elasticsearch_command, shell=True, stdout=subprocess.PIPE).communicate()[0].splitlines()
        for elasticsearch in elasticsearchs:
            elasticsearch = elasticsearch.decode()
            if elasticsearch not in elasticsearch_list:
                elasticsearch_list.append(elasticsearch)
        return elasticsearch_list
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

def parseCI(eshomes):
    global username,state
    for eshome in eshomes:


        if OS_TYPE == "HP-UX":
            java_path = subprocess.Popen("ps -efx|grep %s|grep java|grep -v grep |awk '{print $9}'" % eshome, shell=True, stdout=subprocess.PIPE).communicate()[0].decode()
        elif OS_TYPE == "AIX":
            java_path = subprocess.Popen("ps -ef|grep %s|grep java|grep -v grep |awk '{print $9}'" % eshome, shell=True, stdout=subprocess.PIPE).communicate()[0].decode()
        else:
            java_path = subprocess.Popen("ps -ef|grep %s|grep java|grep -v grep |awk '{print $8}'" % eshome, shell=True, stdout=subprocess.PIPE).communicate()[0].decode()

        print(java_path)
        # add jdk version 1.7 or 1.8 or 1.6 judgement
        if java_path == 'java\n' :
            ### get openjdk install path
            whichjava = subprocess.Popen("which %s" % java_path, shell=True, stdout=subprocess.PIPE).communicate()[0].decode()
            if whichjava == '/usr/bin/java\n':
                java_path=os.path.realpath('/usr/bin/java').split("/jre")[0]
            else:
                java_path = os.path.realpath(whichjava).split("/bin")[0]
            (status, javainfo) = subprocess.getstatusoutput('java -version')
            JAVA_VERSION = re.findall("version (.*)\s", javainfo)

        elif java_path ==  '/bin/java\n':
            java_path = os.path.realpath('/bin/java').split("/jre")[0]
            (status, javainfo) = subprocess.getstatusoutput('java -version')
            JAVA_VERSION = re.findall("version (.*)\s", javainfo)

        else:
            java_path = java_path.split("/bin")[0]
            os.environ['JAVA_HOME'] = java_path
            (status, javainfo) = subprocess.getstatusoutput(java_path + '/bin/java -version')
            JAVA_VERSION = re.findall("version (.*)\s", javainfo)



        JAVA_NUM = float(eval(JAVA_VERSION[0])[0:3])
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
        # get elasticsearch info
        (status, esserverprintcmdinfo) = subprocess.getstatusoutput("grep -v '^#' %s/config/jvm.options" % eshome)
        maxheap = optionsMatch("-Xmx(.+?[mMgG])\S*", esserverprintcmdinfo, "")
        minheap = optionsMatch("-Xms(.+?[mMgG])\S*", esserverprintcmdinfo, "")


        if JAVA_NUM >= 1.8:
            gcpolicy = optionsMatch(
                "(-XX:\+UseSerialGC|-XX:\+UseParallelGC|-XX:\+UseConcMarkSweepGC|-XX:\+UseG1GC|-Xgcpolicy:\S*)",
                esserverprintcmdinfo, "")
            print(gcpolicy)
            esjvm.append(
                {
                    "eshome": eshome,
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
            maxperm = optionsMatch("-XX:MaxPermSize=(.+?[mMgG])\S*", esserverprintcmdinfo, "")
            minperm = optionsMatch("-XX:MinPermSize=(.+?[mMgG])\S*", esserverprintcmdinfo, "")
            gcpolicy = optionsMatch(
                "(-XX:\+UseSerialGC|-XX:\+UseParallelGC|-XX:\+UseConMarkSweepGC|-XX:\+UseG1GC|-Xgcpolicy:\S*)",
                esserverprintcmdinfo, "")
            esjvm.append(
                {
                    "eshome": eshome,
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
        # use elasticsearch-*.jar get es version
        # (status, esserverversion) = subprocess.getstatusoutput("ls %s/lib/ | grep -P 'elasticsearch-\d\.\d\.\d\.jar'|awk -F '-' '{print $2}'|awk -F '.jar' '{print $(NF-1)}'" % eshome)
        esversion = subprocess.Popen("ls %s/lib/ | grep -P 'elasticsearch-\d\.\d\.\d\.jar'|awk -F '-' '{print $2}'|awk -F '.jar' '{print $(NF-1)}'" % eshome, shell=True, stdout=subprocess.PIPE).communicate()[0].decode().split(".jar")[0].replace("\n","")
        esrunusercommand = "ps -ef|grep org.elasticsearch.bootstrap.Elasticsearch|grep % s |grep -v grep | awk '{print $1}'" %eshome
        esrunuser = getCommonInfo(esrunusercommand)
        esusercommand = "ls -lrt %s|grep -v total|grep bin |awk -F ' ' '{print $3}'" % eshome
        esgroupcommand = "ls -lrt %s|grep -v total|grep bin |awk -F ' ' '{print $4}'" % eshome
        esuser = getCommonInfo(esusercommand)
        esgroup = getCommonInfo(esgroupcommand)
        (status, esConfig) = subprocess.getstatusoutput("ps -ef | grep elasticsearch|grep \'%s\' | grep -v grep | grep -o 'Des.path.conf=.*' | awk -F' ' '{print $1}'| awk -F'=' '{print $NF}'" % eshome)
        (status, esconfigprintcmdinfo) = subprocess.getstatusoutput("grep -v '^#' %s/elasticsearch.yml" % esConfig)
        #print(esconfigprintcmdinfo)
        clustername = optionsMatch("cluster.name:(.*)\S*", esconfigprintcmdinfo, "elasticsearch")
        nodename = optionsMatch("node.name:(.*)\S*", esconfigprintcmdinfo, "")
        nodemaster = optionsMatch("node.master:(.*)\S*", esconfigprintcmdinfo, "true")
        nodedata = optionsMatch("node.data:(.*)\S*", esconfigprintcmdinfo, "true")
        indexnumber_of_shards = optionsMatch("index.number_of_shards:(.*)\S*", esconfigprintcmdinfo, "5")
        indexnumber_of_replicas = optionsMatch("index.number_of_replicas:(.*)\S*", esconfigprintcmdinfo, "1")
        pathconf = optionsMatch("path.conf:(.*)\S*", esconfigprintcmdinfo, "/path/to/conf")
        pathdata = optionsMatch("path.data:(.*)\S*", esconfigprintcmdinfo, "/path/to/data")
        pathwork = optionsMatch("path.work:(.*)\S*", esconfigprintcmdinfo, "/path/to/work")
        pathlogs = optionsMatch("path.logs:(.*)\S*", esconfigprintcmdinfo, "/path/to/logs")
        pathplugins = optionsMatch("path.plugins:(.*)\S*", esconfigprintcmdinfo, "/path/to/plugins")
        bootstrapmlockall = optionsMatch("bootstrap.mlockall:(.*)\S*", esconfigprintcmdinfo, "true")
        networkbind_host = optionsMatch("network.bind_host:(.*)\S*", esconfigprintcmdinfo, "0.0.0.0")
        networkhost = optionsMatch("network.host:(.*)\S*", esconfigprintcmdinfo, "0.0.0.0")
        transporttcpport = optionsMatch("transport.tcp.port:(.*)\S*", esconfigprintcmdinfo, "9300")
        transporttcpcompress = optionsMatch("transport.tcp.compress:(.*)\S*", esconfigprintcmdinfo, "false")
        httpport = optionsMatch("http.port:(.*)\S*", esconfigprintcmdinfo, "9200")
        httpmax_content_length = optionsMatch("http.max_content_length:(.*)\S*", esconfigprintcmdinfo, "100Mb")
        httpenabled = optionsMatch("http.enabled:(.*)\S*", esconfigprintcmdinfo, "false")
        gatewaytype = optionsMatch("gateway.type:(.*)\S*", esconfigprintcmdinfo, "local")
        gatewayrecover_after_nodes = optionsMatch("gateway.recover_after_nodes:(.*)\S*", esconfigprintcmdinfo, "1")
        gatewayrecover_after_time = optionsMatch("gateway.recover_after_time:(.*)\S*", esconfigprintcmdinfo, "5m")
        gatewayexpected_nodes = optionsMatch("gateway.expected_nodes:(.*)\S*", esconfigprintcmdinfo, "2")
        routing_allocation_node_initial_primaries_recoveries = optionsMatch("cluster.routing.allocation.node_initial_primaries_recoveries:(.*)\S*", esconfigprintcmdinfo, "4")
        cluster_routing_allocation_node_concurrent_recoveries = optionsMatch("cluster.routing.allocation.node_concurrent_recoveries:(.*)\S*", esconfigprintcmdinfo, "2")
        indices_recovery_max_bytes_per_sec = optionsMatch("indices.recovery.max_bytes_per_sec:(.*)\S*", esconfigprintcmdinfo, "0")
        indices_recovery_concurrent_streams = optionsMatch("indices.recovery.concurrent_streams:(.*)\S*", esconfigprintcmdinfo, "5")
        discovery_zen_minimum_master_nodes = optionsMatch("discovery.zen.minimum_master_nodes:(.*)\S*", esconfigprintcmdinfo, "1")
        discovery_zen_ping_timeout = optionsMatch("discovery.zen.ping.timeout:(.*)\S*", esconfigprintcmdinfo, "3s")
        discovery_zen_ping_unicast_hosts = optionsMatch("discovery.zen.ping.unicast.hosts:(.*)\S*", esconfigprintcmdinfo, "")
        print(eval(discovery_zen_ping_unicast_hosts))
        index_cache_field_max_size = optionsMatch("index.cache.field.max_size:(.*)\S*", esconfigprintcmdinfo, "unlimited")
        index_cache_field_expire = optionsMatch("index.cache.field.expire:(.*)\S*", esconfigprintcmdinfo, "unlimited")
        index_cache_field_type = optionsMatch("index.cache.field.type:(.*)\S*", esconfigprintcmdinfo, "unlimited")
        # esconfig json
        esconfig.append({
                "eshome": eshome,
                "esversion": esversion,
                "esrunuser": esrunuser,
                "esgroup": esgroup,
                "clustername": clustername,
                "nodename": nodename,
                "nodemaster": nodemaster,
                "nodedata": nodedata,
                "indexnumber_of_shards": indexnumber_of_shards,
                "indexnumber_of_replicas": indexnumber_of_replicas,
                "pathconf": pathconf,
                "pathdata": pathdata,
                "pathwork": pathwork,
                "pathlogs": pathlogs,
                "pathplugins": pathplugins,
                "bootstrapmlockall": bootstrapmlockall,
                "networkbind_host": networkbind_host,
                "networkhost": networkhost,
                "transporttcpport": transporttcpport,
                "transporttcpcompress": transporttcpcompress,
                "httpport": httpport,
                "httpmax_content_length": httpmax_content_length,
                "httpenabled": httpenabled,
                "gatewaytype": gatewaytype,
                "gatewayrecover_after_nodes": gatewayrecover_after_nodes,
                "gatewayrecover_after_time": gatewayrecover_after_time,
                "gatewayexpected_nodes": gatewayexpected_nodes,
                "routing_allocation_node_initial_primaries_recoveries": routing_allocation_node_initial_primaries_recoveries,
                "cluster_routing_allocation_node_concurrent_recoveries": cluster_routing_allocation_node_concurrent_recoveries,
                "indices_recovery_max_bytes_per_sec": indices_recovery_max_bytes_per_sec,
                "indices_recovery_concurrent_streams": indices_recovery_concurrent_streams,
                "discovery_zen_minimum_master_nodes": discovery_zen_minimum_master_nodes,
                "discovery_zen_ping_timeout": discovery_zen_ping_timeout,
                "discovery_zen_ping_unicast_hosts": eval(discovery_zen_ping_unicast_hosts),
                "index_cache_field_max_size": index_cache_field_max_size,
                "index_cache_field_expire": index_cache_field_expire,
                "index_cache_field_type": index_cache_field_type
            })

def buildCIJSON():
    elasticsearchcijson = collections.OrderedDict()
    elasticsearch_jvm = []
    elasticsearch_config = []

    for jvm in esjvm:
        JAVA_NUM = float(jvm["javaversion"][0:3])

        ### get java_num  if java_num >= 1.8 don't set maxperm minperm parameter
        if JAVA_NUM >= 1.8:
            elasticsearch_jvm.append(collections.OrderedDict([
                ("eshome", jvm["eshome"]),
                ("javahome", jvm["javahome"]),
                ("maxheap", jvm["maxheap"]),
                ("minheap", jvm["minheap"]),
                ("gcpolicy", jvm["gcpolicy"]),
                ("javaversion", jvm["javaversion"]),
                ("runbit", jvm["runbit"]),
                ("vendor", jvm["vendor"])
            ]))
        else:
            elasticsearch_jvm.append(collections.OrderedDict([
                ("eshome", jvm["eshome"]),
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
    for config in esconfig:
        elasticsearch_config.append(collections.OrderedDict([
            ("eshome", config["eshome"]),
            ("version", config["esversion"]),
            ("esuser", config["esrunuser"]),
            ("esgroup", config["esgroup"]),
            ("cluster.name", config["clustername"]),
            ("node.name", config["nodename"]),
            ("node.data", config["nodedata"]),
            ("index.number_of_shards", config["indexnumber_of_shards"]),
            ("index.number_of_replicas", config["indexnumber_of_replicas"]),
            ("path.conf", config["pathconf"]),
            ("path.data", config["pathdata"]),
            ("path.work", config["pathwork"]),
            ("path.logs", config["pathlogs"]),
            ("path.plugins", config["pathplugins"]),
            ("bootstrap.mlockall", config["bootstrapmlockall"]),
            ("network.bind_host", config["networkbind_host"]),
            ("network.host", config["networkhost"]),
            ("transport.tcp.port", config["transporttcpport"]),
            ("transport.tcp.compress", config["transporttcpcompress"]),
            ("http.port", config["httpport"]),
            ("http.max_content_length", config["httpmax_content_length"]),
            ("http.enabled", config["httpenabled"]),
            ("gateway.type", config["gatewaytype"]),
            ("gateway.recover_after_nodes", config["gatewayrecover_after_nodes"]),
            ("gateway.recover_after_time", config["gatewayrecover_after_time"]),
            ("gateway.expected_nodes", config["gatewayexpected_nodes"]),
            ("cluster.routing.allocation.node_initial_primaries_recoveries",config["routing_allocation_node_initial_primaries_recoveries"]),
            ("cluster.routing.allocation.node_concurrent_recoveries",config["cluster_routing_allocation_node_concurrent_recoveries"]),
            ("indices.recovery.max_bytes_per_sec", config["indices_recovery_max_bytes_per_sec"]),
            ("indices.recovery.concurrent_streams", config["indices_recovery_concurrent_streams"]),
            ("discovery.zen.minimum_master_nodes", config["discovery_zen_minimum_master_nodes"]),
            ("discovery.zen.ping.timeout", config["discovery_zen_ping_timeout"]),
            ("discovery.zen.ping.unicast.hosts", config["discovery_zen_ping_unicast_hosts"]),
            ("index.cache.field.max_size", config["index_cache_field_max_size"]),
            ("index.cache.field.expire", config["index_cache_field_expire"]),
            ("index.cache.field.type", config["index_cache_field_type"])
        ]))


    elasticsearchcijson.update(hostname=hostname)
    elasticsearchcijson.update(ipaddress=":".join(ips))
    elasticsearchcijson.update(elasticsearch_jvm=elasticsearch_jvm)
    elasticsearchcijson.update(elasticsearch_config=elasticsearch_config)
    elasticsearchcijson.update(collection_time=currtime)


    os.system("mkdir -p /tmp/enmotech/es_cmdb")
    os.system("touch %s" %JSONFILE )
    with open(JSONFILE, "w") as f:
         json.dump(elasticsearchcijson, f)



if __name__ == '__main__':

    esjvm = []
    esProduct = []
    esconfig = []

    if sys.version[:1] == '3':
        try:
            printCopyright()

            esprocessCountCommand = "ps -ef|grep org.elasticsearch.bootstrap.Elasticsearch|grep -v grep |wc -l"
            esprocessoutput = getCommonInfo(esprocessCountCommand)
            if eval(esprocessoutput) == 0:
                print("no elasticsearch process")
                sys.exit(0)

            eshomes = getEsHOME()
            parseCI(eshomes)
            buildCIJSON()
        except Exception as e:
            print("error! Execute failed ,message : ")
            print("%s" % e.format_exc())
        sys.exit(0)
    else:
        exit("only support python3,current python version is %s" % sys.version[:5])