// SPDX-FileCopyrightText: 2026 Joe Heffer
// SPDX-License-Identifier: MIT
// Faust architecture for a VST3 effect, built against the MIT-licensed
// VST3 SDK (3.8 or later). See tools/vst3/CMakeLists.txt and `make vst3`.
//
// One effect is one Steinberg::Vst::SingleComponentEffect: processor and
// edit controller in a single class, with the host's generic editor (no GUI).
//
// - Every slider, numeric entry, checkbox and button becomes a VST3 parameter,
//   numbered in the order buildUserInterface() reports them. Units come from
//   [unit:...] metadata. Parameter IDs and the state layout therefore follow
//   the control order in the .dsp, which the [n] label prefixes pin down.
// - A bargraph tagged [lv2:reportsLatency] is the plug-in's latency.
// - Parameter changes are applied once per block (last point of each queue);
//   the DSP smooths its own controls with si.smoo.
// - Factory presets (src/<name>.presets.toml) are compiled in as the root
//   unit's program list. Its program-change parameter has the fixed ID
//   kProgramListId, well clear of the control IDs, and is not part of the
//   saved state. Effects without presets have neither.
//
// Names, version, category and class ID come from plugin_meta.h, which
// tools/vst3-meta.py generates from the .dsp's declare statements. The
// presets come from presets.h, which tools/presets.py generates.

#include <cmath>
#include <cstring>
#include <string>
#include <vector>

#include "faust/dsp/dsp.h"
#include "faust/gui/UI.h"
#include "faust/gui/meta.h"

<<includeIntrinsic>>

<<includeclass>>

#include "base/source/fstreamer.h"
#include "pluginterfaces/base/ibstream.h"
#include "pluginterfaces/vst/ivstparameterchanges.h"
#include "public.sdk/source/main/pluginfactory.h"
#include "public.sdk/source/vst/utility/stringconvert.h"
#include "public.sdk/source/vst/vstsinglecomponenteffect.h"

#include "plugin_meta.h"
#include "presets.h"

#if defined(__x86_64__) || defined(_M_X64) || defined(__SSE__)
#include <xmmintrin.h>
#endif

using namespace Steinberg;
using namespace Steinberg::Vst;

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

class FaustEffect : public SingleComponentEffect
{
public:
    static FUnknown* createInstance(void*) { return static_cast<IAudioProcessor*>(new FaustEffect); }

    tresult PLUGIN_API initialize(FUnknown* context) SMTG_OVERRIDE
    {
        tresult result = SingleComponentEffect::initialize(context);
        if (result != kResultOk) return result;

        if (!arrangementFor(fDSP.getNumInputs(), fIn) || !arrangementFor(fDSP.getNumOutputs(), fOut))
            return kResultFalse;
        addAudioInput(STR16("Input"), fIn);
        addAudioOutput(STR16("Output"), fOut);

        fDSP.buildUserInterface(&fUI);
        for (size_t i = 0; i < fUI.controls.size(); ++i) {
            const auto& c = fUI.controls[i];
            auto title = StringConvert::convert(c.label);
            auto unit = StringConvert::convert(c.unit);
            auto* p = new RangeParameter(reinterpret_cast<const TChar*>(title.c_str()), ParamID(i),
                                         reinterpret_cast<const TChar*>(unit.c_str()), c.min, c.max, c.init,
                                         c.toggle ? 1 : kStepCountContinuous, ParameterInfo::kCanAutomate);
            p->setPrecision(2);
            parameters.addParameter(p);
        }

        if (kNumPresets > 0 && fUI.controls.size() == kNumPresetControls) {
            addUnit(new Unit(STR16("Root"), kRootUnitId, kNoParentUnitId, kProgramListId));
            auto* list = new ProgramList(STR16("Factory Presets"), kProgramListId, kRootUnitId);
            for (unsigned i = 0; i < kNumPresets; ++i) {
                auto name = StringConvert::convert(kPresets[i].name);
                list->addProgram(reinterpret_cast<const TChar*>(name.c_str()));
            }
            addProgramList(list);
            parameters.addParameter(list->getParameter());
        }

        resetDSP(44100);
        return kResultOk;
    }

