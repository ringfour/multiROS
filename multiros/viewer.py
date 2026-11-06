"""Passive MuJoCo frontend. This module never advances simulator physics."""
import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import signal
import time

import mujoco
import mujoco.viewer
import numpy as np


def load_model(path):
    """MJB embeds assets so a native viewer can consume container-owned models."""
    path = Path(path)
    if path.suffix.lower() == '.mjb':
        return mujoco.MjModel.from_binary_path(str(path.resolve()))
    return mujoco.MjModel.from_xml_path(str(path.resolve()))


def update_display_state(model, data, *, kinematics_only=False):
    if kinematics_only:
        # Passive body display does not need contacts, constraints or sensors.
        mujoco.mj_kinematics(model, data)
        mujoco.mj_comPos(model, data)
        mujoco.mj_camlight(model, data)
    else:
        mujoco.mj_forward(model, data)


def load_snapshot(path, model, data, *, allow_legacy=False, model_digest=None, previous=None):
    """Validate the whole snapshot before modifying data; return its identity.

    Schema 1 is a display snapshot, not a restartable physics checkpoint.
    model_sha256 identifies XML or compiled-model bytes. XML assets must be pinned
    separately; compiled MJB models embed their assets.
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
    parser.add_argument("--frontend", choices=("passive", "glfw"), default="passive",
                        help="glfw caps actual drawing; passive retains MuJoCo's full UI")
    parser.add_argument("--profile", type=Path, help="Write timing counters when the viewer closes")
    parser.add_argument("--pose-tolerance", type=float, default=1e-5,
                        help="glfw skips redraws below this visible-pose change (metres/rotation components)")
    parser.add_argument("--full-forward", dest="kinematics_only", action="store_false",
                        help="Override --kinematics-only for full passive-UI diagnostics")
    parser.add_argument("--width", type=int, default=1280)
    parser.add_argument("--height", type=int, default=720)
    parser.add_argument("--rate", type=float, default=None,
                        help="glfw frame cap (default 15); passive state-update rate (default 60)")
    parser.add_argument("--timeout", type=float, default=30.)
    parser.add_argument("--track-body")
    parser.add_argument("--distance", type=float, default=3.)
    parser.add_argument("--azimuth", type=float, default=120.)
    parser.add_argument("--elevation", type=float, default=-20.)
    parser.add_argument("--hide-group", type=int, action="append", default=[])
    parser.add_argument("--show-group", type=int, action="append", default=[])
    parser.add_argument("--legacy-snapshots", action="store_true")
    parser.add_argument("--static", action="store_true", help="Inspect a model without a state source")
    parser.add_argument("--kinematics-only", action="store_true",
                        help="Update body/camera/light transforms without recomputing sensors or contacts")
    parser.add_argument("--quality", choices=("fast", "standard"), default="fast",
                        help="fast disables expensive shadows and planar reflections (default)")
    parser.set_defaults(kinematics_only=False)
    args = parser.parse_args(argv)
    if args.rate is None:
        args.rate = 15. if args.frontend == "glfw" else 60.
    if any(not math.isfinite(value) or value <= 0 for value in (args.rate, args.timeout, args.distance, args.pose_tolerance)):
        parser.error("rate, timeout, distance and pose tolerance must be positive")
    if any(group not in range(6) for group in args.hide_group + args.show_group):
        parser.error("geometry groups must be between 0 and 5")
    if min(args.width, args.height) <= 0:
        parser.error("width and height must be positive")
    scene = args.model or args.runtime / "scene.xml"
    deadline = time.monotonic() + args.timeout
    while not scene.is_file():
        if time.monotonic() > deadline:
            raise RuntimeError(f"Physics owner did not publish {scene}")
        time.sleep(.1)
    with scene.open("rb") as stream:
        digest = hashlib.file_digest(stream, "sha256").hexdigest()
    model = load_model(scene)
    data = mujoco.MjData(model)
    update_display_state(model, data, kinematics_only=args.kinematics_only)
    running = True

    def stop(*_):
        nonlocal running
        running = False

    old_signals = {sig: signal.signal(sig, stop) for sig in (signal.SIGINT, signal.SIGTERM)}
    native = None
    profile = {"snapshot_ms": [], "transforms_ms": [], "sync_ms": [], "frame_ms": []}
    profile_started = None
    cpu_started = None
    try:
        if args.frontend == "glfw":
            from .glfw_viewer import GlfwViewer
            # This frontend draws into the window, not an offscreen sensor FBO.
            model.vis.global_.offwidth = model.vis.global_.offheight = 1
            model.vis.quality.offsamples = 0
            if args.quality == "fast":
                model.vis.quality.shadowsize = 1
            native = GlfwViewer(model, data, width=args.width, height=args.height,
                                pose_tolerance=args.pose_tolerance)
        else:
            native = mujoco.viewer.launch_passive(model, data)
        with native.lock():
            if args.quality == "fast":
                for flag in (mujoco.mjtRndFlag.mjRND_SHADOW, mujoco.mjtRndFlag.mjRND_REFLECTION):
                    native.user_scn.flags[flag] = 0
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
        profile_started = time.monotonic()
        cpu_started = time.process_time()
        while running and native.is_running():
            started = time.monotonic()
            if not args.static:
                try:
                    # Use the descriptor's timestamp: the producer may replace
                    # the path between stat() and open() on every frame.
                    with source.open("rb") as stream:
                        stamp = os.fstat(stream.fileno()).st_mtime_ns
                        if stamp != last:
                            with native.lock():
                                read_started = time.perf_counter()
                                identity = load_snapshot(stream, model, data, allow_legacy=args.legacy_snapshots,
                                                         model_digest=digest, previous=identity)
                                transform_started = time.perf_counter()
                                update_display_state(model, data, kinematics_only=args.kinematics_only)
                                if args.profile:
                                    profile["snapshot_ms"].append((transform_started-read_started)*1000)
                                    profile["transforms_ms"].append((time.perf_counter()-transform_started)*1000)
                            last = stamp
                except FileNotFoundError:
                    stamp = None
                if stamp is None and time.monotonic() > deadline:
                    raise RuntimeError(f"Physics owner did not publish {source}")
            sync_started = time.perf_counter()
            native.sync()
            if args.profile:
                profile["sync_ms"].append((time.perf_counter()-sync_started)*1000)
                profile["frame_ms"].append((time.monotonic()-started)*1000)
            if not announced and (args.static or last is not None):
                print(f"Viewer attached: {scene} (MuJoCo {mujoco.__version__}; {args.frontend}; "
                      f"{'draw cap' if args.frontend == 'glfw' else 'state updates'} {args.rate:g} Hz; "
                      "physics remains external)", flush=True)
                announced = True
            delay = (max(0., 1. / args.rate - (time.monotonic() - started))
                     if args.frontend == "glfw" else 1. / args.rate)
            time.sleep(delay)
    finally:
        result = None
        if args.profile and profile_started is not None:
            elapsed = time.monotonic()-profile_started
            result = {"frontend": args.frontend, "rate_limit": args.rate,
                      "seconds": elapsed, "cpu_percent_one_core": 100*(time.process_time()-cpu_started)/elapsed,
                      "sync_count": len(profile["sync_ms"]),
                      "draw_count": getattr(native, "frames", None),
                      "idle_redraws_skipped": getattr(native, "idle_frames", None)}
            for key, values in profile.items():
                if values:
                    result[key] = {"median": float(np.median(values)), "p95": float(np.percentile(values, 95))}
        try:
            if result is not None:
                args.profile.write_text(json.dumps(result, indent=2)+"\n")
        finally:
            try:
                if native is not None:
                    native.close()
            finally:
                for sig, handler in old_signals.items():
                    signal.signal(sig, handler)


if __name__ == "__main__":
    main()
