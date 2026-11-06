"""Run a robot's container workflow from any supported host."""
import argparse
import json
import os
from pathlib import Path
import platform
import re
import shutil
import subprocess
import sys
import tomllib

from .runtime import (CORE, compose_base, container_name, exec_command,
                      image_commands, lifecycle_command, runtime_name, wslc_existing)


def capture(argv, cwd=None):
    try:
        result = subprocess.run(argv, cwd=cwd, capture_output=True, text=True, timeout=15)
        return result.stdout.strip() if result.returncode == 0 else None
    except (OSError, subprocess.TimeoutExpired):
        return None


def revision(root):
    top = capture(['git', 'rev-parse', '--show-toplevel'], root)
    if not top or Path(top).resolve() != root.resolve():
        return {'revision': None, 'dirty': None}
    status = capture(['git', 'status', '--porcelain'], root)
    return {'revision': capture(['git', 'rev-parse', 'HEAD'], root),
            'dirty': bool(status) if status is not None else None}


def default_config():
    pixi = Path('pixi.toml')
    if pixi.is_file() and 'multiros' in tomllib.loads(pixi.read_text()).get('tool', {}):
        return pixi
    return Path('multiros.json')


def load_config(path):
    path = path.resolve()
    if path.suffix == '.toml':
        document = tomllib.loads(path.read_text())
        config = document.get('tool', {}).get('multiros')
        if not isinstance(config, dict):
            raise ValueError(f'{path}: missing [tool.multiros] configuration')
    else:
        # Compatibility for robots which have not migrated yet.
        config = json.loads(path.read_text())
    if config.get('schema') != 1:
        raise ValueError(f'{path}: multiROS configuration must use schema 1')
    if not re.fullmatch(r'[a-z0-9][a-z0-9_-]*', config.get('project', '')):
        raise ValueError('project must be a lowercase Compose project name')
    root = (path.parent / config.get('root', '.')).resolve()
    if not root.is_dir():
        raise ValueError(f'Robot root does not exist: {root}')
    for item in config.get('compose', []):
        if not (root / item).is_file():
            raise ValueError(f'Compose file not found: {root / item}')
    return config, root


def load_env(root):
    path = root / '.env'
    if not path.is_file():
        return
    for number, line in enumerate(path.read_text().splitlines(), 1):
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        key, sep, value = line.partition('=')
        if not sep or not re.fullmatch(r'[A-Za-z_][A-Za-z_0-9]*', key):
            raise ValueError(f'{path}:{number}: expected NAME=value')
        if value[:1] in ('"', "'"):
            if len(value) < 2 or value[-1] != value[0]:
                raise ValueError(f'{path}:{number}: unmatched quote')
            value = value[1:-1]
        os.environ.setdefault(key, value)


def select_backend(requested, context):
    return ('lighter' if context == 'lighter' else 'default') if requested == 'auto' else requested


def expand(argv, root):
    if not isinstance(argv, list) or not argv or not all(isinstance(x, str) for x in argv):
        raise ValueError('Commands must be nonempty arrays of strings')
    return [arg.replace('{root}', str(root)).replace('{multiros}', str(CORE))
            .replace('{python}', sys.executable) for arg in argv]


def plan(config, root, backend, action, extra, runtime='docker'):
    custom = config.get('commands', {}).get(action)
    if custom is not None:
        if custom.get('where') not in ('host', 'container'):
            raise ValueError(f'Command {action!r} needs where=host or container')
        extra = list(extra)
        configuration = os.environ.get(config.get('configuration_env', ''), config.get('default_configuration', 'standard'))
        if extra and extra[0] in config.get('configurations', []):
            configuration = extra.pop(0)
        if config.get('configurations') and configuration not in config['configurations']:
            raise ValueError(f'Unknown configuration: {configuration}')
        argv = [part.replace('{configuration}', configuration) for part in expand(custom['argv'], root)] + extra
        if custom['where'] == 'host':
            return argv
        interactive = custom.get('interactive', False) and sys.stdin.isatty() and sys.stdout.isatty()
        return exec_command(config, root, backend, runtime, argv, interactive)
    if action == 'exec':
        interactive = not extra and sys.stdin.isatty() and sys.stdout.isatty()
        return exec_command(config, root, backend, runtime, extra or ['bash'], interactive)
    if action == 'build':
        workspace = config.get('workspace')
        if workspace:
            argv = ['colcon', 'build', '--symlink-install', '--parallel-workers', str(workspace.get('workers', 2)),
                    '--base-paths', *workspace['paths'], '--packages-select', *(extra or workspace['packages']),
                    '--cmake-args', *workspace.get('cmake_args', [])]
            return exec_command(config, root, backend, runtime, argv)
        return image_commands(config, root, backend, runtime)[-1] + extra
    return lifecycle_command(config, root, backend, runtime, action, extra)


def prepare_commands(config):
    return [['git', 'submodule', 'update', '--init', '--recursive', *config.get('submodules', [])]]


def doctor(config, root, backend, context, runtime='docker'):
    report = {'host': {'os': platform.system(), 'architecture': platform.machine()},
              'core': {'path': str(CORE), **revision(CORE)}, 'runtime': runtime, 'backend': backend,
              'rendering': 'not probed; run pixi run check-rendering inside the robot project'}
    if runtime == 'docker':
        version = capture(['docker', 'version', '--format', '{{json .Server}}'])
        compose = capture(['docker', 'compose', 'version', '--short'])
        report['docker'] = {'context': context, 'reachable': version is not None, 'compose_version': compose}
        if version:
            server = json.loads(version)
            report['docker']['server'] = {key: server.get(key) for key in ('Version', 'Os', 'Arch')}
        healthy = version is not None and bool(compose)
    else:
        version = capture(['wslc', 'version'])
        report['wslc'] = {'version': version, 'available': version is not None,
                          'validation': 'WSLC version found; GPU/runtime behavior requires Windows testing'}
        healthy = version is not None
    if config:
        report['robot'] = {'path': str(root), 'project': config['project'], **revision(root)}
        if runtime == 'docker':
            report['compose_command'] = compose_base(config, root, backend)
        else:
            report['container'] = container_name(config)
    print(json.dumps(report, indent=2))
    return 0 if healthy else 1


