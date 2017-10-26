# 环境说明：
- ansbile版本：2.2.1.0
- python版本：2.7

# 前言
最近在将Galera Cluster操作集成到管理平台中，其中Galera Cluster启动过程是一件比较麻烦的事情，因为是多主结构，需要先启动最后操作的实例，并且启动命令也不同。
总结了一下，启动涉及到几个难点：
1. 不论启动多少个节点，都需要检测**集群中所有实例**的状态
2. 这些状态信息如何**返回**给控制端


# 1.方案选择
1. 不论启动多少个节点，都需要检测**集群中所有实例**的状态
  这个不难，写个python脚本进行收集
2. 这些状态信息如何**返回**给控制端
  若使用ansible的file/copy/templates将脚本传入到节点，然后通过shell模块执行，若通过stdout返回不容易采集。在这里我们先定义ansible的自定义模块然后将信息通过json格式返回给控制端。


# 2.自定义模块

- 自定义模块名：get_galera_info
作用：获取galera数据库信息

- 自定义模块：set_safe_to_bootstrap
作用：修改grastate.dat文件，将其中的`safe_to_bootstrap: 0`修改为`safe_to_bootstrap: 1`


# 3. 调用程序
调用程序使用ansible 2.0后的接口，2.0后的API接口调用变的复杂一点，但是功能强大很多，在这里对ansible api进行了继承改写

# 4. 部署
1. 安装
```
python setup.py install
```

2. 添加ansible自定义模块路径
```
vi /etc/ansible/ansible.cfg
library        = /usr/share/my_modules/
```
在这里将我们自定义的模块添加到ansible中

3. 配置ansible的inventory
```
vi /etc/ansible/hosts
[galera]
192.168.128.138 ansible_ssh_user=root ansible_ssh_pass=xxxxx ansible_ssh_port=22
192.168.128.139 ansible_ssh_user=root ansible_ssh_pass=xxxxx ansible_ssh_port=22
192.168.128.148 ansible_ssh_user=root ansible_ssh_pass=xxxxx ansible_ssh_port=22

#测试：
ansible galera -m ping
```

