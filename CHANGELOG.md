# RTL88WiFi Changelog

This is the **single consolidated project changelog**. It includes the current semantic-version release and the complete available history from earlier project releases and development checkpoints. Older `rXX` labels below are retained only to identify historical internal milestones; current and future deliverables use version numbers such as `RTL88WiFi 1.0.12`, `1.0.13`, and so on.

## 1.0.13 — 2026-11-15 — 802.11k Neighbor Reports and 802.11v BSS Transition Management

This release adds bounded Neighbor Report discovery and AP-triggered BSS Transition Management to the existing RTL88WiFi 1.0.12 source line.

### Changed

- Added an 802.11k Neighbor Report Request/Response path. The station advertises only the Neighbor Report capability (not Beacon Measurement, Link Measurement, channel-load, noise or location reporting) and requests a report no more often than once per minute.
- Validates AP action-frame addressing, action category/action, request dialog token, IE bounds, Neighbor Report BSSID/channel fields and preference subelements. Cached entries expire after 30 seconds and remain hints, not direct join authorization.
- Added 802.11v BTM Request parsing and response generation. The station advertises BTM only if the AP advertises the matching Extended Capability and the PM-fenced controller timer is available.
- A BTM request with the Preferred Candidate List bit set must carry a nonempty parseable candidate list. If the AP omits the list, a fresh Neighbor Report from the current association may be used as a hint.
- Candidate evaluation is queued on the controller workloop. Existing cache entries must be fresh, same-SSID, same-privacy and compatible with the current CCMP/SAE security profile.
- When no candidate is already suitable in the scan cache, the driver makes one directed connected scan attempt on the highest-preference regulatory-enabled candidate channel. The existing one-channel scan path prioritizes that channel and retains its scan lifecycle, home-channel restoration and TX hold behavior.
- BTM Accept is sent only after a candidate has been observed and validated. The driver starts the existing `cmdRoam()` handoff only after the exact BTM response receives a TX ACK. For WPA3, the receipt correlates the protected response by header identity and CCMP PN without parsing ciphertext.
- BSS Termination and ESS-Disassociation URL modes are rejected rather than partially acted upon. No URL is fetched. No 802.11r Fast Transition or FT key handling is introduced.
- The bundle, kmod and `DriverBuild` identity are bumped to **1.0.13**.

### Preserved

- WPA3-Personal SAE, PMF/BIP, CCMP and GTK/IGTK handling.
- The 1.0.12 WPA3 5 GHz preference, 1.0.11 mesh roaming and same-ESS cache policy, r29 scan lifecycle, r30 UniFi scan priority, existing private-MAC behavior and open/WPA2 association paths.
- AP-provided Neighbor Report and BTM candidates cannot override local regulatory, freshness, same-ESS or security checks.

### Validation status

- `tests/test-rrm-btm.py` compiles the production bounded wire helpers and passes parser, dialog-token, action-frame-address, BTM response and PMF receipt tests. Source checks cover the capability advertisement, directed scan and TX-ACK-gated handoff.
- Targeted existing mesh, scan, WPA3, association, handshake, RX-filter, private-MAC, join-report and queue-backpressure host tests passed in this environment.
- No native Xcode/macOS kext build or real AP/hardware test was possible in the Linux environment. The target RTL8821CE must be rebuilt and tested before installation.
- The initial BTM implementation scans only one preferred candidate channel per request. If no fresh secure candidate is seen, it declines and stays on the current AP. This is intentional rather than accepting an unverified BSSID.

---

## 1.0.12 — 2026-11-15 — WPA3 5 GHz preference and release-version cleanup

Based on the user's confirmed working WPA3-Personal implementation from the 1.0.11 source line. The user reported that WPA3-Personal association and traffic worked, but the driver selected a 2.4 GHz BSSID even though the same SSID was available on 5 GHz.

### Changed

- **WPA3 now uses the same 5 GHz preference policy as WPA2.** The SAE path no longer chooses the strongest RSSI BSSID without considering band, freshness, or recent failures.
- When macOS pins a known 2.4 GHz BSSID, the WPA3 selector can upgrade the join to a fresh, usable 5 GHz BSSID of the same SSID, but only if that BSSID advertises a valid WPA3-Personal SAE + PMF profile and its shared policy score is better.
- An unknown pinned BSSID remains an actual cache miss and follows the existing one-refresh path; the selector does not silently substitute a different access point.
- When no BSSID is pinned, WPA3 candidate selection uses the common join score, including the fresh usable 5 GHz bonus, RSSI, scan age, and failed-BSSID demotion.
- WPA3 same-ESS authentication fallback now uses the same band-aware selector and skips BSSIDs already tried in the current join.
- The preference is controlled by the existing `RTL88WiFiPrefer5GHz` property, enabled by default. A fresh 5 GHz candidate must be at least -72 dBm and have been observed in the current or immediately previous scan generation; recently failed candidates are not eligible for a pinned upgrade. A much stronger 2.4 GHz BSS may still win by score.
- Added connection diagnostics for `prefer5`, selected band, channel, RSSI, and whether a pinned 2.4 GHz request was upgraded.
- Bumped the public bundle, kmod and DriverBuild version to **1.0.12**. New archives use `RTL88WiFi-1.0.12.zip`; internal `r30`/`r33`-style suffixes are no longer used for new builds.
- Consolidated the previous project changelog documents into this one `CHANGELOG.md` file.

### Preserved

- WPA3-Personal SAE Commit/Confirm, Hunting-and-Pecking/H2E, anti-clogging tokens, RSN/RSNXE, EAPOL four-way handshake, CCMP-128, GTK/IGTK, PMF/BIP-CMAC-128, replay protection, and protected management-frame handling from the working 1.0.11 source line.
- WPA2 and open-network behavior, r29 scan-lifecycle handling, r30 UniFi scan candidate priority, queue handling, and existing macOS association plumbing.
- The preference does not force a channel, change country/regulatory state, force a PHY rate, or autonomously roam an already-connected station.

### Validation status

- The new header-only 5 GHz candidate eligibility and shared-score policy has a dedicated host regression test.
- WPA3 source integration guards check both the initial SAE join and the SAE retry/fallback path.
- Host-side regression tests and the WPA3 host crypto suite are run for this source package. They do not substitute for a native Xcode 16.4 kext build or on-device RF validation.
- The user has confirmed that WPA3-Personal works on the target RTL8821CE with the preceding source. The 1.0.12 5 GHz preference change still requires a fresh hardware test to confirm macOS selects the expected 5 GHz BSSID on the same SSID.

---

## Historical release and development history

### 1.0.11 development checkpoint — WPA3 macOS compile fixes (2026-11-15)

Historical internal milestone: r32.2. This was a compile-fix checkpoint within the 1.0.11 development line, not a public semantic-version release.


This revision addresses the two fatal compiler errors reported by the first
macOS build attempt of r32.1. It is a source correction only; it does not
change the SAE cryptographic algorithms, negotiated ciphers, key hierarchy,
or security policy.

## Fixes

1. **RX security helper include order.** `RTW88IEEE80211.cpp` previously
   included `rtw88_rx_security.h` before the compatibility header. The helper
   uses `RX_FLAG_DECRYPTED`, which is defined by the compatibility
   `net/mac80211.h`. The include is now placed immediately after the
   `rtw88_compat.h` import, so the flag is defined before the helper is parsed.
   No flag values or integrity checks were changed.
