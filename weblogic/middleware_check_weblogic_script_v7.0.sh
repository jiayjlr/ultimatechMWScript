#!/bin/bash
#version:2.0
#monitor:weblogic/os
#update: 根据需求，将整体脚本做了切割，以独立产品做数据采集
#update-date:2022-03-18

#----------------------------------------OS层数据采集------------------------------------------------
function collect_sys_info() {

    echo "|+++++++++++++++++++++++++++++++++++++++++++++++++++++++++|"
    echo "|                      os info                            |"
    echo "|+++++++++++++++++++++++++++++++++++++++++++++++++++++++++|"
    echo ""

    echo "--------------系统检查--------------"
    IP_Address=$(ip addr show | grep 'state UP' -A 2 | grep "inet " | grep -v 127.0.0. | head -1 | cut -d" " -f6 | cut -d/ -f1)
    echo "IP:$IP_Address"
    Hostname=$(hostname -s)
    echo "Hostname:$Hostname"
    Architecture=$(getconf LONG_BIT)
    echo "Architecture:$Architecture"
    Kernel_Release=$(uname -r)
    echo "Kernel_Release:$Kernel_Release"
    Physical_Memory=$(sudo dmidecode | grep "^[[:space:]]*Size.*MB$" | uniq -c | sed 's/ \t*Size: /\*/g' | sed 's/^ *//g')
    echo "Physical_Memory:$Physical_Memory"
    Cpu_Cores=$(cat /proc/cpuinfo | grep "cpu cores" | uniq | awk -F ': ' '{print $2}')
    echo "Cpu_Cores:$Cpu_Cores"
    Cpu_Proc_Num=$(cat /proc/cpuinfo | grep "processor" | uniq | wc -l)
    echo "Cpu_Proc_Num:$Cpu_Proc_Num"
    LastReboot=$(who -b | awk '{print $3,$4}')
    echo "LastReboot:$LastReboot"
    Uptime=$(uptime | sed 's/.*up \([^,]*\), .*/\1/')
    echo "Uptime:$Uptime"
    Load=$(uptime | awk -F ":" '{print $NF}')
    echo "Load:$Load"
    MemTotal=$(cat /proc/meminfo | awk '/^MemTotal/{print $2}') #内存总量
    echo "MemTotal:$(convert_unit $MemTotal)"
    MemFree=$(cat /proc/meminfo | awk '/^MemFree/{print $2}') #空闲内存
    echo "MemFree:$(convert_unit $MemFree)"
    MemBuffers=$(cat /proc/meminfo | awk '/^Buffers/{print $2}')    #Buffers
    MemCached=$(cat /proc/meminfo | awk '/^Cached/{print $2}')      #Cached
    MemUsed=$(expr $MemTotal - $MemFree - $MemBuffers - $MemCached) #已用内存
    echo "MemUsed:$(convert_unit $MemUsed)"
    Mem_Rate=$(awk 'BEGIN{printf"%.2f\n",'$MemUsed' / '$MemTotal' *100}') #保留小数点后2位
    echo "Mem_Rate:$Mem_Rate%"
    Swap_Method=$(cat /proc/sys/vm/swappiness)
    Openfile=$(ulimit -a | grep "open files" | awk '{print $NF}')
    echo "Openfile:$Openfile"
    echo "Swap_Method:$Swap_Method"
    Usesum=0
    Totalsum=0
    disknum=$(df -hlT | wc -l)
    for ((n = 2; n <= $disknum; n++)); do
        use=$(df -k | awk NR==$n'{print int($3)}')
        pertotal=$(df -k | awk NR==$n'{print int($2)}')
        Usesum=$(($Usesum + $use))          #计算已使用的总量
        Totalsum=$(($Totalsum + $pertotal)) #计算总量
    done
    Freesum=$(($Totalsum - $Usesum))
    Diskutil=$(awk 'BEGIN{printf"%.2f\n",'$Usesum' / '$Totalsum'*100}')
    Freeutil=$(awk 'BEGIN{printf"%.2f\n",100 - '$Diskutil'}')

    #磁盘总量
    if [ $Totalsum -ge 0 -a $Totalsum -lt 1024 ]; then
        echo "Totalsum:$To'ta'l'su'm K"

    elif [ $Totalsum -gt 1024 -a $Totalsum -lt 1048576 ]; then
        Totalsum=$(awk 'BEGIN{printf"%.2f\n",'$Totalsum' / 1024}')
        echo "Totalsum:$Totalsum M"

    elif [ $Totalsum -gt 1048576 ]; then
        Totalsum=$(awk 'BEGIN{printf"%.2f\n",'$Totalsum' / 1048576}')
        echo "Totalsum:$Totalsum G"

    fi

    #磁盘已使用总量
    if [ $Usesum -ge 0 -a $Usesum -lt 1024 ]; then
        echo "Usesum:$Usesum K"

    elif [ $Usesum -gt 1024 -a $Usesum -lt 1048576 ]; then
        Usesum=$(awk 'BEGIN{printf"%.2f\n",'$Usesum' / 1024}')
        echo "Usesum:$Usesum M"

    elif [ $Usesum -gt 1048576 ]; then
        Usesum=$(awk 'BEGIN{printf"%.2f\n",'$Usesum' / 1048576}')
        echo "Usesum:$Usesum G"

    fi

    #磁盘未使用总量
    if [ $Freesum -ge 0 -a $Freesum -lt 1024 ]; then
        echo "Freesum:$Freesum K"

    elif [ $Freesum -gt 1024 -a $Freesum -lt 1048576 ]; then
        Freesum=$(awk 'BEGIN{printf"%.2f\n",'$Freesum' / 1024}')
        echo "Freesum:$Freesum M"

    elif [ $Freesum -gt 1048576 ]; then
        Freesum=$(awk 'BEGIN{printf"%.2f\n",'$Freesum' / 1048576}')
        echo "Freesum:$Freesum G"
    fi
    #磁盘占用率
    echo "Diskutil:$Diskutil%"

    #磁盘空闲率
    echo "Freeutil:$Freeutil%"

    #
    IO_User=$(iostat -x -k 2 1 | tail -6 | grep -v Device: | grep -v vda | grep -v avg | awk -F " " '{print $2}')
    IO_System=$(iostat -x -k 2 1 | tail -6 | grep -v Device: | grep -v vda | grep -v avg | awk -F " " '{print $4}')
    IO_Wait=$(iostat -x -k 2 1 | tail -6 | grep -v Device: | grep -v vda | grep -v avg | awk -F " " '{print $5}')
    IO_Idle=$(iostat -x -k 2 1 | tail -6 | grep -v Device: | grep -v vda | grep -v avg | awk -F " " '{print $NF}')
    echo "IO_User:$IO_User%"
    echo "IO_System:$IO_System%"
    echo "IO_Wait:$IO_Wait%"
    echo "IO_Idle:$IO_Idle%"
    #TCP参数获取
    Tcp_Tw_Recycle=$(sysctl net.ipv4.tcp_tw_recycle | awk -F "=" '{print $2}')
    echo "Tcp_Tw_Recycle:$Tcp_Tw_Recycle"
    #该参数的作用是快速回收timewait状态的连接。上面虽然提到系统会自动删除掉timewait状态的连接，但如果把这样的连接重新利用起来岂不是更好。
    #所以该参数设置为1就可以让timewait状态的连接快速回收，它需要和下面的参数配合一起使用
    Tcp_Tw_Reuse=$(sysctl net.ipv4.tcp_tw_reuse | awk -F "=" '{print $2}')
    echo "Tcp_Tw_Reuse:$Tcp_Tw_Reuse"
    #该参数设置为1，将timewait状态的连接重新用于新的TCP连接，要结合上面的参数一起使用。
    Tcp_Fin_Timeout=$(sysctl net.ipv4.tcp_fin_timeout | awk -F "=" '{print $2}')
    echo "Tcp_Fin_Timeout:$Tcp_Fin_Timeout"
    #tcp连接的状态中，客户端上有一个是FIN-WAIT-2状态，它是状态变迁为timewait前一个状态。
    #该参数定义不属于任何进程该连接状态的超时时间，默认值为60，建议调整为6。
    Tcp_Keepalive_Time=$(sysctl net.ipv4.tcp_keepalive_time | awk -F "=" '{print $2}')
    echo "Tcp_Keepalive_Time:$Tcp_Keepalive_Time"
    #表示当keepalive起用的时候，TCP发送keepalive消息的频度。缺省是2小时，改为30分钟。
    Tcp_Keepalive_Probes=$(sysctl net.ipv4.tcp_keepalive_probes | awk -F "=" '{print $2}')
    echo "Tcp_Keepalive_Probes:$Tcp_Keepalive_Probes"
    #如果对方不予应答，探测包的发送次数
    Tcp_Keepalive_Intvl=$(sysctl net.ipv4.tcp_keepalive_intvl | awk -F "=" '{print $2}')
    echo "Tcp_Keepalive_Intvl:$Tcp_Keepalive_Intvl"
    #keepalive探测包的发送间隔

    echo "--------------原始数据采集_补充--------------"
    echo "----->>>---->>>  CPU usage"
    sar 2 5
    echo ""
    echo "----->>>---->>>  resource limit"
    cat /etc/security/limits.conf | grep -v '^#' | grep -v '^$'
    echo ""
    echo "----->>>---->>>  io scheduler"
    dmesg | grep -i scheduler
    echo ""
    echo "----->>>---->>>  disk mount "
    df -h
    echo "----->>>---->>>  weblogic process info  "
    ps -ef | grep java | grep -v grep | grep weblogic.Server

}

