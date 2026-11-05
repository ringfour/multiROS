"""Passive MuJoCo frontend. This module never advances simulator physics."""
import argparse
import hashlib
import math
import os
from pathlib import Path
import signal
import time

import mujoco
import mujoco.viewer
import numpy as np


def load_snapshot(path, model, data, *, allow_legacy=False, model_digest=None, previous=None):
    """Validate the whole snapshot before modifying data; return its identity.

    Schema 1 is a display snapshot, not a restartable physics checkpoint.
    model_sha256 identifies scene XML bytes; assets must be pinned separately.
    """
    with np.load(path, allow_pickle=False) as state:
        if "schema" not in state:
            if not allow_legacy:
                raise ValueError("Unversioned snapshot; use --legacy-snapshots for an existing exporter")
            identity = None
        else:
            schema = state["schema"].item()
            if type(schema) is not int or schema != 1:
                raise ValueError("Unsupported snapshot schema")
            if str(state["mujoco_version"]) != mujoco.__version__:
                raise ValueError("Snapshot and viewer MuJoCo versions differ")
            if model_digest is None or str(state["model_sha256"]) != model_digest:
                raise ValueError("Snapshot belongs to a different scene")
            session, sequence = state["session"].item(), state["sequence"].item()
            if not isinstance(session, str) or not session or type(sequence) is not int or sequence < 0:
                raise ValueError("Snapshot requires a session and nonnegative sequence")
            identity = (session, sequence)
            if previous is not None:
                if session != previous[0]:
                    raise ValueError("Simulation session changed; restart the viewer to attach")
                if sequence <= previous[1]:
                    raise ValueError("Snapshot sequence did not advance")
        values = {}
        for name in ("qpos", "qvel", "ctrl"):
            value = np.asarray(state[name], dtype=np.float64)
            if value.shape != getattr(data, name).shape or not np.isfinite(value).all():
                raise ValueError(f"Invalid {name} shape or values for this model")
            values[name] = value.copy()
        timestamp = float(state["time"])
        if not np.isfinite(timestamp):
            raise ValueError("Invalid simulation time")
    for name, value in values.items():
        getattr(data, name)[:] = value
    data.time = timestamp
    return identity


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runtime", type=Path, default=Path(".runtime"))
    parser.add_argument("--model", type=Path)
    parser.add_argument("--file", default="viewer.npz")
    parser.add_argument("--rate", type=float, default=60.)
    parser.add_argument("--timeout", type=float, default=30.)
    parser.add_argument("--track-body")
    parser.add_argument("--distance", type=float, default=3.)
    parser.add_argument("--azimuth", type=float, default=120.)
    parser.add_argument("--elevation", type=float, default=-20.)
    parser.add_argument("--hide-group", type=int, action="append", default=[])
    parser.add_argument("--show-group", type=int, action="append", default=[])
    parser.add_argument("--legacy-snapshots", action="store_true")
    parser.add_argument("--static", action="store_true", help="Inspect a model without a state source")
    args = parser.parse_args(argv)
    if any(not math.isfinite(value) or value <= 0 for value in (args.rate, args.timeout, args.distance)):
        parser.error("rate, timeout and distance must be positive")
    if any(group not in range(6) for group in args.hide_group + args.show_group):
        parser.error("geometry groups must be between 0 and 5")
    scene = args.model or args.runtime / "scene.xml"
    deadline = time.monotonic() + args.timeout
    while not scene.is_file():
        if time.monotonic() > deadline:
            raise RuntimeError(f"Physics owner did not publish {scene}")
        time.sleep(.1)
    digest = hashlib.sha256(scene.read_bytes()).hexdigest()
    model = mujoco.MjModel.from_xml_path(str(scene.resolve()))
    data = mujoco.MjData(model)
    mujoco.mj_forward(model, data)
    running = True

    def stop(*_):
        nonlocal running
        running = False

    old_signals = {sig: signal.signal(sig, stop) for sig in (signal.SIGINT, signal.SIGTERM)}
    native = None
    try:
        native = mujoco.viewer.launch_passive(model, data)
        with native.lock():
            if args.track_body:
                native.cam.type = mujoco.mjtCamera.mjCAMERA_TRACKING
                native.cam.trackbodyid = model.body(args.track_body).id
            native.cam.distance, native.cam.azimuth, native.cam.elevation = args.distance, args.azimuth, args.elevation
            for group in args.show_group:
                native.opt.geomgroup[group] = 1
            for group in args.hide_group:
                native.opt.geomgroup[group] = 0
        last = None
        identity = None
        announced = False
        # One source per adapter: do not silently fall back to an older session.
        source = args.runtime / args.file
        deadline = time.monotonic() + args.timeout
        while running and native.is_running():
            if not args.static:
                try:
                    # Use the descriptor's timestamp: the producer may replace
                    # the path between stat() and open() on every frame.
                    with source.open("rb") as stream:
                        stamp = os.fstat(stream.fileno()).st_mtime_ns
                        if stamp != last:
                            with native.lock():
                                identity = load_snapshot(stream, model, data, allow_legacy=args.legacy_snapshots,
                                                         model_digest=digest, previous=identity)
                                mujoco.mj_forward(model, data)
                            last = stamp
                except FileNotFoundError:
                    stamp = None
                if stamp is None and time.monotonic() > deadline:
                    raise RuntimeError(f"Physics owner did not publish {source}")
            native.sync()
            if not announced and (args.static or last is not None):
                print(f"Viewer attached: {scene} (MuJoCo {mujoco.__version__}; physics remains external)", flush=True)
                announced = True
            time.sleep(1. / args.rate)
    finally:
        if native is not None:
            native.close()
        for sig, handler in old_signals.items():
            signal.signal(sig, handler)


if __name__ == "__main__":
    main()
