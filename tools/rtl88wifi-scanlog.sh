#!/bin/bash
# RTL88WiFi scan/roaming telemetry collector for macOS (r26+; r29 adds
# scan-lifecycle recovery telemetry and TX-rate/MCS/bandwidth CSV fields).
# Read-only: samples the driver's DiagnosticLog registry ring and link properties.
# Default output is ~/Documents/RTL88WiFi-ScanLogs. Raw SSIDs, BSSIDs, MACs, IPs
# and key material are not saved; MACs become per-capture pseudonyms.
#
# Usage:
#   bash tools/rtl88wifi-scanlog.sh
#   bash tools/rtl88wifi-scanlog.sh --duration 600 --interval 2
#   bash tools/rtl88wifi-scanlog.sh --duration 300 --interval 2 --upload-github --repo OWNER/REPO
#
# --upload-github uploads the finished ZIP to a verified PRIVATE GitHub repo via `gh`.
# It always asks for confirmation. Nothing is uploaded unless explicitly chosen.

set -u

VERSION="1.0"
DURATION=300
INTERVAL=2
OUTPUT_DIR="${HOME}/Documents/RTL88WiFi-ScanLogs"
UPLOAD_GITHUB=0
GITHUB_REPO=""

usage() {
    cat <<'EOF'
RTL88WiFi scan/roaming log collector

Options:
  --duration SECONDS   Capture duration, 30..3600 (default: 300)
  --interval SECONDS   Sampling interval, 1..30 (default: 2)
  --output DIR         Output directory (default: ~/Documents/RTL88WiFi-ScanLogs)
  --upload-github      Offer to upload the ZIP to a verified PRIVATE GitHub repository
  --repo OWNER/REPO    Target repository (required with --upload-github)
  -h, --help           Show this help

The collector reads the RTL88WiFi DiagnosticLog ring and selected status
properties. It does not change Wi-Fi settings, initiate scans, or run a speed
test. It pseudonymizes MAC/BSSID, and redacts SSID, IP and key-like values.
GitHub upload is only supported to an existing PRIVATE repository and requires
confirmation. It uses your local GitHub CLI login; no token is stored here.
EOF
}

is_uint() { case "${1:-}" in ''|*[!0-9]*) return 1 ;; *) return 0 ;; esac; }
while [ "$#" -gt 0 ]; do
    case "$1" in
        --duration) [ "$#" -ge 2 ] || { usage; exit 2; }; DURATION="$2"; shift 2 ;;
        --interval) [ "$#" -ge 2 ] || { usage; exit 2; }; INTERVAL="$2"; shift 2 ;;
        --output) [ "$#" -ge 2 ] || { usage; exit 2; }; OUTPUT_DIR="$2"; shift 2 ;;
        --upload-github) UPLOAD_GITHUB=1; shift ;;
        --repo) [ "$#" -ge 2 ] || { usage; exit 2; }; GITHUB_REPO="$2"; shift 2 ;;
        -h|--help) usage; exit 0 ;;
        *) echo "Unknown option: $1" >&2; usage; exit 2 ;;
    esac
done

is_uint "$DURATION" && [ "$DURATION" -ge 30 ] && [ "$DURATION" -le 3600 ] || {
    echo "--duration must be an integer from 30 to 3600 seconds." >&2; exit 2;
}
is_uint "$INTERVAL" && [ "$INTERVAL" -ge 1 ] && [ "$INTERVAL" -le 30 ] || {
    echo "--interval must be an integer from 1 to 30 seconds." >&2; exit 2;
}

if [ "$UPLOAD_GITHUB" -eq 0 ] && [ -n "$GITHUB_REPO" ]; then
    echo "--repo is only valid together with --upload-github." >&2; exit 2
fi
if [ "$UPLOAD_GITHUB" -eq 1 ] && [ -z "$GITHUB_REPO" ]; then
    echo "--repo OWNER/REPO is required with --upload-github." >&2; usage; exit 2
fi

if [ "$(uname -s 2>/dev/null)" != "Darwin" ]; then
    echo "This collector must run on the Mac with RTL88WiFi loaded." >&2
    exit 1
fi
for cmd in ioreg ifconfig date awk sed grep zip shasum python3; do
    command -v "$cmd" >/dev/null 2>&1 || { echo "Required command not found: $cmd" >&2; exit 1; }
done

