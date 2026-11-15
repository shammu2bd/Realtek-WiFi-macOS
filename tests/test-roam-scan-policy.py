"""Bounded associated-STA scan policy regression tests.

Compiles the same pure helpers used by the kext, then checks that the scan
entry points enable connected scans without aging the unscanned BSS cache.
This does not simulate RF timing, CoreWiFi or hardware behavior.
"""
from pathlib import Path
import subprocess
import tempfile

root = Path(__file__).resolve().parents[1]
header = root / 'driver/RTL88WiFi/src/kext/RTW88RoamScanPolicy.hpp'
cpp = root / 'driver/RTL88WiFi/src/kext/RTW88IEEE80211.cpp'
ctrl = root / 'driver/RTL88WiFi/src/kext/RTL88WiFi.cpp'
src = cpp.read_text()
ctl = ctrl.read_text()

assert 'const bool connectedScan = (_state == RTW88_STATE_CONNECTED);' in src
assert 'if (!aborted && !partialScan)' in src
assert 'if (!connectedScan) {' in src and '_scanGeneration++;' in src
assert 'const bool firmwareScan = !connectedScan' in src
assert 'cmdScan(requested, d->num_channels)' in ctl
assert 'software-connected' in src
assert 'kConnectedScanChannelsPerPass = 1' in header.read_text()
assert 'RTW88RoamScan::nextRoundRobinIndex' in src
assert 'buildPrioritizedChannelList(' in src
assert 'connectedScanIntervalElapsed' in src
assert 'mesh scan slice selected_ch=' in src
assert 'same_band=%u cross_band=%u' in src
assert 'scan worker channel-begin' in src and 'scan worker home-restored' in src
assert 'mesh scan slice done ch=' in src
assert 'freshSameESSPeerCount' in src
assert 'bool staTxBlockedByConnectedScan() const' in (root / 'driver/RTL88WiFi/src/kext/RTW88IEEE80211.hpp').read_text()
assert 'return _state == RTW88_STATE_SCANNING' in (root / 'driver/RTL88WiFi/src/kext/RTW88IEEE80211.hpp').read_text()
assert 'staTxBlockedByConnectedScan()' in ctl and 'return kIOReturnOutputStall;' in ctl
assert 'staTxBlockedByConnectedScan()' in ctl[ctl.index('bool RTL88WiFi::txGateWanted()'):ctl.index('SInt32 RTL88WiFi::performCountryCodeOperation')], 'gate must stop pulling packets during connected off-channel scans'
assert 'staTxBlockedByConnectedScan()' in ctl[ctl.index('void RTL88WiFi::kickGatedOutput()'):ctl.index('SInt32 RTL88WiFi::performCountryCodeOperation')], 'do not reopen gated output while radio is off-channel'
pci = (root / 'driver/RTL88WiFi/src/kext/RTW88PCIDevice.cpp').read_text()
pci_output = pci[pci.index('UInt32 RTW88PCIDevice::outputPacket('):pci.index('void RTW88PCIDevice::resumeTxIfStalled(')]
assert 'staTxBlockedByConnectedScan()' in pci_output and 'return kIOReturnOutputStall;' in pci_output
assert 'resumeTxAfterScanWindow()' in (root / 'driver/RTL88WiFi/src/kext/RTW88IEEE80211.hpp').read_text()
assert 'resumeTxAfterScanWindow();' in src
scan_start = src.index('void RTW88IEEE80211::scanDone(')
scan_done = src[scan_start:src.index('static uint64_t rtw88JoinNowUS()', scan_start)]
assert 'connectedScanCompleted && _parent' in scan_done and scan_done.index('restoreConnectedChannel();') < scan_done.index('resumeTxAfterScanWindow();'), 'resume only after scanDone restored the AP channel'
assert 'resumeTxAfterScanWindow()' in ctl
# A connected-scan hold must not set the hardware-ring _txStalled latch: its
# release has a 160-descriptor watermark and may miss every short home window.
out_start = ctl.index('UInt32 RTL88WiFi::outputPacket(')
out_end = ctl.index('IOReturn RTL88WiFi::getHardwareAddress', out_start)
out_packet = ctl[out_start:out_end]
scan_hold = out_packet[out_packet.index('if (_ieee80211->staTxBlockedByConnectedScan())'):out_packet.index('const unsigned int avail')]
assert 'return kIOReturnOutputStall;' in scan_hold
assert '_txStalled' not in scan_hold
resume = ctl[ctl.index('void RTL88WiFi::resumeTxAfterScanWindow()'):ctl.index('bool RTL88WiFi::setLinkStatus', ctl.index('void RTL88WiFi::resumeTxAfterScanWindow()'))]
assert 'q->service(IOBasicOutputQueue::kServiceAsync)' in resume
assert 'staTxBlockedByConnectedScan()' in resume
assert 'resumeTxIfStalled();' in resume
assert 'if (_scanReturnState != RTW88_STATE_IDLE)' in src and '_manualScanAbort = true;' in src
assert 'requested BSS missing/SAE profile unavailable; starting one full refresh' in src
assert '_missingBssRescanAttempted' in src
worker = src[src.index('void RTW88IEEE80211::runManualScan()'):src.index('/* ------------------------------------------------------------------ */\n/*  Connect', src.index('void RTW88IEEE80211::runManualScan()'))]
assert worker.rindex('_manualScanChannelCount = 0;') < worker.index('scanDone(aborted, true);'), 'old worker must release scan state before deferred callback'
assert worker.index('_manualScanAbort = false;') < worker.index('scanDone(aborted, true);'), 'old worker must not clear a new scan abort flag'
assert worker.index('IOSleep(80);') < worker.index('resumeTxAfterScanWindow();'), 'resume STA output only after returning home'