2. **Missing handshake event declaration/dispatch.** Added the existing
   `kRTW88EventHandshakeDone` event to `RTW88Event` and added its controller
   handler. The native WPA3 state machine emits this event only after the SAE +
   EAPOL state is authorized; the controller then posts
   `APPLE80211_M_RSN_HANDSHAKE_DONE`. This is separate from the external Apple
   supplicant's PTK/GTK `CIPHER_KEY` notifications.

## Scope and validation status

The attached r32.1 build log showed precisely these two undeclared-identifier
errors: `RX_FLAG_DECRYPTED` and `kRTW88EventHandshakeDone`. The r32.2 source
contains targeted regression tests for both corrections and retains the r32.1
RX-wrapper relative-path correction. Host-side tests can verify source
contracts, but only the user's Xcode 16.4 environment can establish whether
the complete macOS kext compiles and links. No macOS build or hardware WPA3
association is claimed by this changelog.

---

### 1.0.11 development checkpoint — WPA3 RX source-path correction (2026-11-15)

Historical internal milestone: r32.1. This was a source-path correction within the 1.0.11 development line.


This is a minimal source correction on top of r32. It fixes the fatal error
reported by the target-Mac build of `make -C driver/RTL88WiFi rtl88wifi`.

## Root cause

`driver/RTL88WiFi/src/compat/rtw88_rx.c` included the pinned upstream
`rx.c` as `../../rtw88-stable/...`. Relative includes are resolved from the
wrapper's directory, so that path incorrectly pointed inside
`driver/RTL88WiFi/rtw88-stable/`. The actual source lives at
`driver/rtw88-stable/`.

## Fix

The include now uses `../../../rtw88-stable/...`, which resolves from
`src/compat/` to the actual source under `driver/rtw88-stable/`. The Makefile
already declared the same `$(LINUX_SRC)/rx.c` prerequisite; no source list or
object graph change was needed. A regression test confirms both the path and
that `rx.o` remains in the `rtl88wifi` target.

No WPA3 cryptographic logic, key handling, PMF policy, r30 scan behavior or
other driver behavior was changed.

## Validation

- Corrected include resolves to an existing pinned `rx.c` file.
- `tests/test-r32-build-paths.py` passes.
- WPA3 integration, SAE/Dragonfly, AES/CCMP, r29 lifecycle and r30 scan-policy
  host tests pass.
- The user's build log showed this include as the fatal error; the two Mbed
  TLS signedness diagnostics are warnings, not the cause of exit status 2.
- This environment cannot run Xcode or link a macOS kext. A native target-Mac
  rebuild is still required; further errors, if any, must be diagnosed from
  that rebuild's output.

---

### 1.0.11 development checkpoint — WPA3-Personal SAE and PMF implementation (2026-11-15)

Historical internal milestone: r32. This was the first complete WPA3-Personal implementation checkpoint in the 1.0.11 source line.

Based on the complete r30 UniFi scan-priority source. Experimental; no Apple
kernel build or physical RTL8821CE/WPA3 AP test has been performed.

## Reference implementation

The user-supplied `AirPort-RTW-main.zip` was inspected as the primary WPA3
reference. Its production `RTW88WPA3` session, SAE adapter, private hostap and
Mbed TLS subset, AES/CCMP implementation, RSN helper and host32 association
wire format were used as the implementation guide. Chip-specific RTW89 or
other-device hardware code was not copied. Original SPDX identifiers,
upstream notices, import manifests and third-party license texts are retained.
See `NOTICE-WPA3-AIRPORT-RTW.md` and
`driver/RTL88WiFi/experimental/wpa3/`.

## WPA3-Personal path added

- SAE/Dragonfly authentication with both Hunting-and-Pecking and H2E profiles,
  Commit/Confirm processing, anti-clogging-token handling, peer identity and
  transaction validation, retry fencing, and fresh sessions for fallback and
  roaming.
- WPA3 RSN and RSNXE association IE generation, PMF-required negotiation,
  CCMP-128 pairwise traffic keys, EAPOL four-way handshake, GTK/IGTK extraction,
  group rekey processing and PN/replay protection.
- BIP-CMAC-128 verification for group-addressed robust management frames,
  CCMP protection for unicast robust management frames, SA Query response,
  and rejection of unauthenticated robust deauthentication/disassociation.
- RX descriptor wrapper exposes CRC/ICV failure and verified CCMP status. The
  driver does not treat `RX_FLAG_DECRYPTED` alone as proof of a valid MIC.
- Native macOS menu capability bits advertise SAE and PMF. The validated
  900/908-byte host32 association bridge carries a 63-byte passphrase when the
  extended prefix is present; credentials are copied into bounded temporary
  buffers and wiped after use. An administrator-only `WPA3Connect` property
  path is also provided and does not persist the password in IORegistry.
- Hardware pairwise CCMP key installation is preferred. If the hardware key
  offload cannot be installed, the SAE session uses the audited scalar
  software CCMP implementation; the next join retries hardware offload.
- Password-only menu joins select SAE unless all matching BSS entries
  positively indicate PSK-only security. SAE-only PMK input is rejected, and a
  PMK-only WPA2 request is refused for a transition BSS that also advertises
  SAE, preventing a silent downgrade.
- SAE mode is retained across deferred scans, BSS fallback, and same-ESS roam;
  a roam performs a fresh SAE exchange and fresh PMK/PTK.

## r30 behavior preserved

- r29 scan-lifecycle completion, pending request retention, home-channel
  restoration and connected-scan throttling.
- r30 same-band candidate collection before the eight-channel cap, nearby
  5 GHz prioritization, bounded cross-band discovery, sampled throttle logs,
  rate-adaptation recovery diagnostics and peer VHT telemetry.
- Existing WPA2/open association and mesh scan/roam paths remain in the source.

## Scope and limitations

This is WPA3-Personal station support only. WPA3-Enterprise/802.1X, OWE,
802.11r Fast Transition, WPA3-Enterprise Suite-B/192-bit mode and Wi-Fi
Alliance certification are not implemented or claimed. The reference project
also documents intermittent AP SAE rejection, transition-mode fallback to
WPA2 in some cases, and a guest-network DHCP failure; those cases still need
physical retesting. WPA3-only operation, transition mode, 63-byte passphrases,
roaming, group rekeys and PMF need verification on the target RTL8821CE Mac.

## Validation

`python3 driver/RTL88WiFi/experimental/wpa3/test_host.py` passes the isolated
SAE, H&P/H2E exchange, production four-way handshake, PMF integrity/replay,
CCMP/AES known-answer and association-menu ABI tests. The same test passes
with `SAE_HOST_SANITIZE=1` (ASan/UBSan). `tests/test-wpa3-integration.py` checks
native frontend wiring and PSK-only policy. Existing r29/r30 scan and mesh
helper tests also pass. Some older join-policy/group-key checks cannot compile
in this Linux environment because Apple's `kern/thread_call.h` and
`CommonCrypto/CommonSymmetricKeywrap.h` are not available. No Xcode build,
Kext link, code-sign or physical radio validation has been performed.

---

### 1.0.11 development checkpoint — UniFi scan priority and rate diagnostics (2026-11-09)

Historical internal milestone: r30. This work corrected scan candidate ordering and improved rate diagnostics.

