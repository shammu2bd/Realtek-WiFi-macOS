#!/usr/bin/env python3
"""Regression checks for bounded IO80211 per-AC TX dequeue bursts.

This verifies source configuration and a conservative four-AC burst model.
It is not an IOKit, macOS kernel, radio, or physical throughput test.
"""
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
CTRL = ROOT / "driver/RTL88WiFi/src/kext/RTL88WiFi.cpp"
src = CTRL.read_text()

# Keep the queue depth genuinely per AC and bounded across all four WMM ACs.
def constant(name):
    m = re.search(rf"static constexpr UInt32 {name}\s*=\s*(\d+);", src)
    assert m, f"missing {name}"
    return int(m.group(1))

per_ac = constant("kRTW88DataQueueDepth")
high = constant("kRTW88TxQueueHigh")
low = constant("kRTW88TxQueueLow")
assert per_ac == 8, per_ac
assert high == 32, high
assert low == 16, low
assert 0 < low < high < 256

get_depth = src[src.index("UInt32 RTL88WiFi::getDataQueueDepth"):
                src.index("IOReturn RTL88WiFi::outputStart", src.index("UInt32 RTL88WiFi::getDataQueueDepth"))]
assert "return kRTW88DataQueueDepth;" in get_depth

output_start = src[src.index("IOReturn RTL88WiFi::outputStart"):
                   src.index("SInt32 RTL88WiFi::performCountryCodeOperation")]
assert "txGateWanted()" in output_start
assert "return kIOReturnNoResources;" in output_start
assert "q->getSize() >= kRTW88TxQueueHigh" in output_start
assert "q->getSize() > kRTW88TxQueueLow" in output_start

# Model one outputStart batch: a call begins with a queue size below `high`,
# then may enqueue `per_ac` packets for each of the four ACs before the next
# high-water check. The family queue is capacity 256.
max_precheck_size = high - 1
max_after_one_batch = max_precheck_size + 4 * per_ac
assert max_after_one_batch == 63
assert max_after_one_batch < 256

# Diagnostics must expose queue capacity/peak so the next hardware report can
# verify that the family queue no longer runs up to its capacity.
assert '"txq=%u txcap=%u txpeak=%u txout=%u txretry=%u' in src
assert "qs ? qs->capacity : 0" in src
assert "qs ? qs->peakSize : 0" in src

# Do not regress r24's scan/ring separation and high-water ring safety.
assert "kRTW88TxStallAvail  = 96" in src
assert "kRTW88TxResumeAvail = 160" in src
out_start = src[src.index("UInt32 RTL88WiFi::outputPacket"):
                src.index("IOReturn RTL88WiFi::getHardwareAddress")]
scan_hold = out_start[out_start.index("if (_ieee80211->staTxBlockedByConnectedScan())"):
                       out_start.index("const unsigned int avail")]
assert "return kIOReturnOutputStall;" in scan_hold
assert "_txStalled" not in scan_hold

print("PASS: per-AC depth=8; one four-AC burst <=63/256; high/low watermarks=32/16")
print("PASS: r24 scan pause separation and 96/160 BE-ring hysteresis preserved")
print("PASS: TX queue capacity/peak/output/retry diagnostics present")
