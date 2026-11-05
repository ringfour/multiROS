# Mesa 25.1.9 compiler fixes for lighter / MoltenVK

These patches apply to the checksum-verified Mesa source in `docker/Dockerfile`.
They are built into `multiros:jazzy-lighter`; no patch download is required.
The patch files and license are also installed under
`/usr/share/doc/multiros/mesa-patches/` in that image.

- `0008-moltenvk-shader-io.patch`: merge split texture-coordinate inputs and
  use matching vec4 interfaces for MoltenVK. Derived from the compiler portion
  of the BAR-on-Apple-Silicon patch below. multiROS passes the driver decision
  through each shader's I/O state instead of using its process-wide global.
- `0009-moltenvk-resource-names.patch`: rename resource variables that conflict
  with Metal keywords, including the generated `sampler` name exposed by
  `ZINK_DEBUG=nir`. Renaming does not change numerical bindings or locations.

Origin and investigation:
https://github.com/Meliorative-peasant63/bar-on-apple-silicon/blob/main/patches/mesa-bar-patches.diff
https://github.com/Meliorative-peasant63/bar-on-apple-silicon/blob/main/ATTEMPT-LOG.md

Retrieved 5 November 2026; source attribution and MIT terms are in `LICENSE`.
The other seven platform compatibility adjustments remain in the Dockerfile.
No patch skips failed draws or claims unsupported OpenGL features.