REGISTRY=$(ioreg -r -c RTL88WiFi -l -w0 2>/dev/null)
BUILD=$(printf '%s\n' "$REGISTRY" | sed -n -E 's/.*"DriverBuild" = "([^"]*)".*/\1/p' | head -1)
if [ -z "$BUILD" ]; then
    echo "RTL88WiFi is not loaded (no DriverBuild registry property)." >&2
    exit 1
fi
case "$BUILD" in *rtl88wifi*) ;; *) echo "Unexpected driver build: $BUILD" >&2; exit 1 ;; esac

INTERFACE=$(ioreg -r -c RTL88WiFiInterface -l -w0 2>/dev/null | sed -n -E 's/.*"BSD Name" = "([^"]*)".*/\1/p' | head -1)
[ -n "$INTERFACE" ] || INTERFACE="unknown"

prop() {
    # Read a property from the supplied ioreg text snapshot.
    printf '%s\n' "$REGISTRY" | sed -n -E 's/.*"'"$1"'" = "?([^" ]*)"?.*/\1/p' | head -1
}

# Read the driver's 32 KB DiagnosticLog string. XML form is primary because it
# preserves embedded newlines; fall back to ioreg's escaped text representation.
get_ring() {
    local xml txt
    xml=$(ioreg -r -c RTL88WiFi -l -a 2>/dev/null | awk '
        {
            if (index($0, "<key>DiagnosticLog</key>")) want = 1
            if (want && !inside) {
                if (index($0, "<string/>")) exit
                p = index($0, "<string>")
                if (!p) next
                $0 = substr($0, p + 8)
                inside = 1
            }
            if (inside) {
                p = index($0, "</string>")
                if (p) { print substr($0, 1, p - 1); exit }
                print
            }
        }' | sed -e 's/&lt;/</g' -e 's/&gt;/>/g' -e 's/&quot;/"/g' -e "s/&apos;/'/g" -e 's/&amp;/\&/g')
    if [ -n "$xml" ]; then printf '%s\n' "$xml"; return; fi
    txt=$(ioreg -r -c RTL88WiFi -l -w0 2>/dev/null |
        sed -n -E 's/.*"DiagnosticLog" = "(.*)"$/\1/p' | head -1 |
        awk '{ gsub(/\\n/, "\n"); print }')
    [ -n "$txt" ] && printf '%s\n' "$txt"
}

# One random salt per capture. MAC/BSSID addresses become stable, non-reversible
# pseudonyms within this archive so mesh handoffs can be correlated without
# publishing hardware addresses. The salt is never written to disk.
MAC_SALT=$(python3 -c 'import secrets; print(secrets.token_hex(32))')
[ -n "$MAC_SALT" ] || { echo "Could not initialize private MAC pseudonymization." >&2; exit 1; }
redact() {
    MAC_SALT="$MAC_SALT" python3 -c '
import hashlib, hmac, os, re, sys
salt = bytes.fromhex(os.environ["MAC_SALT"])
mac_re = re.compile(r"(?i)(?:[0-9a-f]{2}:){5}[0-9a-f]{2}")
partial_mac_re = re.compile(r"(?i)(?:xx:){4}[0-9a-f]{2}:[0-9a-f]{2}")
ip_re = re.compile(r"\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b")
for line in sys.stdin:
    # Some driver association messages end immediately after ssid=...;
    # others continue with a secure= field. Cover both formats, including spaces.
    if re.search(r"(?i)\bssid=.*?\s+secure=", line):
        line = re.sub(r"(?i)\bssid=.*?(?=\s+secure=)", "ssid=[SSID-redacted]", line)
    else:
        line = re.sub(r"(?i)\bssid=.*$", "ssid=[SSID-redacted]", line)
    def pseudonym(match):
        digest = hmac.new(salt, match.group(0).lower().encode("ascii"), hashlib.sha256).hexdigest()
        return "AP-" + digest[:10]
    line = mac_re.sub(pseudonym, line)
    line = partial_mac_re.sub("AP-partial-redacted", line)
    line = ip_re.sub("[IP-redacted]", line)
    line = re.sub(r"(?i)\b(password|passphrase)\s*=\s*\"[^\"]*\"", r"\1=[secret-redacted]", line)
    line = re.sub(r"(?i)\b(password|passphrase|psk|pmk|ptk|gtk|igtk|pmkid|key|key_data)\s*=\s*[^,;\s]+", r"\1=[secret-redacted]", line)
    sys.stdout.write(line)
'
}

now_iso() { date '+%Y-%m-%dT%H:%M:%S%z'; }

STAMP=$(date '+%Y%m%d-%H%M%S')
mkdir -p "$OUTPUT_DIR" || { echo "Cannot create output directory: $OUTPUT_DIR" >&2; exit 1; }
RUN_DIR="$OUTPUT_DIR/RTL88WiFi-scanlog-$STAMP"
mkdir -p "$RUN_DIR" || exit 1
EVENTS="$RUN_DIR/scan-events.log"
CSV="$RUN_DIR/samples.csv"
PREV="$RUN_DIR/.previous-events"
CURRENT="$RUN_DIR/.current-events"
: > "$EVENTS"
: > "$PREV"
printf 'timestamp,elapsed_seconds,interface_status,channel,rssi,noise_source,agg,txq,txcap,stalled,qdrop,qstall,txretry,tx_rate_mbps,tx_mcs,tx_nss,tx_bw_mhz,home_bw_mhz,new_scan_events,new_roam_events\n' > "$CSV"

OSVER=$(sw_vers -productVersion 2>/dev/null || echo unknown)
OSBUILD=$(sw_vers -buildVersion 2>/dev/null || echo unknown)
KERNEL=$(uname -r 2>/dev/null || echo unknown)
MODEL=$(sysctl -n hw.model 2>/dev/null || echo unknown)
START_EPOCH=$(date +%s)
END_EPOCH=$((START_EPOCH + DURATION))

cat > "$RUN_DIR/README.txt" <<EOF
RTL88WiFi scan/roaming diagnostic capture
Capture tool version: $VERSION
Driver build: $BUILD
macOS: $OSVER ($OSBUILD), kernel $KERNEL
Mac model: $MODEL
Interface: $INTERFACE
Started: $(now_iso)
Planned duration: $DURATION seconds
Sampling interval: $INTERVAL seconds

Contents:
- samples.csv: link, queue, TX rate/MCS/bandwidth and scan/roam event counts per sample
- scan-events.log: newly observed scan, roaming, association and TX diagnostic lines
- join-report.txt: the driver's standard privacy-redacted join report
- capture-summary.txt: capture timing and final counters

Privacy:
The collector intentionally omits SSID, BSSID, MAC addresses, IP addresses,
router/gateway addresses, Wi-Fi passwords and key material. The selected driver
log lines are redacted before writing. Review the ZIP before sharing it.

This is a read-only observer. It does not initiate scans, change settings,
restart the driver, or run a throughput test.
EOF

get_num() {
    # Extract a decimal DIAG key=value token without depending on sed ERE quirks.
    printf '%s\n' "$1" | awk -v key="$2" '{
        for (i = 1; i <= NF; i++) {
            split($i, pair, "=")
            if (pair[1] == key && pair[2] ~ /^[0-9]+$/) { print pair[2]; exit }
        }
    }'
}

