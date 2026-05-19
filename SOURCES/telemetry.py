#!/usr/bin/python3
# Copyright: Contributors to the Ansible project
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

DOCUMENTATION = '''
    name: telemetry
    short_description: Track various telemetry related data and store in journald
    description:
        - Track various telemetry related data and store in journald
    type: aggregate
    options:
        bypass_insights_check:
            name: Bypass Insights Check
            description: Bypass check to see if insights-client is active
            default: false
            type: bool
            env:
                - name: TELEMETRY_BYPASS_INSIGHTS_CHECK
    notes:
        - The file can also be executed directly from the CLI to retrieve
          the stored telemetry data from journald
'''

import contextlib
import ctypes
import datetime
import functools
import importlib.util
import json
import os
import pathlib
import subprocess
import sys
import uuid
from collections import defaultdict

if __name__ == '__main__':
    # When run as a script via insights-client, these are not needed
    CallbackBase = object
    Display = None
else:
    from ansible.executor.task_result import TaskResult
    from ansible.module_utils.common.yaml import yaml_load
    from ansible.plugins.callback import CallbackBase
    from ansible.plugins.loader import connection_loader
    from ansible.release import __version__ as ansible_version
    from ansible.utils.display import Display

journal_sendv = None
try:
    from systemd import journal
    journal_sendv = journal.sendv
except ImportError:
    # When invoked using the non-system python
    # the systemd python bindings are not available
    with contextlib.suppress(AttributeError, OSError):
        _libsysetmd = ctypes.CDLL('libsystemd.so.0')
        sd_journal_send = _libsysetmd.sd_journal_send

        def journal_sendv(*args):
            b_args = [ctypes.c_char_p(a.encode()) for a in args] + [None]
            sd_journal_send(*b_args)

if sys.version_info >= (3, 10):
    from importlib.resources import files
else:
    # importlib.resources below Python 3.10 doesn't support
    # custom loaders, this is not a full featured replacement
    # but suffices for the needs of this plugin
    def files(name):
        spec = importlib.util.find_spec(name)
        if spec is None:
            raise ImportError(name)
        origin = pathlib.Path(spec.origin)
        if origin.name == '__synthetic__':
            origin = origin.parent
        return origin

if Display:
    display = Display()

_CORE_SYN_COLLECTIONS = frozenset((
    'ansible.builtin',
    'ansible.legacy',
))

_ANSIBLE_TELEMETRY_MESSAGE_ID = uuid.UUID('73df9e03d8c6473eb811065c4ebc370a')


@functools.lru_cache(maxsize=None)
def _get_connection_fqcn(task, host):
    connection = host.vars.get('ansible_connection')
    if not connection:
        connection = task.connection
    is_connection_fqcn = '.' in connection
    if is_connection_fqcn:
        return connection

    return connection_loader.get_with_context(
        connection,
        class_only=True,
        collection_list=task.collections,
    ).plugin_load_context.resolved_fqcn


