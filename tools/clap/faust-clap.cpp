// SPDX-FileCopyrightText: 2026 Joe Heffer
// SPDX-License-Identifier: MIT
// Faust architecture for a CLAP effect, built against the MIT-licensed CLAP
// headers (1.2 or later). See `make clap`.
//
// Written against the plain C API, so a plug-in needs only the CLAP headers
// and the Faust ones: no clap-helpers and no CMake. Extensions: audio-ports,
// params, state and latency. There is no GUI, so hosts show their generic
// parameter editor.
//
// - Every slider, numeric entry, checkbox and button becomes a CLAP parameter,
//   numbered in the order buildUserInterface() reports them. Units come from
//   [unit:...] metadata. Parameter IDs and the state layout therefore follow
//   the control order in the .dsp, which the [n] label prefixes pin down, as
//   in the VST3 architecture (tools/vst3/faust-vst3.cpp).
// - A bargraph tagged [lv2:reportsLatency] is the plug-in's latency.
// - Parameter events are applied at their sample position: the block is split
//   there. The DSP smooths its own controls with si.smoo.
//
// ID, names, version and features come from plugin_meta.h, which
// tools/clap-meta.py generates from the .dsp's declare statements.

#include <algorithm>
#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <string>
#include <vector>

#include "faust/dsp/dsp.h"
#include "faust/gui/UI.h"
#include "faust/gui/meta.h"

<<includeIntrinsic>>

<<includeclass>>

#include <clap/clap.h>

#include "plugin_meta.h"

#if defined(__x86_64__) || defined(_M_X64) || defined(__SSE__)
#include <xmmintrin.h>
#endif

// Flush subnormals to zero while the DSP runs. Decaying filter states would
// otherwise reach subnormal values, which are slow on most CPUs and which
// hosts and validators treat as faulty output.
class NoDenormals {
public:
#if defined(__x86_64__) || defined(_M_X64) || defined(__SSE__)
    NoDenormals() : fSaved(_mm_getcsr()) { _mm_setcsr(fSaved | 0x8040); } // FTZ | DAZ
    ~NoDenormals() { _mm_setcsr(fSaved); }
private:
    unsigned int fSaved;
#elif defined(__aarch64__)
    NoDenormals()
    {
        asm volatile("mrs %0, fpcr" : "=r"(fSaved));
        asm volatile("msr fpcr, %0" : : "r"(fSaved | (1ULL << 24))); // FZ
    }
    ~NoDenormals() { asm volatile("msr fpcr, %0" : : "r"(fSaved)); }
private:
    unsigned long long fSaved;
#endif
};

// Collects the Faust controls. Metadata arrives through declare() before the
// widget it belongs to, so it is buffered until the next add*() call.
struct ControlCollector : public UI {
    struct Control {
        std::string label, unit;
        FAUSTFLOAT* zone;
        FAUSTFLOAT init, min, max;
        bool toggle;
    };
    std::vector<Control> controls;
    FAUSTFLOAT* latency = nullptr;

    std::string pendingUnit;
    bool pendingLatency = false;

    void openTabBox(const char*) override {}
    void openHorizontalBox(const char*) override {}
    void openVerticalBox(const char*) override {}
    void closeBox() override {}

    void addButton(const char* label, FAUSTFLOAT* zone) override { add(label, zone, 0, 0, 1, true); }
    void addCheckButton(const char* label, FAUSTFLOAT* zone) override { add(label, zone, 0, 0, 1, true); }
    void addVerticalSlider(const char* label, FAUSTFLOAT* zone, FAUSTFLOAT init, FAUSTFLOAT min,
                           FAUSTFLOAT max, FAUSTFLOAT) override
    {
        add(label, zone, init, min, max, false);
    }
    void addHorizontalSlider(const char* label, FAUSTFLOAT* zone, FAUSTFLOAT init, FAUSTFLOAT min,
                             FAUSTFLOAT max, FAUSTFLOAT) override
    {
        add(label, zone, init, min, max, false);
    }
    void addNumEntry(const char* label, FAUSTFLOAT* zone, FAUSTFLOAT init, FAUSTFLOAT min,
                     FAUSTFLOAT max, FAUSTFLOAT) override
    {
        add(label, zone, init, min, max, false);
    }

    void addHorizontalBargraph(const char*, FAUSTFLOAT* zone, FAUSTFLOAT, FAUSTFLOAT) override { bargraph(zone); }
    void addVerticalBargraph(const char*, FAUSTFLOAT* zone, FAUSTFLOAT, FAUSTFLOAT) override { bargraph(zone); }
    void addSoundfile(const char*, const char*, Soundfile**) override {}

