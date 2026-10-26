// SPDX-FileCopyrightText: 2026 Joe Heffer
// SPDX-License-Identifier: MIT
// Checks a CLAP plug-in's factory presets, acting as a minimal host. Run by
// `make clap-validate`, which compiles this file once per effect against that
// effect's presets.h (tools/presets.py), so the expected values come from the
// same table the plug-in was built from.
//
// Usage: check-presets <effect.clap>
//
// It crawls the preset discovery factory, then creates the plug-in and loads
// every preset through preset-load, and fails unless:
// - the plug-in lists exactly the presets in presets.h, by name, in order,
//   each for this plug-in's ID;
// - loading each one sets every parameter to its value in presets.h, and
//   calls the host's `loaded` callback and a parameter rescan;
// - an unknown load key is refused and reported through `on_error`.
// An effect without presets must offer neither the factory nor preset-load.
//
// clap-validator's own preset-discovery-crawl and preset-discovery-load
// tests cannot be used: its metadata receiver deadlocks on the second preset
// of a container (see the clap-validate target in the Makefile).

#include <clap/clap.h>
#include <dlfcn.h>

#include <cmath>
#include <cstdio>
#include <cstring>
#include <string>
#include <vector>

#include "presets.h"

static int gFailures = 0;

static void check(bool ok, const std::string& what)
{
    std::printf("  %s %s\n", ok ? "PASS" : "FAIL", what.c_str());
    if (!ok) ++gFailures;
}

struct Found {
    std::string name, key, pluginId;
};

static std::vector<Found> gFound;
static std::vector<clap_preset_discovery_location_t> gLocations;
static int gLoaded = 0, gRescans = 0, gErrors = 0;