Based on the complete r29 source. Experimental; not built with Apple's macOS
kernel SDK and not tested against physical RTL8821CE hardware or UniFi APs.
Keep r25 as the stable fallback and retain the r29 archive for rollback/A-B.

## Changes

- **Fix the scan candidate cap ordering.** r29 collected mixed-band channels
  into an eight-entry array and sorted afterward. CoreWiFi's 2.4 GHz-first
  request order could therefore fill the array before 5 GHz channels were
  appended. r30 now collects enabled same-band and cross-band candidates in
  separate bounded pools before applying the eight-channel cap.
- **Home-band-first selection.** Same-band choices are sorted by channel-number
  distance from the current channel, so a channel-157 link examines nearby
  enabled channels such as 153, 161, 149 and 165 before distant 5 GHz channels.
  Actual candidates are still filtered against the current wiphy regulatory
  enabled-channel list; the driver does not add channels or override country rules.
- **Controlled cross-band discovery.** When same-band candidates exist, one of
  the eight candidate slots is retained for cross-band discovery. If no same-band
  candidate exists, cross-band candidates may use the full budget. This changes
  scan discovery order only; it does not enable cross-band automatic roaming.
- **Throttle log sampling.** Repeated 15-second connected-scan throttle events
  are counted and only the first plus every 32nd event is logged, avoiding log
  ring churn while preserving totals. Scan request coalescing and r29's pending
  scan lifecycle are unchanged.
- **Rate-recovery gate correction.** Re-seeding the existing negotiated rate
  adaptation mask no longer requires a cached alternate BSSID. It still requires
  a strong 5 GHz link, at least 40 MHz home width, a sustained low TX PHY rate,
  and the 90-second cooldown. It never forces MCS or channel width.
- **VHT capability diagnostics.** Association and rate-transition logs now include
  the peer's intersected VHT RX/TX MCS maps and highest supported rates, making
  it easier to see whether MCS 7–9 are available in the negotiated peer profile.

## Preserved behavior and limitations

- r29 pending scan retention, reservation, completion, timer retry, watchdog and
  home-channel restoration behavior are preserved.
- One alternate channel is visited per connected scan pass, with the existing
  15-second minimum interval.
- WPA3-SAE, PMF/BIP, 802.11k/v/r, autonomous roaming and UniFi controller changes
  are not implemented by this revision.
- A host-side test pass is not an Apple kernel build or radio validation.

---

### 1.0.11 development checkpoint — UniFi ESS scan lifecycle recovery (2026-11-09)

Historical internal milestone: r29. This work retained pending scans and repaired scan completion/retry lifecycle handling.

Based on the complete r28 source, including the scan logger. Experimental;
not built with Apple's macOS kernel SDK and not tested on the target Mac or
physical UniFi access points. Keep r25 as the stable fallback and preserve r26/r28
for A/B comparison.

## Evidence motivating r29

The November 9 r28 capture showed a five-minute capture with multiple BSSIDs
advertising one SSID. The associated station was on 5 GHz channel 157. r28
selected the known same-band channel 161 first, performed a one-channel dwell,
and logged home-channel restoration. After that scan, repeated CoreWiFi scan
requests were coalesced and the capture did not contain a corresponding
`mesh scan slice done` or normal scan-completion event. The source also showed
that pending requests were copied and cleared before the dispatcher checked
whether a scan was still active. That ordering could discard the one retained
follow-up request if the timer fired early.

The capture's 5 GHz candidate was approximately -78 dBm, while stronger
-54 dBm candidates were on 2.4 GHz. r29 therefore preserves same-band-first
discovery and does not automatically roam to a weaker 5 GHz candidate or to a
stronger candidate on a different band. A shared SSID identifies an ESS of
BSSIDs; it does not establish whether each UniFi AP has a wired uplink or a
wireless mesh backhaul.

## Changes

- **Pending scan is no longer consumed before readiness checks.** The request
  queue remains intact until both the controller and backend are ready to start
  another scan. Requests are merged by channel and coalesced without discarding
  the retained follow-up.
- **Deferred dispatch watchdog.** Enqueuing a pending scan arms a one-second
  timer. While the raw backend state is SCANNING, the queue is retained and the
  timer is rearmed. Transitional association/authentication states are also
  deferred rather than treated as scan-ready. Coalesced bursts do not keep
  resetting the timer indefinitely.
- **15-second throttle is distinguished from no candidates.** `cmdScan()` can
  return `NotReady` both when a connected scan is rate-limited and when no
  eligible ESS channel exists. r29 now reads the remaining throttle time and
  retains/retries the pending request at that deadline; only a true no-candidate
  result is completed from cache. This prevents pending UniFi ESS scans from
  being lost immediately after a prior scan.
- **Raw-state awareness.** Request handling and pending dispatch use the actual
  backend state rather than the public persistent-RUN state exposed to
  CoreWiFi. This prevents a background scan from being mistaken for an idle
  interface simply because the current association remains visible.
- **Guarded stale scan-latch recovery.** If the backend has remained in stable
  IDLE/CONNECTED state for three one-second observations while the controller
  scan flag is still set, the controller clears the stale flag and posts one
  aborted `SCAN_DONE`. A normal completion event clears the watchdog counters
  first, so the watchdog does not race the ordinary completion path.
- **Manual worker finalizer reconciliation.** The manual scan worker now logs
  entry/return around core scan completion. Its finalizer can reconcile a
  stable IDLE/CONNECTED backend state and complete the Apple scan transaction
  as aborted. Late firmware callbacks remain guarded and cannot finish a newer
  transaction.
- **Atomic controller scan flag.** Reads and writes of the controller's active
  scan flag now use acquire/release atomic accessors; new scan starts use
  compare/exchange to reserve the scanner before consuming a pending request.
- **UniFi multi-AP ESS compatibility.** Each same-SSID BSSID remains a separate
  cache entry. Same-band-first channel ordering is retained, with compatible
  security checks. No vendor-specific assumptions, forced MCS/width, automatic
  BSSID roam, or guessed 802.11k/v/r behavior is introduced.
- **Diagnostic logger improvements.** `samples.csv` now includes firmware
  TX-rate Mbps, MCS, NSS, current TX bandwidth and home bandwidth where present
  in the diagnostic ring. Roaming-event counts now count only explicit
  `mesh roam start/complete/failed` messages rather than matching the build
  banner's `mesh-roam` feature name.
- **Completion telemetry.** Logs record the scan result, backend state, queued
  follow-up count, stable-state recovery observations and manual worker
  completion stages.

## Preserved behavior and limitations

- Connected scans remain one alternate channel per pass with the existing
  15-second minimum interval and same-band-first channel ordering.
- WPA2, existing association/handshake, TX queue handling, A-MPDU and existing
  cache-based CoreWiFi-requested roaming behavior are retained.
- This revision does not implement WPA3-SAE, PMF/BIP, 802.11k Neighbor Reports,
  802.11v BSS Transition Management, 802.11r Fast BSS Transition, or autonomous
  roaming. It does not configure or modify the UniFi controller/APs.
- The raw scan state is read from the backend object without adding a new
  hardware lock. The watchdog requires three stable observations before
  synthesizing completion; actual behavior still requires validation on macOS.
- The capture did not prove that every performance problem is caused by scans.
  TX PHY rate adaptation and UniFi AP/backhaul/airtime behavior remain separate
  diagnostic possibilities. r29 does not force 80 MHz or a fixed MCS.

