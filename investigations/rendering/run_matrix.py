#!/usr/bin/env python3
"""Run each render feature in a separate disposable GPU container."""
import argparse
import json
from pathlib import Path
import subprocess
import uuid

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--image', default='xlerobot:jazzy-lighter')
parser.add_argument('--output', type=Path, required=True)
parser.add_argument('--timeout', type=int, default=30)
args = parser.parse_args()
root = Path(__file__).resolve().parents[2]
args.output.mkdir(parents=True, exist_ok=True)
results = []
for case in ['plain', 'texture', 'skybox', 'reflection', 'lights', 'fog', 'transparency', 'combined']:
    name = 'multiros-render-case-' + uuid.uuid4().hex[:12]
    command = ['docker', 'run', '--rm', '--name', name, '--device', 'lighter.sh/gpu=all',
               '-e', 'MESA_SHADER_CACHE_DISABLE=true', '-v', str(root) + ':/investigation:ro',
               '--entrypoint', '/opt/xlerobot-python/bin/python', args.image,
               '-u', '/investigation/investigations/rendering/reproduce.py', case]
    try:
        process = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                 text=True, timeout=args.timeout)
        output, code = process.stdout, process.returncode
    except subprocess.TimeoutExpired as error:
        output = error.stdout or b''
        if isinstance(output, bytes):
            output = output.decode(errors='replace')
        code = 124
        subprocess.run(['docker', 'rm', '-f', name], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    (args.output / (case + '.log')).write_text(output)
    results.append({'case': case, 'returncode': code})
    print(case, code, output.splitlines()[-1] if output else '', flush=True)
(args.output / 'results.json').write_text(json.dumps({'image': args.image, 'results': results}, indent=2) + '\n')
raise SystemExit(any(row['returncode'] for row in results))
