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

TOMAGENT_VERSION = "v1.0"
OS_TYPE = platform.system()
hostname = socket.gethostname()
currtime = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time()))
JSONFILE = '/tmp/enmotech/tomcat_cmdb/tomcat_cmdb.json'
	
def getCatalina():
	catalina_list = []
	if OS_TYPE == "Linux":
		catalinas_command = "ps -ef|grep java|grep tomcat|grep 'org.apache.catalina.startup.Bootstrap'|grep -v grep|awk -F '-Dcatalina.home=' '{print $2}'| awk '{print $1}'"
		catalinas = subprocess.Popen(catalinas_command, shell=True, stdout=subprocess.PIPE).communicate()[0].decode().splitlines()
		for catalina in catalinas:
			if os.path.exists(catalina+"/conf/server.xml"):
				if catalina not in catalina_list:
					catalina_list.append(catalina)
		return catalina_list

	elif OS_TYPE == "AIX":
		catalinas_command = "ps -ef|grep java|grep tomcat|grep 'org.apache.catalina.startup.Bootstrap'|grep -v grep|awk -F '-Dcatalina.home=' '{print $2}'| awk '{print $1}'"
		catalinas = subprocess.Popen(catalinas_command, shell=True, stdout=subprocess.PIPE).communicate()[0].decode().splitlines()
		for catalina in catalinas:
			if os.path.exists(catalina+"/conf/server.xml"):
				if catalina not in catalina_list:
					catalina_list.append(catalina)
		return catalina_list

	elif OS_TYPE == "HP-UX":
		catalinas_command = "ps -efx|grep java|grep tomcat|grep 'org.apache.catalina.startup.Bootstrap'|grep -v grep|awk -F '-Dcatalina.home=' '{print $2}'| awk '{print $1}'"
		catalinas = subprocess.Popen(catalinas_command, shell=True, stdout=subprocess.PIPE).communicate()[0].decode().splitlines()
		for catalina in catalinas:
			if os.path.exists(catalina + "/conf/server.xml"):
				if catalina not in catalina_list:
					catalina_list.append(catalina)
		return catalina_list
	else:
		print(("ERROR! This os (%s) is not supported." % OS_TYPE))

def getHostAllIPs():
	ipstmp = list(set(socket.gethostbyname_ex(socket.gethostname())[-1]))
	ipstmp.append("localhost")
	return ipstmp
	
def optionsMatch(express,shelloptions,default):
	outvalue = re.findall(express,shelloptions)
	if len(outvalue) > 1:
		custvalue = re.findall(express,custexp)
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
	return subprocess.Popen(cmdstr, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE).communicate()[0].decode().strip()
	
