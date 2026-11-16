#!/bin/bash
# Read-only RTL88WiFi 1.0.13 mesh / 802.11k / 802.11v diagnostic capture.
# Produces a privacy-redacted capture and pushes selected TEXT files and the
# redacted ZIP to the user's PRIVATE RTL88WiFi-Diagnostics repository via gh.

set -euo pipefail

DURATION="${1:-600}"
INTERVAL="${2:-2}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SCANLOG="$SCRIPT_DIR/rtl88wifi-scanlog.sh"
JOINREPORT="$SCRIPT_DIR/rtl88wifi-join-report.sh"
OUTROOT="$HOME/Documents/RTL88WiFi-ScanLogs"
STAMP="$(date '+%Y%m%d-%H%M%S')"
OUTDIR="$OUTROOT/kv-btm-$STAMP"
WORK="$(mktemp -d "${TMPDIR:-/tmp}/rtl88wifi-kv.XXXXXX")"

cleanup() { rm -rf "$WORK"; }
trap cleanup EXIT

fail() { echo "ERROR: $*" >&2; exit 1; }
is_uint() { case "${1:-}" in ''|*[!0-9]*) return 1 ;; *) return 0 ;; esac; }

is_uint "$DURATION" && [ "$DURATION" -ge 60 ] && [ "$DURATION" -le 3600 ] ||
    fail "duration must be 60..3600 seconds."
is_uint "$INTERVAL" && [ "$INTERVAL" -ge 1 ] && [ "$INTERVAL" -le 30 ] ||
    fail "interval must be 1..30 seconds."

[ "$(uname -s)" = "Darwin" ] || fail "Run this on the Mac with RTL88WiFi loaded."
for cmd in ioreg kmutil gh python3 ditto grep find date shasum; do
    command -v "$cmd" >/dev/null 2>&1 || fail "Required command missing: $cmd"
done
[ -f "$SCANLOG" ] || fail "Missing $SCANLOG; update your repository first."
[ -f "$JOINREPORT" ] || fail "Missing $JOINREPORT; update your repository first."
gh auth status >/dev/null 2>&1 || fail "GitHub CLI is not authenticated. Run gh auth login."

REGISTRY="$(ioreg -r -c RTL88WiFi -l -w0 2>/dev/null || true)"
BUILD="$(printf '%s\n' "$REGISTRY" | sed -n -E 's/.*"DriverBuild" = "([^"]*)".*/\1/p' | head -1)"
[ -n "$BUILD" ] || fail "RTL88WiFi has no DriverBuild registry property; is the kext loaded?"
[ "$BUILD" = "1.0.13" ] || fail "Loaded DriverBuild is not 1.0.13: $BUILD"

LOADED_LINE="$(kmutil showloaded 2>/dev/null | grep -i 'io.github.x1ren41l.RTL88WiFi' | head -1 || true)"
[ -n "$LOADED_LINE" ] || fail "kmutil does not show io.github.x1ren41l.RTL88WiFi as loaded."
case "$LOADED_LINE" in *"(1.0.13)"*) ;; *) fail "Loaded kext is not 1.0.13: $LOADED_LINE" ;; esac

mkdir -p "$OUTDIR"
echo "RTL88WiFi 1.0.13 mesh/RRM/BTM capture"
echo "DriverBuild: $BUILD"
echo "Loaded kext: $LOADED_LINE"
echo "Duration: ${DURATION}s; sampling interval: ${INTERVAL}s"
echo "Output: $OUTDIR"

cp "$SCANLOG" "$WORK/rtl88wifi-scanlog.sh"
cp "$JOINREPORT" "$WORK/rtl88wifi-join-report.sh"

# Extend only this temporary copy's event filter. Do not modify the repository
# collector or its working-tree state.
python3 - "$WORK/rtl88wifi-scanlog.sh" <<'PY_PATCH'
from pathlib import Path
import sys
p = Path(sys.argv[1])
s = p.read_text()
old = "scan|roam|mesh ESS|mesh rate|mesh RA|DIAG sample=|TXSTATE|ADDBA|aggregation|ASSOCIATE|AUTH|deauth|disassoc|beacon"
new = old + r"|802[.]11k|802[.]11v|neighbor|BTM|RRM"
if s.count(old) != 1:
    raise SystemExit("Could not safely identify the existing scan-event filter; no capture started.")