printf 'Collecting %s seconds of RTL88WiFi telemetry (sample every %s seconds).\n' "$DURATION" "$INTERVAL"
printf 'Driver: %s | interface: %s\n' "$BUILD" "$INTERFACE"
printf 'Output folder: %s\n\n' "$RUN_DIR"

SAMPLE=0
TOTAL_SCAN=0
TOTAL_ROAM=0
LAST_DIAG=""
while [ "$(date +%s)" -lt "$END_EPOCH" ]; do
    SAMPLE=$((SAMPLE + 1))
    TS=$(now_iso)
    ELAPSED=$(( $(date +%s) - START_EPOCH ))
    REGISTRY=$(ioreg -r -c RTL88WiFi -l -w0 2>/dev/null)
    CHAN=$(prop RADIO_CHANNEL); [ -n "$CHAN" ] || CHAN="n/a"
    RSSI=$(prop RADIO_RSSI); [ -n "$RSSI" ] || RSSI="n/a"
    NOISE=$(prop RADIO_NOISE_SOURCE); [ -n "$NOISE" ] || NOISE="n/a"
    STATUS=$(ifconfig "$INTERFACE" 2>/dev/null | sed -n -E 's/.*status: ([^ ]+).*/\1/p' | head -1)
    [ -n "$STATUS" ] || STATUS="unknown"

    RING=$(get_ring)
    if [ -n "$RING" ]; then
        printf '%s\n' "$RING" | redact | grep -Ei 'scan|roam|mesh ESS|mesh rate|mesh RA|DIAG sample=|TXSTATE|ADDBA|aggregation|ASSOCIATE|AUTH|deauth|disassoc|beacon' > "$CURRENT" || :
    else
        : > "$CURRENT"
    fi

    NEW_EVENTS=$(awk 'FILENAME == ARGV[1] { seen[$0] = 1; next } !seen[$0]' "$PREV" "$CURRENT")
    if [ -n "$NEW_EVENTS" ]; then
        while IFS= read -r LINE; do
            [ -n "$LINE" ] || continue
            printf '[%s] %s\n' "$TS" "$LINE" >> "$EVENTS"
        done <<EOF_EVENTS
