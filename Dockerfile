# SPDX-FileCopyrightText: 2026 Joe Heffer
# SPDX-License-Identifier: MIT
#
# Build and test toolchain: everything `make lv2 lint test describe vst3
# pluginval clap clap-validate` needs. CI builds this image too, so a new dependency goes here,
# not in .github/workflows/ci.yml. Works with Docker or Podman.
#
#   make container                        build the image, then lv2 lint test in it
#   make container RUN="vst3 pluginval"   any other targets
#
# The repository is bind-mounted at /src rather than copied, so the image
# holds only the toolchain. Bundles built here link against Arch's current
# glibc and may not load on older distributions.
#
# Two things pin the toolchain:
# - the base image digest, which Dependabot bumps;
# - ARCH_SNAPSHOT, a date on the Arch Linux Archive
#   (https://archive.archlinux.org/), so pacman installs the package versions
#   of that day. Bump it by hand to move to a newer Faust.

FROM archlinux:base-devel@sha256:3cbf69d2d5958d6a294f3722c5668e6187c4df8e00fa27f72352f0bf83e495e1

ARG ARCH_SNAPSHOT=2026/10/23
ARG PLUGINVAL_VERSION=v1.0.4
ARG CLAP_VALIDATOR_URL=https://github.com/free-audio/clap-validator/releases/download/0.4.1/clap-validator-0.4.1-127-g152b982-ubuntu-22.04.zip

# git and cmake build VST3 bundles against the VST3 SDK; alsa-lib,
# fontconfig and freetype2 are pluginval's runtime libraries. The
# clap-validator release zip wraps a tarball holding the single binary.
RUN echo "Server = https://archive.archlinux.org/repos/${ARCH_SNAPSHOT}/\$repo/os/\$arch" \
        > /etc/pacman.d/mirrorlist \
 && pacman -Syu --noconfirm --needed \
        faust lv2 lv2lint boost python python-numpy python-matplotlib \
        cmake git unzip alsa-lib fontconfig freetype2 \
 && pacman -Scc --noconfirm \
 && curl -sSfL -o /tmp/pluginval.zip \
        "https://github.com/Tracktion/pluginval/releases/download/${PLUGINVAL_VERSION}/pluginval_Linux.zip" \
 && unzip -q /tmp/pluginval.zip -d /usr/local/bin \
 && rm /tmp/pluginval.zip \
 && curl -sSfL -o /tmp/clap-validator.zip "${CLAP_VALIDATOR_URL}" \
 && unzip -q -d /tmp/clap-validator /tmp/clap-validator.zip \
 && tar -xzf /tmp/clap-validator/*.tar.gz -C /usr/local/bin clap-validator \
 && rm -rf /tmp/clap-validator /tmp/clap-validator.zip \
 && clap-validator --version \
 && faust --version

# faust2lv2 derives its include path from `which faust`; with /usr/sbin first
# on the image's PATH that becomes /usr/sinclude/faust. The container runs as
# the caller's UID, which has no home directory, so HOME points at /tmp for
# matplotlib's and git's caches.
ENV FAUSTINC=/usr/include/faust \
    HOME=/tmp

WORKDIR /src