s = s.replace(old, new, 1)
old_guard = 'case "$BUILD" in *rtl88wifi*) ;; *) echo "Unexpected driver build: $BUILD" >&2; exit 1 ;; esac'
new_guard = '[ "$BUILD" = "1.0.13" ] || { echo "Unexpected driver build: $BUILD" >&2; exit 1; }'
if s.count(old_guard) != 1:
    raise SystemExit("Could not safely identify the generic collector DriverBuild guard.")
s = s.replace(old_guard, new_guard, 1)
p.write_text(s)
PY_PATCH

bash "$WORK/rtl88wifi-scanlog.sh" --duration "$DURATION" --interval "$INTERVAL" --output "$OUTDIR"

ZIP_FILE="$(find "$OUTDIR" -maxdepth 1 -type f -name 'RTL88WiFi-scanlog-*.zip' -print | sort | tail -1)"
[ -n "$ZIP_FILE" ] && [ -f "$ZIP_FILE" ] || fail "Collector ZIP not found; local capture remains in $OUTDIR."

EXTRACT="$WORK/extract"
mkdir -p "$EXTRACT"
ditto -x -k "$ZIP_FILE" "$EXTRACT"
CAPTURE_DIR="$(find "$EXTRACT" -mindepth 1 -maxdepth 1 -type d -name 'RTL88WiFi-scanlog-*' -print | head -1)"
[ -n "$CAPTURE_DIR" ] || fail "Could not locate extracted capture directory."

for f in README.txt capture-summary.txt samples.csv scan-events.log join-report.txt; do
    [ -f "$CAPTURE_DIR/$f" ] || fail "Capture is missing $f."
done

count_matches() {
    local pattern="$1" file="$2"
    grep -Eic "$pattern" "$file" || true
}
{
    echo "RTL88WiFi 1.0.13 K/V/mesh event index"
    echo "DriverBuild: $BUILD"
    echo "Neighbor Report request submitted: $(count_matches '802[.]11k neighbor request submitted' "$CAPTURE_DIR/scan-events.log")"
    echo "Neighbor Report response accepted: $(count_matches '802[.]11k neighbor response accepted' "$CAPTURE_DIR/scan-events.log")"
    echo "Neighbor Report response rejected: $(count_matches '802[.]11k neighbor response rejected' "$CAPTURE_DIR/scan-events.log")"
    echo "Neighbor Report timeout: $(count_matches '802[.]11k neighbor response timed out' "$CAPTURE_DIR/scan-events.log")"
    echo "BTM requests queued: $(count_matches '802[.]11v BTM request queued' "$CAPTURE_DIR/scan-events.log")"
    echo "BTM accepted: $(count_matches '802[.]11v BTM accept submitted' "$CAPTURE_DIR/scan-events.log")"
    echo "BTM acknowledged roam handoffs: $(count_matches '802[.]11v BTM acknowledged; roam handoff submitted' "$CAPTURE_DIR/scan-events.log")"
    echo "BTM rejections: $(count_matches '802[.]11v BTM rejected' "$CAPTURE_DIR/scan-events.log")"
    echo "Mesh roam starts: $(count_matches 'mesh roam start' "$CAPTURE_DIR/scan-events.log")"
    echo "Mesh roam completions: $(count_matches 'mesh roam complete' "$CAPTURE_DIR/scan-events.log")"
    echo "Mesh roam failures: $(count_matches 'mesh roam failed' "$CAPTURE_DIR/scan-events.log")"
    echo
    echo "Matching event lines:"
    grep -Ei '802[.]11k|802[.]11v|neighbor|BTM|mesh roam (start|complete|failed)' "$CAPTURE_DIR/scan-events.log" || true
} > "$CAPTURE_DIR/k-v-roaming-index.txt"

