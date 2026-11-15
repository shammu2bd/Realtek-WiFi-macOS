# Host validation

The host regression suites exercise the actual driver functions with host substitutes
for kernel/hardware services, using ASan/UBSan. They cover firmware bounds,
HT/VHT peer capabilities, station lifetime, diagnostic buffers, WPA2
handshake/GTK rekeys, protected RX and A-MSDU filtering, and scan SSID/TIM
handling, and (1.0.2) multi-BSS mesh join selection/fallback and noise
reporting (`test-join-policy.py`), bounded connected-scan policy
(`test-roam-scan-policy.py`), plus same-ESS BSSID-aware scan rotation and mesh rate recovery
(`test-mesh-rate-stability.py`), plus the join-report tool (`test-join-report.py`,
which uses fake `ioreg`/`ifconfig`) the Private Wi-Fi address request
(`test-private-mac.py`) and uplink Block Ack recovery (`test-ba-recovery.py`). Timer lifecycle checks inspect source ordering rather than execute
IOKit. WPA3 regression coverage includes SAE/PMF/CCMP cryptographic host tests,
association-path integration checks and the 1.0.12 same-SSID 5 GHz candidate
preference (`test-wpa3-band-preference.py`). These host suites do not establish
kernel load or hardware behavior.

Run from the repository root on macOS with Xcode Command Line Tools:

```sh
python3 tests/test-focused.py
python3 tests/test-group-key.py
python3 tests/test-handshake.py
python3 tests/test-rx-filter.py
python3 tests/test-scan-ssid.py
python3 tests/test-join-policy.py
python3 tests/test-join-report.py
python3 tests/test-private-mac.py
python3 tests/test-ba-recovery.py
python3 tests/test-roam-scan-policy.py
python3 tests/test-tx-queue-backpressure.py
python3 tests/test-mesh-roaming.py
python3 tests/test-wpa3-integration.py
python3 tests/test-wpa3-band-preference.py
python3 driver/RTL88WiFi/experimental/wpa3/test_host.py
```

Build the complete driver with `make -C driver/RTL88WiFi rtl88wifi`.

### TX queue backpressure (r25)

`python3 tests/test-tx-queue-backpressure.py` checks the per-AC dequeue depth,
output queue high/low watermarks, one-burst bound across four WMM ACs, retained
r24 scan/ring separation, and expanded queue diagnostics. It is a source/model
regression check, not a macOS kernel or hardware test.

### CoreWiFi-requested mesh roaming (r26)

`python3 tests/test-mesh-roaming.py` checks roam-selector dispatch, fresh
same-ESS cache policy, conservative candidate thresholds/cooldown, preserving
the old visible BSSID during association, and roam completion/failure events.
It is a host-side policy/source regression test only; it cannot validate the
Apple80211 payload contract or actual roaming on macOS hardware.

### Scan-log collector

`python3 tests/test-scanlog-tool.py` checks the macOS scan-log collector's Bash syntax, privacy-redaction rules, read-only behavior, CSV/event outputs, and verified-private-repository upload contract. It is a host-side/static check, not a macOS hardware test.


### Same-ESS mesh rate / scan experiment (r27)

`python3 tests/test-mesh-rate-stability.py` validates the policy gates for
strong-signal low-rate monitoring, one-channel-per-connected-scan round-robin,
same-SSID/different-BSSID inventory, same-band rate-recovery candidates and
firmware RA-mask reseeding. `test-mesh-roaming.py` and
`test-roam-scan-policy.py` also cover the updated roaming and scan policy. These
are host-side policy/source checks; no real RF behavior is simulated.


### UniFi multi-AP scan lifecycle (r29)

`python3 tests/test-r29-scan-lifecycle.py` checks the atomic scan reservation,
preservation and retry of pending native scan requests, conservative stale-latch
reconciliation, manual-worker scan completion, same-band BSSID discovery priority,
15-second connected-scan throttle retry timing, and the expanded scan-log telemetry. The test validates source/policy structure;
it does not emulate CoreWiFi callback concurrency or prove RF behavior on UniFi APs.


### WPA3-Personal and same-SSID band preference (1.0.12)

`python3 tests/test-wpa3-band-preference.py` compiles the real shared join
scoring/eligibility helper and checks that the SAE initial-join, retry and
authentication retry-budget paths use the WPA3-capable selector. It covers a
fresh usable 5 GHz sibling winning over a same-SSID 2.4 GHz candidate, while
stale, weak and recently failed 5 GHz entries do not trigger a pinned upgrade.
`python3 tests/test-wpa3-integration.py` guards the WPA3 native join wiring.
`driver/RTL88WiFi/experimental/wpa3/test_host.py` exercises SAE H&P/H2E,
Commit/Confirm, the production four-way handshake, PMF/replay and CCMP/AES.
These remain host checks; the selected over-the-air BSSID and 5 GHz band must
be confirmed on the target Mac.