    tresult PLUGIN_API setBusArrangements(SpeakerArrangement* inputs, int32 numIns, SpeakerArrangement* outputs,
                                          int32 numOuts) SMTG_OVERRIDE
    {
        // Only the DSP's own channel layout is offered.
        if (numIns == 1 && numOuts == 1 && inputs[0] == fIn && outputs[0] == fOut) return kResultTrue;
        return kResultFalse;
    }

    tresult PLUGIN_API canProcessSampleSize(int32 symbolicSampleSize) SMTG_OVERRIDE
    {
        return symbolicSampleSize == kSample32 ? kResultTrue : kResultFalse;
    }

    tresult PLUGIN_API setupProcessing(ProcessSetup& setup) SMTG_OVERRIDE
    {
        resetDSP(int(setup.sampleRate));
        return SingleComponentEffect::setupProcessing(setup);
    }

    tresult PLUGIN_API setActive(TBool state) SMTG_OVERRIDE
    {
        if (state) fDSP.instanceClear();
        return kResultOk;
    }

    uint32 PLUGIN_API getLatencySamples() SMTG_OVERRIDE { return fLatency; }

    tresult PLUGIN_API process(ProcessData& data) SMTG_OVERRIDE
    {
        if (IParameterChanges* changes = data.inputParameterChanges) {
            for (int32 i = 0; i < changes->getParameterCount(); ++i) {
                IParamValueQueue* queue = changes->getParameterData(i);
                if (!queue || queue->getPointCount() <= 0) continue;
                int32 offset;
                ParamValue value;
                if (queue->getPoint(queue->getPointCount() - 1, offset, value) != kResultTrue) continue;
                if (queue->getParameterId() == ParamID(kProgramListId)) applyPreset(value);
                else applyNormalized(queue->getParameterId(), value);
            }
        }

        if (data.numSamples <= 0 || data.numOutputs == 0) return kResultOk;

        // The DSP keeps ringing (filters, latency) after the input falls
        // silent, so silence flags on the input are not passed through.
        FAUSTFLOAT** in = data.numInputs > 0 ? data.inputs[0].channelBuffers32 : nullptr;
        FAUSTFLOAT** out = data.outputs[0].channelBuffers32;
        if (fDSP.getNumInputs() > 0 && !in) return kResultFalse;
        NoDenormals ftz;
        fDSP.compute(data.numSamples, in, out);
        data.outputs[0].silenceFlags = 0;
        return kResultOk;
    }

    // State: format version, control count, then each control's plain value
    // in parameter order.
    tresult PLUGIN_API getState(IBStream* state) SMTG_OVERRIDE
    {
        IBStreamer s(state, kLittleEndian);
        s.writeInt32(kStateVersion);
        s.writeInt32(int32(fUI.controls.size()));
        for (size_t i = 0; i < fUI.controls.size(); ++i)
            s.writeFloat(float(plainOf(ParamID(i))));
        return kResultOk;
    }

    // Choosing a factory preset sets every control's parameter to its value.
    tresult PLUGIN_API setParamNormalized(ParamID tag, ParamValue value) SMTG_OVERRIDE
    {
        tresult result = SingleComponentEffect::setParamNormalized(tag, value);
        if (result != kResultOk || tag != ParamID(kProgramListId)) return result;
        const unsigned index = presetIndex(value);
        if (index >= kNumPresets) return result;
        for (size_t i = 0; i < kNumPresetControls; ++i) {
            Parameter* p = parameters.getParameter(ParamID(i));
            const ParamValue norm = p->toNormalized(kPresets[index].values[i]);
            SingleComponentEffect::setParamNormalized(ParamID(i), norm);
            applyNormalized(ParamID(i), norm);
        }
        if (componentHandler) componentHandler->restartComponent(kParamValuesChanged);
        return result;
    }

