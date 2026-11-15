#!/usr/bin/env python3
"""Host checks for the r26/r27 cache-directed connected mesh-roaming path."""
from pathlib import Path
import subprocess
import tempfile
import textwrap

ROOT = Path(__file__).resolve().parents[1]
KEXT = ROOT / "driver/RTL88WiFi/src/kext"
POLICY = KEXT / "RTW88MeshRoamPolicy.hpp"
IEEE_CPP = (KEXT / "RTW88IEEE80211.cpp").read_text()
IEEE_HPP = (KEXT / "RTW88IEEE80211.hpp").read_text()
CTRL_CPP = (KEXT / "RTL88WiFi.cpp").read_text()

assert POLICY.exists()
assert "case APPLE80211_IOC_ROAM" in CTRL_CPP
assert "d->version != APPLE80211_VERSION" in CTRL_CPP
assert "cmdRoam(d->target_bssid, d->target_channel, evaluateCache)" in CTRL_CPP
assert "kRTW88EventRoamStart" in CTRL_CPP and "APPLE80211_M_ROAM_START" in CTRL_CPP
assert "kRTW88EventRoamEnd" in CTRL_CPP and "APPLE80211_M_ROAM_END" in CTRL_CPP
assert "uint64_t last_seen_us" in IEEE_HPP
assert "bss->last_seen_us = rtw88JoinNowUS()" in IEEE_CPP
assert "RTW88MeshRoam::isFresh(now, b->last_seen_us)" in IEEE_CPP
assert "RTW88MeshRoam::isBetterCandidate(currentRSSI, b->rssi, rateDegraded)" in IEEE_CPP
assert "RTW88MeshRoam::isRateDegraded(now, lowRateSince, currentRSSI, currentRate.kbps)" in IEEE_CPP
assert "_roamPreviousBSS = current" in IEEE_CPP
assert "_roamPreviousBSS" in IEEE_CPP[IEEE_CPP.index("IOReturn RTW88IEEE80211::cmdGetState"):]
assert "finishRoam(true)" in IEEE_CPP
assert "finishRoam(false)" in IEEE_CPP

# Keep this regression focused on the requested handoff method. It must not
# perform the ordinary explicit-disconnect path, which would create a false
# link-down and trigger a full CoreWiFi auto-join.
start = IEEE_CPP.index("IOReturn RTW88IEEE80211::cmdRoam(")
end = IEEE_CPP.index("void RTW88IEEE80211::finishRoam", start)
roam_body = IEEE_CPP[start:end]
assert "doDisconnect(" not in roam_body
assert "_associatedVisible = false" not in roam_body
assert "RTW88_STATE_AUTHENTICATING" in roam_body
assert "releaseSta()" in roam_body
assert "clearKeys()" in roam_body
assert "thread_call_enter(_connectTC)" in roam_body
assert "_externalSupplicant" in roam_body and "kIOReturnUnsupported" in roam_body

# Compile and execute the standalone roam thresholds/freshness helpers.
source = textwrap.dedent(r'''\
    #include <assert.h>
    #include <stdint.h>
    #include "RTW88MeshRoamPolicy.hpp"
    int main() {
        using namespace RTW88MeshRoam;
        const uint8_t all[6] = {255,255,255,255,255,255};
        const uint8_t good[6] = {2,1,2,3,4,5};
        const uint8_t group[6] = {1,1,2,3,4,5};
        const uint8_t zero[6] = {0,0,0,0,0,0};
        assert(isBroadcastBSSID(all));
        assert(!isBroadcastBSSID(good));
        assert(isValidUnicastBSSID(good));
        assert(!isValidUnicastBSSID(group));
        assert(!isValidUnicastBSSID(zero));
        assert(isFresh(20'000'000, 1));
        assert(!isFresh(60'000'002, 1));
        assert(!isFresh(1, 2));
        assert(isBetterCandidate(-72, -60));
        assert(!isBetterCandidate(-68, -50));
        assert(!isBetterCandidate(-72, -61));
        assert(!isBetterCandidate(-72, -83));
        assert(!isBetterCandidate(-72, 0));
        assert(!isBetterCandidate(0, -50));
        assert(!isBetterCandidate(-128, -50));
        assert(isBetterCandidate(-60, -52, true));
        assert(!isBetterCandidate(-60, -53, true));
        assert(!isBetterCandidate(-60, -73, true));
        assert(isRateDegraded(22'000'000, 1'000'000, -60, 13'000));
        assert(!isRateDegraded(20'999'999, 1'000'000, -60, 13'000));
        assert(!isRateDegraded(22'000'000, 1'000'000, -70, 13'000));
        assert(!isRateDegraded(22'000'000, 1'000'000, -60, 0));
        assert(cooldownElapsed(60'000'000, 5'000'000));
        assert(!cooldownElapsed(49'999'999, 5'000'000));
        assert(cooldownElapsed(5, 10));
        return 0;
    }
''')
with tempfile.TemporaryDirectory() as td:
    src = Path(td) / "mesh_roam_policy_test.cpp"
    binary = Path(td) / "mesh_roam_policy_test"
    src.write_text(source)
    subprocess.run(["clang++", "-std=c++14", "-Wall", "-Wextra", "-Werror",
                    "-I", str(KEXT), str(src), "-o", str(binary)], check=True)
    subprocess.run([str(binary)], check=True)

print("PASS: mesh roam ABI dispatch, cache freshness, conservative candidate policy, "
      "link-latch preservation, rate-aware candidate thresholds, cooldowns, completion/failure events, and host policy tests")
