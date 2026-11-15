#!/usr/bin/env python3
"""r29 scan lifecycle, pending dispatch, UniFi ESS and logger regressions."""
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
LOGGER = (ROOT / "tools/rtl88wifi-scanlog.sh").read_text()

assert '1.0.13' in CTRL_CPP
assert 'buildPrioritizedChannelList(' in IEEE_CPP
assert 'same_band=%u cross_band=%u' in IEEE_CPP
assert 'kConnectedScanMinIntervalUS = 15ULL * 1000ULL * 1000ULL' in POLICY
assert 'connected scan rate-limited' in IEEE_CPP
assert 'scan worker core-complete enter' in IEEE_CPP
assert 'scan worker core-complete returned' in IEEE_CPP
assert 'scan worker scanDone returned' in IEEE_CPP
assert 'scanDone(aborted, true)' in IEEE_CPP
assert 'scanDone(bool aborted, bool manualWorkerFinalizer)' in IEEE_CPP
assert 'manual-worker reconciled' in IEEE_CPP
assert 'scanDone ignored stale callback' in IEEE_CPP
assert 'scan completion delivered aborted=' in CTRL_CPP
assert 'volatile bool           _scanInProgress' in CTRL_HPP
assert '__atomic_load_n(&_scanInProgress' in CTRL_HPP
assert '__atomic_store_n(&_scanInProgress' in CTRL_HPP
assert '__atomic_compare_exchange_n(&_scanInProgress' in CTRL_HPP
assert 'bool tryBeginScanRequest()' in CTRL_HPP
assert 'pendingScanDispatchDeferrals' in CTRL_HPP
assert 'pendingScanStableMismatchCount' in CTRL_HPP
assert 'pending scan retained backend_scanning=1' in CTRL_CPP
assert 'stale scan latch recovered' in CTRL_CPP
assert 'pending scan requeued after backend busy race' in CTRL_CPP
assert 'queuePendingScanRequest' in CTRL_CPP
assert 'if (first && _pendingScanTimer)' in CTRL_CPP
assert 'pending scan requeued after backend state race' in CTRL_CPP
assert 'if (!tryBeginScanRequest())' in CTRL_CPP
assert 'rtw88Event(kRTW88EventScanDone, &result)' in CTRL_CPP
assert 'setScanRequestInProgress(true)' not in CTRL_CPP
assert 'pendingScanMustDefer' in CTRL_CPP and 'staleScanLatchCanRecover' in CTRL_CPP
assert 'connectedScanRateLimitRemainingMS' in CTRL_CPP
assert 'pending connected scan retained by 15s throttle' in CTRL_CPP
assert 'deferred by connected-scan throttle' in CTRL_CPP
assert 'connectedScanRemainingMS' in POLICY
assert 'const RTW88State rawState = _ieee80211->rawState()' in CTRL_CPP
assert 'rtw88: mesh ESS inventory fresh_nodes=' in IEEE_CPP
assert 'mesh ESS node id=%02x%02x%02x' in IEEE_CPP
assert 'rtw88: mesh roam start' in IEEE_CPP
assert 'tx_bw=%u home_bw=%u' in IEEE_CPP
assert 'tx_rate_mbps,tx_mcs,tx_nss,tx_bw_mhz,home_bw_mhz' in LOGGER
assert "grep -Eic 'rtw88: mesh roam (start|complete|failed)'" in LOGGER
assert "RATE_LINE=$(grep -E 'mesh rate transition|mesh rate recovery result'" in LOGGER

program = r'''
#include <cassert>
#include <cstdint>
#include "RTW88RoamScanPolicy.hpp"
int main() {
  using namespace RTW88RoamScan;
  assert(pendingScanMustDefer(true, true, false));
  assert(pendingScanMustDefer(false, true, false));
  assert(pendingScanMustDefer(true, false, false));
  assert(!pendingScanMustDefer(false, false, true));
  assert(!pendingScanMustDefer(true, false, true));
  assert(!staleScanLatchCanRecover(true, false, true, 1, 3));
  assert(!staleScanLatchCanRecover(true, true, true, 3, 3));
  assert(!staleScanLatchCanRecover(false, false, true, 3, 3));
  assert(staleScanLatchCanRecover(true, false, true, 3, 3));
  assert(!staleScanLatchCanRecover(true, false, false, 9, 3));

  uint16_t channels[] = {1, 6, 161, 149, 36, 44};
  sortPreferHomeBand(channels, 6, 157);
  const uint16_t expect5[] = {36, 44, 149, 161, 1, 6};
  for (unsigned i=0; i<6; ++i) assert(channels[i] == expect5[i]);
  assert(connectedScanIntervalElapsed(1000000, 0));
  assert(!connectedScanIntervalElapsed(14999999, 1));
  assert(connectedScanIntervalElapsed(15000001, 1));
  assert(connectedScanRemainingMS(2000000, 1000000) == 14000);
  assert(connectedScanRemainingMS(16000000, 1000000) == 0);
  assert(connectedScanRemainingMS(100, 0) == 0);
  assert(connectedScanRemainingMS(100, 200) == 0);
  uint16_t pending[4] = {36, 0, 0, 0};
  const uint16_t incoming[] = {36, 44, 1, 149, 6};
  uint32_t n = mergePendingChannels(pending, 1, 4, incoming, 5);
  assert(n == 4);
  assert(pending[0] == 36 && pending[1] == 44 && pending[2] == 1 && pending[3] == 149);
  return 0;
}
'''
with tempfile.TemporaryDirectory() as td:
    src = Path(td) / "r29_scan_lifecycle_test.cpp"
    exe = Path(td) / "r29_scan_lifecycle_test"
    src.write_text(program)
    subprocess.run(["clang++", "-std=c++14", "-Wall", "-Wextra", "-Werror",
                    "-I", str(KEXT), str(src), "-o", str(exe)], check=True)
    subprocess.run([str(exe)], check=True)

print("PASS: r29 atomic scan state, pending-request retention, 15s rate-limit retry, stale-latch recovery policy, UniFi ESS same-band ordering and rate telemetry")
