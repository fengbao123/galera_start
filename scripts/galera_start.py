#!/usr/bin/python
#encoding:utf-8

import copy
from optparse import OptionParser

from src.ansible_api import ansible_invoke_api

# 检查当前是否有存活节点
def cluster_has_active_instance(galera_info):
    cluster_has_active_instance = False
    for ip in galera_info:
        if galera_info[ip]["is_alive"] == 1:
            cluster_has_active_instance = True
    return cluster_has_active_instance

# 检查是否存在安全启动的节点
def cluster_has_safe_bootstrap(galera_info):
    cluster_has_safe_bootstrap = False
    for ip in galera_info:
        if galera_info[ip]["safe_to_bootstrap"] == '1':
            cluster_has_safe_bootstrap = True
    return cluster_has_safe_bootstrap

# 获取最大seqno的ip地址
def get_maxseqno_host(galera_info):
    tmp_seqno = 0
    for ip in galera_info:
        if galera_info[ip]["seqno"] > tmp_seqno:
            tmp_seqno = galera_info[ip]["seqno"]
            maxseqno_host = ip
    return maxseqno_host


if __name__ == '__main__':
    # global galera_info
    galera_info = {}
    result_info = []


    ## 需要传入的参数##########################################################################
    parser = OptionParser()
    parser.add_option("-c", "--cluster_hosts", dest="cluster_hosts", help="cluster all hosts", default="")
    parser.add_option("-s", "--start_hosts", dest="start_hosts", help="need to start hosts", default="")
    parser.add_option("-p", "--port", dest="port", help="need to start database port", default="")

    parser.add_option("-M", "--mysql_path", dest="mysql_path", help="mysql software path", default="/mysql")
    parser.add_option("-D", "--mysqldata_path", dest="mysqldata_path", help="mysql data path", default="/mysqldata")
    parser.add_option("-U", "--user", dest="user", help="mysql database user", default="dic_wh")
    parser.add_option("-P", "--password", dest="password", help="mysql database user's password", default="xxxx")

    (options, args) = parser.parse_args()


    #集群所有数据库实例IP
    cluster_hosts = options.cluster_hosts.split(",")
    #数据库实例端口
    port = options.port

    # 需要启动的数据库实例IP
    start_hosts = options.start_hosts.split(",")

    #########################################################################################

    # cluster_hosts = ['192.168.128.138', '192.168.128.139', '192.168.128.148']
    # port = 3307
    # start_hosts = ['192.168.128.138', '192.168.128.139', '192.168.128.148']


    # # 定义获取galera信息任务
    # get_galera_info = [
    #     dict(action=dict(module='get_galera_info',
    #                      args=dict(port="%s"  % port,
    #                                mysql_path="%s" % options.mysql_path,
    #                                mysql_data_path="%s" % options.mysqldata_path,
    #                                mysql_user = "%s" % options.user,
    #                                mysql_user_passwd = "%s" % options.password))),
    # ]

    #获取集群数据库状态信息
    for host in cluster_hosts:
        # 定义获取galera信息任务
        get_galera_info = [
            dict(action=dict(module='get_galera_info',
                             args=dict(port="%s" % port,
                                       mysql_path="%s" % options.mysql_path,
                                       mysql_data_path="%s" % options.mysqldata_path,
                                       mysql_user="%s" % options.user,
                                       mysql_user_passwd="%s" % options.password,
                                       host = host))),
        ]

        print get_galera_info

        result_collector = ansible_invoke_api.run_modules(host,get_galera_info)

        if result_collector.host_unreachable:
            print result_collector.host_unreachable

        if result_collector.host_failed:
            print result_collector.host_failed

        result_info.append(result_collector.host_ok)


    # 转换回传结果
    for lists  in result_info:
        for list in  lists:
            galera_info[list['ip']] = dict(list['result']['database_info'] )


    # 检查
    if len(galera_info) == len(cluster_hosts):
        #普通启动
        normal_start_hosts = copy.deepcopy(start_hosts)

        #bootstrap启动
        wsrep_new_cluster_start_host = []


        if cluster_has_active_instance(galera_info):
            print "cluster have active instance"
            for ip in start_hosts:
                if str(galera_info[ip]["is_alive"]) == "1":
                     print "ip:%s,port:%s is active! don't need to start" %(ip,port)
                     normal_start_hosts.remove(ip)

        elif cluster_has_safe_bootstrap(galera_info):
            print "cluster has safe_bootstrap"
            wsrep_new_cluster_start_host=[]
            for ip in cluster_hosts:
                if galera_info[ip]["safe_to_bootstrap"] == "1":
                    if ip in start_hosts:
                        wsrep_new_cluster_start_host.append(ip)
                        normal_start_hosts.remove(ip)
                    else:
                        print "the boostrap instance is not in start_host_list, you must start ip:%s, port:%s first" % (ip,port)
                    break
        else:
            print "cluster has no safe bootstrap"
            maxseqno_host = get_maxseqno_host(galera_info)
            wsrep_new_cluster_start_host = []
            print "the last commited host is:" + maxseqno_host
            for ip in cluster_hosts:
                if ip == maxseqno_host:
                    if ip in start_hosts:
                        wsrep_new_cluster_start_host.append(ip)
                        normal_start_hosts.remove(ip)
                        break
                    else:
                        print "the maxseqno instance is not in start_host_list, you must start ip:%s, port:%s first" % (
                        ip, port)

        # 这里的=号需要有转义符，否则会把defaults-file当成一个shell模块的参数
        normal_start = [
            dict(action=dict(module='shell',
                             args='%s/bin/mysqld_safe  --defaults-file\=%s/%s/my.cnf &' % (
                             options.mysql_path, options.mysqldata_path, port))),
        ]



        set_safe_to_bootstrap = [
            dict(action=dict(module='set_safe_to_bootstrap',
                             args=dict(port="%s" % port,
                                       mysql_data_path="%s" % options.mysqldata_path))),
        ]

        print "new cluster start:" + repr(wsrep_new_cluster_start_host)

        if  wsrep_new_cluster_start_host :
            # 设置safe_to_bootstrap为允许安全启动
            ansible_invoke_api.run_modules(wsrep_new_cluster_start_host,set_safe_to_bootstrap)
            # 启动主节点
            ansible_invoke_api.run_adhoc(wsrep_new_cluster_start_host,'%s/bin/mysqld_safe  --defaults-file\=%s/%s/my.cnf --wsrep-new-cluster &' % (
                options.mysql_path, options.mysqldata_path, port))

        print "normal start: " + repr(normal_start_hosts)
        if    normal_start_hosts :
            ansible_invoke_api.run_adhoc(normal_start_hosts,"%s/bin/mysqld_safe --defaults-file\=%s/%s/my.cnf &" % (
                options.mysql_path, options.mysqldata_path, port))


        # 检查数据库状态
        result_info = []
        for host in start_hosts:
            result_collector = ansible_invoke_api.run_modules(host, get_galera_info)
            result_info.append(result_collector.host_ok)

        for lists in result_info:
            for list in lists:
                print list['ip'] + " now " + ("is alive",'is not alive, you must check!')[list['result']['database_info']['is_alive'] == 0]

    else:
        print "galera info is less than cluster_hosts num, some nodes get galera info error!"