$NEW_EVENTS
EOF_EVENTS
    fi
    cp "$CURRENT" "$PREV"

    NEW_SCAN=$(printf '%s\n' "$NEW_EVENTS" | grep -Eic 'scan' || true)
    NEW_ROAM=$(printf '%s\n' "$NEW_EVENTS" | grep -Eic 'rtw88: mesh roam (start|complete|failed)' || true)
    TOTAL_SCAN=$((TOTAL_SCAN + NEW_SCAN))
    TOTAL_ROAM=$((TOTAL_ROAM + NEW_ROAM))
    DIAG=$(grep 'DIAG sample=' "$CURRENT" | tail -1)
    [ -n "$DIAG" ] && LAST_DIAG="$DIAG"
    AGG=$(get_num "$DIAG" agg); [ -n "$AGG" ] || AGG="n/a"
    TXQ=$(get_num "$DIAG" txq); [ -n "$TXQ" ] || TXQ="n/a"
    TXCAP=$(get_num "$DIAG" txcap); [ -n "$TXCAP" ] || TXCAP="n/a"
    STALLED=$(get_num "$DIAG" stalled); [ -n "$STALLED" ] || STALLED="n/a"
    QDROP=$(get_num "$DIAG" qdrop); [ -n "$QDROP" ] || QDROP="n/a"
    QSTALL=$(get_num "$DIAG" qstall); [ -n "$QSTALL" ] || QSTALL="n/a"
    TXRETRY=$(get_num "$DIAG" txretry); [ -n "$TXRETRY" ] || TXRETRY="n/a"
    RATE_LINE=$(grep -E 'mesh rate transition|mesh rate recovery result' "$CURRENT" | tail -1)
    RATE_KBPS=$(get_num "$RATE_LINE" kbps)
    if [ -n "$RATE_KBPS" ]; then
        TX_RATE=$(awk -v v="$RATE_KBPS" 'BEGIN { printf "%.3f", v / 1000.0 }')
    else
        TX_RATE="n/a"
    fi
    TX_MCS=$(get_num "$RATE_LINE" mcs); [ -n "$TX_MCS" ] || TX_MCS="n/a"
    TX_NSS=$(get_num "$RATE_LINE" nss); [ -n "$TX_NSS" ] || TX_NSS="n/a"
    TX_BW=$(get_num "$RATE_LINE" tx_bw); [ -n "$TX_BW" ] || TX_BW="n/a"
    HOME_BW=$(get_num "$RATE_LINE" home_bw); [ -n "$HOME_BW" ] || HOME_BW="n/a"
    printf '"%s",%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s\n' \
      "$TS" "$ELAPSED" "$STATUS" "$CHAN" "$RSSI" "$NOISE" "$AGG" "$TXQ" "$TXCAP" "$STALLED" "$QDROP" "$QSTALL" "$TXRETRY" "$TX_RATE" "$TX_MCS" "$TX_NSS" "$TX_BW" "$HOME_BW" "$NEW_SCAN" "$NEW_ROAM" >> "$CSV"

    printf '\rSample %s | %ss | ch %s | RSSI %s | new scan events %s | roam events %s   ' \
      "$SAMPLE" "$ELAPSED" "$CHAN" "$RSSI" "$NEW_SCAN" "$NEW_ROAM"
    sleep "$INTERVAL"
done
printf '\n\n'

# Attach the standard join report (it independently redacts MAC/SSID values).
if [ -f "$(dirname "$0")/rtl88wifi-join-report.sh" ]; then
    bash "$(dirname "$0")/rtl88wifi-join-report.sh" 400 2>&1 | redact > "$RUN_DIR/join-report.txt"
else
    echo "join-report.sh not found beside collector." > "$RUN_DIR/join-report.txt"
fi

END_ISO=$(now_iso)
cat > "$RUN_DIR/capture-summary.txt" <<EOF
Capture started: $(date -r "$START_EPOCH" '+%Y-%m-%dT%H:%M:%S%z' 2>/dev/null || echo unknown)
Capture ended: $END_ISO
Samples: $SAMPLE
Planned duration: $DURATION seconds
Sampling interval: $INTERVAL seconds
Newly observed scan-related events: $TOTAL_SCAN
Newly observed roaming-related events: $TOTAL_ROAM
Driver build: $BUILD
Last DIAG line (redacted): ${LAST_DIAG:-not present in ring snapshot}