    void declare(FAUSTFLOAT*, const char* key, const char* val) override
    {
        if (std::strcmp(key, "unit") == 0) pendingUnit = val;
        if (std::strcmp(key, "lv2") == 0 && std::strcmp(val, "reportsLatency") == 0) pendingLatency = true;
    }

    void add(const char* label, FAUSTFLOAT* zone, FAUSTFLOAT init, FAUSTFLOAT min, FAUSTFLOAT max, bool toggle)
    {
        controls.push_back({label, pendingUnit, zone, init, min, max, toggle});
        pendingUnit.clear();
        pendingLatency = false;
    }

    void bargraph(FAUSTFLOAT* zone)
    {
        if (pendingLatency) latency = zone;
        pendingUnit.clear();
        pendingLatency = false;
    }
};

// The last slot but one is filled with "mono" or "stereo" by entryInit(),
// once the DSP's channel count is known.
static const char* gFeatures[] = {FX_FEATURES, nullptr, nullptr};
static constexpr size_t kChannelFeature = sizeof(gFeatures) / sizeof(gFeatures[0]) - 2;

static const clap_plugin_descriptor_t gDescriptor = {
    CLAP_VERSION_INIT, FX_ID, FX_NAME, FX_VENDOR, FX_URL, "", "", FX_VERSION, FX_DESCRIPTION, gFeatures,
};

// The plug-in instance. The CLAP callbacks below reach it through
// plugin_data, so its members are public.
struct FaustEffect {
    explicit FaustEffect(const clap_host_t* host) : fHost(host)
    {
        fPlugin.desc = &gDescriptor;
        fPlugin.plugin_data = this;
        fPlugin.init = [](const clap_plugin_t* p) { return self(p)->init(); };
        fPlugin.destroy = [](const clap_plugin_t* p) { delete self(p); };
        fPlugin.activate = [](const clap_plugin_t* p, double sampleRate, uint32_t, uint32_t) {
            self(p)->resetDSP(int(sampleRate));
            return true;
        };
        fPlugin.deactivate = [](const clap_plugin_t*) {};
        fPlugin.start_processing = [](const clap_plugin_t*) { return true; };
        fPlugin.stop_processing = [](const clap_plugin_t*) {};
        fPlugin.reset = [](const clap_plugin_t* p) { self(p)->fDSP.instanceClear(); };
        fPlugin.process = [](const clap_plugin_t* p, const clap_process_t* process) {
            return self(p)->process(process);
        };
        fPlugin.get_extension = [](const clap_plugin_t* p, const char* id) { return self(p)->extension(id); };
        fPlugin.on_main_thread = [](const clap_plugin_t*) {};
    }

    clap_plugin_t fPlugin;
    const clap_host_t* fHost;
    const clap_host_params_t* fHostParams = nullptr;
    mydsp fDSP;
    ControlCollector fUI;
    std::vector<FAUSTFLOAT*> fIn, fOut;
    uint32_t fLatency = 0;

    static FaustEffect* self(const clap_plugin_t* p) { return static_cast<FaustEffect*>(p->plugin_data); }

    bool init()
    {
        fDSP.buildUserInterface(&fUI);
        fIn.resize(size_t(fDSP.getNumInputs()));
        fOut.resize(size_t(fDSP.getNumOutputs()));
        fHostParams = static_cast<const clap_host_params_t*>(fHost->get_extension(fHost, CLAP_EXT_PARAMS));
        // Sets every control to its default, so the parameters can be read
        // before the host activates the plug-in.
        fDSP.init(48000);
        return true;
    }

    // init() resets every control to its default and clears the state. The
    // latency bargraph is only written by compute(), so one sample of silence
    // is run to read it, then the state is cleared again and the host's
    // parameter values are put back.
    void resetDSP(int sampleRate)
    {
        std::vector<FAUSTFLOAT> values;
        for (const auto& c : fUI.controls) values.push_back(*c.zone);
        fDSP.init(sampleRate);
        if (fUI.latency) {
            std::vector<FAUSTFLOAT> silence(size_t(fDSP.getNumInputs() + fDSP.getNumOutputs()), 0);
            std::vector<FAUSTFLOAT*> ptrs;
            for (auto& x : silence) ptrs.push_back(&x);
            NoDenormals ftz;
            fDSP.compute(1, ptrs.data(), ptrs.data() + fDSP.getNumInputs());
            fLatency = uint32_t(std::lround(std::fmax(0.0, *fUI.latency)));
            fDSP.instanceClear();
        }
        for (size_t i = 0; i < values.size(); ++i) *fUI.controls[i].zone = values[i];
    }

