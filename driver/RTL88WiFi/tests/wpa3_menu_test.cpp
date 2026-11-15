#include "../src/kext/RTW88AssocWire.hpp"
#include <cassert>
#include <cstdint>
#include <cstdio>
#include <cstring>
#include <vector>

using namespace RTW88AssocWire;

static void put32(std::vector<uint8_t> &p, size_t offset, uint32_t value)
{
    for (unsigned i = 0; i < 4; ++i)
        p[offset + i] = uint8_t(value >> (8 * i));
}

static std::vector<uint8_t> request(uint32_t upper, uint32_t cipher,
                                    uint32_t keyLength, uint32_t keyVersion = 1)
{
    std::vector<uint8_t> p(PrefixSize, 0);
    put32(p, 0, 1);       // version
    put32(p, 4, 2);       // request type: ASSOCIATE
    put32(p, 8, 1);       // subtype
    put32(p, 12, upper);  // auth AKM mask
    put32(p, 16, 4);      // SSID length
    std::memcpy(p.data() + 20, "test", 4);
    p[52] = 2;            // unicast BSSID
    put32(p, 60, keyVersion);
    put32(p, 64, keyLength);
    put32(p, 68, cipher);
    for (size_t i = 76; i < 108; ++i) p[i] = 0x42;
    return p;
}

int main()
{
    constexpr uint32_t WPA2 = 1u << 3;
    constexpr uint32_t SAE_LEGACY = 1u << 9;
    constexpr uint32_t SAE_MODERN = 1u << 12;
    constexpr uint32_t PASSPHRASE = 10;
    constexpr uint32_t PMK = 6;
    Personal out{};

    // WPA3-Personal pure SAE and WPA2/WPA3 transition requests carry a
    // passphrase, never a pre-derived PMK.
    for (uint32_t upper : {SAE_LEGACY, SAE_MODERN,
                           WPA2 | SAE_LEGACY, WPA2 | SAE_MODERN}) {
        for (uint32_t length : {8u, 16u, 32u}) {
            auto p = request(upper, PASSPHRASE, length);
            assert(decode(p.data(), p.size(), out));
            assert(out.upper == upper && out.cipher == PASSPHRASE);
            assert(out.keyLength == length && out.key[0] == 0x42);
        }
    }

    // A WPA2 PSK passphrase path remains valid, as does the pre-derived PMK ABI.
    for (uint32_t length : {8u, 16u, 32u}) {
        auto p = request(WPA2, PASSPHRASE, length);
        assert(decode(p.data(), p.size(), out));
    }
    auto pmk = request(WPA2, PMK, 32);
    assert(decode(pmk.data(), pmk.size(), out));
    assert(out.cipher == PMK && out.keyLength == 32);

    // A transition request with a PMK can be decoded so the front end can
    // explicitly reject WPA2-only fallback instead of silently downgrading.
    auto transitionPMK = request(WPA2 | SAE_MODERN, PMK, 32);
    assert(decode(transitionPMK.data(), transitionPMK.size(), out));
    assert(out.upper == (WPA2 | SAE_MODERN));

    // An SAE-only request must never reinterpret a PMK as an SAE password.
    for (uint32_t sae : {SAE_LEGACY, SAE_MODERN}) {
        auto p = request(sae, PMK, 32);
        assert(!decode(p.data(), p.size(), out));
    }

    // Reject unsupported AKMs, bad passphrase lengths, missing key bytes,
    // embedded NULs, and malformed fixed-size Apple80211 envelopes.
    auto badAKM = request(SAE_MODERN | (1u << 7), PASSPHRASE, 16);
    assert(!decode(badAKM.data(), badAKM.size(), out));
    for (uint32_t length : {0u, 1u, 7u, 33u, 64u}) {
        auto p = request(SAE_MODERN, PASSPHRASE, length);
        assert(!decode(p.data(), p.size(), out));
    }
    auto embeddedNul = request(SAE_MODERN, PASSPHRASE, 16);
    embeddedNul[82] = 0;
    assert(!decode(embeddedNul.data(), embeddedNul.size(), out));
    auto wrongVersion = request(SAE_MODERN, PASSPHRASE, 16);
    put32(wrongVersion, 0, 2);
    assert(!decode(wrongVersion.data(), wrongVersion.size(), out));
    auto invalidBssid = request(SAE_MODERN, PASSPHRASE, 16);
    invalidBssid[52] = 3;
    assert(!decode(invalidBssid.data(), invalidBssid.size(), out));
    auto tooShort = request(SAE_MODERN, PASSPHRASE, 16);
    assert(!decode(tooShort.data(), PrefixSize - 1, out));
    assert(supportedRequestSize(RequestSize));
    assert(supportedRequestSize(TahoeRequestSize));
    assert(!supportedRequestSize(PrefixSize));

    // Open network behavior remains available and has no secret material.
    auto open = request(0, 0, 0, 0);
    assert(decode(open.data(), open.size(), out));
    assert(out.upper == 0 && out.keyLength == 0);

    wipe(&out, sizeof(out));
    std::puts("PASS: WPA2/SAE/transition menu ABI validation; PMK is never treated as SAE password");
    return 0;
}
