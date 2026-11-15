#!/usr/bin/env python3
"""Regression checks for the two fatal errors from the r32.1 macOS build log."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
KEXT = ROOT / "driver/RTL88WiFi/src/kext"
compat = (KEXT / "../compat/rtw88_compat.h").resolve()
rx_helper = (KEXT / "../compat/rtw88_rx_security.h").resolve()
cpp = (KEXT / "RTW88IEEE80211.cpp").read_text()
hpp = (KEXT / "RTW88IEEE80211.hpp").read_text()
controller = (KEXT / "RTL88WiFi.cpp").read_text()

compat_pos = cpp.index('#include "../compat/rtw88_compat.h"')
helper_pos = cpp.index('#include "../compat/rtw88_rx_security.h"')
assert compat_pos < helper_pos, "RX security helper must follow compat/mac80211 flag definitions"
assert "RX_FLAG_DECRYPTED" in (rx_helper.read_text()), "RX helper must retain decrypted flag guard"
assert "kRTW88EventHandshakeDone" in hpp, "WPA3 handshake event must be declared"
assert "case kRTW88EventHandshakeDone:" in controller, "controller must consume WPA3 handshake event"
assert "APPLE80211_M_RSN_HANDSHAKE_DONE" in controller[controller.index("case kRTW88EventHandshakeDone:"):], "controller must notify IO80211 after WPA3 handshake"
assert '1.0.13' in controller
print("PASS: RX flag include order and WPA3 handshake event declaration/dispatch")
