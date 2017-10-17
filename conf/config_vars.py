#!/usr/bin/python
#encoding:utf-8


# 全局变量设置

"""
[root@mysqldb1 mysqldata]# tree -Lf 1 /mysqldata/3306
/mysqldata/3306
├── /mysqldata/3306/binlog
├── /mysqldata/3306/data
├── /mysqldata/3306/log
├── /mysqldata/3306/my.cnf
├── /mysqldata/3306/run
└── /mysqldata/3306/tmp
"""

# mysql软件路径
MYSQL_PATH = '/mysql'

# 我们的MySQL规范中，数据库文件路径根据端口号设定 : /mysqldata/{port}/
MYSQLDATA_PATH = '/mysqldata'


# 操作系统用户
#OS_USER = 'root'

# 操作系统用户密码
#OS_USER_PASSWD = 'xxxxxxxxx'

MYSQL_USER = 'dic_wh'
MYSQL_USER_PASSWD = 'tydic123'
# 目录
#ANSIBLE_LIBRARY = '/home/fengbao/PycharmProjects/galera_start/src/ansible_modules'