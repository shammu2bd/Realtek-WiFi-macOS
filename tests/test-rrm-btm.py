#!/usr/bin/env python3
"""Host tests for 802.11k Neighbor Report and 802.11v BTM wire handling.

Compiles the production bounded wire helpers used by the kext. Source guards
cover capability negotiation, PMF-verified RX, TX-ACK-gated BTM handoff and the
controller's PM-fenced ACK timer. This does not emulate CoreWiFi or RF behavior.
"""
from pathlib import Path
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
KEXT = ROOT / "driver/RTL88WiFi/src/kext"
IEEE_CPP = (KEXT / "RTW88IEEE80211.cpp").read_text()
IEEE_HPP = (KEXT / "RTW88IEEE80211.hpp").read_text()
CTRL_CPP = (KEXT / "RTL88WiFi.cpp").read_text()
CTRL_HPP = (KEXT / "RTL88WiFi.hpp").read_text()
ROAMING = (KEXT / "RTW88Roaming.hpp").read_text()

assert '#include "RTW88Roaming.hpp"' in IEEE_HPP
assert "handleRoamingAction(skb->data, skb->len" in IEEE_CPP
assert "rtw88JoinNowUS() / 1000ULL, pmfVerified" in IEEE_CPP
assert "_stationNeighborReport" in IEEE_CPP and "_stationBTM" in IEEE_CPP
assert "neighborReportCaps[] = {70, 5, 0x02" in IEEE_CPP
assert "btmExtCaps[] = {127, 3, 0, 0, 0x08}" in IEEE_CPP
assert "roamingTick(now / 1000ULL)" in IEEE_CPP
assert "_btmProtectedReceipt.record" in IEEE_CPP
assert "observeBtmTx(skb->data, skb->len" in IEEE_CPP
assert "cmdRoam(target, channel, false)" in IEEE_CPP
assert "_btmAckIdentity" in IEEE_CPP and "_btmAckDeadlineMs" in IEEE_CPP
assert "virtual bool roamingControlAvailable() const override" in CTRL_HPP
assert "virtual bool scheduleRoamingControl(unsigned delayMs) override" in CTRL_HPP
assert "roamingTimerFired" in CTRL_CPP
assert "_diagnosticsInHardware, true" in CTRL_CPP[CTRL_CPP.index("void RTL88WiFi::roamingTimerFired"):CTRL_CPP.index("/* IO80211FamilyLegacy re-enters", CTRL_CPP.index("void RTL88WiFi::roamingTimerFired"))]
assert "__atomic_load_n(&_pmTransition" in CTRL_CPP
assert "BSS termination and ESS-disassociation semantics" in IEEE_CPP
assert "no fresh secure same-ESS candidate in scan cache" in IEEE_CPP or "no secure candidate found after directed scan" in IEEE_CPP
assert "selectBtmScanChannel" in IEEE_CPP
assert "cmdScan(&requestedChannel, 1)" in IEEE_CPP
assert "_btmScanCompleted && b->last_seen_us < _btmScanStartUS" in IEEE_CPP
assert "meshChannels[0] == _btmScanChannel" in IEEE_CPP
assert "_btmPhase, 1U, __ATOMIC_RELEASE" in IEEE_CPP
assert "directed candidate scan was aborted" in IEEE_CPP
assert "RTW88Roaming::BtmRequest acceptedRequest = request;" in IEEE_CPP
assert "if (!(acceptedRequest.mode & 0x01))" in IEEE_CPP
assert "acceptedRequest.candidates = _roaming.neighbors;" in IEEE_CPP
assert "empty BTM preferred candidate list" in IEEE_CPP
assert "if (_saeMode && !pmfVerified)" in IEEE_CPP
assert "bool pmfVerified = false;" in IEEE_CPP[IEEE_CPP.index("void RTW88IEEE80211::processRxMgmt"):IEEE_CPP.index("static uint32_t rtw88ReadSuite")]

