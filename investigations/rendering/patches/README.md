The shader I/O patch is the `zink_compiler.c` portion of:
https://github.com/Meliorative-peasant63/bar-on-apple-silicon/blob/main/patches/mesa-bar-patches.diff

Retrieved 5 November 2026. The upstream license is included as `LICENSE`.
The patch merges split fragment inputs and widens vertex outputs / fragment
inputs to vec4 at component zero for MoltenVK. It does not suppress failed
draw calls. This is an experimental patch; the upstream process-wide quirk
flag needs review before treating it as a general multi-device solution.
