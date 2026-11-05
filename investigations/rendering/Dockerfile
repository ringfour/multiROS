# syntax=docker/dockerfile:1
# Isolated experiment: leave the working multiROS and robot images untouched.
ARG MESA_BUILDER_IMAGE=multiros:mesa-builder
ARG RENDER_TEST_IMAGE=xlerobot:jazzy-lighter
FROM ${MESA_BUILDER_IMAGE} AS mesa-fix
COPY investigations/rendering/patches/moltenvk-shader-io.patch /tmp/shader-io.patch
WORKDIR /build/mesa-25.1.9
RUN patch -p1 < /tmp/shader-io.patch
RUN ninja -C build -j2 && ninja -C build install
FROM ${RENDER_TEST_IMAGE}
COPY --from=mesa-fix /opt/mesa-25.1.9 /opt/mesa-25.1.9
ENV MESA_SHADER_CACHE_DISABLE=true