def init_robot(destination):
    source = CORE / 'templates/robot'
    if not source.is_dir():
        raise ValueError('Run init from the multiROS source checkout')
    files = sorted(path for path in source.rglob('*') if path.is_file())
    for path in files:
        target = destination / path.relative_to(source)
        if target.exists() or target.is_symlink():
            raise ValueError(f'Refusing to overwrite {target}')
        if any(parent.exists() and not parent.is_dir() for parent in target.parents):
            raise ValueError(f'Destination parent is not a directory: {target}')
    for path in files:
        target = destination / path.relative_to(source)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(path, target)
    print(f'Created robot starter in {destination}. Configure its image and commands before running it.')
    return 0


def viewer_command(config, root, extra, backend="default"):
    executable = shutil.which('mjpython') if platform.system() == 'Darwin' else sys.executable
    if not executable:
        raise ValueError('mjpython is required on macOS; use the robot viewer Pixi environment')
    spec = config['viewer']
    return [executable, '-m', 'multiros.viewer', '--runtime', str(root / spec.get('runtime', '.runtime')),
            *spec.get('args', []), *spec.get('backend_args', {}).get(backend, []), *extra]


def execute(commands, root, dry_run):
    if dry_run:
        print(json.dumps({'cwd': str(root), 'commands': commands}, indent=2))
        return 0
    for command in commands:
        print('+ ' + subprocess.list2cmdline(command), flush=True)
        result = subprocess.call(command, cwd=root)
        if result:
            return result
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, epilog='Actions: doctor, setup, images, up, down, restart, build, sim, sim-stop, view, test, exec, status, logs, init; plus robot commands.')
    parser.add_argument('--config', type=Path)
    parser.add_argument('--runtime', default=os.environ.get('MULTIROS_RUNTIME', 'auto'))
    parser.add_argument('--backend', default=os.environ.get('MULTIROS_BACKEND', 'auto'))
    parser.add_argument('--dry-run', action='store_true')
    parser.add_argument('action')
    parser.add_argument('arguments', nargs=argparse.REMAINDER)
    args = parser.parse_args(argv)
    extra = args.arguments[1:] if args.arguments[:1] == ['--'] else args.arguments
    try:
        if args.action == 'init':
            if len(extra) != 1 or args.dry_run:
                raise ValueError('Usage: multiros init DESTINATION')
            return init_robot(Path(extra[0]).resolve())
        if args.action == 'view-example':
            command = viewer_command({'viewer': {'args': ['--model', str(CORE / 'examples/mujoco/scene.xml'), '--static']}}, CORE, extra)
            return execute([command], CORE, args.dry_run)
        runtime = runtime_name(args.runtime)
        context = capture(['docker', 'context', 'show']) if runtime == 'docker' else None
        backend = select_backend(args.backend, context)
        path = args.config or default_config()
        if args.action == 'doctor' and args.config is None and not path.exists():
            return doctor(None, None, backend, context, runtime)
        config, root = load_config(path)
        load_env(root)
        if args.action == 'doctor':
            return doctor(config, root, backend, context, runtime)
        if args.action == 'view':
            env = dict(os.environ)
            env['PYTHONPATH'] = os.pathsep.join(filter(None, [str(CORE), env.get('PYTHONPATH')]))
            command = viewer_command(config, root, extra, backend)
            if args.dry_run:
                return execute([command], root, True)
            return subprocess.call(command, cwd=root, env=env)
        if args.action == 'setup':
            commands = prepare_commands(config)
        elif args.action == 'images':
            commands = prepare_commands(config) + image_commands(config, root, backend, runtime)
        elif args.action == 'up':
            if runtime == 'wslc' and not args.dry_run and wslc_existing(config):
                commands = [['wslc', 'container', 'start', container_name(config)]]
            else:
                commands = prepare_commands(config) + image_commands(config, root, backend, runtime)
                if 'sim-stop' in config.get('commands', {}) and (
                        args.dry_run or container_running(config, root, backend, runtime)):
                    commands.append(plan(config, root, backend, 'sim-stop', [], runtime))
                commands += [plan(config, root, backend, 'up', extra, runtime)]
        elif args.action in ('down', 'restart'):
            commands = []
            if 'sim-stop' in config.get('commands', {}):
                # Only stop the simulator when this project's container is running.
                if args.dry_run or container_running(config, root, backend, runtime):
                    commands.append(plan(config, root, backend, 'sim-stop', [], runtime))
            commands.append(plan(config, root, backend, args.action, extra, runtime))
        else:
            commands = [plan(config, root, backend, args.action, extra, runtime)]
        return execute(commands, root, args.dry_run)
    except KeyboardInterrupt:
        return 130
    except (OSError, ValueError, KeyError) as error:
        print(f'multiros: {error}', file=sys.stderr)
        return 2


def container_running(config, root, backend, runtime):
    if runtime == 'docker':
        output = capture(compose_base(config, root, backend) + ['ps', '--status', 'running', '-q', config.get('service', 'ros-dev')], root)
        return bool(output)
    output = capture(['wslc', 'container', 'list', '--filter', 'name=' + container_name(config), '--quiet'])
    return bool(output)


if __name__ == '__main__':
    raise SystemExit(main())
