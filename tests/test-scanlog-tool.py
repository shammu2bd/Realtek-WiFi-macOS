#!/usr/bin/env python3
"""Static regression checks for the macOS scan-log collector."""
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
script = ROOT / "tools" / "rtl88wifi-scanlog.sh"
text = script.read_text()
checks = {
    "uses driver DiagnosticLog ring": "DiagnosticLog" in text and "get_ring()" in text,
    "records scan and roam events": "scan-events.log" in text and "roam" in text,
    "records r27 same-ESS/rate events": "mesh ESS" in text and "mesh rate" in text and "mesh RA" in text,
    "creates CSV time series": "samples.csv" in text,
    "records TX rate/MCS/bandwidth": "tx_rate_mbps,tx_mcs,tx_nss,tx_bw_mhz,home_bw_mhz" in text and "RATE_LINE" in text,
    "counts actual roam transitions only": "rtw88: mesh roam (start|complete|failed)" in text,
    "extracts latest DIAG counters": "DIAG=$(grep" in text and "DIAG sample=" in text and '"$CURRENT"' in text and "get_num()" in text,
    "private repository upload only": "repos/$GITHUB_REPO/contents/$REMOTE_PATH" in text and "VISIBILITY" in text and "PRIVATE" in text,
    "upload requires explicit flag": "--upload-github" in text and "--repo" in text,
    "upload is not a public gist": "gh gist create" not in text and "--public" not in text,
    "upload confirmation prompt": "Upload this redacted diagnostic ZIP to PRIVATE repository" in text,
    "MAC pseudonymization": "AP-" in text and "hmac.new" in text and "MAC_SALT" in text,
    "SSID redaction": "[SSID-redacted]" in text,
    "IP redaction": "[IP-redacted]" in text,
    "key/secret redaction": "[secret-redacted]" in text,
    "does not invoke scan command": "airport --scan" not in text and "wdutil scan" not in text,
}
result = subprocess.run(["bash", "-n", str(script)], capture_output=True, text=True)
checks["bash syntax"] = result.returncode == 0
for name, ok in checks.items():
    print(("PASS" if ok else "FAIL") + "  " + name)
if result.returncode:
    print(result.stderr)
raise SystemExit(0 if all(checks.values()) else 1)
