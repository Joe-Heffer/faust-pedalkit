// Offline render harness for the effect tests (one binary per effect).
//
// Usage: render <samplerate> [Label=value ...] < in.f32 > out.f32
//
// Reads mono 32-bit float samples from stdin, processes them and writes the
// result to stdout. Before reading any input it runs two seconds of silence
// through the DSP, so the parameter smoothers have settled on their targets.

#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <string>
#include <vector>

#include "faust/dsp/dsp.h"
#include "faust/gui/MapUI.h"
#include "faust/gui/meta.h"

<<includeIntrinsic>>

<<includeclass>>

int main(int argc, char* argv[])
{
    if (argc < 2) {
        std::fprintf(stderr, "usage: %s samplerate [Label=value ...]\n", argv[0]);
        return 2;
    }
    const int sr = std::atoi(argv[1]);

    mydsp dsp;
    dsp.init(sr);
    MapUI ui;
    dsp.buildUserInterface(&ui);

    for (int i = 2; i < argc; ++i) {
        std::string arg(argv[i]);
        const auto eq = arg.find('=');
        if (eq == std::string::npos) {
            std::fprintf(stderr, "bad parameter '%s'\n", argv[i]);
            return 2;
        }
        const std::string label = arg.substr(0, eq);
        const float value = std::strtof(arg.c_str() + eq + 1, nullptr);
        if (ui.getParamZone(label) == nullptr) {
            std::fprintf(stderr, "unknown parameter '%s'\n", label.c_str());
            return 2;
        }
        ui.setParamValue(label, value);
    }

    const int block = 256;
    std::vector<FAUSTFLOAT> in(block, 0.0f), out(block, 0.0f);
    FAUSTFLOAT* ins[1]  = { in.data() };
    FAUSTFLOAT* outs[1] = { out.data() };

    // Pre-roll on silence so the smoothers reach their targets.
    for (int n = 0; n < 2 * sr; n += block) {
        dsp.compute(block, ins, outs);
    }

    size_t got;
    while ((got = std::fread(in.data(), sizeof(FAUSTFLOAT), block, stdin)) > 0) {
        dsp.compute(static_cast<int>(got), ins, outs);
        std::fwrite(out.data(), sizeof(FAUSTFLOAT), got, stdout);
    }
    return 0;
}