class CallbackModule(CallbackBase):
    CALLBACK_VERSION = 2.0
    CALLBACK_TYPE = 'aggregate'
    CALLBACK_NAME = 'telemetry'

    def __init__(self, *args, **kwargs):
        self.wants_implicit_tasks = False
        self.disabled = False

        self._telemetry = {
            'collections': defaultdict(
                lambda: {
                    'resources': defaultdict(
                        lambda: defaultdict(lambda: {
                            'count': 0,
                        })
                    ),
                    'version': '*',
                },
            ),
        }
        self._hosts = set()
        self._conn_cache = {}

    def _is_insights_client_active(self):
        if self.get_option('bypass_insights_check'):
            return True

        if not os.path.exists('/etc/insights-client/.registered'):
            return False

        with contextlib.suppress(subprocess.CalledProcessError):
            subprocess.run(
                ['systemctl', 'is-active', '--quiet', 'insights-client.timer'],
                capture_output=True,
                check=True,
            )
            return True

        return False

    def _set_disabled(self):
        if not self._is_insights_client_active():
            return True

        if journal_sendv is None:
            return True

        return False

    def set_options(self, task_keys=None, var_options=None, direct=None):
        super().set_options(task_keys=task_keys, var_options=var_options, direct=direct)
        self.disabled = self._set_disabled()

    def _handle_result(self, *args, **kwargs):
        if not args:
            return

        result = args[0]
        if not isinstance(result, TaskResult):
            return

        host = result._host
        task = result._task
        role = task._role

        self._hosts.add(host.get_name())

        action = task.resolved_action
        action_collection = None
        if action and '.' in action:
            action_collection = '.'.join(action.split('.', 2)[:2])

        role_collection = None
        role_name = None if not role else role.get_name()
        if role and '.' in role_name:
            role_collection = '.'.join(role_name.split('.', 2)[:2])

        connection_collection = None
        connection = _get_connection_fqcn(task, host)
        if '.' in connection:
            connection_collection = '.'.join(connection.split('.')[:2])

        collections = self._telemetry['collections']
        for resource, collection, name in (('action', action_collection, action),
                                           ('role', role_collection, role_name),
                                           ('connection', connection_collection, connection)):
            if not collection:
                continue

            collections[collection]['resources'][resource][name]['count'] += 1

    # v2_on_file_diff = _handle_result
    v2_runner_item_on_failed = _handle_result
    v2_runner_item_on_ok = _handle_result
    v2_runner_item_on_skipped = _handle_result
    v2_runner_on_async_failed = _handle_result
    v2_runner_on_async_ok = _handle_result
    v2_runner_on_async_poll = _handle_result
    v2_runner_on_failed = _handle_result
    v2_runner_on_ok = _handle_result
    v2_runner_on_skipped = _handle_result
    v2_runner_on_unreachable = _handle_result
    v2_runner_retry = _handle_result

    def v2_playbook_on_stats(self, stats):
        self._telemetry['ansible_core'] = {
            'version': ansible_version,
        }
        self._telemetry['hosts'] = {
            'count': len(self._hosts),
        }

        for collection in self._telemetry['collections']:
            if collection in _CORE_SYN_COLLECTIONS:
                continue
            cpath = files('ansible_collections.%s' % collection)
            for candidate in ('METADATA.json', 'galaxy.yml'):
                mdfile = cpath.joinpath(candidate)
                if mdfile.exists():
                    self._telemetry['collections'][collection]['version'] = yaml_load(
                        mdfile.read_text()
                    ).get('version', '*')
                    break

        with contextlib.suppress(Exception):
            self._write_journal()

    def _write_journal(self):
        journal_sendv(
            'MESSAGE=%s' % json.dumps(self._telemetry, separators=(',', ':')),
            'MESSAGE_ID=%s' % _ANSIBLE_TELEMETRY_MESSAGE_ID.hex,
            'ANSIBLE_TELEMETRY=core',
            'ANSIBLE_TELEMETRY_ID=%s' % uuid.uuid4().hex,
        )


@contextlib.contextmanager
def _get_journal_reader(seek=None):
    with journal.Reader() as j:
        if seek:
            j.seek_realtime(seek)
        j.add_match('MESSAGE_ID=%s' % _ANSIBLE_TELEMETRY_MESSAGE_ID.hex)
        j.add_match('ANSIBLE_TELEMETRY=core')
        yield j


def main():
    lastupload_file = pathlib.Path('/etc/insights-client/.lastupload')
    lastupload = None
    with contextlib.suppress(ValueError, OSError):
        lastupload = datetime.datetime.strptime(
            lastupload_file.read_text(),
            '%Y-%m-%dT%H:%M:%S.%f'
        )

    with _get_journal_reader(lastupload) as j:
        for entry in j:
            print(entry['MESSAGE'])


if __name__ == '__main__':
    main()
