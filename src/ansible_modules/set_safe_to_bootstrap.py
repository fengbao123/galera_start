#!/usr/bin/python
#encoding:utf-8

from ansible.module_utils.basic import *
# import os,MySQLdb

#修改booststrap
def set_safe_to_bootstrap(params):
    with open("%s/%s/data/grastate.dat" % (params['mysql_data_path'],params['port']), "r") as f:
        file_data = f.read()

    file_data = file_data.replace('safe_to_bootstrap: 0','safe_to_bootstrap: 1')

    with open("%s/%s/data/grastate.dat" % (params['mysql_data_path'],params['port']), "w") as f:
        f.write(file_data)

def main():
    fields = {
        "port": {"required": True, "type": "str"},
        "mysql_data_path": {"required": True, "type": "str"}
    }


    module = AnsibleModule(argument_spec=fields)
    set_safe_to_bootstrap(module.params)


    module.exit_json(changed=False)

if __name__ == '__main__':
    main()