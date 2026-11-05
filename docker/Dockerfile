# syntax=docker/dockerfile:1
# Shared ROS Jazzy offscreen rendering base. No robot packages or assets.
# Zink patches adapted from GPUAccelerationTest/vendor/Dockerfile (2026-11-02).
FROM ubuntu:24.04 AS mesa-build

ARG DEBIAN_FRONTEND=noninteractive
ARG MESA_VERSION=25.1.9

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    cmake \
    ca-certificates \
    curl \
    python3 \
    python3-mako \
    python3-yaml \
    python3-ply \
    python3-jinja2 \
    meson \
    ninja-build \
    pkg-config \
    libglvnd-dev \
    bison \
    flex \
    libdrm-dev \
    libexpat1-dev \
    libelf-dev \
    libzstd-dev \
    libxml2-dev \
    libvulkan-dev \
    glslang-tools \
    spirv-tools \
    libx11-dev \
    libx11-xcb-dev \
    libxext-dev \
    libxfixes-dev \
    libxrandr-dev \
    libxdamage-dev \
    libxxf86vm-dev \
    libxcb1-dev \
    libxcb-glx0-dev \
    libxcb-dri2-0-dev \
    libxcb-dri3-dev \
    libxcb-present-dev \
    libxcb-sync-dev \
    libxcb-xfixes0-dev \
    libxcb-randr0-dev \
    libxcb-shm0-dev \
    libxshmfence-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /build

RUN curl -fSLO \
    https://archive.mesa3d.org/mesa-${MESA_VERSION}.tar.xz \
    && echo "412df33a1bb3c785ed698555a3972118a37c458e7accf6ae53f4bb87b3db454a  mesa-${MESA_VERSION}.tar.xz" \
       | sha256sum -c - \
    && tar -xf mesa-${MESA_VERSION}.tar.xz

WORKDIR /build/mesa-25.1.9

# ------------------------------------------------------------
# Patch 1: glibc 2.42+ now provides once_flag / call_once itself
# ------------------------------------------------------------
RUN python3 - <<'PY'
from pathlib import Path

header = Path("src/c11/threads.h")
source = Path("src/c11/impl/threads_posix.c")

h = header.read_text()
s = source.read_text()

old_header = """typedef pthread_mutex_t mtx_t;
typedef pthread_once_t  once_flag;
#  define ONCE_FLAG_INIT PTHREAD_ONCE_INIT
"""

new_header = """typedef pthread_mutex_t mtx_t;
#ifndef __once_flag_defined
typedef pthread_once_t  once_flag;
#  define ONCE_FLAG_INIT PTHREAD_ONCE_INIT
#endif
"""

old_source = """void
call_once(once_flag *flag, void (*func)(void))
{
    pthread_once(flag, func);
}
"""

new_source = """#ifndef __once_flag_defined
void
call_once(once_flag *flag, void (*func)(void))
{
    pthread_once(flag, func);
}
#endif
"""

if h.count(old_header) != 1:
    raise SystemExit("once_flag anchor not unique in threads.h")
if s.count(old_source) != 1:
    raise SystemExit("call_once anchor not unique in threads_posix.c")

header.write_text(h.replace(old_header, new_header, 1))
source.write_text(s.replace(old_source, new_source, 1))
print("patch 1 applied: glibc once_flag compatibility")
PY

# ------------------------------------------------------------
# Patch 2: log every failure point in zink_internal_create_screen
# (release builds silently drop to 'goto fail' with no output)
# ------------------------------------------------------------
RUN python3 - <<'PY'
from pathlib import Path

p = Path("src/gallium/drivers/zink/zink_screen.c")
text = p.read_text()

start = text.index(
    "zink_internal_create_screen(const struct pipe_screen_config *config")
end = text.index("\nfail:\n", start)
segment = text[start:end]