#单位转换函数
function convert_unit() {
    result=$1
    if [ $result -ge 1048576 ]; then
        value=1048576                                                 #1024*1024
        result_gb=$(awk 'BEGIN{printf"%.2f\n",'$result' / '$value'}') #将KB转换成GB，并保留2位小数
        echo $result_gb"GB"
    elif [ $result -ge 1024 ]; then
        value=1024
        result_mb=$(awk 'BEGIN{printf"%.2f\n",'$result' / '$value'}') #将KB转换成MB，并保留2位小数
        echo $result_mb"MB"
    else
        echo $result"KB"
    fi
}

#----------------------------------------weblogic info------------------------------------------------
function weblogic_info() {
    init=0
    jdbcinit=0
    jmsinit=0
    PIDCOUNT=$(ps -eo ruser,pid,args | grep "java" | grep weblogic.Server | grep -v grep | wc -l)
    PID=$(ps -eo ruser,pid,args | grep "java" | grep weblogic.Server | grep -v grep | awk ' { print $2 }')
    for OPID in $PID; do

        domain_dir=$(pwdx $OPID | awk -F ":" '{print $NF}')

        echo "{"

        echo "\"domain_dir\"":"\"$domain_dir\""","
        weblogic_dir=$(ps -feww | grep $OPID | grep -v grep | grep -io "weblogic.home=.*" | awk '{FS=" "; print $1}' | cut -d "=" -f2)
        echo "\"weblogic_dir\"":"\"$weblogic_dir\""","

        domain_name=${domain_dir##*/}
        echo "\"domain_name\"":"\"$domain_name\""","

        server_name=$(ps -feww | grep $OPID | grep -v grep | grep -io "weblogic.Name=.*" | awk '{FS=" "; print $1}' | cut -d "=" -f2)
        echo "\"server_name\"":"\"$server_name\""","

        server_port=$(netstat -tnlop | grep $OPID | grep tcp | head -n 1 | awk '{print $4}' | awk -F ':' '{print $NF}')

        #server_port=`netstat -natp|grep $OPID`
        #echo "server port is  $server_port"
        echo "\"server_port\"":"\"$server_port\""","

        server_jvm_Xms=$(ps -feww | grep $OPID | grep -v grep | grep -io "\-Xms.*" | awk '{print $1}')
        server_jvm_Xmx=$(ps -feww | grep $OPID | grep -v grep | grep -io "\-Xmx.*" | awk '{print $1}')
        server_jvm_permsize=$(ps -feww | grep $OPID | grep -v grep | grep -io "\-XX:PermSize=.*" | awk '{print $1}')
        server_jvm_MAXpermsize=$(ps -feww | grep $OPID | grep -v grep | grep -io "\-XX:MaxPermSize=.*" | awk '{print $1}')
        server_jvm="$server_jvm_Xms $server_jvm_Xmx $server_jvm_permsize $server_jvm_MAXpermsize"

        echo "\"server_jvm\"":"\"$server_jvm\""","

        managerServerCount=$(ps -ef | grep $OPID | grep Dweblogic.management.server | wc -l)
        if [ $managerServerCount != 0 ]; then
            adminUrl=$(ps -feww | grep $OPID | grep -v grep | grep -io "weblogic.management.server=.*" | awk '{FS=" "; print $1}' | cut -d "=" -f2)
            echo "\"adminURL\"":"\"$adminUrl\""","

        fi

        java_bin=$(ps -feww | grep $OPID | grep -v grep | awk '{print $8}')
        java_version=$($java_bin -version 2>&1 | sed '1!d' | sed s/\"//g)
        echo "\"java_version\"":"\"$java_version\""","

        source $domain_dir/bin/setDomainEnv.sh
        domain_version=$($java_bin weblogic.version | head -n 2 | tail -n 1)
        #domain_version=`grep 'domain-version' $domain_dir/config/config.xml | awk 'BEGIN{FS=">";RS="</"}{print $NF}' | sed '/^\(\s\)*$/d'`
        echo "\"domain_version\"":"\"$domain_version\""","

        mkdir -p /tmp/enmoResult/tmpcheck/${domain_name}_${server_name}_${OPID}
        cp $domain_dir/config/config.xml /tmp/enmoResult/tmpcheck/${domain_name}_${server_name}_${OPID}
        jdbcresourcecount=$(grep -i '</jdbc-system-resource>' $domain_dir/config/config.xml | wc -l)
        if [ $jdbcresourcecount -gt 0 ]; then
            cp $domain_dir/config/jdbc/* /tmp/enmoResult/tmpcheck/${domain_name}_${server_name}_${OPID}
            jdbc_start_num=$(grep -n '<jdbc-system-resource>' $domain_dir/config/config.xml | head -n 1 | awk -F ':' '{print $1}' | cut -d ' ' -f 4)
            jdbc_end_num=$(grep -n '</jdbc-system-resource>' $domain_dir/config/config.xml | tail -n 1 | awk -F ':' '{print $1}' | cut -d ' ' -f 4)
            jdbcinfo=$(sed -n ' '$jdbc_start_num','$jdbc_end_num' 'p' ' $domain_dir/config/config.xml | grep '<name>' | awk 'BEGIN{FS=">";RS="</"}{print $NF}' | sed '/^\(\s\)*$/d' | sed "s/[[:space:]]/_/g")

            echo \"jdbcinfo\": [
            for jdbc in $jdbcinfo; do

                jdbcurl=$(grep -i 'url' $domain_dir/config/jdbc/$jdbc*.xml | awk 'BEGIN{FS=">";RS="</"}{print $NF}' | sed '/^\(\s\)*$/d')
                jdbcdriver=$(grep -i 'driver-name' $domain_dir/config/jdbc/$jdbc*.xml | awk 'BEGIN{FS=">";RS="</"}{print $NF}' | sed '/^\(\s\)*$/d')

                usernumline=$(grep -n '<name>user</name>' $domain_dir/config/jdbc/$jdbc*.xml | awk -F ':' '{print $1}' | cut -d ' ' -f 4)
                uservaluenumline=$(expr $usernumline + 1)
                jdbcuser=$(sed -n ' '$uservaluenumline' 'p' ' $domain_dir/config/jdbc/$jdbc*.xml | awk 'BEGIN{FS=">";RS="</"}{print $NF}' | sed '/^\(\s\)*$/d')
                #jdbcuser=`grep -i 'value'  $domain_dir/config/jdbc/$jdbc*.xml | awk 'BEGIN{FS=">";RS="</"}{print $NF}' | sed '/^\(\s\)*$/d'`

                initialcapacitycount=$(grep -i 'initial-capacity' $domain_dir/config/jdbc/$jdbc*.xml | wc -l)
                if [ $initialcapacitycount == 1 ]; then
                    jdbcinitialcapacity=$(grep -i 'initial-capacity' $domain_dir/config/jdbc/$jdbc*.xml | awk 'BEGIN{FS=">";RS="</"}{print $NF}' | sed '/^\(\s\)*$/d')
                    #echo $jdbcinitialcapacity
                else
                    jdbcinitialcapacity=1
                    #echo $jdbcinitialcapacity
                fi
                maxcapacitycount=$(grep -i 'max-capacity' $domain_dir/config/jdbc/$jdbc*.xml | wc -l)
                if [ $maxcapacitycount == 1 ]; then
                    jdbcmaxcapacity=$(grep -i 'max-capacity' $domain_dir/config/jdbc/$jdbc*.xml | awk 'BEGIN{FS=">";RS="</"}{print $NF}' | sed '/^\(\s\)*$/d')
                    #echo $jdbcmaxcapacity
                else
                    jdbcmaxcapacity=15
                    #echo $jdbcmaxcapacity
                fi
                echo "{"
                echo "\"jdbcname\"":"\"$jdbc\""","
                echo "\"jdbcurl\"":"\"$jdbcurl\""","
                echo "\"jdbcdriver\"":"\"$jdbcdriver\""","
                echo "\"jdbcuser\"":"\"$jdbcuser\""","
                echo "\"jdbcinitialcapacity\"":"\"$jdbcinitialcapacity\""","
                echo "\"jdbcmaxcapacity\"":"\"$jdbcmaxcapacity\""
                jdbcinit=$(expr $jdbcinit + 1)
                echo "}"
                [ $jdbcinit -lt $jdbcresourcecount ] && echo ","
            done
            jdbcinit=0
            echo "],"
        fi

        jmsresourcecount=$(grep -i '</jms-system-resource>' $domain_dir/config/config.xml | wc -l)
        if [ $jmsresourcecount -gt 0 ]; then
            cp $domain_dir/config/jms/* /tmp/enmoResult/tmpcheck/${domain_name}_${server_name}_${OPID}
            jms_start_num=$(grep -n '<jms-system-resource>' $domain_dir/config/config.xml | head -n 1 | awk -F ':' '{print $1}' | cut -d ' ' -f 4)
            jms_end_num=$(grep -n '</jms-system-resource>' $domain_dir/config/config.xml | tail -n 1 | awk -F ':' '{print $1}' | cut -d ' ' -f 4)
            jmsinfo=$(sed -n ' '$jms_start_num','$jms_end_num' 'p' ' $domain_dir/config/config.xml | grep '<descriptor-file-name>' | awk 'BEGIN{FS=">";RS="</"}{print $NF}' | sed '/^\(\s\)*$/d' | sed "s/[[:space:]]/_/g")

            echo \"jmsinfo\": [
            for jms in $jmsinfo; do
                echo "{"
                connectorycount=$(grep -i '<connection-factory' $domain_dir/config/$jms | wc -l)
                if [ $connectorycount -gt 0 ]; then
                    connectory=$(cat $domain_dir/config/$jms | grep '<connection-factory' | awk -F '"' '{print $2}')
                    echo "\"connectory\"":"\"$connectory\""","
                fi

                queuecount=$(grep -i '<queue' $domain_dir/config/$jms | wc -l)
                if [ $queuecount -gt 0 ]; then
                    queue=$(cat $domain_dir/config/$jms | grep '<queue' | awk -F '"' '{print $2}')
                    echo "\"queue\"":"\"$queue\""","
                fi

                topiccount=$(grep -i '<topic' $domain_dir/config/$jms | wc -l)
                if [ $topiccount -gt 0 ]; then
                    topic=$(cat $domain_dir/config/$jms | grep '<topic' | awk -F '"' '{print $2}')
                    echo "\"topic\"":"\"$topic\""","
                fi

                jndicount=$(grep -i '<jndi-name>' $domain_dir/config/$jms | wc -l)
                if [ $jndicount -gt 0 ]; then
                    jndi=$(cat $domain_dir/config/$jms | grep '<jndi-name>' | awk 'BEGIN{FS=">";RS="</"}{print $NF}' | sed '/^\(\s\)*$/d' | sed "s/[[:space:]]/_/g")
                    echo "\"jndi\"":"\"$jndi\""","
                fi
                jmsmodulename=$(echo ${jms#*/})
                jmsmodulename=$(echo ${jmsmodulename%.*})
                echo "\"jmsmodulename\"":"\"$jmsmodulename\""
                jmsinit=$(expr $jmsinit + 1)
                echo "}"
                [ $jmsinit -lt $jmsresourcecount ] && echo ","
            done
            jmsinit=0
            echo "],"
        fi

        appdeploymentcount=$(grep '<app-deployment>' $domain_dir/config/config.xml | wc -l)
        if [ $appdeploymentcount -gt 0 ]; then
            app_start_num=$(grep -n '<app-deployment>' $domain_dir/config/config.xml | head -n 1 | awk -F ':' '{print $1}' | cut -d ' ' -f 4)
            app_end_num=$(grep -n '</app-deployment>' $domain_dir/config/config.xml | tail -n 1 | awk -F ':' '{print $1}' | cut -d ' ' -f 4)

            appinfo=$(sed -n ' '$app_start_num','$app_end_num' 'p' ' $domain_dir/config/config.xml | grep -oP '(?<=name>)[^<]+')

            #appinfo=`sed -n  ' '$app_start_num','$app_end_num' 'p' ' config.xml | grep 'name' | awk 'BEGIN{FS=">";RS="</"}{print $NF}' | sed '/^\(\s\)*$/d' `
            appinfo=$(echo $appinfo | sed 's/[ ][ ]*/,/g')
            echo "\"appinfo\"":"\"$appinfo\""","
        fi

        #判断生产模式开发模式
        productionmodecount=$(grep -i 'production-mode-enabled' $domain_dir/config/config.xml | wc -l)
        if [ $productionmodecount == 0 ]; then
            productionmode=development
        else
            productionmode=production
        fi

        runUser=$(ps -eo ruser,pid | grep $OPID | awk '{print $1}')
        adminServer=$(grep 'admin-server-name' $domain_dir/config/config.xml | awk 'BEGIN{FS=">";RS="</"}{print $NF}' | sed '/^\(\s\)*$/d')

        echo "\"adminServer\"":"\"$adminServer\""","
        echo "\"productionmode\"":"\"$productionmode\""","
        echo "\"runUser\"":"\"$runUser\""","
        if [ x$runUser == x'root' ]; then
                echo "\"runUserResult\"":"\"Failed\""
            else
                echo "\"runUserResult\"":"\"Pass\""
            fi

        cp $domain_dir/servers/${server_name}/logs/${server_name}.log /tmp/enmoResult/tmpcheck/${domain_name}_${server_name}_${OPID}
        init=$(expr $init + 1)
        echo "}"
        [ $init -lt $PIDCOUNT ] && echo ","

    done

}

