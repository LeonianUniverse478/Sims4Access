# prism.dll

`prism.dll` in this folder is a build of [Prism](https://github.com/ethindp/prism)
by Ethin Probst — the screen-reader bridge Sims 4 Access speaks through. It is
**not** part of Sims 4 Access and is not covered by this project's MIT licence.

Prism is licensed under the **Mozilla Public License 2.0**, included here as
`PRISM-LICENSE.txt`. MPL-2.0 is file-level copyleft: this binary may be
redistributed alongside MIT-licensed work, and anyone who modifies Prism's own
source must publish those modifications. Prism also bundles `simdutf` under
Apache-2.0; see the NOTICE file in Prism's repository for the full list.

Prism publishes no binaries, so this one is built from source with CMake and
MSVC x64, all backends compiled in. To build your own, follow the instructions
in Prism's repository — nothing here depends on this particular build.

macOS and Linux need `libprism.dylib` or `libprism.so` built the same way and
placed beside the mod instead.