    clap_process_status process(const clap_process_t* p)
    {
        const uint32_t numIn = uint32_t(fIn.size()), numOut = uint32_t(fOut.size());
        if (p->audio_outputs_count < 1 || p->audio_outputs[0].channel_count < numOut || !p->audio_outputs[0].data32)
            return CLAP_PROCESS_ERROR;
        if (numIn > 0 && (p->audio_inputs_count < 1 || p->audio_inputs[0].channel_count < numIn ||
                        !p->audio_inputs[0].data32))
            return CLAP_PROCESS_ERROR;

        NoDenormals ftz;
        const clap_input_events_t* events = p->in_events;
        const uint32_t numEvents = events ? events->size(events) : 0;
        uint32_t ev = 0;
        for (uint32_t pos = 0; pos < p->frames_count;) {
            uint32_t next = p->frames_count;
            for (; ev < numEvents; ++ev) {
                const clap_event_header_t* hdr = events->get(events, ev);
                if (hdr->time > pos) {
                    next = std::min(hdr->time, p->frames_count);
                    break;
                }
                applyEvent(hdr);
            }
            for (uint32_t c = 0; c < numIn; ++c) fIn[c] = p->audio_inputs[0].data32[c] + pos;
            for (uint32_t c = 0; c < numOut; ++c) fOut[c] = p->audio_outputs[0].data32[c] + pos;
            fDSP.compute(int(next - pos), fIn.data(), fOut.data());
            pos = next;
        }
        for (; ev < numEvents; ++ev) applyEvent(events->get(events, ev)); // timed at or past the block end

        // The DSP keeps ringing (filters, latency) after the input falls
        // silent, so the output is never flagged constant.
        p->audio_outputs[0].constant_mask = 0;
        return CLAP_PROCESS_CONTINUE;
    }

    void applyEvent(const clap_event_header_t* hdr)
    {
        if (hdr->space_id != CLAP_CORE_EVENT_SPACE_ID || hdr->type != CLAP_EVENT_PARAM_VALUE) return;
        const auto* ev = reinterpret_cast<const clap_event_param_value_t*>(hdr);
        if (ev->param_id >= fUI.controls.size()) return;
        const auto& c = fUI.controls[ev->param_id];
        *c.zone = FAUSTFLOAT(std::fmin(std::fmax(ev->value, c.min), c.max));
    }

    const void* extension(const char* id);

    // One main audio port each way, with the DSP's own channel count.
    uint32_t channels(bool isInput) const { return uint32_t(isInput ? fIn.size() : fOut.size()); }
};

// The ports are not an in-place pair: Faust's generated code may write an
// output before it has read every input.
static constexpr clap_plugin_audio_ports_t kAudioPorts = {
    [](const clap_plugin_t* p, bool isInput) -> uint32_t { return FaustEffect::self(p)->channels(isInput) > 0 ? 1 : 0; },
    [](const clap_plugin_t* p, uint32_t index, bool isInput, clap_audio_port_info_t* info) {
        const uint32_t n = FaustEffect::self(p)->channels(isInput);
        if (index != 0 || n == 0) return false;
        info->id = 0;
        std::snprintf(info->name, sizeof(info->name), "%s", isInput ? "Input" : "Output");
        info->flags = CLAP_AUDIO_PORT_IS_MAIN;
        info->channel_count = n;
        info->port_type = n == 1 ? CLAP_PORT_MONO : n == 2 ? CLAP_PORT_STEREO : nullptr;
        info->in_place_pair = CLAP_INVALID_ID;
        return true;
    },
};

static constexpr clap_plugin_params_t kParams = {
    [](const clap_plugin_t* p) { return uint32_t(FaustEffect::self(p)->fUI.controls.size()); },
    [](const clap_plugin_t* p, uint32_t index, clap_param_info_t* info) {
        const auto& controls = FaustEffect::self(p)->fUI.controls;
        if (index >= controls.size()) return false;
        const auto& c = controls[index];
        info->id = index;
        info->flags = CLAP_PARAM_IS_AUTOMATABLE | (c.toggle ? CLAP_PARAM_IS_STEPPED : 0);
        info->cookie = nullptr;
        std::snprintf(info->name, sizeof(info->name), "%s", c.label.c_str());
        info->module[0] = '\0';
        info->min_value = c.min;
        info->max_value = c.max;
        info->default_value = c.init;
        return true;
    },
    [](const clap_plugin_t* p, clap_id id, double* value) {
        const auto& controls = FaustEffect::self(p)->fUI.controls;
        if (id >= controls.size()) return false;
        *value = *controls[id].zone;
        return true;
    },
    [](const clap_plugin_t* p, clap_id id, double value, char* text, uint32_t size) {
        const auto& controls = FaustEffect::self(p)->fUI.controls;
        if (id >= controls.size()) return false;
        const auto& c = controls[id];
        if (c.toggle)
            std::snprintf(text, size, "%s", value >= 0.5 ? "On" : "Off");
        else if (c.unit.empty())
            std::snprintf(text, size, "%.2f", value);
        else
            std::snprintf(text, size, "%.2f %s", value, c.unit.c_str());
        return true;
    },
    [](const clap_plugin_t* p, clap_id id, const char* text, double* value) {
        const auto& controls = FaustEffect::self(p)->fUI.controls;
        if (id >= controls.size()) return false;
        if (controls[id].toggle && std::strcmp(text, "On") == 0) *value = 1;
        else if (controls[id].toggle && std::strcmp(text, "Off") == 0) *value = 0;
        else {
            // Any unit after the number is ignored.
            char* end;
            *value = std::strtod(text, &end);
            if (end == text) return false;
        }
        return true;
    },
    [](const clap_plugin_t* p, const clap_input_events_t* in, const clap_output_events_t*) {
        for (uint32_t i = 0, n = in->size(in); i < n; ++i) FaustEffect::self(p)->applyEvent(in->get(in, i));
    },
};

