#!/usr/bin/python
#encoding:utf-8

#import json
from collections import namedtuple
from ansible.parsing.dataloader import DataLoader
from ansible.vars import VariableManager
from ansible.inventory import Inventory
from ansible.playbook.play import Play
from ansible.executor.task_queue_manager import TaskQueueManager
from ansible.plugins.callback import CallbackBase
from optparse import OptionParser
import copy


# Create a callback object so we can capture the output
class ResultCallback(CallbackBase):
    """A sample callback plugin used for performing an action as results come in

    If you want to collect all results into a single object for processing at
    the end of the execution, look into utilizing the ``json`` callback plugin
    or writing your own custom callback plugin
    """

    def v2_runner_on_ok(self, result, **kwargs):
        """Print a json representation of the result

        This method could store the result in an instance attribute for retrieval later
        """
        host = result._host
        #print dict(result._result)
        galera_info[host.name] = dict(result._result)
        #print galera_info


def ansibleRun(host_list, task_list):
    Options = namedtuple('Options',
                         ['connection', 'module_path', 'forks', 'remote_user', 'private_key_file',
                          'ssh_common_args', 'ssh_extra_args', 'sftp_extra_args', 'scp_extra_args',
                          'become', 'become_method', 'become_user', 'verbosity', 'check'])

    # initialize needed objects
    variable_manager = VariableManager()
    loader = DataLoader()
    options = Options(connection='smart', module_path=None,
                      forks=100, remote_user="root", private_key_file=None, ssh_common_args=None, ssh_extra_args=None,
                      sftp_extra_args=None, scp_extra_args=None, become=None, become_method=None,
                      become_user="root", verbosity=None, check=False
                      )

    passwords = dict()

    # Instantiate our ResultCallback for handling results as they come in
    results_callback = ResultCallback()

    # create inventory and pass to var manager
    inventory = Inventory(loader=loader, variable_manager=variable_manager, host_list=host_list)
    variable_manager.set_inventory(inventory)

    # create play with tasks
    play_source = dict(
        name="Ansible Play",
        hosts=host_list,
        gather_facts='no',
        tasks=task_list
    )
    play = Play().load(play_source, variable_manager=variable_manager, loader=loader)

    # actually run it
    tqm = None
    try:
        tqm = TaskQueueManager(
            inventory=inventory, variable_manager=variable_manager,
            loader=loader, options=options, passwords=passwords,
            stdout_callback=results_callback,  # Use our custom callback instead of the ``default`` callback plugin
            #stdout_callback='default',
        )
        result = tqm.run(play)
    except Exception,ex:
        print ex
    finally:
        if tqm is not None:
            tqm.cleanup()

def cluster_has_active_instance(galera_info):
    cluster_has_active_instance = False
    for ip in galera_info:
        if galera_info[ip]["database_info"]["is_alive"] == 1:
            cluster_has_active_instance = True
    return cluster_has_active_instance

def cluster_has_active_instance(galera_info):
    cluster_has_active_instance = False
    for ip in galera_info:
        # 为0表示为active，为1表示not active
        if galera_info[ip]["database_info"]["is_alive"] == 0:
            cluster_has_active_instance = True
    return cluster_has_active_instance

def cluster_has_safe_bootstrap(galera_info):
    cluster_has_safe_bootstrap = False
    for ip in galera_info:
        if galera_info[ip]["database_info"]["safe_to_bootstrap"] == '1':
            cluster_has_safe_bootstrap = True
    return cluster_has_safe_bootstrap

# 获取最大seqno的ip地址
def get_maxseqno_host(galera_info):
    tmp_seqno = 0
    for ip in galera_info:
        if galera_info[ip]["database_info"]["seqno"] > tmp_seqno:
            tmp_seqno = galera_info[ip]["database_info"]["seqno"]
            maxseqno_host = ip
    return maxseqno_host


if __name__ == '__main__':
    global galera_info
    galera_info = {}

    ## 需要传入的参数##########################################################################
    parser = OptionParser()
    parser.add_option("-c", "--cluster_hosts", dest="cluster_hosts", help="cluster all hosts", default="")
    parser.add_option("-s", "--start_hosts", dest="start_hosts", help="need to start hosts", default="")
    parser.add_option("-p", "--port", dest="port", help="need to start database port", default="")
    (options, args) = parser.parse_args()

    #集群所有数据库实例IP
    cluster_hosts = options.cluster_hosts.split(",")
    #数据库实例端口
    port = options.port
    #需要启动的数据库实例IPlist(options.cluster_hosts)
    start_hosts = options.start_hosts.split(",")
    #########################################################################################

    # 定义获取galera信息任务
    tasks_list = [
        dict(action=dict(module='get_galera_info', args=dict(port="%s"  % port))),
    ]

    #获取集群数据库状态信息
    ansibleRun(cluster_hosts, tasks_list)

    if len(galera_info) == len(cluster_hosts):
        #普通启动
        normal_start_hosts = copy.deepcopy(start_hosts)

        #bootstrap启动
        wsrep_new_cluster_start_host = []


        if cluster_has_active_instance(galera_info):
            print "cluster have active instance"
            for ip in start_hosts:
                if str(galera_info[ip]["database_info"]["is_alive"]) == "0":
                     print "ip:%s,port:%s is active! don't need to start" %(ip,port)
                     normal_start_hosts.remove(ip)

        elif cluster_has_safe_bootstrap(galera_info):
            print "cluster has safe_bootstrap"
            wsrep_new_cluster_start_host=[]
            for ip in cluster_hosts:
                if galera_info[ip]["database_info"]["safe_to_bootstrap"] == "1":
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
                             args='/mysql/bin/mysqld_safe  --defaults-file\=/mysqldata/%s/my.cnf &' % port)),
        ]

        wsrep_new_cluster_start = [
            dict(action=dict(module='set_safe_to_bootstrap',
                             args=dict(port="%s" % port))),
            dict(action=dict(module='shell',
                         args='/mysql/bin/mysqld_safe  --defaults-file\=/mysqldata/%s/my.cnf --wsrep-new-cluster &' % port)),
        ]

        print "new cluster start:" + repr(wsrep_new_cluster_start_host)
        ansibleRun(wsrep_new_cluster_start_host, wsrep_new_cluster_start)

        print "normal start: " + repr(normal_start_hosts)
        ansibleRun(normal_start_hosts, normal_start)
    else:
        print "galera info is less than cluster_hosts num, some nodes get galera info error!"