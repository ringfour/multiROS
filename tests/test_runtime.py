import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from multiros.cli import load_env, main, plan
from multiros.runtime import image_commands, runtime_name, wslc_run


class RuntimeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='robot space ')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / 'compose.yaml').write_text('services: {}\n')
        self.config = {
            'schema': 1, 'project': 'arm-one', 'service': 'ros-dev',
            'compose': ['compose.yaml'], 'rendering_base': True,
            'entrypoint': ['/entrypoint'], 'submodules': ['dependencies/arm'],
            'configurations': ['standard', 'mod101'],
            'container': {'image': {'default': 'arm:test'}, 'workdir': '/workspace/arm',
                          'mounts': [{'source': '{root}', 'target': '/workspace/arm'},
                                     {'type': 'volume', 'source': 'arm-one-build', 'target': '/workspace/arm/build'}],
                          'ports': ['127.0.0.1:8889:8888'], 'environment': {'RMW_IMPLEMENTATION': 'rmw_fastrtps_cpp'}},
            'commands': {'sim': {'where': 'container', 'argv': ['launch', '{configuration}']},
                         'sim-stop': {'where': 'container', 'argv': ['stop-sim']}}}

    def test_windows_selects_wslc_without_docker(self):
        with patch('multiros.runtime.platform.system', return_value='Windows'):
            self.assertEqual(runtime_name(), 'wslc')
        command = plan(self.config, self.root, 'default', 'sim', ['mod101', 'world:=a b'], 'wslc')
        self.assertEqual(command, ['wslc', 'exec', '--workdir', '/workspace/arm',
                                   'arm-one-ros-dev', '/entrypoint', 'launch', 'mod101', 'world:=a b'])

    def test_wslc_mounts_keep_spaces_and_use_named_volumes(self):
        command = wslc_run(self.config, self.root, 'default')
        self.assertIn('type=bind,source=' + str(self.root) + ',target=/workspace/arm', command)
        self.assertIn('type=volume,source=arm-one-build,target=/workspace/arm/build', command)
        self.assertNotIn('compose', command)
        self.assertIn('--gpus', command)
        self.assertNotIn('--rm', command)

    def test_cpu_profile_does_not_request_gpu(self):
        self.assertNotIn('--gpus', wslc_run(self.config, self.root, 'cpu'))

    def test_image_builds_use_the_selected_engine(self):
        commands = image_commands(self.config, self.root, 'default', 'wslc')
        self.assertEqual([x[0] for x in commands], ['wslc', 'wslc'])
        self.assertIn('ROS_RENDERING_IMAGE=multiros:jazzy-rendering', commands[1])

    def test_down_stops_simulation_before_container_and_aborts_on_failure(self):
        path = self.root / 'multiros.json'
        path.write_text(json.dumps(self.config))
        with patch('multiros.cli.container_running', return_value=True), \
             patch('multiros.cli.subprocess.call', return_value=7) as call:
            result = main(['--config', str(path), '--runtime', 'wslc', 'down'])
        self.assertEqual(result, 7)
        self.assertEqual(call.call_count, 1)
        self.assertEqual(call.call_args.args[0][-1], 'stop-sim')

    def test_dotenv_is_data_and_does_not_override_explicit_environment(self):
        (self.root / '.env').write_text('MULTIROS_TEST_VALUE="hello world"\nMULTIROS_LITERAL=$(whoami)\n')
        with patch.dict(os.environ, {'MULTIROS_TEST_VALUE': 'explicit'}):
            load_env(self.root)
            self.assertEqual(os.environ['MULTIROS_TEST_VALUE'], 'explicit')
            self.assertEqual(os.environ['MULTIROS_LITERAL'], '$(whoami)')

    def test_up_stops_simulation_before_replacing_docker_container(self):
        path = self.root / 'multiros.json'
        path.write_text(json.dumps(self.config))
        with patch('multiros.cli.capture', return_value='default'), \
             patch('multiros.cli.container_running', return_value=True), \
             patch('multiros.cli.execute', return_value=0) as execute:
            self.assertEqual(main(['--config', str(path), '--runtime', 'docker', 'up']), 0)
        commands = execute.call_args.args[0]
        self.assertEqual(commands[-2][-1], 'stop-sim')
        self.assertEqual(commands[-1][-3:], ['up', '-d', 'ros-dev'])
