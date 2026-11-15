# 802.11k / 802.11v roaming source notice

The bounded Neighbor Report and BSS Transition Management wire helpers in
`src/kext/RTW88Roaming.hpp` are adapted from the corresponding
`RTW88Roaming.hpp` implementation in the GPL-2.0-licensed AirPort-RTW project:

- Upstream project: https://github.com/JoMei9019-real/AirPort-RTW
- Reference file: `src/kext/RTW88Roaming.hpp`
- Reference archive supplied for this port: AirPort-RTW 1.2.1 source tree

The helper retains its `SPDX-License-Identifier: GPL-2.0 OR BSD-3-Clause`
identifier. The RTL88WiFi integration around it is part of this repository's
GPL-2.0 driver source. Upstream license and source notices remain applicable.

The RTL88WiFi integration adapts these bounded parsers to this driver's
controller, PMF, management TX-status, connected-scan and existing roam paths.
It does not import the complete AirPort-RTW driver or claim support for
802.11r Fast Transition or general 802.11k Radio Measurement procedures.
