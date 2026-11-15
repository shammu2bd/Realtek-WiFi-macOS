# RTL88WiFi

Native macOS Wi-Fi support for Realtek **RTL8821CE, RTL8822BE and RTL8822CE** PCIe cards on Hackintosh systems. This source tree is an unofficial community-maintained continuation of a project whose original upstream release history is marked discontinued.

> **Current source version: RTL88WiFi 1.0.13.** This release adds a bounded 802.11k Neighbor Report request/response path and 802.11v BSS Transition Management handling on top of the existing WPA2/WPA3 and same-ESS roaming work.

This release is provided as a complete source archive. Build the kext on the target Mac using Xcode; this package does not contain a newly built or signed kext. Keep a bootable EFI backup and your previously working kext for rollback.

## 1.0.13 changes

- Advertises 802.11k Neighbor Report support only when the associated AP advertises the Neighbor Report capability and the connection uses a supported internal CCMP security path.
- Sends a bounded Neighbor Report Request, validates the response action category/action/token/IE lengths, and stores candidate BSSID/channel/preference entries for a limited lifetime.
- Advertises the 802.11v BSS Transition capability only when the AP advertises it and the controller's PM-fenced control timer is available.
- Parses BTM Requests and their candidate list, supports an intra-ESS candidate handoff, and uses a fresh Neighbor Report list as a fallback only when the AP omits the Preferred Candidate List.
- BTM candidate selection requires a fresh scan-cache observation, the same SSID and privacy mode, matching supported CCMP security, a valid unicast BSSID, an enabled channel, and WPA3 SAE+PMF compatibility when the current link uses WPA3.
- If no listed candidate is already usable in the cache, the driver can request one directed connected scan on the highest-preference regulatory-enabled candidate channel. A BTM acceptance is sent only after a matching candidate is observed.
- The driver waits for the response frame's TX ACK before invoking the existing `cmdRoam()` path. WPA3 response ACK matching binds the protected-frame header identity and CCMP packet number; it does not inspect ciphertext as plaintext.
- The source bundle, kmod and `DriverBuild` identity are now `1.0.13`. Historical release details remain in the consolidated [CHANGELOG.md](CHANGELOG.md).

## 802.11k / 802.11v scope and limits

This is **Neighbor Report only**, not full Radio Measurement support. The station does not advertise Beacon Measurement, Link Measurement, channel-load, noise or location measurement capabilities, and it does not implement general Beacon Measurement request/report exchanges.

BTM is limited to same-ESS BSS candidates and the driver's existing association/roam path. BSS Termination and ESS Disassociation URL modes are parsed safely but rejected; the driver does not fetch URLs or leave the ESS on an AP's behalf. Candidate information is a hint, not authorization: the AP-supplied BSSID is never joined unless the driver's fresh scan cache independently confirms the target and security profile. If the target cannot be found in the one directed scan, the driver declines the request. 802.11r Fast Transition is not implemented; every accepted WPA3 roam uses a fresh SAE exchange through the existing path.

The 802.11k/v features are enabled only for the driver's internal WPA2-Personal/CCMP and WPA3-Personal/CCMP paths. External supplicant, Enterprise/802.1X, open, TKIP and unsupported security combinations are not advertised as supported for these management features. WPA3 robust management actions must pass the existing PMF authentication/decryption path.

## Existing band preference behavior

The default `RTL88WiFiPrefer5GHz` property is enabled. For a pinned 2.4 GHz request, an upgrade requires a same-SSID BSS that passes the WPA3 SAE+PMF profile check, is seen in the current or immediately previous scan generation, has RSSI of at least -72 dBm, has not recently failed, and scores better than the requested node. This is a preference, not an unconditional 5 GHz lock: an exceptionally stronger 2.4 GHz candidate can still win, and stale/weak 5 GHz entries cannot displace a better candidate. The driver does not force a channel, country, transmit rate or channel width.

## Compatibility

| Chip | PCI ID | Status |
|---|---|---|
| RTL8821CE | `10ec:c821`, `10ec:b821` | Primary target platform; new 1.0.13 management-frame work requires hardware validation |
| RTL8822BE | `10ec:b822` | Supported, needs reports |
| RTL8822CE | `10ec:c822`, `10ec:c82f` | Supported, needs reports |

| macOS | Status |
|---|---|
| Sonoma 14 | Previously verified on 14.8.9 |
| Sequoia 15 / Tahoe 26 | Needs reports; target user reports WPA3-Personal operation on macOS 15.8.1 with the preceding source line |
| Ventura 13.7.7–13.7.8 | Add only `RTL88WiFi.kext` (no other kexts or Block entry); needs reports |
| Monterey and older | Unsupported |

PCIe only; USB and SDIO adapters are not supported. See [docs/COMPATIBILITY.md](docs/COMPATIBILITY.md).

## Diagnostics

```sh
bash tools/rtl88wifi-check.sh           # chip, macOS, kexts, link
bash tools/rtl88wifi-check.sh --speed   # plus ping and networkQuality
```

For timed scan/mesh-roaming captures, see [tools/SCANLOG-GITHUB.md](tools/SCANLOG-GITHUB.md).

## Build

```sh
make -C driver/RTL88WiFi clean
make -C driver/RTL88WiFi rtl88wifi
```

Expected output: `driver/RTL88WiFi/build/out/RTL88WiFi.kext`. Requires Xcode Command Line Tools, the macOS SDK/kernel headers included in the project and `python3`. Load the kext through OpenCore, not `make install`. See [INSTALL.md](INSTALL.md) and [tests/README.md](tests/README.md).

## Status and known limits

Versions 1.0.2–1.0.13 in this tree are unofficial community source updates to an upstream project whose release history is marked discontinued. The 1.0.13 802.11k/v code has passed host-side parser and source-integration tests, but it has not been natively built, signed, loaded or exercised over the air. A target-Mac Xcode build and real AP interoperability test are required before replacing a working kext. No 802.11r FT, full RRM beacon measurement, autonomous roaming, true 802.11s mesh-point mode, AirDrop or Continuity is claimed.

## License

GPL-2.0. See [LICENSE](LICENSE) and [NOTICE.md](NOTICE.md).