# 5.调测
- 注意：我这边规范化路径如下：数据库软件/mysql目录；数据库目录/mysqldata，子目录以端口号分割
```
    [root@mysqldb1 mysqldata]# tree -Lf 1 /mysqldata/3306
    /mysqldata/3306
    ├── /mysqldata/3306/binlog
    ├── /mysqldata/3306/data
    ├── /mysqldata/3306/log
    ├── /mysqldata/3306/my.cnf
    ├── /mysqldata/3306/run
    └── /mysqldata/3306/tmp
```
- 数据库全部已启动状态测试
```
$ galera_start.py --cluster_hosts=192.168.128.138,192.168.128.139,192.168.128.148 --port=3307 --start_hosts=192.168.128.138,192.168.128.139,192.168.128.148 --user=dic_wh --password=xxxxx
{u'192.168.128.139': {u'seqno': u'null', u'is_alive': 1, u'port': u'3307', u'safe_to_bootstrap': u'null'}, u'192.168.128.138': {u'seqno': u'null', u'is_alive': 1, u'port': u'3307', u'safe_to_bootstrap': u'null'}, u'192.168.128.148': {u'seqno': u'null', u'is_alive': 1, u'port': u'3307', u'safe_to_bootstrap': u'null'}}
cluster have active instance
ip:192.168.128.138,port:3307 is active! don't need to start
ip:192.168.128.139,port:3307 is active! don't need to start
ip:192.168.128.148,port:3307 is active! don't need to start
new cluster start:[]
normal start: []
192.168.128.138 now is alive
192.168.128.139 now is alive
192.168.128.148 now is alive
```
- 正常关闭数据库2个节点，启动：
```
$ galera_start.py --cluster_hosts=192.168.128.138,192.168.128.139,192.168.128.148 --port=3307 --start_hosts=192.168.128.138,192.168.128.139 --user=dic_wh --password=xxxx
{u'192.168.128.139': {u'seqno': u'108197', u'is_alive': 0, u'port': u'3307', u'safe_to_bootstrap': u'0'}, u'192.168.128.138': {u'seqno': u'108197', u'is_alive': 0, u'port': u'3307', u'safe_to_bootstrap': u'0'}, u'192.168.128.148': {u'seqno': u'null', u'is_alive': 1, u'port': u'3307', u'safe_to_bootstrap': u'null'}}
cluster have active instance
new cluster start:[]
normal start: ['192.168.128.138', '192.168.128.139']
192.168.128.138 now is not alive, you must check!
192.168.128.139 now is alive

# 由于刚启动数据库可能无法正常对外提供服务，可重复执行几次，确保数据库正常启动
$ galera_start.py --cluster_hosts=192.168.128.138,192.168.128.139,192.168.128.148 --port=3307 --start_hosts=192.168.128.138,192.168.128.139 --user=dic_wh --password=xxxx
{u'192.168.128.139': {u'seqno': u'null', u'is_alive': 1, u'port': u'3307', u'safe_to_bootstrap': u'null'}, u'192.168.128.138': {u'seqno': u'null', u'is_alive': 1, u'port': u'3307', u'safe_to_bootstrap': u'null'}, u'192.168.128.148': {u'seqno': u'null', u'is_alive': 1, u'port': u'3307', u'safe_to_bootstrap': u'null'}}
cluster have active instance
ip:192.168.128.138,port:3307 is active! don't need to start
ip:192.168.128.139,port:3307 is active! don't need to start
new cluster start:[]
normal start: []
192.168.128.138 now is alive
192.168.128.139 now is alive
```
- 正常关闭所有节点，启动bootstrap不为1的节点，以及启动为1的节点
```
# 启动bootstrap不为1的节点，会有提示需要先启动bootstrap，并且普通启动138和139两个节点，不过138和139启动后不能提供服务以及连接
$ galera_start.py --cluster_hosts=192.168.128.138,192.168.128.139,192.168.128.148 --port=3307 --start_hosts=192.168.128.138,192.168.128.139 --user=dic_wh --password=xxx
{u'192.168.128.139': {u'seqno': u'108197', u'is_alive': 0, u'port': u'3307', u'safe_to_bootstrap': u'0'}, u'192.168.128.138': {u'seqno': u'108197', u'is_alive': 0, u'port': u'3307', u'safe_to_bootstrap': u'0'}, u'192.168.128.148': {u'seqno': u'null', u'is_alive': 0, u'port': u'3307', u'safe_to_bootstrap': u'1'}}
cluster has safe_bootstrap
the boostrap instance is not in start_host_list, you must start ip:192.168.128.148, port:3307 first
new cluster start:[]
normal start: ['192.168.128.138', '192.168.128.139']
192.168.128.138 now is not alive, you must check!
192.168.128.139 now is not alive, you must check!

#启动safe_to_bootstrap=1的节点，或者全部启动：
$ galera_start.py --cluster_hosts=192.168.128.138,192.168.128.139,192.168.128.148 --port=3307 --start_hosts=192.168.128.148 --user=dic_wh --password=xxx
{u'192.168.128.139': {u'seqno': u'108197', u'is_alive': 0, u'port': u'3307', u'safe_to_bootstrap': u'0'}, u'192.168.128.138': {u'seqno': u'108197', u'is_alive': 0, u'port': u'3307', u'safe_to_bootstrap': u'0'}, u'192.168.128.148': {u'seqno': u'null', u'is_alive': 0, u'port': u'3307', u'safe_to_bootstrap': u'1'}}
cluster has safe_bootstrap
new cluster start:['192.168.128.148']
normal start: []
192.168.128.148 now is not alive, you must check!

$ galera_start.py --cluster_hosts=192.168.128.138,192.168.128.139,192.168.128.148 --port=3307 --start_hosts=192.168.128.148 --user=dic_wh --password=xxx
{u'192.168.128.139': {u'seqno': u'108197', u'is_alive': 0, u'port': u'3307', u'safe_to_bootstrap': u'0'}, u'192.168.128.138': {u'seqno': u'108197', u'is_alive': 0, u'port': u'3307', u'safe_to_bootstrap': u'0'}, u'192.168.128.148': {u'seqno': u'null', u'is_alive': 1, u'port': u'3307', u'safe_to_bootstrap': u'null'}}
cluster have active instance
ip:192.168.128.148,port:3307 is active! don't need to start
new cluster start:[]
normal start: []
192.168.128.148 now is alive

$ galera_start.py --cluster_hosts=192.168.128.138,192.168.128.139,192.168.128.148 --port=3307 --start_hosts=192.168.128.138,192.168.128.139 --user=dic_wh --password=xxx
{u'192.168.128.139': {u'seqno': u'108197', u'is_alive': 0, u'port': u'3307', u'safe_to_bootstrap': u'0'}, u'192.168.128.138': {u'seqno': u'108197', u'is_alive': 0, u'port': u'3307', u'safe_to_bootstrap': u'0'}, u'192.168.128.148': {u'seqno': u'null', u'is_alive': 1, u'port': u'3307', u'safe_to_bootstrap': u'null'}}
cluster have active instance
new cluster start:[]
normal start: ['192.168.128.138', '192.168.128.139']
192.168.128.138 now is alive
192.168.128.139 now is alive

```

- kill掉所有节点，启动所有节点
```
$ galera_start.py --cluster_hosts=192.168.128.138,192.168.128.139,192.168.128.148 --port=3307 --start_hosts=192.168.128.138,192.168.128.139,192.168.128.148 --user=dic_wh --password=xxx
{u'192.168.128.139': {u'seqno': u'108197', u'is_alive': 0, u'port': u'3307', u'safe_to_bootstrap': u'0'}, u'192.168.128.138': {u'seqno': u'108197', u'is_alive': 0, u'port': u'3307', u'safe_to_bootstrap': u'0'}, u'192.168.128.148': {u'seqno': u'108197', u'is_alive': 0, u'port': u'3307', u'safe_to_bootstrap': u'0'}}
cluster has no safe bootstrap
the last commited host is:192.168.128.139
new cluster start:['192.168.128.139']
normal start: ['192.168.128.138', '192.168.128.148']
192.168.128.138 now is alive
192.168.128.139 now is alive
192.168.128.148 now is alive

```

*注：脚本可以重复执行几次，确保所有节点都是活动状态*