    tresult PLUGIN_API setState(IBStream* state) SMTG_OVERRIDE
    {
        IBStreamer s(state, kLittleEndian);
        int32 version = 0, count = 0;
        if (!s.readInt32(version) || version != kStateVersion || !s.readInt32(count)) return kResultFalse;
        for (int32 i = 0; i < count; ++i) {
            float plain;
            if (!s.readFloat(plain)) return kResultFalse;
            if (size_t(i) >= fUI.controls.size()) continue; // saved by a newer build with more controls
            Parameter* p = parameters.getParameter(ParamID(i));
            ParamValue norm = p->toNormalized(plain);
            setParamNormalized(ParamID(i), norm);
            applyNormalized(ParamID(i), norm);
        }
        return kResultOk;
    }

private:
    static constexpr int32 kStateVersion = 1;
    // ID of the factory preset list and of its program-change parameter.
    // Chosen far above the control IDs (0, 1, 2, ...) so that adding controls
    // never collides with it. Hosts save it in projects, so it must not change.
    static constexpr ProgramListID kProgramListId = 0x10000;

    // Normalised program-change value -> preset index (kNumPresets if none).
    unsigned presetIndex(ParamValue norm)
    {
        Parameter* p = parameters.getParameter(ParamID(kProgramListId));
        if (!p) return kNumPresets;
        return unsigned(std::lround(p->toPlain(norm)));
    }

    // Audio side of a preset change: write the values straight to the DSP.
    void applyPreset(ParamValue norm)
    {
        const unsigned index = presetIndex(norm);
        if (index >= kNumPresets) return;
        for (size_t i = 0; i < kNumPresetControls; ++i) {
            const auto& c = fUI.controls[i];
            *c.zone = FAUSTFLOAT(std::fmin(std::fmax(kPresets[index].values[i], c.min), c.max));
        }
    }

    static bool arrangementFor(int channels, SpeakerArrangement& arr)
    {
        if (channels == 1) arr = SpeakerArr::kMono;
        else if (channels == 2) arr = SpeakerArr::kStereo;
        else return false;
        return true;
    }

    ParamValue plainOf(ParamID id)
    {
        Parameter* p = parameters.getParameter(id);
        return p ? p->toPlain(p->getNormalized()) : 0;
    }

    void applyNormalized(ParamID id, ParamValue norm)
    {
        if (id >= fUI.controls.size()) return;
        Parameter* p = parameters.getParameter(id);
        *fUI.controls[id].zone = FAUSTFLOAT(p->toPlain(norm));
    }

    // init() resets every control to its default and clears the state. The
    // latency bargraph is only written by compute(), so one sample of silence
    // is run to read it, then the state is cleared again and the host's
    // parameter values are put back.
    void resetDSP(int sampleRate)
    {
        fDSP.init(sampleRate);
        if (fUI.latency) {
            std::vector<FAUSTFLOAT> silence(size_t(fDSP.getNumInputs() + fDSP.getNumOutputs()), 0);
            std::vector<FAUSTFLOAT*> ptrs;
            for (auto& x : silence) ptrs.push_back(&x);
            NoDenormals ftz;
            fDSP.compute(1, ptrs.data(), ptrs.data() + fDSP.getNumInputs());
            fLatency = uint32(std::lround(std::fmax(0.0, *fUI.latency)));
            fDSP.instanceClear();
        }
        for (size_t i = 0; i < fUI.controls.size(); ++i)
            *fUI.controls[i].zone = FAUSTFLOAT(plainOf(ParamID(i)));
    }

    mydsp fDSP;
    ControlCollector fUI;
    SpeakerArrangement fIn = SpeakerArr::kEmpty, fOut = SpeakerArr::kEmpty;
    uint32 fLatency = 0;
};

BEGIN_FACTORY_DEF(FX_VENDOR, FX_URL, "")

DEF_CLASS2(FX_CID, PClassInfo::kManyInstances, kVstAudioEffectClass, FX_NAME, 0, FX_SUBCATEGORY, FX_VERSION,
           kVstVersionString, FaustEffect::createInstance)

END_FACTORY