function get_os_jsondata() {

    #for file in  $data_path/tmp/tmpcheck/*_os_*.txt ;

    file="$filepath""$filename1"

    #echo "=====================OS基础信息=====================" >> $new_document
    IP_Address=$(cat $file | grep IP | awk -F ":" '{print $2}') && echo "\"IP_Address\"":"\"$IP_Address\"""," >>$new_document
    Hostname=$(cat $file | grep Hostname | awk -F ":" '{print $2}') && echo "\"Hostname\"":"\"$Hostname\"""," >>$new_document
    Architecture=$(cat $file | grep Architecture | awk -F ":" '{print $2}') && echo "\"Architecture\"":"\"$Architecture\"""," >>$new_document
    Kernel_Release=$(cat $file | grep Kernel_Release | awk -F ":" '{print $2}') && echo "\"Kernel_Release\"":"\"$Kernel_Release\"""," >>$new_document
    Physical_Memory=$(cat $file | grep Physical_Memory | awk -F ":" '{print $2}') && echo "\"Physical_Memory\"":"\"$Physical_Memory\"""," >>$new_document
    Cpu_Cores=$(cat $file | grep Cpu_Cores | awk -F ":" '{print $2}') && echo "\"Cpu_Cores\"":"\"$Cpu_Cores\"""," >>$new_document
    Cpu_Proc_Num=$(cat $file | grep Cpu_Proc_Num | awk -F ":" '{print $2}') && echo "\"Cpu_Proc_Num\"":"\"$Cpu_Proc_Num\"""," >>$new_document
    LastReboot=$(cat $file | grep LastReboot | awk -F ":" '{print $2}') && echo "\"LastReboot\"":"\"$LastReboot\"""," >>$new_document
    Uptime=$(cat $file | grep Uptime | awk -F ":" '{print $2}') && echo "\"Uptime\"":"\"$Uptime\"""," >>$new_document
    Load=$(cat $file | grep Load | awk -F ":" '{print $2}') && echo "\"Load\"":"\"$Load\"""," >>$new_document
    MemTotal=$(cat $file | grep MemTotal | awk -F ":" '{print $2}') && echo "\"MemTotal\"":"\"$MemTotal\"""," >>$new_document
    MemFree=$(cat $file | grep MemFree | awk -F ":" '{print $2}') && echo "\"MemFree\"":"\"$MemFree\"""," >>$new_document
    MemUsed=$(cat $file | grep MemUsed | awk -F ":" '{print $2}') && echo "\"MemUsed\"":"\"$MemUsed\"""," >>$new_document
    Mem_Rate=$(cat $file | grep Mem_Rate | awk -F ":" '{print $2}') && echo "\"Mem_Rate\"":"\"$Mem_Rate\"""," >>$new_document
    Openfile=$(cat $file | grep Openfile | awk -F ":" '{print $2}') && echo "\"Openfile\"":"\"$Openfile\"""," >>$new_document
    Swap_Method=$(cat $file | grep Swap_Method | awk -F ":" '{print $2}') && echo "\"Swap_Method\"":"\"$Swap_Method\"""," >>$new_document
    Totalsum=$(cat $file | grep Totalsum | awk -F ":" '{print $2}') && echo "\"Totalsum\"":"\"$Totalsum\"""," >>$new_document
    Usesum=$(cat $file | grep Usesum | awk -F ":" '{print $2}') && echo "\"Usesum\"":"\"$Usesum\"""," >>$new_document
    Freesum=$(cat $file | grep Freesum | awk -F ":" '{print $2}') && echo "\"Freesum\"":"\"$Freesum\"""," >>$new_document
    Diskutil=$(cat $file | grep Diskutil | awk -F ":" '{print $2}') && echo "\"Diskutil\"":"\"$Diskutil\"""," >>$new_document
    Freeutil=$(cat $file | grep Freeutil | awk -F ":" '{print $2}') && echo "\"Freeutil\"":"\"$Freeutil\"""," >>$new_document
    IO_User=$(cat $file | grep IO_User | awk -F ":" '{print $2}') && echo "\"IO_User\"":"\"$IO_User\"""," >>$new_document
    IO_System=$(cat $file | grep IO_System | awk -F ":" '{print $2}') && echo "\"IO_System\"":"\"$IO_System\"""," >>$new_document
    IO_Wait=$(cat $file | grep IO_Wait | awk -F ":" '{print $2}') && echo "\"IO_Wait\"":"\"$IO_Wait\"""," >>$new_document
    IO_Idle=$(cat $file | grep IO_Idle | awk -F ":" '{print $2}') && echo "\"IO_Idle\"":"\"$IO_Idle\"""," >>$new_document
    Tcp_Tw_Recycle=$(cat $file | grep Tcp_Tw_Recycle | awk -F ":" '{print $2}') && echo "\"Tcp_Tw_Recycle\"":"\"$Tcp_Tw_Recycle\"""," >>$new_document
    Tcp_Tw_Reuse=$(cat $file | grep Tcp_Tw_Reuse | awk -F ":" '{print $2}') && echo "\"Tcp_Tw_Reuse\"":"\"$Tcp_Tw_Reuse\"""," >>$new_document
    Tcp_Fin_Timeout=$(cat $file | grep Tcp_Fin_Timeout | awk -F ":" '{print $2}') && echo "\"Tcp_Fin_Timeout\"":"\"$Tcp_Fin_Timeout\"""," >>$new_document
    Tcp_Keepalive_Time=$(cat $file | grep Tcp_Keepalive_Time | awk -F ":" '{print $2}') && echo "\"Tcp_Keepalive_Time\"":"\"$Tcp_Keepalive_Time\"""," >>$new_document
    Tcp_Keepalive_Probes=$(cat $file | grep Tcp_Keepalive_Probes | awk -F ":" '{print $2}') && echo "\"Tcp_Keepalive_Probes\"":"\"$Tcp_Keepalive_Probes\"""," >>$new_document
    Tcp_Keepalive_Intvl=$(cat $file | grep Tcp_Keepalive_Intvl | awk -F ":" '{print $2}') && echo "\"Tcp_Keepalive_Intvl\"":"\"$Tcp_Keepalive_Intvl\"" >>$new_document

}