## Host-side validation

`tests/test-r29-scan-lifecycle.py` exercises the scan deferral/recovery policy,
same-band ordering, pending-channel merge, and source integration checks.
`tests/test-mesh-rate-stability.py`, `tests/test-r28-mesh-scan.py`,
`tests/test-scanlog-tool.py` and the broader existing host tests remain part of
validation. These tests are not an Apple kernel build or RF/hardware test.

Additional review tightened the dispatch race: an atomic compare/exchange reserves
the scan before the pending request is consumed. Coalesced bursts no longer reset
the watchdog timer on every request. Cache-only completions use the common
completion event so queued follow-up scans are not stranded. The 15-second connected
scan throttle is now separately identified; a rate-limited pending request waits
for its actual retry deadline instead of being mistaken for an empty ESS cache.

---

### 1.0.11 development checkpoint — mesh scan priority and rate diagnostics (2026-11-09)

Historical internal milestone: r28. This work added bounded connected scan scheduling and related telemetry.

Based on the complete r27 source and scan logger. Experimental; not built with
Apple's macOS kernel SDK and not validated on the user's Mac or office APs.
Keep r25 as the known stable fallback until a local build and hardware test pass.

## Evidence motivating r28

The r27 capture showed multiple distinct BSSIDs advertising the same SSID.
The associated link was on 5 GHz channel 157, but the first connected scan
slice selected 2.4 GHz channel 1 while a same-ESS 5 GHz candidate on channel 161
was present. The log also recorded a burst of coalesced CoreWiFi scan requests.
The user clarified that the capture was intentionally stopped; the shortened
capture is not treated as proof of a stuck scan worker.

The capture's TX rate reports moved between 260, 87.75, 58.5, 40.5, 6.5, 27
and 13 Mbps while reported PHY width changed between 80, 40 and 20 MHz. r28
adds more precise rate/scan telemetry; it does not claim that scans caused every
rate reduction.

## Changes

- **Same-band-first channel ordering.** Connected-scan candidates are stably
  partitioned so channels on the associated band are visited before cross-band
  channels; channels are sorted numerically within each band. For a 5 GHz
  association, 5 GHz candidates are now selected before 2.4 GHz candidates.
  Roam eligibility continues to enforce same-band policy for low-rate recovery.
- **Connected scan interval floor.** The backend rate-limits connected
  off-channel scan starts to at most one every 15 seconds. Requests arriving
  during this interval receive a cache-only scan completion rather than another
  off-channel excursion. Disconnected/full scans are unchanged.
- **One pending request per active-scan burst.** While a scan is active, the
  controller retains at most one follow-up request and merges its channel hints
  (up to 128 distinct channels). Additional requests are coalesced. After the
  current scan completes, a controller-workloop timer waits two seconds and
  dispatches the retained request unless a newer scan already started. The
  backend's 15-second floor still applies.
- **Scan worker lifecycle telemetry.** Logs expose worker entry, radio
  preparation, channel begin/switch, dwell completion, home-channel restoration,
  finalization, and timeout stage/channel. This is intended to localize any
  future scan that does not complete; it does not itself prove successful RF
  reception during a dwell.
- **Rate-transition diagnostics.** Firmware TX-rate change logs now include
  TX-reported bandwidth, negotiated home bandwidth, RSSI, fresh same-band peer
  count and why the rate-recovery watch is armed or held. Rate recovery still
  reseeds only the already-negotiated firmware rate-adaptation mask; it never
  forces a fixed MCS, NSS or channel width.
- **Diagnostic collector compatibility.** The existing scan-log collector
  includes the new scan-worker, scan-rate-limit, pending-request and rate
  transition messages.

## Preserved behavior / limitations

- Existing association, WPA2, mesh cache/roaming filters, TX queue behavior,
  A-MPDU and r27 firmware rate-adaptation reseed logic are retained.
- A shared SSID is treated as an ESS of multiple BSSIDs; it does not prove the
  vendor's mesh controller, backhaul or steering protocol.
- No 802.11k Neighbor Reports, 802.11v BSS Transition Management, 802.11r Fast
  BSS Transition, autonomous roam engine, true 802.11s mesh-point mode or
  WPA3-SAE implementation is added.
- The 15-second floor can delay discovery of newly added APs; this trades scan
  freshness for fewer off-channel interruptions on a single-radio STA.
- The scan queue retains a single follow-up request to avoid replaying bursts.
  It does not guarantee that the host will submit a new request after every
  scan completion.
- Rate reports are firmware-reported PHY metadata. They do not by themselves
  identify AP-side retries, mesh backhaul load, airtime contention or RF noise.

## Host-side validation

`tests/test-r28-mesh-scan.py` checks band-priority ordering, the 15-second
interval helper, one-pending-request source wiring and worker telemetry. The
r27 scan, mesh-rate, roam-policy, association, queue, RX and report tests remain
in the tree. These checks are not a macOS kext build or RF validation.

---

### 1.0.11 development checkpoint — same-ESS mesh rate and scan experiment (2026-11-09)

Historical internal milestone: r27. This was an experimental same-ESS scan/rate recovery iteration.

This is an experimental source revision based on the r26 mesh-roaming source
and the r26 scan-log toolkit. It has not been built with the macOS SDK or
validated on the user's Mac / mesh APs. Keep r25 as the stable fallback.

## Why this experiment exists

The reported normal-router baseline reached approximately 433 Mbps, while the
same RTL8821CE on the office network's shared-SSID AP group reported 6–27 Mbps
with high ping latency. The scan cache can contain multiple BSSIDs for the same
SSID. This revision treats those as distinct same-ESS AP nodes; a shared SSID
alone does not prove that the APs implement a coordinated mesh protocol.

## Changes

- **One channel per connected scan request.** Candidate channels are sorted and
  visited round-robin, with at most one off-channel channel dwell per connected
  scan request. Disconnected/full scans remain unchanged. This reduces the
  duration of each off-channel burst; it does not control how often CoreWiFi
  requests scans. A complete sweep may consequently take several scan periods.
- **Same-ESS inventory.** The driver counts and logs recently observed,
  security-compatible same-SSID BSSIDs, their channel and RSSI. The rate-
  recovery watch separately requires at least one fresh same-band BSSID.
  Log identifiers include only the final three octets, not the complete BSSID.
  Cache freshness is 60 s to match the slower one-channel scan rotation. Roam
  candidates must still
  match the existing open/WPA2 security compatibility checks; PMF-required or
  incompatible security entries remain excluded.
- **Mesh-specific rate monitoring.** Uses the existing firmware RA report to
  log PHY rate, MCS, NSS, bandwidth, GI and RSSI. A recovery watch is armed only
  on 5 GHz, with negotiated width >=40 MHz, RSSI >= -67 dBm, at least one fresh
  compatible alternate BSSID, and TX rate <=24 Mbps.
- **Conservative rate-adaptation reseed.** After the low-rate condition remains
  for 20 s, the driver resends the peer's already-negotiated RA capability mask
  to firmware, no more than once every 90 s. It does not force a fixed MCS,
  NSS, or channel width. The firmware remains responsible for rate selection.
