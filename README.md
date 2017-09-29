[TOC]

#环境说明：
- ansbile版本：2.2.1.0
- python版本：2.7

#前言
最近在将Galera Cluster操作集成到管理平台中，其中Galera Cluster启动过程是一件比较麻烦的事情，因为是多主结构，需要先启动最后操作的实例，并且启动命令也不同。总结了一下，启动的大致流程如下：

```flow
st=>start: 开始
e=>end: 结束
cond1=>condition: 集群存在Active节点
op2=>operation: 正常启动
其它节点
cond2=>condition: safe-to-bootstrap=1
op3=>operation: 以
--wsrep-new
-cluster
方式启动
bootstrap
为1节点
op4=>operation: 获取所有节点
last commited
的seqno
op5=>operation: 修改最大seqno
节点grastate.dat
文件，将
safe-to-bootstrap
修改为1
op6=>operation: 以
--wsrep-new
-cluster
方式启动seqno
最大的节点

st->cond1(yes)->op2
cond1(no,left)->cond2
cond2(yes)->op3
cond2(no,left)->op4
op4->op5
op5->op6(right)->op2
op3->op2
op2->e
```

这里涉及到几个难点：
1. 不论启动多少个节点，都需要检测**集群中所有实例**的状态
2. 这些状态信息如何**返回**给控制端


#1.方案选择
1. 不论启动多少个节点，都需要检测**集群中所有实例**的状态
  这个不难，写个python脚本进行收集
2. 这些状态信息如何**返回**给控制端
  若使用ansible的file/copy/templates将脚本传入到节点，然后通过shell模块执行，若通过stdout返回不容易采集。在这里我们先定义ansible的自定义模块然后将信息通过json格式返回给控制端。


#2.自定义模块
设置自定义模块路径
```
vi /etc/ansible/ansible.cfg
library        = /usr/share/my_modules/
```

自定义模块名：get_galera_info
作用：获取galera数据库信息


自定义模块：set_safe_to_bootstrap
作用：修改grastate.dat文件，将其中的`safe_to_bootstrap: 0`修改为`safe_to_bootstrap: 1`


#3. 调用程序
调用程序使用ansible 2.0后的接口，2.0后的API接口调用变的复杂一点，但是功能强大很多


#4.调测
- 正常关闭数据库2个节点（128.138/139），启动：
```
$ python galera_start.py --cluster_hosts=192.168.128.138,192.168.128.139,192.168.128.148 --port=4309 --start_hosts=192.168.128.138,192.168.128.139
cluster have active instance
new cluster start:[]
normal start: ['192.168.128.138', '192.168.128.139']
```
- 正常关闭所有节点，启动bootstrap不为1的节点，以及启动为1的节点
```
# 启动bootstrap不为1的节点，会有提示需要先启动bootstrap，并且普通启动138和139两个节点，不过138和139启动后不能提供服务以及连接
$ python galera_start.py --cluster_hosts=192.168.128.138,192.168.128.139,192.168.128.148 --port=4309 --start_hosts=192.168.128.138,192.168.128.139
cluster has safe_bootstrap
the boostrap instance is not in start_host_list, you must start ip:192.168.128.148, port:4309 first
new cluster start:[]
normal start: ['192.168.128.138', '192.168.128.139']
#启动safe_to_bootstrap=1的节点：
$ python galera_start.py --cluster_hosts=192.168.128.138,192.168.128.139,192.168.128.148 --port=4309 --start_hosts=192.168.128.148
cluster has safe_bootstrap
new cluster start:['192.168.128.148']
normal start: []
```

- kill掉所有节点，启动所有节点
```
$ python galera_start.py --cluster_hosts=192.168.128.138,192.168.128.139,192.168.128.148 --port=4309 --start_hosts=192.168.128.148,192.168.128.138,192.168.128.139
cluster has no safe bootstrap
the last commited host is:192.168.128.138
new cluster start:['192.168.128.138']
normal start: ['192.168.128.148', '192.168.128.139']
```

- 重复启动
```
$ python galera_start.py --cluster_hosts=192.168.128.138,192.168.128.139,192.168.128.148 --port=4309 --start_hosts=192.168.128.148,192.168.128.138,192.168.128.139
cluster have active instance
ip:192.168.128.148,port:4309 is active! don't need to start
ip:192.168.128.138,port:4309 is active! don't need to start
ip:192.168.128.139,port:4309 is active! don't need to start
[]
new cluster start:[]
normal start: []
```