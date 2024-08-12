seq-detective's fingerprint phase can be built with `tracy` profiling support.
to do so, pass `-Dtracy_enable=enabled` to `meson setup`

tracy's profiler server can be built from the subproject:
```
cd subprojects/tracy
cmake -B profiler/build -S profiler -DCMAKE_BUILD_TYPE=Release
cmake --build profiler/build --config Release --parallel
```

configuring (first cmake command) with `-DNO_PARALLEL_STL=1 -DLEGACY=1` may help on WSL.

binary will be located at `profiler/build/tracy-profiler`
