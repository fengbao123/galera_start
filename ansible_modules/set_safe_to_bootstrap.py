#!/usr/bin/python
#encoding:utf-8

from ansible.module_utils.basic import *
import os,MySQLdb

#修改booststrap
def set_safe_to_bootstrap(database_port):
    with open("/mysqldata/%s/data/grastate.dat" % database_port, "r") as f:
        file_data = f.read()

    file_data = file_data.replace('safe_to_bootstrap: 0','safe_to_bootstrap: 1')

    with open("/mysqldata/%s/data/grastate.dat" % database_port, "w") as f:
        f.write(file_data)

def main():
    fields = {
        "port": {"required": True, "type": "str"}
    }


    module = AnsibleModule(argument_spec=fields)
    set_safe_to_bootstrap(module.params['port'])


    module.exit_json(changed=False)

if __name__ == '__main__':
    main()