# Fail closed if any obvious unredacted network identifiers or key values remain.
python3 - "$CAPTURE_DIR" <<'PY_AUDIT'
from pathlib import Path
import re, sys
root = Path(sys.argv[1])
names = [
    "README.txt", "capture-summary.txt", "samples.csv",
    "scan-events.log", "join-report.txt", "k-v-roaming-index.txt",
]
mac = re.compile(r"(?i)(?:[0-9a-f]{2}:){5}[0-9a-f]{2}")
ipv4 = re.compile(r"(?<![0-9])(?:[0-9]{1,3}[.]){3}[0-9]{1,3}(?![0-9])")
key_assignment = re.compile(r"(?i)(password|passphrase|psk|pmk|ptk|gtk|igtk|pmkid|key_data)=")
bad = []
for name in names:
    text = (root / name).read_text(errors="replace")
    if mac.search(text):
        bad.append(f"{name}: possible raw MAC/BSSID")
    if ipv4.search(text):
        bad.append(f"{name}: possible raw IPv4 address")
    for line in text.splitlines():
        low = line.lower()
        if "ssid=" in low:
            ssid_value = low.split("ssid=", 1)[1].split(" ", 1)[0]
            if not (ssid_value.startswith("[ssid-redacted]") or ssid_value.startswith("[hidden]")):
                bad.append(f"{name}: possible unredacted SSID")
                break
    for match in key_assignment.finditer(text):
        value = text[match.end():].split()[0] if text[match.end():].split() else ""
        if value != "[secret-redacted]":
            bad.append(f"{name}: possible unredacted key-like value")
            break
if bad:
    print("Privacy audit failed; nothing was uploaded:")
    print("\n".join(" - " + x for x in bad))
    raise SystemExit(3)
print("Privacy audit passed for all redacted capture files.")
PY_AUDIT

HASH="$(shasum -a 256 "$ZIP_FILE" | awk '{print $1}')"
printf 'ZIP SHA-256: %s\n' "$HASH" > "$CAPTURE_DIR/zip-sha256.txt"

DIAGNOSTICS_REPO="shammu2bd/RTL88WiFi-Diagnostics"
VISIBILITY="$(gh repo view "$DIAGNOSTICS_REPO" --json visibility -q '.visibility' 2>/dev/null || true)"
[ "$VISIBILITY" = "PRIVATE" ] || fail "Diagnostics repository is not accessible as a PRIVATE repository: $DIAGNOSTICS_REPO"

echo "Uploading redacted diagnostics to PRIVATE repository $DIAGNOSTICS_REPO ..."
DIAG_CLONE="$WORK/diagnostics-repo"
gh repo clone "$DIAGNOSTICS_REPO" "$DIAG_CLONE"

DEST_REL="captures/kv-btm-$STAMP"
DEST_DIR="$DIAG_CLONE/$DEST_REL"
mkdir -p "$DEST_DIR"

for f in README.txt capture-summary.txt samples.csv scan-events.log join-report.txt k-v-roaming-index.txt zip-sha256.txt; do
    cp "$CAPTURE_DIR/$f" "$DEST_DIR/$f"
done
cp "$ZIP_FILE" "$DEST_DIR/RTL88WiFi-scanlog-$STAMP.zip"

cat > "$DEST_DIR/upload-metadata.txt" <<EOF_META
DriverBuild: $BUILD
Capture started: $STAMP
Duration seconds: $DURATION
Sampling interval seconds: $INTERVAL
Archive SHA-256: $HASH
Privacy audit: passed
EOF_META

(
    cd "$DIAG_CLONE"
    git add "$DEST_REL"
    git -c user.name="RTL88WiFi Diagnostic Uploader" \
        -c user.email="diagnostics-uploader@users.noreply.github.com" \
        commit -m "Add RTL88WiFi 1.0.13 diagnostic capture $STAMP"
    git push origin HEAD:main
)

CAPTURE_URL="https://github.com/$DIAGNOSTICS_REPO/tree/main/$DEST_REL"
printf '%s\n' "$CAPTURE_URL" > "$OUTDIR/private-repository-url.txt"
echo
echo "UPLOAD SUCCESS"
echo "Private repository: $CAPTURE_URL"
echo "Local ZIP: $ZIP_FILE"
echo "Repository visibility: PRIVATE"
