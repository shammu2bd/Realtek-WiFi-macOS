# RTL88WiFi 1.0.12 validation record

## Source changes

- WPA3 initial selection now uses the shared join score and 5 GHz upgrade eligibility rule.
- A known pinned 2.4 GHz BSSID can be upgraded only to a fresh, usable 5 GHz BSSID of the same SSID that passes the WPA3-Personal SAE+PMF profile check and scores better.
- Unpinned WPA3 joins use the common score, including its fresh/usable 5 GHz preference, RSSI, scan age and failed-BSSID demotion.
- SAE retry/fallback and the authentication retry-budget check now use the same WPA3-capable, band-aware selector and skip BSSIDs already tried.
- Unknown pinned BSSIDs remain cache misses and are not silently substituted.
- The existing `RTL88WiFiPrefer5GHz` property remains enabled by default; disabling it suppresses pinned 2.4-to-5 GHz upgrades.
- Kext bundle, kmod and `DriverBuild` identity are updated to `1.0.12`.
- All project release and development history is consolidated into the single root `CHANGELOG.md`.

## Host-side checks that passed

- `tests/test-wpa3-band-preference.py`
- `tests/test-wpa3-integration.py`
- `tests/test-r32.2-compile-fixes.py` (historical compile-regression assertions)
- `tests/test-r29-scan-lifecycle.py`
- `tests/test-r30-unifi-scan-priority.py`
- `tests/test-r28-mesh-scan.py`
- `tests/test-mesh-rate-stability.py`
- `tests/test-r32-build-paths.py`
- `tests/test-assoc-wire.py`
- `tests/test-handshake.py`
- `tests/test-rx-filter.py`
- `tests/test-private-mac.py`
- `tests/test-mesh-roaming.py`
- `tests/test-roam-scan-policy.py`
- `tests/test-scan-ssid.py`
- `tests/test-join-report.py`
- `tests/test-scanlog-tool.py`
- `tests/test-tx-queue-backpressure.py`
- `driver/RTL88WiFi/experimental/wpa3/test_host.py`
- `SAE_HOST_SANITIZE=1 python3 driver/RTL88WiFi/experimental/wpa3/test_host.py`
- Plist/version/changelog uniqueness checks.

The WPA3 host suite passed both normal and ASan/UBSan runs, including SAE H&P/H2E exchanges, Commit/Confirm handling, production four-way handshake, PMF integrity/replay checks, CCMP/AES known answers and menu/association ABI validation.

## Checks blocked by this environment

- `tests/test-group-key.py` cannot compile because this Linux environment does not provide Apple's `CommonCrypto/CommonSymmetricKeywrap.h`.
- `tests/test-join-policy.py` and `tests/test-ba-recovery.py` cannot compile because Apple's `kern/thread_call.h` is unavailable.
- The Makefile references `xcrun` to discover the macOS SDK; `xcrun` is not installed in this environment.

These are environment/toolchain limitations, not passed tests. No native Xcode kext compile/link, signing, installation or load test is claimed.

## Hardware status

The user confirmed that WPA3-Personal worked on the target RTL8821CE with the preceding source, but that it initially selected the 2.4 GHz band. Version 1.0.12 changes the WPA3 BSS-selection and retry paths to prefer a suitable 5 GHz sibling on the same SSID. The new 5 GHz preference still needs a target-Mac rebuild and over-the-air test to confirm CoreWiFi selects the intended BSSID, DHCP completes, and traffic remains stable.