def parseCI(catalina_homes):

	global httpport,connetiontimeout,maxThreads,minsparethreads,acceptcount,maxHttpHeaderSize,username,state,JAVA_NUM
	
	for catalina_home in catalina_homes:
    
		if OS_TYPE == "HP-UX":
			java_command = "ps -efx|grep %s|grep java|grep -v grep |awk '{print $9}'" % catalina_home
			java_path = subprocess.Popen(java_command, shell=True, stdout=subprocess.PIPE).communicate()[0].decode().split("bin")[0]
		elif OS_TYPE == "AIX":
			java_command = "ps -ef|grep %s|grep java|grep -v grep |awk '{print $9}'" % catalina_home
			java_path = subprocess.Popen(java_command, shell=True, stdout=subprocess.PIPE).communicate()[0].decode().split("bin")[0]
		else:
			java_command = "ps -ef|grep %s|grep java|grep -v grep |awk '{print $8}'" % catalina_home
			java_path = subprocess.Popen(java_command, shell=True, stdout=subprocess.PIPE).communicate()[0].decode().split("bin")[0]
		
		os.environ['JAVA_HOME']=java_path
		env_shell_options = subprocess.Popen("%s/bin/version.sh" %catalina_home, shell=True, stdout=subprocess.PIPE).communicate()[0].decode()
		PRODVERSION = re.findall("Server version: (.*)\s",env_shell_options)[0].split("/");
		JAVA_VERSION = re.findall("JVM Version:    (.*)\s",env_shell_options)
		JAVA_NUM = float(JAVA_VERSION[0].split("_")[0][0:3])
        
		if OS_TYPE == "HP-UX":
			options_command = "ps -efx|grep %s|grep -v grep" % catalina_home
			jvm_shell_options = subprocess.Popen(options_command, shell=True, stdout=subprocess.PIPE).communicate()[0].decode()
		elif OS_TYPE == "AIX":
			options_command = "ps -ef|grep %s|grep -v grep" % catalina_home
			jvm_shell_options = subprocess.Popen(options_command, shell=True, stdout=subprocess.PIPE).communicate()[0].decode()
		else:
			options_command = "ps -ef|grep %s|grep -v grep" % catalina_home
			jvm_shell_options = subprocess.Popen(options_command, shell=True, stdout=subprocess.PIPE).communicate()[0].decode()

		maxheap = optionsMatch("-Xmx(.+?[mMgG])\S*",jvm_shell_options,"512m")
		minheap = optionsMatch("-Xms(.+?[mMgG])\S*",jvm_shell_options,"256m")
		youngsize = optionsMatch("-Xmn(.+?[mMgG])\S*",jvm_shell_options,"")

		if JAVA_NUM >= 1.8:
			maxmate = optionsMatch("-XX:MaxMetaspaceSize=(.+?[mMgG])\S*",jvm_shell_options,"")
			minmate = optionsMatch("-XX:MetaspaceSize=(.+?[mMgG])\S*",jvm_shell_options,"20m")
		else:
			maxperm = optionsMatch("-XX:MaxPermSize=(.+?[mMgG])\S*",jvm_shell_options,"256m")
			minperm = optionsMatch("-XX:PermSize=(.+?[mMgG])\S*",jvm_shell_options,"128m")

		startscript = catalina_home+'/bin/startup.sh'
		stopscript = catalina_home+'/bin/shutdown.sh'
		CATALINA_LOGPATH = catalina_home + "/logs"
		
		javainfo = subprocess.Popen("%s/bin/java -version 2>&1" % java_path, shell=True, stdout=subprocess.PIPE).communicate()[0].decode()

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
						
		serverxml = catalina_home+'/conf/server.xml'
		tree=ET.parse(serverxml) 
		root = tree.getroot()  
		shutdownport = root.attrib.get("port")
		
		for connector in root.iter(tag = 'Connector'):
			protocol = connector.get('protocol')
			if protocol.lower().find("http") >= 0:
				httpport = connector.get('port')
				maxHttpHeaderSize = connector.get('maxHttpHeaderSize')
				maxThreads = connector.get('maxThreads')
				minsparethreads = connector.get('minSpareThreads')
				acceptcount = connector.get('acceptCount')
				connetiontimeout = connector.get('connectionTimeout')

		if OS_TYPE == "HP-UX":
			username = getServerInfo("ps -efx|grep %s|grep -v grep|awk '{print $1}'" % catalina_home)
		else:
			username = getServerInfo("ps -ef|grep %s|grep -v grep|awk '{print $1}'" % catalina_home)

		if OS_TYPE == "HP-UX":
			serverinfo = getServerInfo("ps -efx|grep java|grep tomcat|grep 'org.apache.catalina.startup.Bootstrap'|grep -v grep|awk '{print $NF}'")
			if len(serverinfo) > 0:
				state = "start"
			else:
				state = "No Tomcat Process"
		else:
			serverinfo = getServerInfo("ps -ef|grep java|grep tomcat|grep 'org.apache.catalina.startup.Bootstrap'|grep -v grep|awk '{print $NF}'")
			if len(serverinfo) > 0:
				state = "start"
			else:
				state = "No Tomcat Process"
		
		appdir = catalina_home + "/webapps/"
		filenum = 0
		list = os.listdir(appdir)
		for line in list:
			filepath = os.path.join(appdir, line)
			if os.path.isdir(filepath):
				filenum = filenum + 1
				if os.path.exists(filepath+"/WEB-INF/web.xml"):
					if line != "ROOT" and line != "docs" and line != "examples" and line != "host-manager" and line !="manager" :
						appname = line
						sourcepath = filepath
						catalinatoapp.append(
						{"catalina_home":catalina_home,
						"appname":appname,
						"sourcepath":sourcepath
						})
		
		for engine in root.iterfind("Service/Engine"):
			engine_name = engine.get("name")
			for host in engine.iterfind("Host"):
				host_name = host.get("name")
				dirfile="%s" % (catalina_home+ "/conf/"+engine_name +"/"+host_name)
				if os.path.exists(dirfile):
					filenames = os.listdir(dirfile)
					if len(filenames) > 0:
						for filename in filenames:
							file_name = os.path.splitext(filename)[0]
							file_extends = os.path.splitext(filename)[1]
							if file_extends == ".xml" :
								fileTree = ET.parse(dirfile + "/" + filename)
								fileroot = fileTree.getroot()
								sourcepath = fileroot.attrib.get("docBase")
								if sourcepath is None:
									pass
								else:
									appname = os.path.splitext(filename)[0]
									catalinatoapp.append(
										{"catalina_home":catalina_home,
										"appname":appname,
										"sourcepath":sourcepath
										})
				else:
					print("dir file not exists")

				for context in host.iterfind("Context"):
					appname = context.attrib.get("path")
					sourcepath = context.attrib.get("docBase")
					catalinatoapp.append(
						{"catalina_home":catalina_home,
						"appname":appname,
						"sourcepath":sourcepath
						})
					
		#tomcat server info
		catalinatoserver.append(
		{"shutdownport":shutdownport,
		"httpport":httpport,
		"connetiontimeout":connetiontimeout,
		"maxThreads":maxThreads,
		"minsparethreads":minsparethreads,
		"acceptcount":acceptcount,
		"catalina_home":catalina_home,
		"prodname":PRODVERSION[0],
		"prodversion":PRODVERSION[1],
		"prodlogpath":CATALINA_LOGPATH,
		"startscript":startscript,
		"stopscript":stopscript,
		"username":username,
		"serverxml":serverxml
		})
		
	
		#tomcat jvm info
		if JAVA_NUM >= 1.8:
			catalinatojvm.append(
			{"catalina_home":catalina_home,
			"javahome":java_path,
			"maxheap":maxheap,
			"minheap":minheap,
			"youngsize":youngsize,
			"maxmate":maxmate,
			"minmate":minmate,
			"runbit":runbit,
			"javaversion":JAVA_VERSION[0],
			"vendor":vendor
			})
		else:
			catalinatojvm.append(
			{"catalina_home":catalina_home,
			"javahome":java_path,
			"maxheap":maxheap,
			"minheap":minheap,
			"youngsize":youngsize,
			"maxperm":maxperm,
			"minperm":minperm,
			"runbit":runbit,
			"javaversion":JAVA_VERSION[0],
			"vendor":vendor
			})

