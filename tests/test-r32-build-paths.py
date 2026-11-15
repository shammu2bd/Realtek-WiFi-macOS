#!/usr/bin/env python3
"""Regression guard for the r32.1 RX wrapper path fix."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DRIVER = ROOT / "driver/RTL88WiFi"
wrapper = DRIVER / "src/compat/rtw88_rx.c"
text = wrapper.read_text()
expected = '#include "../../../rtw88-stable/drivers/net/wireless/realtek/rtw88/rx.c"'
assert expected in text, "RX wrapper must walk from driver/RTL88WiFi/src/compat to driver/rtw88-stable"
assert '#include \"../../rtw88-stable/drivers/net/wireless/realtek/rtw88/rx.c\"' not in text, "old broken relative path remains"
resolved = (wrapper.parent / "../../../rtw88-stable/drivers/net/wireless/realtek/rtw88/rx.c").resolve()
assert resolved.is_file(), f"RX implementation not found at corrected include target: {resolved}"
makefile = (DRIVER / "Makefile").read_text()
assert "$(LINUX_SRC)/rx.c" in makefile
assert "$(COMPAT_DIR)/rtw88_rx.c" in makefile
assert "$(BUILD_DIR)/driver/rx.o" in makefile
assert "rtl88wifi: $(AIRPORT_OUT_BIN)" in makefile
assert "$(BUILD_DIR)/driver/rx.o" in makefile[makefile.index("DRIVER_OBJS"):]  # RX wrapper is in kext dependency graph
print("PASS: r32.1 RX wrapper include resolves to the pinned rtw88 rx.c and rtl88wifi target includes rx.o")
