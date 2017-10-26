#!/usr/bin/python
#encoding:utf-8

from ansible.module_utils.basic import *
import os,MySQLdb

#检查grastate.dat的safe_to_bootstap是否为1
def get_safe_to_bootstrap(params):
    with open("%s/%s/data/grastate.dat" % (params['mysql_data_path'],params['port']), "r") as f:
        for line in f:
            if "safe_to_bootstrap" in line:
                safe_to_bootstrap = line.split(":")[-1].strip()
    return safe_to_bootstrap

#获取最后提交的seqno
#注意： galera mysql 5.7版本的 mysqld_safe默认不会输出Recovered position信息，需要改动一下mysqld_safe shell脚本
def get_seqno(params):
    seqno = 0
    for line in os.popen("%s/bin/mysqld_safe --defaults-file=/%s/%s/my.cnf --wsrep_recover" %
                                 (params['mysql_path'],
                                  params['mysql_data_path'],
                                  params['port'])).readlines():
        if "Recovered position" in line:
            seqno = line.split(":")[-1].strip().replace("\n","")
    return  seqno

# 检查数据库是否存活,1存活，0异常
def get_is_alive(params):
    is_alive = 0

    try:
        cnx = MySQLdb.connect(host='%s' % params['host'] ,
                              user='%s' % params['mysql_user'],
                              passwd='%s' % params['mysql_user_passwd'],
                              port=int(params['port']))
        is_alive = 1
        cnx.close()
    except Exception, e:
        pass
        #print Exception, ":", e
    return is_alive

def main():

    # 调用module传入的变量
    fields = {
        "port": {"required": True, "type": "str"},
        "mysql_path": {"required": True, "type": "str"},
        "mysql_data_path": {"required": True, "type": "str"},
        "mysql_user": {"required": True, "type": "str"},
        "mysql_user_passwd": {"required": True, "type": "str"},
        "host": {"required": True, "type": "str"}
    }

    module = AnsibleModule(argument_spec=fields)

    database_info = {}
    database_info['is_alive'] = get_is_alive(module.params)

    #若数据库不存活，则检测safe_to_boostrap与last commited no
    if database_info['is_alive'] == 0:

        database_info['safe_to_bootstrap'] = get_safe_to_bootstrap(module.params)

        #若节点不允许安全启动（safe_to_bootstrap=0），那么检测last commited no
        if database_info['safe_to_bootstrap'] == '0':
            database_info['seqno'] = get_seqno(module.params)
        else:
            database_info['seqno'] = "null"
    else:
        database_info['safe_to_bootstrap'] = "null"
        database_info['seqno'] = "null"

    database_info['port'] = module.params['port']

    # 模块执行完成后返回json格式信息
    module.exit_json(changed=False,database_info=database_info)

    #module.fail_json(msg="Something fatal happened")

if __name__ == '__main__':
    main()