# NOTE: the replacement MUST be brace-wrapped. A bare "log(); goto fail;"
# substitution turns 'if (x)\n goto fail;' into an *unconditional* goto
# (that is exactly what broke the previous build at zink_screen.c:3428:
# screen->dev was set, goto fail jumped the dispatch-table load, and
# zink_destroy_screen then called VKSCR(DestroyDevice) == NULL).
fail_marker = ("{ mesa_loge(\"ZINK: create_screen failing at "
               "zink_screen.c:%d\\n\", __LINE__); goto fail; }")
n = segment.count("goto fail;")
if n == 0:
    raise SystemExit("no 'goto fail;' found in zink_internal_create_screen")

segment = segment.replace("goto fail;", fail_marker)
text = text[:start] + segment + text[end:]
p.write_text(text)
print(f"patch 2 applied: instrumented {n} failure points (braced)")
PY

# ------------------------------------------------------------
# Patch 3: guard Zink driconf queries when the option cache is
# empty (pipe_loader_sw provides no driconf for zink -> aborts)
# ------------------------------------------------------------
RUN python3 - <<'PY'
from pathlib import Path

p = Path("src/gallium/drivers/zink/zink_screen.c")
text = p.read_text()

old = """   if (config) {
      driParseConfigFiles(config->options, config->options_info, 0, "zink","""

new = """   if (config && config->options->tableSize) {
      driParseConfigFiles(config->options, config->options_info, 0, "zink","""

if text.count(old) != 1:
    raise SystemExit("driconf query anchor not found")
p.write_text(text.replace(old, new, 1))
print("patch 3 applied: driconf tableSize guard")
PY

# ------------------------------------------------------------
# Patch 4: Venus lacks logicOp; never enable it in pipelines
# ------------------------------------------------------------
RUN python3 - <<'PY'
from pathlib import Path

p = Path("src/gallium/drivers/zink/zink_pipeline.c")
text = p.read_text()

old = "      blend_state.logicOpEnable = state->blend_state->logicop_enable;"
new = ("      blend_state.logicOpEnable = state->blend_state->logicop_enable"
       " && screen->info.feats.features.logicOp;")

n = text.count(old)
if n != 2:
    raise SystemExit(f"expected 2 logicOpEnable sites, found {n}")
p.write_text(text.replace(old, new))
print("patch 4 applied: logicOp disabled when feature missing")
PY

# ------------------------------------------------------------
# Patch 5: KHR_external_memory_fd is absent on Venus/MoltenVK.
# zink_drm_create_screen tears the screen down silently when it's
# missing (debug_printf is compiled out under NDEBUG). Make the
# check bypassable for headless surfaceless testing.
# ------------------------------------------------------------
RUN python3 - <<'PY'
from pathlib import Path

p = Path("src/gallium/drivers/zink/zink_screen.c")
text = p.read_text()

old = """   if (ret && !ret->info.have_KHR_external_memory_fd) {
      debug_printf("ZINK: KHR_external_memory_fd required!\\n");
      zink_destroy_screen(&ret->base);
      return NULL;
   }
"""

new = """   if (ret && !ret->info.have_KHR_external_memory_fd &&
       !getenv("ZINK_ALLOW_MISSING_EXT_MEM_FD")) {
      mesa_loge("ZINK: KHR_external_memory_fd required!\\n");
      zink_destroy_screen(&ret->base);
      return NULL;
   }
   if (ret && !ret->info.have_KHR_external_memory_fd)
      mesa_loge("ZINK: running without KHR_external_memory_fd\\n");
"""

if text.count(old) != 1:
    raise SystemExit("zink_drm_create_screen external-memory-fd anchor not found")
p.write_text(text.replace(old, new, 1))
print("patch 5 applied: KHR_external_memory_fd teardown bypass")
PY

# ------------------------------------------------------------
# Patch 6: depth/stencil renderbuffers on Venus use LAZILY_ALLOCATED
# memory (transient attachment). Zink's heap demotion only tries
# DEVICE_LOCAL_VISIBLE → DEVICE_LOCAL, never DEVICE_LOCAL_LAZY, so
# the allocation assert fires. Scan ALL heaps before giving up.
# ------------------------------------------------------------
RUN python3 - <<'PY'
from pathlib import Path

