#!/usr/bin/env python
# -*- coding:utf-8 -*-
# nginx_cmdb with python3

import os
import sys
import re
import time
import json
import traceback
import collections
import subprocess
import platform
import socket

OS_TYPE = platform.system()
hostname = socket.gethostname()
currtime = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time()))
JSONFILE = '/tmp/enmotech/nginx_cmdb/nginx_cmdb.json'

def getNginx():
	nginx_list = []
	if OS_TYPE == "Linux":
		psCMD = "ps -ef|grep nginx|grep master|grep -v grep|awk '{print $2}'"
		nginxPID = os.popen(psCMD).read().splitlines()
		if nginxPID:
			for npid in nginxPID:
				exeCMD = "ls -l /proc/%s/exe |awk '{print $NF}'" % npid
				nginx_bin = os.popen(exeCMD).read().strip()
				nginx_info = os.popen(nginx_bin + " -V 2>&1").read().strip()
				nginx_dir = nginx_info.split('--prefix=')[1].split()[0]
				if os.path.exists(nginx_dir+"/conf/nginx.conf"):
					if nginx_dir not in nginx_list:
						nginx_list.append(nginx_dir)
			return nginx_list
		else:
			print("No Nginx Process!")

	elif OS_TYPE == "AIX":
		psCMD = "ps -ef|grep nginx|grep master|grep -v grep|awk '{print $2}'"
		nginxPID = os.popen(psCMD).read().splitlines()
		if len(nginxPID):
			for npid in nginxPID:
				cwdCMD = "ls -l /proc/%s/cwd|awk '{print $NF}'" % npid
				nginx_dir = os.popen(cwdCMD).read().strip()
				if os.path.exists(nginx_dir+"/conf/nginx.conf"):
					if nginx_dir not in nginx_list:
						nginx_list.append(nginx_dir)
				else:
					print("Can't find process of nginx！")
			return nginx_list
		else:
			print("No Nginx Process!")

	elif OS_TYPE == "HP-UX":
		psCMD = "ps -efx|grep nginx|grep master|grep -v grep|awk '{print $2}'"
		nginxPID = os.popen(psCMD).read().splitlines()
		if len(nginxPID):
			for npid in nginxPID:
				cwdCMD = "lsof -p %s 2>/dev/null|grep cwd|awk '{print $NF}'" % npid
				nginx_dir = os.popen(cwdCMD).read().strip()
				if os.path.exists(nginx_dir+"/conf/nginx.conf"):
					if nginx_dir not in nginx_list:
						nginx_list.append(nginx_dir)
				else:
					print("Can't find process of nginx！")
			return nginx_list
		else:
			print("No Nginx Process!")
	else:
		print(("ERROR! This os (%s) is not supported." % OS_TYPE))

def parse(nginx_homes):

	userCMD = "ps -ef|grep -v grep|grep nginx|grep master|awk '{print $1}'"
	runuser = os.popen(userCMD).read().splitlines()
	a = 0
	for nginx_home in nginx_homes:

		nginx_tmp = os.popen(nginx_home + "/sbin/nginx -V 2>&1").read().strip()
		prodversion = re.findall("nginx version: (.*)\s", nginx_tmp)[0].split("/")[1]
		username = runuser[a]
		a = a + 1
		startscript = nginx_home + "/sbin/nginx"
		stopscript = nginx_home + "/sbin/nginx"
		nginxconf = nginx_home + "/conf/nginx.conf"
		confCMD = "cat %s|grep -v '#'|sed '/^$/d'" % nginxconf
		confData = os.popen(confCMD).read().strip()
		listenport = re.findall("listen(.*)\s", confData)[0].strip().strip(";")
		processnum = re.findall("worker_processes(.*)\s", confData)[0].strip().strip(";")
		access_log = re.findall("access_log.+", confData)
		error_log = re.findall("error_log.+", confData)
		if access_log:
			accesslog = access_log[0].strip()
		else:
			accesslog = nginx_home + "/logs/access.log"
		if error_log:
			errorlog = error_log[0].strip()
		else:
			errorlog = nginx_home + "/logs/error.log"
		hide = re.findall("server_tokens(.*)", confData)
		if hide:
			server_tokens = hide[0].strip()
		else:
			server_tokens = "ON"

		nginxinfo.append(
		{"nginxhome":nginx_home,
		"prodversion":prodversion,
		"listenport":listenport,
		"username":username,
		"processnum":processnum,
		"nginxconf":nginxconf,
		"accesslog":accesslog,
		"errorlog":errorlog,
		"startscript":startscript,
		"stopscript":stopscript,
		"server_tokens":server_tokens
		})

def buildJSON():
	nginxjson = collections.OrderedDict()
	nginx_info = []

	for nginx in nginxinfo:
		nginx_info.append(collections.OrderedDict([
			("hostname",hostname),
			("nginxhome",nginx["nginxhome"]),
			("prodversion",nginx["prodversion"]),
			("username",nginx["username"]),
			("listenport",nginx["listenport"]),
			("processnum",nginx["processnum"]),
			("nginxconf",nginx["nginxconf"]),
			("accesslog",nginx["accesslog"]),
			("errorlog",nginx["errorlog"]),
			("server_tokens",nginx["server_tokens"]),
			("startscript",nginx["startscript"]),
			("stopscript",nginx["stopscript"])
		]))

	nginxjson.update(nginx_info=nginx_info)
	nginxjson.update(collection_time=currtime)

	os.system("mkdir -p /tmp/enmotech/nginx_cmdb")
	with open(JSONFILE, "w") as f:
		json.dump(nginxjson, f)


if "__main__" == __name__:
	nginxinfo = []
	os.system("rm -f " + JSONFILE)
	try:
		nginx_homes = getNginx()
		parse(nginx_homes)
		buildJSON()
	except Exception as e:
		print("error! Execute failed ,message : ")
		print(("%s" % traceback.format_exc()))
	sys.exit(0)