- **Rate-aware cache roaming.** If CoreWiFi issues a cache-evaluation roam
  request while the persistent-low-rate condition is active, same-band
  candidates may qualify at >= -72 dBm and >=8 dB better than the current BSSID.
  The recovery path excludes cross-band handoffs. The ordinary weak-signal
  policy remains unchanged otherwise. Cache roam cooldown is 45 s.
- **Scan timing diagnostics.** Logs identify the selected scan channel, number
  of cached candidates, round-robin cursor, and elapsed scan-slice time.
- The existing `tools/rtl88wifi-scanlog.sh` collector is updated to capture
  same-ESS inventory, scan-slice, rate-report and RA-reseed messages.

## Deliberate non-goals / limitations

- No fixed-rate/MCS forcing; no claim that this guarantees 433 Mbps.
- No autonomous roam trigger. Cache-based handoff still depends on a
  CoreWiFi `APPLE80211_IOC_ROAM` request.
- No 802.11k Neighbor Report, 802.11v BSS Transition Management, 802.11r Fast
  BSS Transition, 802.11s mesh-point operation, or WPA3-SAE implementation.
- Same SSID nodes are treated as an ESS based on BSSID and security compatibility;
  their mesh controller/backhaul/steering protocol is not inferred.
- One-channel slices reduce the size of each interruption but may lengthen the
  time to discover a candidate on a different channel. The actual CoreWiFi
  scan-request interval is not changed.
- The RA reseed is experimental and needs hardware testing; it may not improve
  a rate-control condition caused by AP-side retries, interference, airtime
  contention or mesh backhaul issues.

## Host-side validation

Run `python3 tests/test-mesh-roaming.py`,
`python3 tests/test-roam-scan-policy.py`, and
`python3 tests/test-mesh-rate-stability.py`, plus the complete `tests/test-*.py`
suite. These test pure policy helpers and source wiring only. They do not
replace an Xcode/macOS kext build or an RF test against the actual AP group.

---

### 1.0.11 development checkpoint — CoreWiFi-requested mesh BSSID handoff (2026-11-08)

Historical internal milestone: r26. This introduced the cache-backed CoreWiFi-requested BSSID handoff path.

unofficial community source update built on the r25 source. No macOS kernel
build or physical Wi-Fi/mesh test has been performed.

## Scope

The source previously had same-SSID BSS discovery and join fallback, but the
`APPLE80211_IOC_ROAM` SET request returned unsupported. r26 adds a request-driven
connected handoff for the internal open/WPA2-PSK station path. It does not run
an independent roaming timer or force CoreWiFi to initiate a roam.

## Candidate policy

- The requested BSSID must be present in the scan cache and have an observation
  no older than 20 seconds. A cache-wide evaluation is treated as a no-op when
  no suitable stronger candidate exists.
- Candidates must have the same SSID, same open/protected class and compatible
  cipher/group-cipher/AKM. PMF-required and SAE-only candidates are excluded.
- For cache-wide evaluation, the current RSSI must be at or below -70 dBm; a
  candidate must be at least -82 dBm and at least 12 dB stronger. Cache-wide
  attempts are rate-limited by a 15-second cooldown. Explicit BSSID requests do
  not use the relative-RSSI threshold, but still require a fresh compatible
  cache entry.
- The previous BSSID remains the visible current network while the new BSSID
  authenticates. Roam success is posted after open association or completion
  of the WPA2 four-way handshake; a failed attempt ends the roam and reports
  failure.

## Limitations and risks

This is not 802.11r Fast BSS Transition. It performs ordinary authentication
and the WPA2 four-way handshake, so brief packet interruption is expected. It
does not implement 802.11k Neighbor Reports or 802.11v BSS Transition
Management, and it does not autonomously decide when to roam. The external Apple
RSN supplicant path, WPA3-SAE, Enterprise/802.1X, PMF-required networks and
true 802.11s mesh-point operation are not supported by this handoff.

The Apple80211 roam payload assumptions, notification sequence, rollback
behavior and actual CoreWiFi invocation still need validation on the target
macOS version and mesh hardware. Keep r25 available as a known fallback until
r26 has been built, installed and tested.

## Validation

`tests/test-mesh-roaming.py` checks the dispatch, freshness and selection
policy helpers, link-latch handling and completion/failure event wiring. These
are host-side source tests only; they do not replace an Xcode kernel build or
a live mesh-roaming test.

---

### 1.0.11 — bounded TX queue bursts and private-address support (2026-11-05)

This is the 1.0.11 source line’s initial documented update, including the queue-burst fix and private-address transport work.

community source update. The macOS kernel extension has not been built with
Apple’s Xcode kernel toolchain or tested on physical hardware. Host-side tests
check the queue-depth configuration and the four-access-category burst bound.

## Changes in r25 — cap family queue bursts and expose queue pressure

The r24 hardware report showed `txq` reaching 256, the output queue's capacity,
while `qdrop` climbed from zero to 4,942. The source set
`getDataQueueDepth()` to 64 per access category. With four ACs, one output-start
pass could therefore pull as many as 256 packets before the next high-water
check ran. A preflight gate cannot prevent a single burst that fills the queue.

- Reduce per-AC dequeue depth from 64 to 8 (maximum 32 packets across four ACs
  per pass).
- Reduce the output-queue gate high-water mark from 128 to 32 and reopen at 16.
  Under the four-AC burst model, one pass can grow the queue to at most 63
  packets, well below the 256-entry family queue capacity.
- Extend driver diagnostics with queue capacity, peak size, output count and
  retry count so the next hardware run can distinguish burst saturation from
  normal backpressure.
- Preserve r24's distinct connected-scan pause, asynchronous home-channel
  resume, and 160-descriptor hardware-ring hysteresis. Mesh scan/roaming policy,
  channel selection and A-MPDU negotiation are unchanged.

## What this does and does not establish

The r24 report is consistent with output-queue burst saturation and bufferbloat:
router ping averaged 865.5 ms, downlink capacity was 4.23 Mbps, and the queue
reached 256 while drops increased. r25 addresses that specific queueing path.
It does not prove the low RF/PHY rate is fixed; r24's submitted report did not
include the follow-up TX-rate/MCS samples. A macOS build and hardware test are
required to establish whether MCS, throughput, packet loss and latency improve.



### Diagnostic tooling update (2026-11-08)

- Added `tools/rtl88wifi-scanlog.sh`, a read-only timed scan/roaming log collector for the existing DiagnosticLog ring.
- Produces a CSV timeline and redacted scan/roam event log; optional upload is limited to a user-confirmed commit into a verified private GitHub repository via GitHub CLI.
- No driver code or runtime radio behavior changed; this is a tooling addition, not a new driver build.

---

### 1.0.10 — open association and Private Wi-Fi Address modes (2026-10-31)

community source update. The macOS kernel extension has not been built with
Apple's Xcode kernel toolchain or tested on physical Wi-Fi hardware; host tests
cover the changed decoder and PRIVATE_MAC handler only.

## Changes

- **Open-network association:** the newer 32-bit ASSOCIATE decoder now accepts
  an empty key object whose embedded key-version is zero, as supplied for an
  unsecured network. WPA2 still requires a version-1 key object and 32-byte
  PMK. This addresses the observed host request that otherwise fell through
  to the Ventura 16-bit parser and appeared as `lower=0, upper=1, ssidLen=0`.
