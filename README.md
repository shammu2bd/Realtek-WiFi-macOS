# RTL88WiFi

Native macOS Wi-Fi support for Realtek **RTL8821CE, RTL8822BE and RTL8822CE** PCIe cards on Hackintosh systems. This source tree is an unofficial community-maintained continuation of a project whose original upstream release history is marked discontinued.

> **Current source version: RTL88WiFi 1.0.12.** The previous 1.0.11 source line introduced native WPA3-Personal SAE and PMF/BIP support, which the user has confirmed works on the target RTL8821CE. Version 1.0.12 applies the existing 5 GHz band-preference policy to the WPA3/SAE join and retry paths. The preference is enabled by default and remains subject to candidate freshness, signal strength, security compatibility and failed-BSSID history.

This release is provided as a complete source archive. Build the kext on the target Mac using Xcode; this package does not claim to contain a newly built or signed kext. Keep a bootable EFI backup and your previously working kext for rollback.

## 1.0.12 changes

- WPA3 joins now score matching SAE+PMF BSSIDs using the same RSSI, freshness and band policy as WPA2.
- A known pinned 2.4 GHz BSSID can be upgraded to a fresh, usable 5 GHz sibling on the same SSID when the 5 GHz candidate's score is better.
- Unpinned WPA3 joins prefer a fresh usable 5 GHz candidate through the common join score.
- SAE retry/fallback selection also uses the band-aware selector, avoiding a return to 2.4 GHz simply because its RSSI is strongest.
- Unknown pinned BSSIDs remain explicit cache misses; the driver still performs its normal one-refresh path and does not silently substitute an unrelated BSSID.
- The kext bundle, kmod and DriverBuild identity are now `1.0.12`. New builds use semantic version names (`RTL88WiFi-1.0.12.zip`), not internal `rXX` suffixes.
- All project release history is now in the single [CHANGELOG.md](CHANGELOG.md).

## Band preference behavior

The default `RTL88WiFiPrefer5GHz` property is enabled. For a pinned 2.4 GHz request, an upgrade requires a same-SSID BSS that passes the WPA3 SAE+PMF profile check, is seen in the current or immediately previous scan generation, has RSSI of at least -72 dBm, has not recently failed, and scores better than the requested node. When macOS does not pin a BSSID, the same shared score ranks all WPA3-capable matching nodes. This is a preference, not an unconditional 5 GHz lock: an exceptionally stronger 2.4 GHz candidate can still win, and stale/weak 5 GHz entries cannot displace a better candidate. The driver does not force a channel, country, transmit rate or channel width.

## Security and feature scope

The source includes WPA2-Personal, WPA3-Personal SAE with PMF/BIP, open-network association, same-SSID BSSID selection, WPA3 group rekeys and an experimental same-ESS handoff that performs a fresh SAE exchange. WPA3-Enterprise/802.1X, OWE/Enhanced Open, 802.11r Fast Transition, Wi-Fi Alliance certification, true 802.11s mesh mode, AirDrop and Continuity are not supported or not claimed. TKIP is untested.

## Compatibility

| Chip | PCI ID | Status |
|---|---|---|
| RTL8821CE | `10ec:c821`, `10ec:b821` | Primary user platform; 1.0.12 band change still needs testing |
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

The original upstream release history is marked discontinued; versions 1.0.2–1.0.12 in this tree are unofficial community source updates. Each new release requires its own target-Mac Xcode build and hardware validation. The 1.0.12 5 GHz preference path is not yet hardware-tested. WPA3-Personal working operation has been reported by the user on the previous source version, while the new WPA3 5 GHz selection behavior still needs confirmation. The driver does not force a regulatory country; it follows a valid country supplied by Apple80211.

Known limitations also include no 802.11k/v/r fast roaming, no autonomous roaming, no true 802.11s mesh-point mode, and no AirDrop/Continuity support. See the consolidated [CHANGELOG.md](CHANGELOG.md) for the complete history.

## License

GPL-2.0. See [LICENSE](LICENSE) and [NOTICE.md](NOTICE.md).
