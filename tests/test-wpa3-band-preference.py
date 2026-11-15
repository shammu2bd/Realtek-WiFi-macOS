#!/usr/bin/env python3
"""WPA3 same-SSID 5 GHz preference regression tests.

Compiles the actual header-only join scoring/eligibility policy and checks
that the SAE connect and retry paths call the production WPA3 BSS selector.
This does not emulate CoreWiFi, the Apple kext runtime or RF behaviour.
"""
from pathlib import Path
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
KEXT = ROOT / "driver/RTL88WiFi/src/kext"
POLICY = (KEXT / "RTW88JoinPolicy.hpp").read_text()
IEEE = (KEXT / "RTW88IEEE80211.cpp").read_text()
HEADER = (KEXT / "RTW88IEEE80211.hpp").read_text()

assert "usable5GHzUpgrade" in POLICY
assert "RTW88BSS *RTW88IEEE80211::selectWpa3BssForJoinLocked" in IEEE
selector = IEEE.split("RTW88BSS *RTW88IEEE80211::selectWpa3BssForJoinLocked", 1)[1]
selector = selector.split("/* Is there another node", 1)[0]
assert "RTW88WPA3::profile" in selector, "WPA3 selector must reject non-SAE/PMF BSS entries"
assert "RTW88Join::score" in selector, "WPA3 selection must use the shared band/freshness/RSSI score"
assert "RTW88Join::usable5GHzUpgrade" in selector, "pinned 2.4 GHz upgrade must require a usable fresh 5 GHz sibling"
assert "_prefer5GHzUpgrade" in selector, "the existing user preference switch must gate pinned upgrades"
assert "if (!requested)" in selector, "unknown pinned BSSID must not silently select another node"
assert "selectWpa3BssForJoinLocked(ssid, wantedLen, bssid, false" in IEEE
assert "_joinHasRequested = true" in IEEE and "_joinRequestedBssid" in IEEE
assert "selectWpa3BssForJoinLocked(_targetBSS.ssid" in IEEE, "SAE failure fallback must use the band-aware selector"
assert "if (_saeMode)" in IEEE.split("bool RTW88IEEE80211::hasUntriedAlternativeLocked()", 1)[1].split("/* If macOS supplied", 1)[0], "SAE retry budget must count only WPA3-capable alternatives"
assert "nullptr, true, nullptr" in IEEE, "SAE fallback must skip BSSIDs already tried"
assert "prefer5=%u" in IEEE, "connection diagnostics must expose the active preference"
assert "selectWpa3BssForJoinLocked" in HEADER

program = r'''
#include <cassert>
#include <cstdint>
#include "RTW88JoinPolicy.hpp"
struct Candidate { int rssi; uint8_t channel; uint32_t age; bool failed; };
static const Candidate *best(const Candidate *v, unsigned n) {
  const Candidate *pick = nullptr; int pickScore = -2147483647;
  for (unsigned i=0; i<n; ++i) {
    int s = RTW88Join::score(v[i].rssi, v[i].channel, v[i].age, v[i].failed);
    if (!pick || s > pickScore) { pick = &v[i]; pickScore = s; }
  }
  return pick;
}
static bool shouldUpgrade(const Candidate &requested, const Candidate &five,
                          bool enabled) {
  if (!enabled || requested.channel > 14 ||
      !RTW88Join::usable5GHzUpgrade(five.rssi, five.channel, five.age, five.failed))
    return false;
  return RTW88Join::score(five.rssi, five.channel, five.age, five.failed) >
         RTW88Join::score(requested.rssi, requested.channel, requested.age, requested.failed);
}
int main() {
  Candidate two{ -48, 6, 0, false };
  Candidate five{ -56, 157, 0, false };
  assert(shouldUpgrade(two, five, true));
  Candidate bandPick[] = {two, five};
  assert(best(bandPick, 2) == &bandPick[1]);

  Candidate stale{ -56, 157, 2, false };
  assert(!shouldUpgrade(two, stale, true));
  Candidate weak{ -78, 157, 0, false };
  assert(!shouldUpgrade(two, weak, true));
  Candidate failed{ -55, 157, 0, true };
  assert(!shouldUpgrade(two, failed, true));
  assert(!shouldUpgrade(two, five, false));

  Candidate close24{ -30, 1, 0, false };
  Candidate far5{ -72, 149, 0, false };
  // The preference is strong, not absolute: a dramatically stronger 2.4 GHz
  // BSS may still outscore the 5 GHz sibling, matching the existing WPA2 rule.
  assert(!shouldUpgrade(close24, far5, true));

  Candidate fiveSecond{ -70, 153, 1, false };
  assert(RTW88Join::usable5GHzUpgrade(fiveSecond.rssi, fiveSecond.channel,
                                      fiveSecond.age, fiveSecond.failed));
  assert(shouldUpgrade(two, fiveSecond, true));
  return 0;
}
'''
with tempfile.TemporaryDirectory() as td:
    src = Path(td) / "wpa3_band_preference.cpp"
    exe = Path(td) / "wpa3_band_preference"
    src.write_text(program)
    subprocess.run(["clang++", "-std=c++14", "-Wall", "-Wextra", "-Werror",
                    "-I", str(KEXT), str(src), "-o", str(exe)], check=True)
    subprocess.run([str(exe)], check=True)
print("PASS: WPA3 SAE candidate selection uses shared fresh/usable 5 GHz preference and retains pinned-BSSID safeguards")
