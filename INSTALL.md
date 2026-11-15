# Build and install RTL88WiFi 1.0.13

This package is a complete source archive for **RTL88WiFi 1.0.13**. Build the kext on the target Mac with Xcode 16.4 or a compatible Apple kernel toolchain. Do not install a kext binary copied from an older archive.

## Build

From the extracted project root:

```sh
make -C driver/RTL88WiFi clean
make -C driver/RTL88WiFi rtl88wifi
```

Expected output: `driver/RTL88WiFi/build/out/RTL88WiFi.kext`.

This source package does not include a newly compiled, signed or notarized macOS kext. Host tests cannot replace the target Mac build.

## Install

Use the existing OpenCore installation process for the target machine. Keep a bootable EFI backup and preserve your previously working kext so you can roll back. Do not replace the installed driver until the new kext builds successfully and the built bundle reports version `1.0.13`.

## 802.11k Neighbor Report test

1. Use an AP that advertises the Neighbor Report capability (RRM Enabled Capabilities IE, bit 1 in the first octet).
2. Reassociate after installing the new kext and inspect logs for `802.11k neighbor request submitted` and `802.11k neighbor response accepted`.
3. Check that a response with a stale/wrong dialog token or malformed Neighbor Report IE is rejected and does not alter the current association.
4. Neighbor Reports are hints only. A reported BSSID/channel is not joined until a matching same-SSID BSS is freshly observed and passes the security preflight.

## 802.11v BSS Transition Management test

1. Use an AP that advertises BSS Transition Management in Extended Capabilities (bit 19), and ensure the controller reports `ROAMING_CONTROL_TIMER_AVAILABLE`.
2. First test a normal WPA2-Personal/CCMP connection, then test WPA3-Personal/CCMP with PMF. Confirm that WPA3 BTM action frames pass the PMF verification path.
3. Trigger an AP BTM request with a Preferred Candidate List. Confirm the driver selects only a fresh same-ESS candidate, and logs `BTM directed scan started` when a scan is needed.
4. Confirm the driver sends BTM Accept only after candidate validation, and starts the roam only after the matching BTM response TX ACK. If no candidate is found, it should send a decline and stay on the current AP.
5. Test a BTM request without a Preferred Candidate List only after a fresh Neighbor Report response has been received; the Neighbor Report list may then be used as the candidate hint.
6. Confirm unsupported BSS Termination and ESS-Disassociation modes are declined. No 802.11r Fast Transition should be expected.

The implementation uses a bounded one-channel directed scan and respects the connected-scan throttle and regulatory enabled-channel list. Candidate scans can be declined when the BTM validity/disassociation deadline is too short or the required channel cannot be scanned. These limitations are intentional safety gates.

## Existing WPA3 / band preference regression

1. Confirm WPA3-Personal still joins and passes traffic on the same SSID.
2. When the same SSID has both bands, confirm that a fresh 5 GHz BSSID with RSSI at least -72 dBm wins over the requested 2.4 GHz BSSID when its shared join score is better.
3. Verify that a weak/stale 5 GHz candidate does not displace a better 2.4 GHz candidate.

See [CHANGELOG.md](CHANGELOG.md), [VALIDATION-1.0.13.md](VALIDATION-1.0.13.md) and [tests/README.md](tests/README.md).