- **PRIVATE_MAC transport:** added a narrowly scoped 28-byte GET/SET bridge for
  selector 238 on the primary interface where the restored family rejects the
  selector before forwarding it to the controller. The split SET hook uses the
  same validated payload handler.
- **Private Wi-Fi Address modes:** Off restores the EFuse/permanent station
  MAC; Fixed retains the host-supplied address or generates one if none is
  supplied; Rotating generates a new locally administered unicast address at
  the requested interval. Host-supplied unicast addresses are preserved as
  supplied, matching Apple's reference behavior.
- **Safe rotation:** changes are serialized through an IOKit workloop timer.
  A rotation that expires during a scan, authentication, association or an
  active link is deferred and retried rather than changing the station MAC
  mid-session. The requested interval is range-checked before milliseconds
  conversion.
- **MAC privacy in logs:** the backend no longer prints every full station
  address when programming it.
- **Country code:** no country is forced or hardcoded. The driver continues to
  use a valid regulatory country delivered by Apple80211 and reports the host
  value; this release does not make macOS replace its currently reported `US`
  with `BD`.
- **Security:** WPA3-SAE remains disabled; WPA2 and eligible transition-mode
  WPA2 fallback remain. This release does not implement OWE, SAE, PMF/BIP,
  or 802.11k/v/r.

## Validation

- `test-assoc-wire.py`: host32 open/no-key version-0 decode, 22-byte SSID,
  legacy misread reproduction, WPA2 and transition tests.
- `test-private-mac.py`: 28-byte ABI, Off/Fixed/Rotating state, supplied and
  generated addresses, interval bounds, pending workloop apply and source
  bridge guards.
- No macOS kernel compilation or over-the-air join validation was possible in
  this build environment. Treat the archive as experimental and retain a
  bootable EFI backup.

---

### 1.0.9 — host association ABI and open-network fix (2026-10-31)

source update, not an upstream release. It has not been built with Apple's
macOS kernel SDK or verified against a physical access point in this
environment.

## Fixed / changed

- **Decode the newer 32-bit host ASSOCIATE payload.** The macOS 15/26 restored
  IO80211 path can pass a 32-bit field layout directly to the native
  `apple80211Request` callback. The driver previously interpreted it as the
  older Ventura structure, whose mode/auth fields are 16-bit. For an open
  network this produced the observed false values `auth lower=0`,
  `auth upper=1`, `SSID length=0`, causing the handler to reject the request
  before it reached the open-system association code. The new path validates
  the 108-byte common prefix with the existing strict `RTW88AssocWire` decoder,
  translates it to the legacy internal structure, and then uses the existing
  join path. The unknown request tail is not parsed.
- **WPA3-SAE remains disabled.** SAE-only requests remain rejected. A transition
  request may use the existing WPA2-PSK fallback only when WPA2-PSK is present
  and the decoded request includes the expected PMK.
- **Diagnostics are corrected.** A lower-auth value other than `1` is no longer
  automatically labelled WPA3. An empty SSID and the exact `lower=0 / upper=1`
  signature are reported as a possible 32-bit/16-bit ABI mismatch, not as proof
  of SAE. Early-rejected association headers are logged with lengths and flags
  only. The report now distinguishes a current result from a stale return value.
- **Country behavior remains host-driven.** The driver has no forced US or BD
  default. It continues to apply a valid country code supplied by Apple80211;
  this release does not claim to correct a country code that macOS itself
  reports as `US`.

## Validation

- Association wire decoder tests pass, including a regression reproducing the
  exact `lower=0 / upper=1 / SSID length=0` misread and verifying that the
  32-bit open request decodes to `lower=1 / upper=0 / SSID length=3`.
- Join-report tests pass.
- Roaming scan-policy source tests pass.
- Apple-only tests requiring `xcrun`/Xcode could not run in the Linux build
  environment. One unrelated test also hits a Linux `thread_t`/`NULL` type
  incompatibility. The macOS kext build and hardware join test remain required.

---

### 1.0.8 — open-network and WPA3-transition handling (2026-10-31)

## Fixed

- Corrected the Association Request Capability Information field. The old base value `0x0431` set the 802.11 Privacy bit even for open networks. Open joins now use `0x0421`; protected WPA2 joins use `0x0431`.
- Made the WPA2 selection policy require the BSS Privacy capability bit. A stale RSN hint or an unexpected PMK can no longer turn a genuinely open BSS into a protected association.
- Extended RSN AKM inspection to identify SAE/FT-SAE and the PMF Required (MFPR) bit.
- Added WPA2-PSK fallback for WPA2/WPA3 transition BSSs only when the AP permits a non-PMF WPA2 association.
- Rejects SAE-only or PMF-required networks clearly, because this driver does not yet implement SAE commit/confirm, PMF negotiation, or BIP management-frame keys.
- Allows the known WPA2-PSK + WPA3-SAE transition auth mask through the newer host association bridge, while keeping SAE-only requests unsupported.

## Security support status

- Open: supported by the open-system authentication path; association Privacy bit is now clear.
- WPA2-Personal (CCMP-PSK): supported by the existing PSK/4-way handshake path.
- WPA2/WPA3 transition: WPA2-PSK fallback only, where PSK is advertised and PMF is optional.
- WPA3-Personal (SAE-only): **not implemented**.
- PMF-required networks: **not implemented; rejected deliberately**.

This release does not claim full WPA3 support. Real WPA3-Personal needs a complete SAE exchange and PMF/BIP support, not just an RSN AKM flag.

## Validation

The host tests for association-wire parsing and join/security policy pass. The full macOS kernel extension build and hardware association tests still need to be run on macOS with Xcode and a supported PCIe adapter. Two unrelated host tests depend on Apple-only SDK facilities and cannot run in the Linux test container.

---

### 1.0.7 — connected mesh scan and cache handling (2026-10-31)

Build identity `1.0.7-rtl88wifi-r18-20261031`. **Source-level tests only; not yet
built with the macOS SDK or run on Wi-Fi hardware.**

- **Connected mesh scans are no longer cache-only.** When CoreWiFi requests a
  scan while associated, the driver now performs a bounded software scan on
  up to eight channels: known alternate BSS channels for the current SSID and
  security class are prioritized, then remaining CoreWiFi-requested channels
  fill the budget. Each off-channel dwell is short and the STA is returned to
  its home channel between channels. Full-band scans remain unchanged while
  disconnected.
- **Partial scans preserve the complete BSS cache.** A connected scan does not
  advance the full-scan generation or age/prune BSS entries on channels it did
  not visit. This prevents a partial result from deleting other mesh nodes.
- **Missing mesh BSSID recovery.** If CoreWiFi asks to join a BSSID that is
  absent from the current cache, the driver performs one full enabled-channel
  scan and retries the exact same request. It never substitutes a different
  BSSID just because it shares the SSID; the request fails explicitly if the
  named node is still not found.
- **Safer 5 GHz upgrade.** A requested 2.4 GHz BSSID is upgraded only when a
  same-security 5 GHz candidate is fresh (at most one full scan old), at least
  -72 dBm, not recently failed, and scores better than the requested node.
- **802.11k/v/r are still unsupported.** The driver does not implement Neighbor
  Report, BSS Transition Management, or Fast BSS Transition/FT key hierarchy.
  The new path is ordinary scan-assisted roaming through CoreWiFi, not an
  11k/v/r implementation.

