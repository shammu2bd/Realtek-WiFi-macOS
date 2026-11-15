#!/usr/bin/env python3
"""r30 regression tests for UniFi same-band scan candidate prioritization.

Compiles the exact host-testable policy helper used by the kext and checks
source integration. It does not test Apple kernel linking, CoreWiFi or RF.
"""
from pathlib import Path
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
KEXT = ROOT / "driver/RTL88WiFi/src/kext"
IEEE = (KEXT / "RTW88IEEE80211.cpp").read_text()
CTRL = (KEXT / "RTL88WiFi.cpp").read_text()
CTRL_H = (KEXT / "RTL88WiFi.hpp").read_text()
POLICY = (KEXT / "RTW88RoamScanPolicy.hpp").read_text()

assert "kMaxCandidatePoolChannels = 128" in POLICY
assert "kMaxCrossBandChannelsPerPass = 1" in POLICY
assert "sortByHomeChannelDistance" in IEEE
assert "buildPrioritizedChannelList(" in IEEE
assert "sameBandChannelPool" in IEEE and "crossBandChannelPool" in IEEE
assert "channelEnabled(channelNumber)" in IEEE
assert "connected scan rate-limited events=%u" in IEEE
assert "_connectedScanThrottleEvents" in (KEXT / "RTW88IEEE80211.hpp").read_text()
assert "sampled_total=%u" in CTRL
assert "_pendingScanThrottleDeferrals" in CTRL_H
assert "1.0.12" in CTRL
assert "strong5GHz && txRate.kbps <= RTW88MeshRoam::kLowRateTriggerKbps" in IEEE
assert "strong5GHz && multiBSSID" not in IEEE
assert "peer_vht_rx_map=0x%04x peer_vht_tx_map=0x%04x" in IEEE
assert "vht_rx_highest=%u vht_tx_highest=%u" in IEEE
assert "set_fixed_rate" not in IEEE

program = r'''
#include <cassert>
#include <cstdint>
#include "RTW88RoamScanPolicy.hpp"
int main() {
  using namespace RTW88RoamScan;
  uint16_t same[] = {36, 165, 149, 153, 161, 100, 44, 48};
  uint16_t cross[] = {1, 6, 11, 2, 3, 4, 5, 10};
  sortByHomeChannelDistance(same, 8, 157);
  assert(same[0] == 153 && same[1] == 161 && same[2] == 149 && same[3] == 165);
  uint16_t out[8] = {};
  uint32_t n = buildPrioritizedChannelList(out, 8, same, 8, cross, 8, 1);
  assert(n == 8);
  for (unsigned i=0; i<7; ++i) assert(out[i] > 14);
  assert(out[7] == 1);
  uint16_t eightSame[] = {36, 149, 153, 161, 165, 100, 44, 48};
  n = buildPrioritizedChannelList(out, 8, eightSame, 8, cross, 8, 1);
  assert(n == 8 && out[7] == 1);
  n = buildPrioritizedChannelList(out, 8, nullptr, 0, cross, 8, 1);
  assert(n == 8);
  for (unsigned i=0; i<8; ++i) assert(out[i] == cross[i]);
  n = buildPrioritizedChannelList(out, 8, same, 5, nullptr, 0, 1);
  assert(n == 5);
  uint16_t fullSame[] = {36, 149, 153, 161, 165, 100, 44, 48};
  n = buildPrioritizedChannelList(out, 8, fullSame, 8, cross, 8, 0);
  assert(n == 8 && out[7] == 48); // zero cross-band budget does not waste a slot
  return 0;
}
'''
with tempfile.TemporaryDirectory() as td:
    src = Path(td) / "r30_policy_test.cpp"
    exe = Path(td) / "r30_policy_test"
    src.write_text(program)
    subprocess.run(["clang++", "-std=c++14", "-Wall", "-Wextra", "-Werror",
                    "-I", str(KEXT), str(src), "-o", str(exe)], check=True)
    subprocess.run([str(exe)], check=True)
print("PASS: r30 collects band-separated candidates before the eight-channel cap, preserves one cross-band probe, prioritizes home-adjacent channels, and records VHT/rate diagnostics")
