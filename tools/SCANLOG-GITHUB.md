# RTL88WiFi scan/roaming diagnostic capture

`rtl88wifi-scanlog.sh` captures the driver's existing diagnostic ring without
changing radio behavior. It is intended for the RTL8821CE built-in Wi-Fi driver
on macOS and works with r26+ `DiagnosticLog` properties. On r27-r29 it also captures same-ESS BSSID inventory, scan-slice timing, firmware TX-rate reports, rate-adaptation reseeds, scan-worker stages, pending scan-request coalescing, connected-scan rate limits and r29 throttle-retry/completion lifecycle events.

## Recommended mesh capture

1. Boot with the r26 mesh-roaming, r27 mesh-rate/scan, r28 mesh-scan, or experimental r29 UniFi scan-lifecycle build.
2. Connect to the mesh network you want to investigate.
3. Open Terminal in the extracted source folder.
4. Start a five-minute capture:

   ```bash
   bash tools/rtl88wifi-scanlog.sh --duration 300 --interval 2
   ```

5. During capture, use Wi-Fi normally. Do not manually toggle Wi-Fi or change
   the AP unless that is part of the test. Note the exact time if you move
   between mesh nodes.
6. The ZIP appears in `~/Documents/RTL88WiFi-ScanLogs/`.

For a longer roaming test, use `--duration 900 --interval 2`.

## Upload to a private GitHub repository

The uploader requires an existing repository with **PRIVATE** visibility. It
checks repository visibility before offering upload and asks for confirmation.
It does not upload to a public repository or create a public/secret Gist.

Install and authenticate GitHub CLI once:

```bash
brew install gh
gh auth login
gh auth refresh -s repo
```

Create a private repository on GitHub (or use an existing private repository).
For example, the GitHub CLI can create one:

```bash
gh repo create rtl88wifi-diagnostics --private --add-readme \
  --description "Private RTL88WiFi hardware diagnostics"
```

Then run the capture and upload command, replacing `YOUR_GITHUB_NAME` with
your GitHub account name:

```bash
bash tools/rtl88wifi-scanlog.sh --duration 300 --interval 2 \
  --upload-github --repo YOUR_GITHUB_NAME/rtl88wifi-diagnostics
```

After capture, the script checks `gh auth status`, verifies that the target
repository is private, shows the destination branch and requests confirmation.
It then uploads the ZIP under
`diagnostics/rtl88wifi-scanlogs/` using your local GitHub CLI authentication.
No access token is saved in the project. The ZIP remains on the Mac whether
upload succeeds or is declined.

## What is captured

- Driver build, macOS version/build, kernel and Mac model
- Interface link status, channel, RSSI and noise-source indicator
- Newly observed scan, connected-scan, same-ESS BSSID inventory, scan-slice
  timing, association, roaming, aggregation, firmware TX-rate and (r27/r28)
  rate-adaptation reseed, scan-worker stage, pending-request and scan-rate-limit log lines
- CSV time series of channel, RSSI, aggregation state, TX queue depth, stall,
  drop and retry counters; r29 adds TX-rate Mbps, MCS, NSS, TX bandwidth and
  home-channel bandwidth when those values appear in the diagnostic ring
- The existing privacy-redacted `rtl88wifi-join-report.sh` output

## Privacy and limitations

The collector does not preserve network names, real BSSIDs, MAC addresses,
IP/gateway addresses, passwords or key material. Each full MAC/BSSID is
replaced with a capture-specific HMAC pseudonym, preserving node correlation
inside one capture; the random salt is not saved, so labels cannot be correlated
across different captures. SSIDs, IP addresses and key-like values are redacted.
Review the ZIP before uploading anyway. It includes Mac model and OS build,
which can reveal device/software details.

The driver's `DiagnosticLog` is a bounded in-memory ring. It can wrap. A 1-2
second sampling interval helps preserve newly appended scan events, but this is
not a packet capture and cannot recover events that were overwritten before a
sample. The tool is read-only: it does not start scans, initiate roaming, alter
scan timing, run networkQuality, or change driver settings.

The ZIP is a diagnostic artifact, not a driver build. Current release builds report the semantic version in `DriverBuild` (for example, `1.0.12`). The consolidated project history is in the root `CHANGELOG.md`.