This does not guarantee an immediate handoff: CoreWiFi chooses whether and
when to reassociate, and the updated path needs real mesh/router testing.

---

### 1.0.6 — diagnostic and scan handling updates (2026-10-25)

Follow-up to a tester's report on a mesh network: the connection is normal at
first, then becomes slow or unstable after roughly 40 to 60 minutes. Build
identity `1.0.6-rtl88wifi-r17-20261025`. **Not yet run on hardware.**

- **Uplink aggregation is now re-negotiated when the AP tears it down.** The
  driver set up the uplink Block Ack agreement (which is what makes transmit
  A-MPDU aggregation possible) exactly once, right after the keys were
  installed. If the AP later sent a DELBA, declined the request, or the response
  was lost, aggregation stayed off for the rest of the association: the link
  stayed up but uploads ran as un-aggregated frames, slow and erratic. The
  driver now asks again, from the existing 5-second diagnostic tick (which
  already runs inside the guard against power transitions), with backoff
  (1, 2, 5, 10, 30, then 60 seconds, restarting after an agreement has proven
  stable for a minute) so an AP that accepts and immediately tears down again
  cannot cause a request storm. A response that never arrives is treated as a
  failure after 3 seconds.
- **The DELBA log line now includes the reason code** (37 declined, 38 unknown
  block ack, 39 timeout), which says why an AP tore the agreement down.
- **`tools/rtl88wifi-join-report.sh` gained two sections**: uplink aggregation
  (events, whether aggregation is on in the latest heartbeat, how many
  heartbeats while connected had it off) and key rekeys and key errors.

This is a defect that fits the symptom, **not a confirmed cause**. Other
candidates that also produce a delay of about an hour are listed in the docs
(key rotation intervals, radio drift with the periodic watchdog disabled,
mesh steering), and the report is meant to tell them apart.

---

### 1.0.5 — diagnostic and compatibility updates (2026-10-25)

Follow-up to a tester's report on 1.0.4 (RTL8821CE, OpenCore): the 5 GHz
preference works; the "Private Wi-Fi address" control in Network settings is
greyed out showing only "Fixed"; and the hotspot report contained no driver
lines. Build identity `1.0.5-rtl88wifi-r16-20261025`. **Not yet run on
hardware.**

- **Private Wi-Fi address: the request behind the control is now answered.**
  macOS reads and writes the mode with `APPLE80211_IOC_PRIVATE_MAC` (238). The
  driver replaces the family's own dispatcher and answered that request
  "unsupported", so System Settings could not read the current mode. It is now
  answered the way Apple's own driver does it: a 28-byte payload (enabled flag,
  flags, rotation interval, current address) whose layout and size were read
  from Apple's IO80211FamilyLegacy and AirPort_BrcmNIC binaries. The driver
  stores the mode macOS sets and reports it back. It does **not** change the
  radio's address from this request: the per-network address is still applied
  by the existing `setHardwareAddress` path before each join. Whether this makes
  the control usable is **unconfirmed**; every request is logged
  (`PRIVATE_MAC get/set`) so the next report shows what macOS sends.
- **The report tool could never see the driver log, and now can.** The driver
  does not write its lines to the macOS system log (macOS shows kernel text from
  kexts as `<private>`); it keeps them in a 32 KB ring buffer published as the
  `DiagnosticLog` registry property. `tools/rtl88wifi-join-report.sh` read the
  system log, which is why every earlier report held no driver lines. It now
  reads the ring (via `ioreg -a`, with a text fallback), shows how long before
  the newest line each event happened, lists every join attempt and every
  Private Wi-Fi address change, and flags a wrapped buffer. Its line arguments
  changed: a number of lines or `all` (no time windows).
- **Fixed in the tool while testing:** one output section printed full MAC
  addresses; all log output now goes through a single redaction step.

Not changed: the iPhone hotspot problem (still no evidence; see the docs for the
one thing to do before rebooting), WPA3, AirDrop/Continuity, TX rate starting low
after idle.

---

### 1.0.4 — 5 GHz band preference and join policy (2026-10-24)

Follow-up to a tester's report on 1.0.3 (RTL8821CE, OpenCore): after boot or a
Wi-Fi off/on the card often joined the 2.4 GHz node of a dual-band network
instead of the 5 GHz one, sometimes needing several tries to reach 5 GHz. Build
identity `1.0.4-rtl88wifi-r15-20261024`. **Not yet run on hardware.**

- **Likely cause was 1.0.2's own change, now fixed.** Node selection gave 5 GHz
  only +5 dB over 2.4 GHz, but 2.4 GHz is usually a few dB *stronger* at the
  same spot, so the winner flipped between bands with small signal changes
  between scans. A usable 5 GHz node (>= -72 dBm, seen in the latest scan) now
  beats any 2.4 GHz node; marginal 5 GHz still loses to a good 2.4 GHz link.
- **1.0.2's "requested BSSID not in the scan cache, use any other node" is
  removed.** It could silently turn a request for the 5 GHz node into a 2.4 GHz
  join. An unknown BSSID reports "not found" again, as the original driver did.
- **New, switchable: a requested 2.4 GHz node is upgraded to 5 GHz.** If macOS
  itself names a 2.4 GHz node but a fresh, usable 5 GHz node of the same SSID
  and security type is known (and has not just failed), the driver joins the
  5 GHz node. If it then fails, the node macOS asked for is the fallback. Set
  the Info.plist key `RTL88WiFiPrefer5GHz` to `false` to honour the requested
  BSSID exactly (`PREFER_5GHZ_POLICY` in the registry shows the setting).
- **Every join request is now logged**, including the reason for each early
  refusal (for example a WPA3-only request), plus one line per join saying
  whether macOS named a BSSID, how many 2.4/5 GHz nodes were known, and which
  band was chosen. Lengths and flags only: no key bytes, no BSSID.
- **`tools/rtl88wifi-join-report.sh` fixed**: its filter could pick up an
  unrelated macOS message that merely mentioned the folder name, so a report
  could contain no driver lines at all. It now matches the driver's own prefix,
  summarises each join attempt found in the log, and accepts a longer window
  or `boot`.

Not changed: the iPhone hotspot problem (cause still unknown, evidence now
captured per attempt), WPA3, AirDrop/Continuity, TX rate starting low after
idle.

---

### 1.0.3 — protected association and diagnostic updates (2026-10-24)

Follow-up to 1.0.2 after a tester's report on an RTL8821CE: 1.0.2 built and
loaded, the noise value now shows, and upload speed improved; mesh joining has
not been tested yet and an iPhone hotspot still does not connect. Build
identity `1.0.3-rtl88wifi-r14-20261024`. **1.0.3 itself has not been run on
hardware.** - **Protected joins no longer fall back to "no security".** If macOS asked for
  a protected PSK join and supplied the 32-byte key, but the driver's simple
  beacon parser did not recognise the AP's security, the driver associated with
  no RSN element and then declared the link up with no keys. No protected AP
  accepts that. A PMK on a protected BSS is now trusted as WPA2-CCMP-PSK, since
  macOS parsed the AP's full RSN element before asking. Open networks and joins
  without a PMK are unchanged.
- **One log line per join shows what the AP advertises**: channel, signal,
  capability bits, and the AP's RSN element (AKM list and capability bits),
  plus whether the driver chose WPA2. No network name and no BSSID is logged.
