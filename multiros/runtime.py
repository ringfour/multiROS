"""Container commands for Docker Compose and Microsoft's WSL container CLI."""
import os
from pathlib import Path
import platform
import re
import subprocess

CORE = Path(__file__).resolve().parents[1]


def runtime_name(requested="auto"):
    if requested == "auto":
        return "wslc" if platform.system() == "Windows" else "docker"
    if requested not in ("docker", "wslc"):
        raise ValueError(f"Unknown runtime: {requested}")
    return requested


def value(item, backend):
    return item.get(backend, item.get("default")) if isinstance(item, dict) else item


def expand(text, root):
    text = text.replace("{root}", str(root)).replace("{multiros}", str(CORE))
    return re.sub(r"\$\{([A-Za-z_][A-Za-z_0-9]*)(?::-([^}]*))?\}",
                  lambda match: os.environ.get(match[1], match[2] or ""), text)


def compose_base(config, root, backend):
    files = list(config.get("compose", []))
    if not files:
        raise ValueError("No Compose files configured")
    if backend != "default":
        overrides = config.get("backends", {})
        if backend not in overrides:
            raise ValueError(f"Backend {backend!r} is not configured for this robot")
        files += overrides[backend]
    argv = ["docker", "compose", "--project-name", config["project"],
            "--project-directory", str(root)]
    for file in files:
        path = root / file
        if not path.is_file():
            raise ValueError(f"Compose file not found: {path}")
        argv += ["-f", str(path)]
    return argv


def container_name(config):
    return config["project"] + "-" + config.get("service", "ros-dev")


def exec_command(config, root, backend, runtime, command, interactive=False):
    if runtime == "docker":
        argv = compose_base(config, root, backend) + ["exec"]
        if not interactive:
            argv += ["-T"]
        argv += [config.get("service", "ros-dev")]
    else:
        argv = ["wslc", "exec"] + (["-it"] if interactive else [])
        argv += ["--workdir", config["container"]["workdir"], container_name(config)]
    return argv + config.get("entrypoint", []) + command


def wslc_run(config, root, backend):
    spec = config["container"]
    argv = ["wslc", "run", "--detach", "--name", container_name(config),
            "--label", "org.multiros.project=" + config["project"],
            "--workdir", spec["workdir"], "--stop-timeout", "30"]
    if spec.get("gpu", True) and backend != "cpu":
        argv += ["--gpus", "all"]
    for mount in spec.get("mounts", []):
        kind = mount.get("type", "bind")
        source = expand(mount["source"], root)
        if "," in source:
            raise ValueError("WSLC bind mount paths cannot contain commas")
        argv += ["--mount", f"type={kind},source={source},target={mount['target']}"]
    environment = dict(spec.get("environment", {}))
    environment.update(spec.get("backend_environment", {}).get(backend, {}))
    for key, item in environment.items():
        argv += ["--env", key + "=" + expand(str(item), root)]
    for port in spec.get("ports", []):
        argv += ["--publish", expand(port, root)]
    return argv + [value(spec["image"], backend)] + spec.get("command", ["sleep", "infinity"])


def image_commands(config, root, backend, runtime):
    engine = "wslc" if runtime == "wslc" else "docker"
    commands = []
    base = "multiros:jazzy-lighter" if backend == "lighter" else "multiros:jazzy-rendering"
    if config.get("rendering_base"):
        commands.append([engine, "build", "--target", "lighter" if backend == "lighter" else "runtime",
                         "--tag", base, "--file", str(CORE / "docker/Dockerfile"), str(CORE)])
    if runtime == "docker":
        commands.append(compose_base(config, root, backend) + ["build", config.get("service", "ros-dev")])
    else:
        spec = config["container"]
        commands.append([engine, "build", "--tag", value(spec["image"], backend),
                         "--build-arg", "ROS_RENDERING_IMAGE=" + base,
                         "--file", str(root / spec.get("dockerfile", "docker/Dockerfile")), str(root)])
    return commands


def lifecycle_command(config, root, backend, runtime, action, extra):
    if runtime == "docker":
        base = compose_base(config, root, backend)
        service = config.get("service", "ros-dev")
        suffix = {"up": ["up", "-d", service], "down": ["stop"],
                  "restart": ["restart", service], "status": ["ps"],
                  "logs": ["logs", "--follow", service]}.get(action)
    else:
        base = ["wslc", "container"]
        name = container_name(config)
        suffix = {"down": ["stop", "--time", "30", name], "restart": ["restart", name],
                  "status": ["inspect", name], "logs": ["logs", "--follow", name]}.get(action)
        if action == "up":
            return wslc_run(config, root, backend) + extra
    if suffix is None:
        raise ValueError(f"Unknown lifecycle action: {action}")
    if action == "down" and extra:
        raise ValueError("down accepts no extra arguments; it preserves project volumes")
    return base + suffix + extra


def wslc_existing(config):
    result = subprocess.run(["wslc", "container", "inspect", container_name(config)],
                            capture_output=True, text=True)
    return result.returncode == 0
