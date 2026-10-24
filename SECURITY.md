# Security policy

## Reporting a vulnerability

Please report security problems privately through GitHub's [private vulnerability reporting](https://github.com/Joe-Heffer/faust-pedalkit/security/advisories/new) ("Report a vulnerability" on the repository's Security tab). Don't open a public issue, pull request or discussion.

Please include:

- the affected effect, file or build target, and the commit or version
- the host and platform, if a built plugin is involved
- steps or an input file that reproduce the problem
- what you think the impact is

This is a small, volunteer-run project. Expect an acknowledgement within about a week. Once there is a fix, we will publish an advisory and credit you, unless you would rather stay anonymous.

## Scope

In scope:

- the DSP sources, shared library and the plugins built from them (for example, a crash, out-of-bounds access or unbounded output triggered by audio input or control values)
- the build scripts, tools and CI workflows in this repository

Out of scope, but please report them upstream:

- bugs in Faust, `faust2lv2`, the VST3 SDK, LV2 hosts or other dependencies
- problems that need an attacker who can already run code on your machine

## Supported versions

Only the latest commit on `main` is supported. There are no maintained release branches.