int main(int argc, char** argv)
{
    if (argc != 2) {
        std::fprintf(stderr, "usage: %s <effect.clap>\n", argv[0]);
        return 2;
    }
    void* library = dlopen(argv[1], RTLD_NOW | RTLD_LOCAL);
    if (!library) {
        std::fprintf(stderr, "%s\n", dlerror());
        return 1;
    }
    const auto* entry = static_cast<const clap_plugin_entry_t*>(dlsym(library, "clap_entry"));
    if (!entry || !entry->init(argv[1])) {
        std::fprintf(stderr, "%s: no usable clap_entry\n", argv[1]);
        return 1;
    }
    const auto* factory = static_cast<const clap_plugin_factory_t*>(entry->get_factory(CLAP_PLUGIN_FACTORY_ID));
    const char* pluginId = factory->get_plugin_descriptor(factory, 0)->id;
    std::printf("%s: %u factory preset(s)\n", argv[1], kNumPresets);

    // Crawl.
    const auto* presetFactory =
        static_cast<const clap_preset_discovery_factory_t*>(entry->get_factory(CLAP_PRESET_DISCOVERY_FACTORY_ID));
    check((presetFactory != nullptr) == (kNumPresets > 0), "preset discovery factory offered iff there are presets");
    if (presetFactory) {
        clap_preset_discovery_indexer_t indexer = {};
        indexer.clap_version = CLAP_VERSION;
        indexer.name = "check-presets";
        indexer.declare_filetype = [](const clap_preset_discovery_indexer_t*,
                                      const clap_preset_discovery_filetype_t*) { return true; };
        indexer.declare_location = [](const clap_preset_discovery_indexer_t*,
                                      const clap_preset_discovery_location_t* location) {
            gLocations.push_back(*location);
            return true;
        };
        indexer.declare_soundpack = [](const clap_preset_discovery_indexer_t*,
                                       const clap_preset_discovery_soundpack_t*) { return true; };
        indexer.get_extension = [](const clap_preset_discovery_indexer_t*, const char*) -> const void* {
            return nullptr;
        };

        clap_preset_discovery_metadata_receiver_t receiver = {};
        receiver.on_error = [](const clap_preset_discovery_metadata_receiver_t*, int32_t, const char* msg) {
            std::printf("  metadata error: %s\n", msg);
            ++gErrors;
        };
        receiver.begin_preset = [](const clap_preset_discovery_metadata_receiver_t*, const char* name,
                                   const char* key) {
            gFound.push_back({name ? name : "", key ? key : "", ""});
            return true;
        };
        receiver.add_plugin_id = [](const clap_preset_discovery_metadata_receiver_t*,
                                    const clap_universal_plugin_id_t* id) {
            if (!gFound.empty() && std::strcmp(id->abi, "clap") == 0) gFound.back().pluginId = id->id;
        };
        receiver.set_soundpack_id = [](const clap_preset_discovery_metadata_receiver_t*, const char*) {};
        receiver.set_flags = [](const clap_preset_discovery_metadata_receiver_t*, uint32_t) {};
        receiver.add_creator = [](const clap_preset_discovery_metadata_receiver_t*, const char*) {};
        receiver.set_description = [](const clap_preset_discovery_metadata_receiver_t*, const char*) {};
        receiver.set_timestamps = [](const clap_preset_discovery_metadata_receiver_t*, clap_timestamp,
                                     clap_timestamp) {};
        receiver.add_feature = [](const clap_preset_discovery_metadata_receiver_t*, const char*) {};
        receiver.add_extra_info = [](const clap_preset_discovery_metadata_receiver_t*, const char*, const char*) {};

        for (uint32_t i = 0; i < presetFactory->count(presetFactory); ++i) {
            const auto* desc = presetFactory->get_descriptor(presetFactory, i);
            const auto* provider = presetFactory->create(presetFactory, &indexer, desc->id);
            check(provider && provider->init(provider), std::string("provider ") + desc->id + " initialises");
            if (!provider) continue;
            for (const auto& location : gLocations)
                check(provider->get_metadata(provider, location.kind, location.location, &receiver),
                      std::string("location '") + location.name + "' crawls");
            provider->destroy(provider);
        }
        check(gErrors == 0, "no metadata errors");
        check(gFound.size() == kNumPresets, std::to_string(gFound.size()) + " preset(s) found");
        for (size_t i = 0; i < gFound.size() && i < kNumPresets; ++i)
            check(gFound[i].name == kPresets[i].name && gFound[i].pluginId == pluginId,
                  "'" + gFound[i].name + "' listed for " + pluginId);
    }

    // Load.
    static clap_host_params_t hostParams = {};
    hostParams.rescan = [](const clap_host_t*, clap_param_rescan_flags) { ++gRescans; };
    hostParams.clear = [](const clap_host_t*, clap_id, clap_param_clear_flags) {};
    hostParams.request_flush = [](const clap_host_t*) {};
    static clap_host_preset_load_t hostPresetLoad = {};
    hostPresetLoad.on_error = [](const clap_host_t*, uint32_t, const char*, const char*, int32_t, const char*) {
        ++gErrors;
    };
    hostPresetLoad.loaded = [](const clap_host_t*, uint32_t, const char*, const char*) { ++gLoaded; };
    clap_host_t host = {};
    host.clap_version = CLAP_VERSION;
    host.name = "check-presets";
    host.vendor = host.url = "";
    host.version = "1";
    host.get_extension = [](const clap_host_t*, const char* id) -> const void* {
        if (std::strcmp(id, CLAP_EXT_PARAMS) == 0) return &hostParams;
        if (std::strcmp(id, CLAP_EXT_PRESET_LOAD) == 0) return &hostPresetLoad;
        return nullptr;
    };
    host.request_restart = host.request_process = host.request_callback = [](const clap_host_t*) {};

    const clap_plugin_t* plugin = factory->create_plugin(factory, &host, pluginId);
    plugin->init(plugin);
    const auto* params = static_cast<const clap_plugin_params_t*>(plugin->get_extension(plugin, CLAP_EXT_PARAMS));
    const auto* presetLoad =
        static_cast<const clap_plugin_preset_load_t*>(plugin->get_extension(plugin, CLAP_EXT_PRESET_LOAD));
    check((presetLoad != nullptr) == (kNumPresets > 0), "preset-load offered iff there are presets");
    if (presetLoad) {
        check(params->count(plugin) == kNumPresetControls, "parameter count matches presets.h");
        for (const auto& found : gFound) {
            const unsigned index = unsigned(std::stoul(found.key));
            const int loaded = gLoaded, rescans = gRescans;
            bool ok = index < kNumPresets &&
                      presetLoad->from_location(plugin, CLAP_PRESET_DISCOVERY_LOCATION_PLUGIN, nullptr,
                                                found.key.c_str());
            for (uint32_t i = 0; ok && i < kNumPresetControls; ++i) {
                clap_param_info_t info;
                double value;
                ok = params->get_info(plugin, i, &info) && params->get_value(plugin, info.id, &value) &&
                     std::fabs(value - kPresets[index].values[i]) < 1e-6;
            }
            check(ok && gLoaded == loaded + 1 && gRescans == rescans + 1,
                  "'" + found.name + "' loads and sets every parameter");
        }
        const int errors = gErrors;
        check(!presetLoad->from_location(plugin, CLAP_PRESET_DISCOVERY_LOCATION_PLUGIN, nullptr, "999999") &&
                  gErrors == errors + 1,
              "an unknown load key is refused and reported");
    }
    plugin->destroy(plugin);
    entry->deinit();
    return gFailures ? 1 : 0;
}