Note: event counts are based on newly observed lines in the driver's bounded
DiagnosticLog ring. If the ring wraps between samples, some older events may
no longer be available. Use a 1-2 second interval for the most complete capture.
EOF

rm -f "$PREV" "$CURRENT"
ZIP_FILE="$OUTPUT_DIR/RTL88WiFi-scanlog-$STAMP.zip"
if ! (cd "$OUTPUT_DIR" && zip -qr "$ZIP_FILE" "$(basename "$RUN_DIR")"); then
    echo "Could not create ZIP archive; raw capture remains at $RUN_DIR" >&2
    exit 1
fi
HASH=$(shasum -a 256 "$ZIP_FILE" | awk '{print $1}')
printf '\nCapture complete.\nZIP: %s\nSHA-256: %s\n' "$ZIP_FILE" "$HASH"

if [ "$UPLOAD_GITHUB" -eq 1 ]; then
    echo
    if [ -z "$GITHUB_REPO" ]; then
        echo "--repo OWNER/REPO is required with --upload-github." >&2
        echo "The repository must already exist and have PRIVATE visibility." >&2
        exit 2
    fi
    case "$GITHUB_REPO" in
        */*) case "$GITHUB_REPO" in *[!A-Za-z0-9_./-]*) echo "Invalid OWNER/REPO value." >&2; exit 2 ;; esac ;;
        *) echo "Repository must be OWNER/REPO." >&2; exit 2 ;;
    esac
    if ! command -v gh >/dev/null 2>&1; then
        echo "GitHub CLI (gh) is not installed. Install with: brew install gh"
        echo "Then sign in with: gh auth login"
        echo "For private-repository write access, run: gh auth refresh -s repo"
    elif ! gh auth status >/dev/null 2>&1; then
        echo "GitHub CLI is not authenticated. Run: gh auth login"
    else
        VISIBILITY=$(gh repo view "$GITHUB_REPO" --json visibility --jq .visibility 2>/dev/null || echo unavailable)
        if [ "$VISIBILITY" != "PRIVATE" ]; then
            echo "Refusing upload: $GITHUB_REPO visibility is '$VISIBILITY', not PRIVATE." >&2
            echo "Create/use a private repository; no data was uploaded." >&2
            exit 1
        fi
        BRANCH=$(gh repo view "$GITHUB_REPO" --json defaultBranchRef --jq .defaultBranchRef.name 2>/dev/null || echo '')
        [ -n "$BRANCH" ] || { echo "Could not determine the repository's default branch." >&2; exit 1; }
        REMOTE_PATH="diagnostics/rtl88wifi-scanlogs/$(basename "$ZIP_FILE")"
        printf 'Upload this redacted diagnostic ZIP to PRIVATE repository %s (branch %s)? [y/N] ' "$GITHUB_REPO" "$BRANCH"
        read -r ANSWER
        case "$ANSWER" in
            y|Y|yes|YES)
                command -v python3 >/dev/null 2>&1 || { echo "python3 is required to prepare the GitHub upload payload." >&2; exit 1; }
                PAYLOAD="$RUN_DIR/.github-upload.json"
                python3 - "$ZIP_FILE" "$BRANCH" "$BUILD" "$STAMP" "$PAYLOAD" <<'PY_PAYLOAD'
import base64, json, sys
zip_path, branch, build, stamp, output = sys.argv[1:]
with open(zip_path, "rb") as f:
    content = base64.b64encode(f.read()).decode("ascii")
payload = {
    "message": "Add RTL88WiFi scan diagnostics " + stamp + " (" + build + ")",
    "content": content,
    "branch": branch,
}
with open(output, "w", encoding="utf-8") as f:
    json.dump(payload, f)
PY_PAYLOAD
                if gh api --method PUT --input "$PAYLOAD" "repos/$GITHUB_REPO/contents/$REMOTE_PATH" --jq .content.html_url; then
                    echo "Uploaded to $GITHUB_REPO/$REMOTE_PATH"
                else
                    echo "GitHub upload failed. The ZIP remains saved locally." >&2
                    rm -f "$PAYLOAD"
                    exit 1
                fi
                rm -f "$PAYLOAD"
                ;;
            *) echo "Not uploaded. The ZIP remains saved locally." ;;
        esac
    fi
fi