p = Path("src/gallium/drivers/zink/zink_resource.c")
text = p.read_text()

old = """   if (zink_mem_type_idx_from_types(screen, heap, reqs->memoryTypeBits) == UINT32_MAX) {
      /* not valid based on reqs; demote to more compatible type */
      switch (heap) {
      case ZINK_HEAP_DEVICE_LOCAL_VISIBLE:
         heap = ZINK_HEAP_DEVICE_LOCAL;
         break;
      case ZINK_HEAP_HOST_VISIBLE_COHERENT_CACHED:
         heap = ZINK_HEAP_HOST_VISIBLE_COHERENT;
         break;
      default:
         break;
      }
      assert(zink_mem_type_idx_from_types(screen, heap, reqs->memoryTypeBits) != UINT32_MAX);
   }
"""

new = """   if (zink_mem_type_idx_from_types(screen, heap, reqs->memoryTypeBits) == UINT32_MAX) {
      /* not valid based on reqs; demote to more compatible type */
      switch (heap) {
      case ZINK_HEAP_DEVICE_LOCAL_VISIBLE:
         heap = ZINK_HEAP_DEVICE_LOCAL;
         break;
      case ZINK_HEAP_HOST_VISIBLE_COHERENT_CACHED:
         heap = ZINK_HEAP_HOST_VISIBLE_COHERENT;
         break;
      default:
         break;
      }
      if (zink_mem_type_idx_from_types(screen, heap, reqs->memoryTypeBits) == UINT32_MAX) {
         /* last resort: scan all heaps (Venus LAZILY_ALLOCATED depth bufs) */
         for (unsigned h = 0; h < ZINK_HEAP_MAX; h++) {
            if (zink_mem_type_idx_from_types(screen, (enum zink_heap)h, reqs->memoryTypeBits) != UINT32_MAX) {
               heap = (enum zink_heap)h;
               break;
            }
         }
      }
   }
"""

if text.count(old) != 1:
    raise SystemExit("zink_resource allocate_bo demotion anchor not found")
p.write_text(text.replace(old, new, 1))
print("patch 6 applied: all-heap scan before allocation failure")
PY

# ------------------------------------------------------------
# Patch 7: Venus/MoltenVK advertises VK_EXT_host_image_copy for
# depth/stencil formats, but any depth image created with
# VK_IMAGE_USAGE_HOST_TRANSFER_BIT_EXT reports memoryTypeBits == 0
# (no bindable memory), so resource_create fails and Mesa silently
# zeroes the renderbuffer -> depth FBO is INCOMPLETE_ATTACHMENT.
# Do not request host-transfer usage for depth/stencil formats.
# Color formats keep it (works fine). See attempts.md attempt 17.
# ------------------------------------------------------------
RUN python3 - <<'PY'
from pathlib import Path

p = Path("src/gallium/drivers/zink/zink_resource.c")
text = p.read_text()

old = """   if (!(templ->flags & PIPE_RESOURCE_FLAG_SPARSE) &&
       screen->info.have_EXT_host_image_copy &&
       feats & VK_FORMAT_FEATURE_2_HOST_IMAGE_TRANSFER_BIT_EXT)
      usage |= VK_IMAGE_USAGE_HOST_TRANSFER_BIT_EXT;
"""

new = """   if (!(templ->flags & PIPE_RESOURCE_FLAG_SPARSE) &&
       screen->info.have_EXT_host_image_copy &&
       !util_format_is_depth_or_stencil(templ->format) &&
       feats & VK_FORMAT_FEATURE_2_HOST_IMAGE_TRANSFER_BIT_EXT)
      usage |= VK_IMAGE_USAGE_HOST_TRANSFER_BIT_EXT;
"""