// State: format version, control count, then each control's plain value
// in parameter order, as native-endian 32-bit values.
static constexpr int32_t kStateVersion = 1;

static bool writeAll(const clap_ostream_t* s, const void* data, size_t size)
{
    for (auto* b = static_cast<const char*>(data); size > 0;) {
        int64_t n = s->write(s, b, size);
        if (n <= 0) return false;
        b += n;
        size -= size_t(n);
    }
    return true;
}

static bool readAll(const clap_istream_t* s, void* data, size_t size)
{
    for (auto* b = static_cast<char*>(data); size > 0;) {
        int64_t n = s->read(s, b, size);
        if (n <= 0) return false;
        b += n;
        size -= size_t(n);
    }
    return true;
}

static constexpr clap_plugin_state_t kState = {
    [](const clap_plugin_t* p, const clap_ostream_t* s) {
        const auto& controls = FaustEffect::self(p)->fUI.controls;
        const int32_t header[2] = {kStateVersion, int32_t(controls.size())};
        if (!writeAll(s, header, sizeof(header))) return false;
        for (const auto& c : controls) {
            const float v = float(*c.zone);
            if (!writeAll(s, &v, sizeof(v))) return false;
        }
        return true;
    },
    [](const clap_plugin_t* p, const clap_istream_t* s) {
        FaustEffect* fx = FaustEffect::self(p);
        int32_t header[2];
        if (!readAll(s, header, sizeof(header)) || header[0] != kStateVersion || header[1] < 0) return false;
        for (int32_t i = 0; i < header[1]; ++i) {
            float v;
            if (!readAll(s, &v, sizeof(v))) return false;
            if (size_t(i) >= fx->fUI.controls.size()) continue; // saved by a newer build with more controls
            const auto& c = fx->fUI.controls[size_t(i)];
            *c.zone = FAUSTFLOAT(std::fmin(std::fmax(v, c.min), c.max));
        }
        if (fx->fHostParams) fx->fHostParams->rescan(fx->fHost, CLAP_PARAM_RESCAN_VALUES);
        return true;
    },
};

static constexpr clap_plugin_latency_t kLatency = {
    [](const clap_plugin_t* p) { return FaustEffect::self(p)->fLatency; },
};


const void* FaustEffect::extension(const char* id)
{
    if (std::strcmp(id, CLAP_EXT_AUDIO_PORTS) == 0) return &kAudioPorts;
    if (std::strcmp(id, CLAP_EXT_PARAMS) == 0) return &kParams;
    if (std::strcmp(id, CLAP_EXT_STATE) == 0) return &kState;
    if (std::strcmp(id, CLAP_EXT_LATENCY) == 0) return &kLatency;
    return nullptr;
}


static bool entryInit(const char*)
{
    mydsp dsp;
    const int n = dsp.getNumOutputs();
    gFeatures[kChannelFeature] = n == 1 ? CLAP_PLUGIN_FEATURE_MONO : n == 2 ? CLAP_PLUGIN_FEATURE_STEREO : nullptr;
    return true;
}

static constexpr clap_plugin_factory_t gFactory = {
    [](const clap_plugin_factory_t*) -> uint32_t { return 1; },
    [](const clap_plugin_factory_t*, uint32_t index) { return index == 0 ? &gDescriptor : nullptr; },
    [](const clap_plugin_factory_t*, const clap_host_t* host, const char* id) -> const clap_plugin_t* {
        if (!clap_version_is_compatible(host->clap_version) || std::strcmp(id, gDescriptor.id) != 0)
            return nullptr;
        return &(new FaustEffect(host))->fPlugin;
    },
};

extern "C" CLAP_EXPORT const clap_plugin_entry_t clap_entry = {
    CLAP_VERSION_INIT,
    entryInit,
    [] {},
    [](const char* id) -> const void* { return std::strcmp(id, CLAP_PLUGIN_FACTORY_ID) == 0 ? &gFactory : nullptr; },
};
