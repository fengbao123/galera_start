#!/usr/bin/env python
# -*- coding: utf-8 -*-
import json
from ansible.parsing.dataloader import DataLoader
from ansible.vars import VariableManager
from ansible.inventory import Inventory
from ansible.playbook.play import Play
from ansible.executor.task_queue_manager import TaskQueueManager
from ansible.executor.playbook_executor import PlaybookExecutor

from ansible.plugins import callback_loader
from ansible.plugins.callback import CallbackBase

import os
import logging


loader = DataLoader()
variable_manager = VariableManager()
inventory = Inventory(loader=loader, variable_manager=variable_manager)
variable_manager.set_inventory(inventory)

#get result output
class ResultsCollector(CallbackBase):
    def __init__(self, *args, **kwargs):
        super(ResultsCollector, self).__init__(*args, **kwargs)
        self.host_ok = []
        self.host_unreachable = []
        self.host_failed = []

    def v2_runner_on_unreachable(self, result, ignore_errors=False):
        name = result._host.get_name()
        task = result._task.get_name()
        #ansible_log(result)
        #self.host_unreachable[result._host.get_name()] = result
        self.host_unreachable.append(dict(ip=name, task=task, result=result._result))

    def v2_runner_on_ok(self, result,  *args, **kwargs):
        name = result._host.get_name()
        task = result._task.get_name()
        if task == "setup":
            pass
        elif "Info" in task:
            self.host_ok.append(dict(ip=name, task=task, result=result._result))
        else:
            #ansible_log(result)
            self.host_ok.append(dict(ip=name, task=task, result=result._result))

    def v2_runner_on_failed(self, result,   *args, **kwargs):
        name = result._host.get_name()
        task = result._task.get_name()
        #ansible_log(result)
        self.host_failed.append(dict(ip=name, task=task, result=result._result))

class Options(object):
    def __init__(self):
        self.connection = "smart"
        self.forks = 100
        self.check = False
        self.become = None
        self.become_method = None
        self.remote_user = None
        self.become_user= None
        self.private_key_file=None
        self.ssh_common_args=None
        self.sftp_extra_args=None
        self.scp_extra_args=None
        self.ssh_extra_args=None
        self.verbosity=None
    def __getattr__(self, name):
        return None

options = Options()


def run_adhoc(host,order):
    variable_manager.extra_vars={"ansible_ssh_user":"root" , "ansible_ssh_pass":"tydic123"}

    play_source = dict(
        name = "Ansible Ad-Hoc",
        hosts = host,
        gather_facts = "no",
        tasks = [{"action":{"module":"command","args":"%s"%order}}]
    )

    play = Play().load(play_source, variable_manager=variable_manager, loader=loader)
    tqm = None
    callback = ResultsCollector()

    try:
        tqm = TaskQueueManager(
            inventory=inventory,
            variable_manager=variable_manager,
            loader=loader,
            options=options,
            passwords=None,
            run_tree=False,
        )
        tqm._stdout_callback = callback
        result = tqm.run(play)
        return callback

    finally:
        if tqm is not None:
            tqm.cleanup()

def run_modules(host,task_list):
    variable_manager.extra_vars={"ansible_ssh_user":"root" , "ansible_ssh_pass":"tydic123"}

    play_source = dict(
        name="Ansible Ad-Hoc",
        hosts=host,
        gather_facts="no",
        tasks=task_list
    )

    play = Play().load(play_source, variable_manager=variable_manager, loader=loader)
    tqm = None
    callback = ResultsCollector()

    try:
        tqm = TaskQueueManager(
            inventory=inventory,
            variable_manager=variable_manager,
            loader=loader,
            options=options,
            passwords=None,
            run_tree=False,
        )
        tqm._stdout_callback = callback
        result = tqm.run(play)
        return callback

    finally:
        if tqm is not None:
            tqm.cleanup()

def run_playbook(books):
    results_callback = callback_loader.get('json')
    playbooks = [books]

    variable_manager.extra_vars={"ansible_ssh_user":"root" , "ansible_ssh_pass":"tydic123"}
    callback = ResultsCollector()

    pd = PlaybookExecutor(
        playbooks=playbooks,
        inventory=inventory,
        variable_manager=variable_manager,
        loader=loader,
        options=options,
        passwords=None,

        )
    pd._tqm._stdout_callback = callback

    try:
        result = pd.run()
        return callback

    except Exception as e:
        print e