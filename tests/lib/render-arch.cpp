// SPDX-FileCopyrightText: 2026 Joe Heffer
// SPDX-License-Identifier: MIT
// Offline render harness for the effect tests (one binary per effect).
//
// Usage: render <samplerate> [options] [Label=value[@seconds] ...] < in.f32 > out.f32
//
// Reads mono 32-bit float samples from stdin, processes them and writes the
// result to stdout. Before reading any input it runs two seconds of silence
// through the DSP, so the parameter smoothers have settled on their targets.
//
// Label=value sets a control before the pre-roll. Label=value@seconds changes
// it that many seconds into the input instead, at that exact sample, the way a
// host applies an automation point; give the same label several times for a
// sequence of changes.
//
// Options:
//   --block N   process in blocks of N samples (default 256)
//   --ftz       flush subnormals to zero while computing, as the VST3 and CLAP
//               wrappers do (tools/vst3/faust-vst3.cpp, tools/clap/faust-clap.cpp)
//   --latency   print the latency the effect reports to hosts (the bargraph
//               tagged [lv2:reportsLatency], 0 if none) and exit
//   --bench     read the input, time compute() on it and print
//               "<ns per sample> <times faster than real time>" instead of audio

#include <algorithm>
#include <chrono>
#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <string>
#include <vector>

#include "faust/dsp/dsp.h"
#include "faust/gui/MapUI.h"
#include "faust/gui/meta.h"

#if defined(__SSE__) || defined(__x86_64__)
#include <xmmintrin.h>
#endif

<<includeIntrinsic>>

<<includeclass>>

// MapUI, plus the zone of the bargraph tagged [lv2:reportsLatency].
struct HarnessUI : MapUI {
    FAUSTFLOAT* latency = nullptr;
    bool pending = false;

    void declare(FAUSTFLOAT* zone, const char* key, const char* val) override
    {
        if (std::strcmp(key, "lv2") == 0 && std::strcmp(val, "reportsLatency") == 0) pending = true;
        MapUI::declare(zone, key, val);
    }
    void addHorizontalBargraph(const char* label, FAUSTFLOAT* zone, FAUSTFLOAT lo, FAUSTFLOAT hi) override
    {
        if (pending) latency = zone;
        pending = false;
        MapUI::addHorizontalBargraph(label, zone, lo, hi);
    }
    void addVerticalBargraph(const char* label, FAUSTFLOAT* zone, FAUSTFLOAT lo, FAUSTFLOAT hi) override
    {
        if (pending) latency = zone;
        pending = false;
        MapUI::addVerticalBargraph(label, zone, lo, hi);
    }
};

// Same FTZ | DAZ bits as the plug-in wrappers. The harness exits afterwards,
// so there is nothing to restore.
static void setFlushToZero()
{
#if defined(__SSE__) || defined(__x86_64__)
    _mm_setcsr(_mm_getcsr() | 0x8040);
#elif defined(__aarch64__)
    unsigned long fpcr;
    asm volatile("mrs %0, fpcr" : "=r"(fpcr));
    asm volatile("msr fpcr, %0" : : "r"(fpcr | (1UL << 24)));
#endif
}

struct Event {
    size_t at;
    std::string label;
    float value;
};

int main(int argc, char* argv[])
{
    if (argc < 2) {
        std::fprintf(stderr, "usage: %s samplerate [--block N] [--ftz] [--latency] [--bench] "
                             "[Label=value[@seconds] ...]\n", argv[0]);
        return 2;
    }
    const int sr = std::atoi(argv[1]);

    mydsp dsp;
    dsp.init(sr);
    HarnessUI ui;
    dsp.buildUserInterface(&ui);

    int block = 256;
    bool ftz = false, latency = false, bench = false;
    std::vector<Event> events;
    for (int i = 2; i < argc; ++i) {
        std::string arg(argv[i]);
        if (arg == "--block" && i + 1 < argc) { block = std::max(1, std::atoi(argv[++i])); continue; }
        if (arg == "--ftz") { ftz = true; continue; }
        if (arg == "--latency") { latency = true; continue; }
        if (arg == "--bench") { bench = true; continue; }
        const auto eq = arg.find('=');
        if (eq == std::string::npos) {
            std::fprintf(stderr, "bad parameter '%s'\n", argv[i]);
            return 2;
        }
        const std::string label = arg.substr(0, eq);
        if (ui.getParamZone(label) == nullptr) {
            std::fprintf(stderr, "unknown parameter '%s'\n", label.c_str());
            return 2;
        }
        const char* text = arg.c_str() + eq + 1;
        char* end = nullptr;
        const float value = std::strtof(text, &end);
        if (*end == '@') {
            const double t = std::strtod(end + 1, nullptr);
            events.push_back({ size_t(std::llround(std::max(0.0, t) * sr)), label, value });
        } else {
            ui.setParamValue(label, value);
        }
    }
    std::stable_sort(events.begin(), events.end(),
                     [](const Event& a, const Event& b) { return a.at < b.at; });
    if (ftz) setFlushToZero();

    std::vector<FAUSTFLOAT> in(block, 0.0f), out(block, 0.0f);
    FAUSTFLOAT* ins[1]  = { in.data() };
    FAUSTFLOAT* outs[1] = { out.data() };

    // Pre-roll on silence so the smoothers reach their targets.
    for (int n = 0; n < 2 * sr; n += block) {
        dsp.compute(block, ins, outs);
    }

    if (latency) {
        std::printf("%ld\n", ui.latency ? std::lround(*ui.latency) : 0L);
        return 0;
    }

    if (bench) {
        std::vector<FAUSTFLOAT> x;
        size_t got;
        while ((got = std::fread(in.data(), sizeof(FAUSTFLOAT), block, stdin)) > 0) {
            x.insert(x.end(), in.begin(), in.begin() + got);
        }
        // The best of five passes, to keep scheduler noise out of the figure.
        double best = 1e300;
        for (int pass = 0; pass < 5; ++pass) {
            const auto t0 = std::chrono::steady_clock::now();
            for (size_t n = 0; n < x.size(); n += block) {
                const int len = int(std::min<size_t>(block, x.size() - n));
                FAUSTFLOAT* bin[1] = { x.data() + n };
                dsp.compute(len, bin, outs);
            }
            const std::chrono::duration<double> dt = std::chrono::steady_clock::now() - t0;
            best = std::min(best, dt.count());
        }
        const double nsPerSample = 1e9 * best / std::max<size_t>(x.size(), 1);
        std::printf("%.3f %.1f\n", nsPerSample, 1e9 / (nsPerSample * sr));
        return 0;
    }

    // Split blocks at each event, so a change lands on its exact sample.
    size_t pos = 0, next = 0, got;
    while ((got = std::fread(in.data(), sizeof(FAUSTFLOAT), block, stdin)) > 0) {
        size_t done = 0;
        while (done < got) {
            while (next < events.size() && events[next].at <= pos + done) {
                ui.setParamValue(events[next].label, events[next].value);
                ++next;
            }
            size_t len = got - done;
            if (next < events.size()) len = std::min(len, events[next].at - (pos + done));
            FAUSTFLOAT* bin[1]  = { in.data() + done };
            FAUSTFLOAT* bout[1] = { out.data() + done };
            dsp.compute(int(len), bin, bout);
            done += len;
        }
        std::fwrite(out.data(), sizeof(FAUSTFLOAT), got, stdout);
        pos += got;
    }
    return 0;
}
