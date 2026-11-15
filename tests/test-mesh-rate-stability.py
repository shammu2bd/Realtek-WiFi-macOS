#!/usr/bin/env python3
"""Host-side regression checks for same-ESS mesh rate recovery and scan slices.

These checks exercise pure policy helpers and source integration guards. They do
not emulate CoreWiFi, RF behavior, the Realtek firmware, or a physical AP.
"""
from pathlib import Path
import subprocess
import tempfile
import textwrap

ROOT = Path(__file__).resolve().parents[1]
KEXT = ROOT / "driver/RTL88WiFi/src/kext"
COMPAT = ROOT / "driver/RTL88WiFi/src/compat"
IEEE_CPP = (KEXT / "RTW88IEEE80211.cpp").read_text()
IEEE_HPP = (KEXT / "RTW88IEEE80211.hpp").read_text()
COMPAT_C = (COMPAT / "rtw88_compat.c").read_text()
COMPAT_H = (COMPAT / "rtw88_compat.h").read_text()
POLICY = (KEXT / "RTW88MeshRoamPolicy.hpp").read_text()
SCAN_POLICY = (KEXT / "RTW88RoamScanPolicy.hpp").read_text()

# Same-SSID networks are disambiguated by BSSID, with compatible security and
# a bounded freshness window; logs expose only a short BSSID suffix.
assert "memcmp(b->ssid, _targetBSS.ssid, _targetBSS.ssid_len)" in IEEE_CPP
assert "memcmp(b->bssid, _targetBSS.bssid, 6) == 0" in IEEE_CPP
assert "RTW88RoamScan::recentlySeen(nowUS, b->last_seen_us)" in IEEE_CPP
assert "((_targetBSS.channel > 14) != (b->channel > 14))" in IEEE_CPP
assert "(rateDegraded && ((current.channel > 14) != (b->channel > 14)))" in IEEE_CPP
assert "mesh ESS inventory fresh_nodes=" in IEEE_CPP
assert "mesh ESS node id=%02x%02x%02x" in IEEE_CPP
assert '1.0.12' in (KEXT / "RTL88WiFi.cpp").read_text()
assert "_targetBSS.cipher != b->cipher" in IEEE_CPP
assert "b->rsn_pmf_required" in IEEE_CPP

# Connected scanning is one candidate channel per request, round-robin sorted,
# and records actual scan-slice timing.
assert "kConnectedScanChannelsPerPass = 1" in SCAN_POLICY
assert "buildPrioritizedChannelList(" in IEEE_CPP
assert "nextRoundRobinIndex" in IEEE_CPP
assert "mesh scan slice selected_ch=" in IEEE_CPP
assert "mesh scan slice done ch=" in IEEE_CPP
assert "_meshScanStartUS" in IEEE_HPP and "_meshScanCursor" in IEEE_HPP

# Rate recovery must be scoped to a strong 5 GHz multi-BSSID ESS and sustained
# low rate; do not pin a fixed MCS. It only reseeds the negotiated RA mask.
assert "const bool strong5GHz = _targetBSS.channel > 14 && _rssi >= -67" in IEEE_CPP
assert "strong5GHz && txRate.kbps <= RTW88MeshRoam::kLowRateTriggerKbps" in IEEE_CPP
assert "strong5GHz && multiBSSID" not in IEEE_CPP
assert "peer_vht_rx_map=0x%04x peer_vht_tx_map=0x%04x" in IEEE_CPP
assert "vht_rx_highest=%u vht_tx_highest=%u" in IEEE_CPP
assert "txRate.kbps <= RTW88MeshRoam::kLowRateTriggerKbps" in IEEE_CPP
assert "RTW88MeshRoam::isRateDegraded(now, lowSince, _rssi, txRate.kbps)" in IEEE_CPP
assert "rtw88_reset_sta_rate_adaptation()" in IEEE_CPP
assert "kLowRateStableUS = 20ULL * 1000ULL * 1000ULL" in POLICY
assert "kLowRateTriggerKbps = 24000U" in POLICY
assert "kRateRecoveryCooldownUS = 90ULL * 1000ULL * 1000ULL" in POLICY
assert "rtw_update_sta_info(rtwdev, si, true)" in COMPAT_C
assert "mutex_lock(&rtwdev->mutex)" in COMPAT_C
assert "bool rtw88_reset_sta_rate_adaptation(void);" in COMPAT_H
assert "set_fixed_rate" not in IEEE_CPP
assert "fix_rate" not in IEEE_CPP[IEEE_CPP.index("void RTW88IEEE80211::housekeeping()"):
                                  IEEE_CPP.index("void RTW88IEEE80211::handleBackAction")]

# Pure helper tests (same policy header compiled by the kernel-side C++ source).
program = textwrap.dedent(r'''\
    #include <cassert>
    #include <cstdint>
    #include "RTW88MeshRoamPolicy.hpp"
    #include "RTW88RoamScanPolicy.hpp"
    int main() {
      using namespace RTW88MeshRoam;
      assert(isRateDegraded(21'000'000, 1'000'000, -56, 13'000));
      assert(!isRateDegraded(20'999'999, 1'000'000, -56, 13'000));
      assert(!isRateDegraded(21'000'000, 1'000'000, -70, 13'000));
      assert(!isRateDegraded(21'000'000, 1'000'000, -56, 27'000));
      assert(isBetterCandidate(-56, -48, true));
      assert(!isBetterCandidate(-56, -49, true));
      assert(!isBetterCandidate(-56, -74, true));
      assert(isBetterCandidate(-72, -60, false));
      using namespace RTW88RoamScan;
      uint16_t channels[] = {157, 36, 149, 44};
      sortAscending(channels, 4);
      assert(channels[0] == 36 && channels[3] == 157);
      uint16_t same[] = {36, 165, 149, 153, 161, 100, 44, 48};
      uint16_t cross[] = {1, 6, 11, 2, 3, 4, 5, 10};
      sortByHomeChannelDistance(same, 8, 157);
      uint16_t selected[8] = {};
      uint32_t selectedCount = buildPrioritizedChannelList(
          selected, 8, same, 8, cross, 8, 1);
      assert(selectedCount == 8);
      for (unsigned i = 0; i < 7; ++i) assert(selected[i] > 14);
      assert(selected[7] == 1);
      uint16_t crossOnly[8] = {};
      selectedCount = buildPrioritizedChannelList(
          crossOnly, 8, nullptr, 0, cross, 8, 1);
      assert(selectedCount == 8);
      for (unsigned i = 0; i < 8; ++i) assert(crossOnly[i] == cross[i]);
      uint32_t cursor = 0;
      assert(nextRoundRobinIndex(3, &cursor) == 0);
      assert(nextRoundRobinIndex(3, &cursor) == 1);
      assert(nextRoundRobinIndex(3, &cursor) == 2);
      assert(nextRoundRobinIndex(3, &cursor) == 0);
      assert(nextRoundRobinIndex(0, &cursor) == 0);
      assert(recentlySeen(60'000'000, 1));
      assert(!recentlySeen(60'000'002, 1));
      return 0;
    }
''')
with tempfile.TemporaryDirectory() as td:
    src = Path(td) / "mesh_rate_scan_test.cpp"
    binary = Path(td) / "mesh_rate_scan_test"
    src.write_text(program)
    subprocess.run(["clang++", "-std=c++14", "-Wall", "-Wextra", "-Werror",
                    "-I", str(KEXT), str(src), "-o", str(binary)], check=True)
    subprocess.run([str(binary)], check=True)

print("PASS: same-ESS BSSID inventory, one-channel scan rotation, rate-degradation policy, and negotiated RA reseed integration")