- **New tool `tools/rtl88wifi-join-report.sh`** (read-only): run right after a
  failed join; it shows what macOS asked the driver for, decodes a refusal
  (for example a WPA3-only request) in plain words, and prints the driver log
  with MAC addresses and the network name redacted.

The iPhone hotspot problem is **not** fixed: no defect that explains it was
found by reading the code, and the report tool exists to find out which of the
likely causes it is (see the docs). Also unchanged: the TX rate that starts low
after the link has been idle (firmware rate adaptation; see the docs).

---

### 1.0.2 — mesh selection, noise reporting and AWDL policy (2026-10-23)

Targets the instability reported on RTL8821CE: noise shown as 0, upload speed
dropping, and mesh Wi-Fi sometimes failing to connect. Build identity
`1.0.2-rtl88wifi-r13-20261023`. Details, reasoning and limits:
[docs/FIXES-1.0.2.md](docs/FIXES-1.0.2.md).

**Status:** one tester has built and run this on an RTL8821CE (noise shows,
upload improved; mesh not yet tested). The author of the changes has no Mac or
card of their own: they were checked by reading the code and by host tests that
compile the changed functions (`tests/test-join-policy.py`, plus the existing
suites). Keep the previous EFI kext as a backup.

- **Noise no longer shows 0.** The RTL8821C parser never read the per-path RX
  SNR that its PHY status already carries (the field macros existed in
  `rtw8821c.h`); it now does, as the 8822C parser does. When no plausible SNR is
  available (idle 2.4 GHz link, no samples yet), noise falls back to the thermal
  noise floor for the channel width (−95 / −92 / −89 / −86 dBm for 20 / 40 / 80 /
  160 MHz). This is an estimate; `RADIO_NOISE_SOURCE` in the registry says
  `measured` or `estimated`. Other networks in the list now carry the same
  estimate instead of 0.
- **Upload drops and stalls: AWDL no longer takes the radio.** While the
  `awdl0` interface existed, the AWDL scheduler put the NIC in near-promiscuous
  receive mode and repeatedly retuned the radio to channels 6/44/149; during
  those windows en0 transmit was stalled, so a full-rate upload overflowed the
  256-packet output queue. AWDL has never found a peer on this driver, so the
  cost bought nothing. By default the AWDL interface now exists but never
  touches the radio, the RX filter, or the scheduler timer. Set the Info.plist
  key `RTL88WiFiAWDLRadio` to `true` to restore the old behaviour
  (`AWDL_RADIO_POLICY` in the registry shows the active policy).
- **Mesh: joining picks the best node.** The driver used to join the first
  list entry with a matching SSID, even if it was weak or stale. It now ranks
  nodes by signal, freshness and band, and demotes nodes that just failed.
- **Mesh: join failures are reported and retried on another node.** A rejected
  authentication or association (for example status 17 or 30 from a node that
  is band-steering or full) used to leave the driver silently idle, so macOS
  never learned the join had failed and retried the same node. Now the driver
  moves to the next node of the same SSID (up to 3 nodes per join, never
  crossing between protected and open), and only then reports the failure. A
  BSSID that macOS requests but that has aged out of the scan cache falls back
  to another node of that SSID instead of failing. Single-AP networks behave as
  before.

Not fixed (see the docs for why): WPA3/SAE, PMF-required networks, AirDrop and
Continuity, roaming between nodes while connected, 802.11k/v/r.

---

### 1.0.1 — final maintenance history (2026-10-14)

Final maintenance release. It only corrects what macOS shows in System
Information (`system_profiler SPAirPortDataType`) and the Option-click Wi-Fi
menu. Throughput, connecting, sleep/wake and the data path are unchanged.
Build identity `1.0.1-rtl88wifi-r12-20261014`.

- **Transmit Rate and MCS Index** now show the card's real current transmit
  rate (for example 866 Mbps, MCS 9 on an 80 MHz 802.11ac link). Before, they
  showed the router's fastest basic rate (displayed as 108) and MCS 0. Right
  after joining, both stay empty for a moment until the card reports its
  first rate; no placeholder value is shown.
- **Signal / Noise** no longer shows a fixed −95 dBm noise. On RTL8822BE and
  RTL8822CE the noise value comes from the signal-to-noise ratio the card
  measures on the connected network (noise = signal − SNR; the cards have no
  direct noise-floor measurement, so this is an estimate). RTL8821CE does not
  measure SNR, so it reports no noise value. Other networks in the list show
  no noise value (0) instead of −95 dBm.
- **Channel width of nearby networks** now shows 40 or 80 MHz when the network
  uses it, instead of always 20 MHz.
- **Supported Channels** now follow the Wi-Fi country code: channel 14 is
  listed only in Japan, and channels 12–13 are hidden in the US, Canada and US
  territories. Elsewhere (for example Brazil) channels 1–13 are listed. When
  macOS has not set a country, the full list is shown as before.

Not changed in 1.0.1:

- **Card Type** shows the Realtek vendor ID and the card's PCI subsystem ID
  (for example `0x10EC, 0xC123` on some RTL8822CE boards). The value comes
  from the card itself; the driver does not set it.
- **AirDrop and Auto Unlock** are still listed as "Supported" although they
  do not work. The capability flags behind them are kept because changing
  them risks breaking driver loading.

These fixes have been built and checked for compilation only; they have not
been tested on hardware.

---

### Original upstream discontinuation notice (2026-10-06)

Development has stopped. 1.0.0 is the final release; the kext in `Kexts/` is
unchanged. The README lists the remaining issues, which will not be fixed.

- Removed unused source files (Linux-only chip, transport and optional
  feature code, unreachable compatibility headers, an unbuilt kext class).
  The driver still builds to the same binary.
- Test fixtures use generic network names and addresses.

---

### 1.0.0 — first release under the RTL88WiFi name (2026-10-02)

First release under the RTL88WiFi name.

- Driver, executable and bundle renamed to `RTL88WiFi`
  (`io.github.x1ren41l.RTL88WiFi`), with native controller/interface classes
  `RTL88WiFi` / `RTL88WiFiInterface`. Build identity
  `1.0.0-rtl88wifi-r11-20261002`.
- WPA2 handshake retries, key installation and group rekeys fixed; stable
  SNonce; idempotent key install.
- Router HT/VHT capabilities parsed and used (5 GHz at line rate).
- Memory, firmware-bounds and station-lifetime fixes.
- Correct disconnect reasons, Sonoma-format network info, SSIDs kept in scan
  results, AP IE list ABI fix.
- Beacon TIM kept for the connected network and scan padding no longer
  copied (hidden-network label after wakes and network switches).
- Undecrypted/plaintext frames on protected links dropped; FragAttacks
  A-MSDU check; multicast and NoAck QoS traffic bypass RX reordering.
- Output-pull limit and two experimental output gates. On the current
  IO80211 push data path these gates do not engage; they are kept for
  diagnostics.
- Built-in `DiagnosticLog` with queue drop/stall counters.
- Added `tools/rtl88wifi-check.sh`, `docs/COMPATIBILITY.md` and issue
  templates for compatibility reports.

Hardware verification (RTL8821CE, Sonoma 14.8.9): load and join, ~15 minutes
of load and idle without link drops, 0% idle ping loss, `networkQuality`
86–87 down / 89–105 up Mbps. Known remaining issue: queue drops under heavy
parallel uploads (see README).

---