source = r'''
#include <cassert>
#include <cstdint>
#include <cstring>
#include "RTW88Roaming.hpp"

static void make_neighbor_ie(uint8_t *ie, size_t &n, const uint8_t *bssid,
                             uint8_t channel, bool preference) {
    ie[0] = 52;
    ie[1] = preference ? 16 : 13;
    std::memcpy(ie + 2, bssid, 6);
    ie[8] = 1; ie[9] = 0; ie[10] = 0; ie[11] = 0; // BSSID information
    ie[12] = 115; // Operating class hint
    ie[13] = channel;
    ie[14] = 7;   // PHY type
    if (preference) { ie[15] = 3; ie[16] = 1; ie[17] = 200; }
    n = preference ? 18 : 15;
}

int main() {
    using namespace RTW88Roaming;
    const uint8_t local[6] = {0x02,0,0,0,0,0x22};
    const uint8_t ap[6]    = {0x02,0,0,0,0,0x11};
    const uint8_t peer[6]  = {0x02,0,0,0,0,0x33};

    Capabilities caps;
    const uint8_t ap_ies[] = {70,5,0x02,0,0,0,0, 127,3,0,0,0x08};
    assert(capabilities(ap_ies, sizeof(ap_ies), caps));
    assert(caps.neighborReport && caps.btm);
    const uint8_t malformed_caps[] = {70,4,0,0,0,0};
    assert(!capabilities(malformed_caps, sizeof(malformed_caps), caps));

    uint8_t request[40] = {};
    const uint8_t ssid[] = {'M','e','s','h'};
    size_t n = neighborRequest(request, sizeof(request), 9, ssid, sizeof(ssid));
    assert(n == 9 && request[0] == 5 && request[1] == 4 && request[2] == 9);
    assert(request[3] == 0 && request[4] == 4 && !std::memcmp(request + 5, ssid, 4));
    assert(neighborRequest(request, sizeof(request), 0, ssid, sizeof(ssid)) == 0);

    uint8_t neighbor[32] = {};
    size_t neighborLen = 0;
    make_neighbor_ie(neighbor, neighborLen, peer, 149, true);
    uint8_t response[40] = {5,5,9};
    std::memcpy(response + 3, neighbor, neighborLen);
    Candidates candidates;
    ParseDiagnostic diagnostic;
    assert(neighborResponse(response, 3 + neighborLen, 9, candidates, &diagnostic));
    assert(candidates.count == 1 && candidates.entries[0].channel == 149);
    assert(candidates.entries[0].hasPreference && candidates.entries[0].preference == 200);
    assert(!neighborResponse(response, 3 + neighborLen, 8, candidates, &diagnostic));
    response[3 + 1] = 0xff;
    assert(!neighborResponse(response, 3 + neighborLen, 9, candidates, &diagnostic));

    uint8_t btm[48] = {10,7,4,0x01,0,0,10};
    std::memcpy(btm + 7, neighbor, neighborLen);
    BtmRequest parsed;
    assert(btmRequest(btm, 7 + neighborLen, parsed));
    assert(parsed.token == 4 && parsed.mode == 1 && parsed.candidates.count == 1);
    btm[3] = 0x20; // Reserved bit.
    assert(!btmRequest(btm, 7 + neighborLen, parsed));
    btm[3] = 0x01;

    uint8_t reply[11] = {};
    assert(btmResponse(reply, sizeof(reply), 4, 0, peer) == 11);
    assert(reply[0] == 10 && reply[1] == 8 && reply[2] == 4 && reply[3] == 0);
    assert(!std::memcmp(reply + 5, peer, 6));
    assert(btmResponse(reply, sizeof(reply), 4, 7, nullptr) == 5);
    assert(btmResponse(reply, sizeof(reply), 4, 0, nullptr) == 0);

    /* Validate AP-originated action-frame addressing and subtype. */
    uint8_t frame[24 + 3] = {};
    frame[0] = 0xd0;
    std::memcpy(frame + 4, local, 6);
    std::memcpy(frame + 10, ap, 6);
    std::memcpy(frame + 16, ap, 6);
    frame[24] = 5; frame[25] = 5; frame[26] = 9;
    assert(actionFromAP(frame, sizeof(frame), local, ap));
    frame[4] ^= 1;
    assert(!actionFromAP(frame, sizeof(frame), local, ap));

    /* PMF receipt must bind both TX header sequence identity and CCMP PN. */
    uint8_t plain[35] = {};
    plain[0] = 0xd0;
    std::memcpy(plain + 4, ap, 6);
    std::memcpy(plain + 10, local, 6);
    std::memcpy(plain + 16, ap, 6);
    plain[22] = 0x30; // sequence 3
    plain[24] = 10; plain[25] = 8; plain[26] = 4; plain[27] = 0;
    std::memcpy(plain + 29, peer, 6);
    const uint64_t identity = btmIdentity(3, ap);
    BtmProtectedReceipt receipt;
    assert(receipt.record(plain, sizeof(plain), identity, 0x060504030201ULL));
    uint8_t encrypted[51] = {};
    std::memcpy(encrypted, plain, 24);
    encrypted[1] |= 0x40;
    encrypted[24] = 1; encrypted[25] = 2; encrypted[26] = 0; encrypted[27] = 0x20;
    encrypted[28] = 3; encrypted[29] = 4; encrypted[30] = 5; encrypted[31] = 6;
    assert(receipt.matches(encrypted, sizeof(encrypted)));
    encrypted[31] ^= 1;
    assert(!receipt.matches(encrypted, sizeof(encrypted)));
    receipt.clear();
    assert(!receipt.matches(encrypted, sizeof(encrypted)));

    return 0;
}
'''
with tempfile.TemporaryDirectory() as td:
    src = Path(td) / "rrm_btm_test.cpp"
    binary = Path(td) / "rrm_btm_test"
    src.write_text(source)
    subprocess.run(["clang++", "-std=c++17", "-Wall", "-Wextra", "-Werror",
                    "-I", str(KEXT), str(src), "-o", str(binary)], check=True)
    subprocess.run([str(binary)], check=True)
print("PASS: 802.11k Neighbor Report parsing/request and 802.11v BTM parsing/response/PMF ACK receipt tests")