def buildCIJSON():
	catalinacijson = collections.OrderedDict()
	catalina_jvm = []
	catalina_server = []
	catalina_app = []

	for jvm in catalinatojvm:
		if JAVA_NUM >= 1.8:
			catalina_jvm.append(collections.OrderedDict([
				("hostname",hostname),
				("catalina_home",jvm["catalina_home"]),
				("javahome",jvm["javahome"]),
				("maxheap",jvm["maxheap"]),
				("minheap",jvm["minheap"]),
				("youngsize",jvm["youngsize"]),
				("maxmate",jvm["maxmate"]),
				("minmate",jvm["minmate"]),
				("runbit",jvm["runbit"]),
				("javaversion",jvm["javaversion"]),
				("vendor",jvm["vendor"])
			]))
		else:
			catalina_jvm.append(collections.OrderedDict([
				("hostname",hostname),
				("catalina_home",jvm["catalina_home"]),
				("javahome",jvm["javahome"]),
				("maxheap",jvm["maxheap"]),
				("minheap",jvm["minheap"]),
				("youngsize",jvm["youngsize"]),
				("maxperm",jvm["maxperm"]),
				("minperm",jvm["minperm"]),
				("runbit",jvm["runbit"]),
				("javaversion",jvm["javaversion"]),
				("vendor",jvm["vendor"])
			]))

	for server in catalinatoserver:
		catalina_server.append(collections.OrderedDict([
			("hostname",hostname),
			("catalina_home",server["catalina_home"]),
			("prodname",server["prodname"]),
			("prodversion",server["prodversion"]),
			("prodlogpath",server["prodlogpath"]),
			("username",server["username"]),
			("shutdownport",server["shutdownport"]),
			("httpport",server["httpport"]),
			("connetiontimeout",server["connetiontimeout"]),
			("maxThreads",server["maxThreads"]),
			("minsparethreads",server["minsparethreads"]),
			("acceptcount",server["acceptcount"]),
			("startscript",server["startscript"]),
			("stopscript",server["stopscript"]),
			("serverxml",server["serverxml"])			
		]))
	
	for app in catalinatoapp:
		catalina_app.append(collections.OrderedDict([
			("hostname",hostname),
			("catalina_home",app["catalina_home"]),
			("appname",app["appname"]),
			("sourcepath",app["sourcepath"])
		]))
		
	catalinacijson.update(tomcat_server=catalina_server)
	catalinacijson.update(tomcat_jvm=catalina_jvm)
	catalinacijson.update(tomcat_app=catalina_app)
	catalinacijson.update(collection_time=currtime)
	
	if state != "start":
		print("No Tomcat Process")
		exit()
	else:
		os.system("mkdir -p /tmp/enmotech/tomcat_cmdb")
		with open(JSONFILE, "w") as f:
			json.dump(catalinacijson, f)

if __name__ == "__main__":
	catalinatojvm = []
	catalinatoserver = []
	catalinatoapp = []
	os.system("rm -rf " + JSONFILE)

	try:
		catalina_homes = getCatalina()
		parseCI(catalina_homes)
		buildCIJSON()
	except Exception as e:
		print("error! Execute failed ,message : ")
		print(("%s" % traceback.format_exc()))
	sys.exit(0)