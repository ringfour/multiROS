# Standalone MuJoCo viewer example

From the multiROS repository:

```bash
pixi install --locked
pixi run -e mujoco example-view
```

This opens the included static scene without Docker, ROS or a physics process.
The shared viewer never steps the model.

To follow a live robot, use its `pixi run view` task. See
[Simulation and viewing](../../docs/simulation.md) for model assets, options and
the versioned snapshot format used by new exporters.
