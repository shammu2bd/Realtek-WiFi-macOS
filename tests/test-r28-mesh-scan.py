#!/usr/bin/env python3
"""r28 mesh scan-priority, throttling, deferred-request and telemetry checks."""
from pathlib import Path
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
KEXT = ROOT / "driver/RTL88WiFi/src/kext"
CTRL_CPP = (KEXT / "RTL88WiFi.cpp").read_text()
CTRL_HPP = (KEXT / "RTL88WiFi.hpp").read_text()
IEEE_CPP = (KEXT / "RTW88IEEE80211.cpp").read_text()
IEEE_HPP = (KEXT / "RTW88IEEE80211.hpp").read_text()
POLICY = (KEXT / "RTW88RoamScanPolicy.hpp").read_text()

assert 'buildPrioritizedChannelList(' in IEEE_CPP
assert 'same_band=%u cross_band=%u' in IEEE_CPP
assert 'kConnectedScanMinIntervalUS = 15ULL * 1000ULL * 1000ULL' in POLICY
assert 'connectedScanIntervalElapsed' in IEEE_CPP
assert 'connected scan rate-limited' in IEEE_CPP
assert 'scan worker enter' in IEEE_CPP
assert 'scan worker radio-prepared' in IEEE_CPP
assert 'scan worker channel-begin' in IEEE_CPP
assert 'scan worker channel-switched' in IEEE_CPP
assert 'scan worker dwell-complete' in IEEE_CPP
assert 'scan worker home-restored' in IEEE_CPP
assert 'scan worker finalize' in IEEE_CPP
assert 'scan timeout stage=' in IEEE_CPP
assert 'mesh rate transition' in IEEE_CPP and 'home_bw=%u' in IEEE_CPP
assert 'scan request saved as one pending follow-up' in CTRL_CPP
assert 'queuePendingScanRequest' in CTRL_CPP
assert 'dispatchPendingScanRequest' in CTRL_CPP
assert 'pendingScanTimerFired' in CTRL_CPP
assert 'mergePendingChannels' in CTRL_CPP and 'mergePendingChannels' in POLICY
assert '_pendingScanTimer' in CTRL_HPP and '_pendingScanLock' in CTRL_HPP
assert '_manualScanStage' in IEEE_HPP

program = r'''
#include <cassert>
#include <cstdint>
#include "RTW88RoamScanPolicy.hpp"
int main() {
  using namespace RTW88RoamScan;
  uint16_t channels[] = {1, 6, 161, 149, 36, 44};
  sortPreferHomeBand(channels, 6, 157);
  const uint16_t expect5[] = {36, 44, 149, 161, 1, 6};
  for (unsigned i=0; i<6; ++i) assert(channels[i] == expect5[i]);
  uint16_t channels2[] = {149, 6, 1, 36, 11};
  sortPreferHomeBand(channels2, 5, 6);
  const uint16_t expect2[] = {1, 6, 11, 36, 149};
  for (unsigned i=0; i<5; ++i) assert(channels2[i] == expect2[i]);
  assert(connectedScanIntervalElapsed(1000000, 0));
  assert(!connectedScanIntervalElapsed(14999999, 1));
  assert(connectedScanIntervalElapsed(15000001, 1));
  assert(connectedScanIntervalElapsed(1, 5));
  uint16_t pending[4] = {36, 0, 0, 0};
  const uint16_t incoming[] = {36, 44, 1, 149, 6};
  uint32_t n = mergePendingChannels(pending, 1, 4, incoming, 5);
  assert(n == 4);
  assert(pending[0] == 36 && pending[1] == 44 && pending[2] == 1 && pending[3] == 149);
  return 0;
}
'''
with tempfile.TemporaryDirectory() as td:
    src = Path(td) / "r28_scan_test.cpp"
    exe = Path(td) / "r28_scan_test"
    src.write_text(program)
    subprocess.run(["clang++", "-std=c++14", "-Wall", "-Wextra", "-Werror",
                    "-I", str(KEXT), str(src), "-o", str(exe)], check=True)
    subprocess.run([str(exe)], check=True)
print("PASS: r28 same-band channel priority, 15-second scan throttle, pending-scan coalescing and worker telemetry")
