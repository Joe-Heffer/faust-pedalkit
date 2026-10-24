# SPDX-FileCopyrightText: 2026 Joe Heffer
# SPDX-License-Identifier: MIT
# Builds one Faust effect as a VST3 bundle. Driven by `make vst3`, which
# passes:
#   FX_NAME       effect (file) name, e.g. bassdrive -> bassdrive.vst3
#   FX_VERSION    major.minor.micro from `declare version`
#   FX_GEN_DIR    directory holding <name>.cpp (faust -a faust-vst3.cpp)
#                 and plugin_meta.h (tools/vst3-meta.py)
#   FAUST_INC     faust --includedir
#   VST3_SDK_DIR  checkout of github.com/steinbergmedia/vst3sdk

cmake_minimum_required(VERSION 3.25)

# Only the libraries and the validator are needed from the SDK: no example
# plug-ins or hosts (which pull in VSTGUI, X11, GTK and JACK), and no
# symlink into ~/.vst3. The validator runs on the bundle after each build.
set(SMTG_ENABLE_VST3_PLUGIN_EXAMPLES OFF CACHE BOOL "" FORCE)
set(SMTG_ENABLE_VST3_HOSTING_EXAMPLES OFF CACHE BOOL "" FORCE)
set(SMTG_ENABLE_VSTGUI_SUPPORT OFF CACHE BOOL "" FORCE)
set(SMTG_CREATE_PLUGIN_LINK OFF CACHE BOOL "" FORCE)
set(SMTG_RUN_VST_VALIDATOR ON CACHE BOOL "" FORCE)

project(pedalkit-${FX_NAME} VERSION ${FX_VERSION})

# The layout of the SDK's own plug-in project template.
set(vst3sdk_SOURCE_DIR ${VST3_SDK_DIR})
add_subdirectory(${vst3sdk_SOURCE_DIR} ${PROJECT_BINARY_DIR}/vst3sdk)
smtg_enable_vst3_sdk()

smtg_add_vst3plugin(${FX_NAME}
    ${FX_GEN_DIR}/${FX_NAME}.cpp
    ${vst3sdk_SOURCE_DIR}/public.sdk/source/vst/vstsinglecomponenteffect.cpp
)
target_compile_features(${FX_NAME} PRIVATE cxx_std_17)
target_include_directories(${FX_NAME} PRIVATE ${FX_GEN_DIR} ${FAUST_INC})
target_link_libraries(${FX_NAME} PRIVATE sdk)
# The SDK turns on -Wsuggest-override, which Faust's generated class trips.
if(CMAKE_CXX_COMPILER_ID MATCHES "GNU|Clang")
    target_compile_options(${FX_NAME} PRIVATE -Wno-suggest-override)
endif()
