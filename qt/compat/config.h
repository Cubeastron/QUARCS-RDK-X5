#pragma once

// The Debian libqhy package omits the config.h included by the public SDK
// headers. QUARCS consumes the C++ API, matching the INDI QHY driver build.
#ifndef __CPP_MODE__
#define __CPP_MODE__ 1
#endif

#ifndef CALLBACK_MODE_SUPPORT
#define CALLBACK_MODE_SUPPORT 1
#endif
