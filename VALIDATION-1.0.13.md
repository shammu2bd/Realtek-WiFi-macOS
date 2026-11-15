# RTL88WiFi 1.0.13 validation record

## Source changes

- Added bounded 802.11k Neighbor Report Request/Response wire handling, dialog-token validation, IE bounds/duplicate checks, candidate preference parsing and a 30-second hint-cache lifetime.
- Advertises Neighbor Report only when the AP advertises RRM Neighbor Report capability and the association uses the internal WPA2-Personal/CCMP or WPA3-Personal/CCMP path.
- Added 802.11v BSS Transition Management Request parsing and BTM Accept/Reject responses.
- Advertises BTM only when the AP advertises the BSS Transition capability and the controller's PM-fenced control timer is available.
- When a BTM request has no Preferred Candidate List, a fresh Neighbor Report response from this association may be used as a hint. When the PCL bit is set but its list is empty, the request is declined rather than silently substituting another list.
- BTM candidates must be fresh scan-cache observations with the same SSID/privacy mode and matching supported CCMP security. WPA3 targets must offer a valid SAE+PMF profile.
- If no existing cache candidate is suitable, the driver makes one directed connected scan attempt on the highest-preference regulatory-enabled candidate channel. The requested channel is prioritized in the bounded one-channel scan pass.
- A BTM Accept is transmitted only after candidate validation. The driver waits for the exact response TX ACK before calling the existing `cmdRoam()` path. WPA3 ACK matching binds both the protected frame's header identity and CCMP packet number.
- BSS Termination and ESS-Disassociation request modes are rejected. No FT key derivation or 802.11r FT handoff is implemented.
- Kext bundle, kmod and `DriverBuild` identity are updated to `1.0.13`.

## Host-side checks that passed in this environment

- `tests/test-rrm-btm.py` — production header parser/request/response helpers compiled with `clang++ -std=c++17 -Wall -Wextra -Werror`; validates RRM AP capability parsing, Neighbor Report request/response, dialog tokens, malformed IE rejection, BTM request/response parsing, AP action-frame addressing, and WPA3 CCMP-PN receipt binding. Source guards cover capability advertisement, PMF verification, directed BTM scan, and TX-ACK-gated roam handoff.
- `tests/test-assoc-wire.py`
- `tests/test-mesh-roaming.py`
- `tests/test-roam-scan-policy.py`
- `tests/test-r28-mesh-scan.py`
- `tests/test-r29-scan-lifecycle.py`
- `tests/test-r30-unifi-scan-priority.py`
- `tests/test-r32-build-paths.py`
- `tests/test-r32.2-compile-fixes.py`
- `tests/test-wpa3-band-preference.py`
- `tests/test-wpa3-integration.py`
- `tests/test-private-mac.py`
- `tests/test-handshake.py`
- `tests/test-rx-filter.py`
- `tests/test-scan-ssid.py`
- `tests/test-tx-queue-backpressure.py`
- `tests/test-join-report.py`
- `tests/test-scanlog-tool.py`
- `python3 -m py_compile tests/*.py`

These are host parser, source-contract and policy checks. They do not emulate the macOS CoreWiFi controller, kernel scheduling or actual RF behavior.

## Checks blocked by this environment

- No Xcode or `xcrun`/macOS SDK is installed in the Linux build environment. A native kext compile/link/sign test could not be run here.
- Some pre-existing test suites (`tests/test-join-policy.py`, `tests/test-ba-recovery.py`) rely on Apple `kern/thread_call.h`; the Linux environment does not provide it. They were not counted as passes for this release.
- No real AP BTM request/response exchange, WPA3 PMF management-frame round trip, directed scan or on-device roam has been tested on the target Mac.

## Hardware status

The user previously confirmed WPA3-Personal works on the target RTL8821CE with the preceding source line. This 1.0.13 implementation has not yet been rebuilt or tested on that Mac. The target-Mac Xcode build and interoperability tests with an AP that advertises 802.11k Neighbor Reports and 802.11v BSS Transition Management are required before replacing the working kext.