if text.count(old) != 1:
    raise SystemExit("zink_resource host-transfer usage anchor not found")
p.write_text(text.replace(old, new, 1))
print("patch 7 applied: skip HOST_TRANSFER usage for depth/stencil")
PY

# ------------------------------------------------------------
# Configure and compile Mesa
# ------------------------------------------------------------
# Keep these compiler fixes local and apply them to the checksum-verified source.
COPY docker/patches/mesa-25.1.9/ /tmp/multiros-mesa-patches/
RUN patch --batch --fuzz=0 -p1 < /tmp/multiros-mesa-patches/0008-moltenvk-shader-io.patch \
    && patch --batch --fuzz=0 -p1 < /tmp/multiros-mesa-patches/0009-moltenvk-resource-names.patch
RUN meson setup build \
    --prefix=/opt/mesa-25.1.9 \
    --libdir=lib \
    -Dplatforms=x11 \
    -Degl=enabled \
    -Dglvnd=true \
    -Degl-native-platform=surfaceless \
    -Dglx=dri \
    -Dgallium-drivers=zink \
    -Dvulkan-drivers= \
    -Dllvm=disabled \
    -Dbuild-tests=false \
    -Dgallium-va=disabled \
    -Dgallium-vdpau=disabled

RUN ninja -C build -j"$(nproc)" \
    && ninja -C build install


# ------------------------------------------------------------
# Stage 2: ROS 2 + custom Mesa 25.1.9 + MuJoCo
# ------------------------------------------------------------

FROM ros:jazzy-ros-base AS runtime
SHELL ["/bin/bash", "-c"]
RUN apt-get update && apt-get install -y --no-install-recommends \
    libegl1 libgl1 libegl-mesa0 libgl1-mesa-dri libosmesa6 \
    mesa-vulkan-drivers libvulkan1 vulkan-tools mesa-utils \
    && rm -rf /var/lib/apt/lists/*
ENV MUJOCO_GL=egl EGL_PLATFORM=surfaceless
COPY checks/check_rendering.py /usr/local/bin/multiros-check-rendering
RUN chmod +x /usr/local/bin/multiros-check-rendering

FROM runtime AS lighter
LABEL org.multiros.mesa.shader-io="screen-scoped-v1" \
      org.multiros.mesa.resource-names="v1"
USER root
COPY --from=mesa-build /opt/mesa-25.1.9 /opt/mesa-25.1.9
COPY docker/patches/mesa-25.1.9/ /usr/share/doc/multiros/mesa-patches/
RUN mkdir -p /usr/local/share/glvnd/egl_vendor.d \
    && printf '%s\n' '{"file_format_version":"1.0.0","ICD":{"library_path":"/opt/mesa-25.1.9/lib/libEGL_mesa.so.0"}}' > /usr/local/share/glvnd/egl_vendor.d/50_zink-mesa.json \
    && sed 's|"library_path": "[^"]*"|"library_path": "/usr/lib/aarch64-linux-gnu/libvulkan_virtio.so"|' /usr/share/vulkan/icd.d/virtio_icd*.json > /tmp/virtio.json \
    && mv /tmp/virtio.json /usr/share/vulkan/icd.d/virtio_icd_abs.json
ENV LD_LIBRARY_PATH=/opt/mesa-25.1.9/lib \
    LIBGL_DRIVERS_PATH=/opt/mesa-25.1.9/lib/dri \
    MESA_LOADER_DRIVER_OVERRIDE=zink GALLIUM_DRIVER=zink \
    ZINK_ALLOW_MISSING_EXT_MEM_FD=1 \
    VK_DRIVER_FILES=/usr/share/vulkan/icd.d/virtio_icd_abs.json \
    __EGL_VENDOR_LIBRARY_FILENAMES=/usr/local/share/glvnd/egl_vendor.d/50_zink-mesa.json \
    MUJOCO_GL=egl PYOPENGL_PLATFORM=egl EGL_PLATFORM=surfaceless
