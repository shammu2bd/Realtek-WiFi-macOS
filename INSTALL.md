# Build and install RTL88WiFi 1.0.12

This package is a complete source archive for **RTL88WiFi 1.0.12**. Build the kext on the target Mac with Xcode 16.4 or a compatible Apple kernel toolchain. Do not install a kext binary copied from an older archive.

## Build

From the extracted project root:

```sh
make -C driver/RTL88WiFi clean
make -C driver/RTL88WiFi rtl88wifi
```

Expected output:

`driver/RTL88WiFi/build/out/RTL88WiFi.kext`

This source package does not include a newly compiled, signed or notarized macOS kext. Host tests cannot replace the target Mac build.

## Install

Use the existing OpenCore installation process for the target machine. Keep a bootable EFI backup and preserve your previously working kext so you can roll back. Do not replace the installed driver until the new kext builds successfully and the built bundle reports version `1.0.12`.

## WPA3 and band-preference test

1. First confirm WPA3-Personal still joins and passes traffic on the same SSID.
2. Verify the selected channel using Option-click Wi-Fi details or the driver's current-channel diagnostics.
3. When the same SSID has both bands, confirm that a fresh 5 GHz BSSID with RSSI at least -72 dBm wins over the requested 2.4 GHz BSSID when its shared join score is better.
4. Verify that a weak/stale 5 GHz candidate does not displace a better 2.4 GHz candidate, and that a BSSID missing from the scan cache still triggers the normal one-refresh path instead of an arbitrary AP substitution.
5. Test WPA3 transition mode separately after WPA3-only operation is confirmed.

The default `RTL88WiFiPrefer5GHz` personality property is enabled. Setting it to false disables upgrading a pinned 2.4 GHz request. The preference does not force a country, channel, MCS or bandwidth and does not autonomously roam an already-connected station.

See the consolidated [CHANGELOG.md](CHANGELOG.md) and [VALIDATION-1.0.12.md](VALIDATION-1.0.12.md).
