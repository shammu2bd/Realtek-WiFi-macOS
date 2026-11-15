#!/usr/bin/env python3
"""WPA3-Personal frontend/PMF integration guards plus host-testable RSN policy.

This test does not compile an Apple kext or exercise a physical radio. The
cryptographic/session path is covered by experimental/wpa3/test_host.py.
"""
from pathlib import Path
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
DRIVER = ROOT / "driver/RTL88WiFi"
KEXT = DRIVER / "src/kext"
ctrl = (KEXT / "RTL88WiFi.cpp").read_text()
ieee = (KEXT / "RTW88IEEE80211.cpp").read_text()
ieee_h = (KEXT / "RTW88IEEE80211.hpp").read_text()
wire = (KEXT / "RTW88AssocWire.hpp").read_text()
wpa3 = (KEXT / "RTW88WPA3.hpp").read_text()
makefile = (DRIVER / "Makefile").read_text()

# Native macOS menu and credential transport.
assert "d->capabilities[6] |= 0x01" in ctrl
assert "d->capabilities[9] |= 0x18" in ctrl
assert "WPA3_MENU_CAPABILITIES" in ctrl
assert "RTW88AssocWire::PasswordPrefixSize" in ctrl
assert "RTW88AssocWire::decode(prefix, sizeof(prefix), fields)" in ctrl
assert "fields.cipher == 10" in ctrl and "connectPersonalPassword" in ctrl
assert "keyLength > 63" in wire
assert "keyLength > n - 76" in wire
assert "IOUserClient::clientHasPrivilege(current_task(), kIOClientPrivilegeAdministrator)" in ctrl
assert "Deliberately do not call super::setProperties()" in ctrl

# Mode selection must use positive evidence for PSK-only BSSes. Explicit SAE
# requests always remain SAE; SAE-only PMK input is rejected, not reinterpreted.
assert "const bool sae = (r->upper & kSaeMask) != 0 ||" in ctrl
assert "bssOffersPSKOnly(r->ssid, b)" in ctrl
assert "pmk-only-transition-refused" in ctrl
assert "if (explicitSAE)" in ctrl and "sae-passphrase-required" in ctrl
assert "connectPersonalPassword(ssid, password, bssid, upper)" in ctrl

# SAE auth, RSN/RSNXE association, EAPOL, pairwise key installation and PMF.
for token in [
    "RTW88WPA3::Session _sae",
    "cmdConnectSAE",
    "RTW88WPA3::profile",
    "_sae.rsn(body)",
    "wpa3Auth()",
    "wpa3ReceiveAuth",
    "wpa3Eapol",
    "wpa3InstallPairwise",
    "wpa3TxMgmt",
    "wpa3Mgmt",
    "RX_FLAG_RTW_CCMP_VERIFIED",
    "RX_FLAG_RTW_INTEGRITY_FAILED",
    "bip(",
]:
    assert token in (ieee_h + ieee + wpa3), f"missing WPA3 path element: {token}"

# A transition-mode PMK must not silently start SAE or fall back to PSK.
assert "SAE requires the original passphrase for Dragonfly" in ctrl
assert "transition BSS offers SAE; refusing PMK-only WPA2 downgrade" in ctrl
assert "current.akm != b->akm" in ieee
assert "(!_saeMode && current.akm && b->akm && current.akm != b->akm)" in ieee
assert "_saeMode = true" in ieee[ieee.index("IOReturn RTW88IEEE80211::cmdRoam"):]
# If firmware cannot install the pairwise CAM key, the session must use the
# software CCMP implementation rather than leaving WPA3 half-authorized.
assert "using software CCMP for this session" in ieee
clear = ieee[ieee.index("void RTW88IEEE80211::clearWPA3()"):]
assert "_saeSoftwareCCMP = false" in clear.split("}", 1)[0]

# Crypto backend must be included in both native targets and retain private
# namespacing/attribution with an auditable host test.
assert "RTW88WPA3Crypto.cpp" in makefile
assert "$(filter %.d,$(ALL_OBJS:.o=.d))" in makefile
assert "$(WPA3_SAE_ARCHIVE)" in makefile
assert "build-sae.sh" in makefile
assert (DRIVER / "experimental/wpa3/validate_provenance.py").exists()
assert (DRIVER / "experimental/wpa3/rtw80211/sae/NOTICE.txt").exists()
assert (DRIVER / "NOTICE-WPA3-AIRPORT-RTW.md").exists()

# Compile the pure RSN helper and verify PSK-only / mixed / SAE-only / PMF cases.
program = r'''#include <cassert>
#include <cstdint>
#include <vector>
#include "RTW88Enterprise.hpp"
using namespace RTW88Enterprise;
static void le16(std::vector<uint8_t>&v,uint16_t x){v.push_back(x);v.push_back(x>>8);}
static void suite(std::vector<uint8_t>&v,uint8_t type){v.insert(v.end(),{0,15,172,type});}
static std::vector<uint8_t> rsn(bool psk,bool sae,uint16_t caps){
 std::vector<uint8_t> b;le16(b,1);suite(b,4);le16(b,1);suite(b,4);
 le16(b,uint16_t(psk+sae));if(psk)suite(b,2);if(sae)suite(b,8);le16(b,caps);
 std::vector<uint8_t> out={48,uint8_t(b.size())};out.insert(out.end(),b.begin(),b.end());return out;
}
int main(){
 auto p=rsn(true,false,0);assert(pskOnly(p.data(),p.size()));
 auto pMFPC=rsn(true,false,1u<<7);assert(pskOnly(pMFPC.data(),pMFPC.size()));
 auto trans=rsn(true,true,1u<<7);assert(!pskOnly(trans.data(),trans.size()));
 auto sae=rsn(false,true, (1u<<6)|(1u<<7));assert(!pskOnly(sae.data(),sae.size()));
 auto mfpr=rsn(true,false,1u<<6);assert(!pskOnly(mfpr.data(),mfpr.size()));
 return 0;
}'''
with tempfile.TemporaryDirectory(prefix="rtw88-wpa3-policy-") as td:
    src = Path(td) / "policy.cpp"
    exe = Path(td) / "policy"
    src.write_text(program)
    subprocess.run(["clang++", "-std=c++17", "-Wall", "-Wextra", "-Werror",
                    "-I", str(KEXT), str(src), "-o", str(exe)], check=True)
    subprocess.run([str(exe)], check=True)
print("PASS: WPA3 menu bridge, password-only SAE selection, PMK downgrade fence, SAE roaming, PMF/CCMP backend wiring, provenance and PSK-only RSN policy")