program = r'''
#include <cassert>
#include <cstdint>
#include "RTW88RoamScanPolicy.hpp"
int main() {
    using namespace RTW88RoamScan;
    uint16_t channels[kMaxMeshChannels] = {};
    uint32_t count = 0;
    assert(requestedContains(nullptr, 0, 36));
    const uint16_t requested[] = { 6, 36, 149 };
    assert(requestedContains(requested, 3, 36));
    assert(!requestedContains(requested, 3, 44));
    assert(appendUnique(channels, &count, kMaxMeshChannels, 36, 6));
    assert(!appendUnique(channels, &count, kMaxMeshChannels, 6, 6)); // home
    assert(!appendUnique(channels, &count, kMaxMeshChannels, 36, 6)); // duplicate
    assert(appendUnique(channels, &count, kMaxMeshChannels, 149, 6));
    for (uint16_t c = 1; c <= 20; ++c)
        (void)appendUnique(channels, &count, kMaxMeshChannels, c, 6);
    assert(count == kMaxMeshChannels);
    assert(!appendUnique(channels, &count, kMaxMeshChannels, 161, 6)); // capped
    assert(channels[0] == 36 && channels[1] == 149);
    sortAscending(channels, count);
    for (uint32_t i = 1; i < count; ++i) assert(channels[i - 1] <= channels[i]);
    uint32_t cursor = 0;
    assert(nextRoundRobinIndex(3, &cursor) == 0 && cursor == 1);
    assert(nextRoundRobinIndex(3, &cursor) == 1 && cursor == 2);
    assert(nextRoundRobinIndex(3, &cursor) == 2 && cursor == 0);
    assert(nextRoundRobinIndex(0, &cursor) == 0);
    assert(recentlySeen(60'000'000, 1));
    assert(!recentlySeen(60'000'002, 1));
    assert(!recentlySeen(1, 2));
    return 0;
}
'''
with tempfile.TemporaryDirectory() as td:
    srcfile = Path(td) / 'test.cpp'
    exe = Path(td) / 'test'
    srcfile.write_text(program)
    subprocess.run(['clang++', '-std=c++17', '-Wall', '-Wextra', '-Werror',
                    '-I', str(header.parent), str(srcfile), '-o', str(exe)],
                   check=True)
    subprocess.run([str(exe)], check=True)
print('PASS: bounded connected-scan policy and source integration guards')
