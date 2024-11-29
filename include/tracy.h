// wrapper for tracy profiler
#pragma once

#ifdef TRACY_ENABLE
#include "tracy/TracyC.h"
#else
#define TracyCZoneS(ctx, d, active)
#define TracyCZoneNS(ctx, name, d, active)
#define TracyCZoneEnd(ctx)
#define TracyCSetThreadName(name)
#endif