function get_wls_jsondata() {

    echo \"wlsinfo\": [ >>$new_document
    weblogic_info >>$new_document
    echo ] >>$new_document

}

function mwcheckr_result_jsondata() {
    new_document=$new_data/wls_$ipinfo.txt
    echo "{" >$new_document
    echo \"osinfo\": \{ >>$new_document
    get_os_jsondata
    echo "}," >>$new_document
    get_wls_jsondata
    echo "}" >>$new_document
}

function get_weblogic_main() {

    ####check /tmp/tmpcheck Is empty
    tmpcheck_dir="/tmp/enmoResult/tmpcheck"
    if [ "$(ls -A $tmpcheck_dir)" ]; then
        echo "$tmpcheck_dir is not empty!!!"
        rm -rf $tmpcheck_dir/*
        echo "clean $tmpcheck_dir !!!"
    else
        echo "$tmpcheck_dir is empty!!!"
    fi

    ####get system info
    #filename1=$HOSTNAME"_"$name"_"wls"_"os_""$ipinfo"_"$qctime".txt"
    collect_sys_info >>"$filepath""$filename1"
    #filename2=$HOSTNAME"_"$name"_"wls"_"$ipinfo"_"$qctime".txt"
    qctime=$(date +'%Y%m%d%H%M%S')
    #weblogic_info >> "$filepath""$filename2"
    mwcheckr_result_jsondata
    #tar -czvf /tmp/enmoResult/"$HOSTNAME"_"$ipinfo"_"$qctime".tar.gz /tmp/enmoResult
    tar -czf /tmp/enmoResult/"$HOSTNAME"_"$ipinfo"_"$qctime".tar.gz  --exclude=/tmp/enmoResult/*.tar.gz --format=ustar /tmp/enmoResult/*

    echo -e "___________________"
    echo -e "Collection info Finished."
    echo -e "Result File Path:" $filepath
    echo -e "\n"
    cd /tmp/enmoResult/tmpcheck
}

######################Main##########################
filepath="/tmp/enmoResult/tmpcheck/"
excmkdir=$(which mkdir | awk 'NR==1{print}')
$excmkdir -p $filepath
qctime=$(date +'%Y%m%d%H%M%S')
ipinfo=$(ip addr show | grep 'state UP' -A 2 | grep "inet " | grep -v 127.0.0. | head -1 | cut -d" " -f6 | cut -d/ -f1)

new_data=/tmp/enmoResult/wls
if [ "$(ls -A $new_data)" ]; then
    echo "$new_data is not empty!!!"
    rm -rf $new_data/*
    echo "clean $new_data !!!"
else
    echo "$new_data is empty!!!"
fi
$excmkdir -p $new_data

####脚本基础数据收集
filename1=$HOSTNAME"_"wls"_"os_""$ipinfo"_"$qctime".txt"
#filename2=$HOSTNAME"_"wls"_"$ipinfo"_"$qctime".txt"
get_weblogic_main
