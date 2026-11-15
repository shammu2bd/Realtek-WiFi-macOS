#pragma once
#include <stdint.h>
#include <stddef.h>
#include <string.h>

// Sequoia 900-byte and Tahoe 908-byte ASSOCIATE envelopes. Only the stable
// 108-byte shared prefix and, for explicitly typed passphrases, the extended
// 140-byte credential prefix are read. The unknown tail is never inspected.
namespace RTW88AssocWire {
constexpr size_t RequestSize = 900, TahoeRequestSize = 908;
constexpr size_t PrefixSize = 108, PasswordPrefixSize = 140;
inline bool supportedRequestSize(size_t n) { return n == RequestSize || n == TahoeRequestSize; }
struct Personal {
    uint32_t mode, lower, upper, ssidLength, keyLength, cipher;
    uint8_t ssid[32], bssid[6], key[64];
};
inline uint32_t le32(const uint8_t *p) {
    return uint32_t(p[0]) | uint32_t(p[1])<<8 | uint32_t(p[2])<<16 | uint32_t(p[3])<<24;
}
inline bool decode(const uint8_t *p, size_t n, Personal &out) {
    if (!p || (n != PrefixSize && n != PasswordPrefixSize) ||
        le32(p) != 1 || le32(p + 4) != 2 || le32(p + 8) != 1)
        return false;

    const uint32_t upper = le32(p + 12);
    const uint32_t ssidLength = le32(p + 16);
    const uint32_t keyVersion = le32(p + 60);
    const uint32_t keyLength = le32(p + 64);
    const uint32_t cipher = le32(p + 68);

    constexpr uint32_t kWpa2Psk = 1U << 3;
    constexpr uint32_t kSaeLegacy = 1U << 9;
    constexpr uint32_t kSaeModern = 1U << 12;
    constexpr uint32_t kKnownAKMs = kWpa2Psk | kSaeLegacy | kSaeModern;
    constexpr uint32_t kPassphraseCipher = 10;
    constexpr uint32_t kPmkCcmp = 6;
    constexpr uint32_t kPmkTkip = 7;

    if (!ssidLength || ssidLength > 32 || (upper & ~kKnownAKMs) != 0)
        return false;

    // A WPA3 or transition request must carry the original passphrase. A
    // pre-derived WPA2 PMK is not an SAE password and must never be used to
    // start an SAE exchange.
    const bool password = cipher == kPassphraseCipher;
    if (password) {
        if (upper == 0 || keyVersion != 1 || keyLength < 8 ||
            keyLength > 63 || keyLength > n - 76)
            return false;
        for (uint32_t i = 0; i < keyLength; ++i)
            if (!p[76 + i]) return false;
    } else if (upper == 0) {
        // The legacy Apple ABI uses keyVersion=0 for an open-network join.
        if ((keyVersion != 0 && keyVersion != 1) || keyLength != 0 ||
            (cipher != 0 && cipher != kPmkCcmp && cipher != kPmkTkip))
            return false;
    } else {
        // Accept a PMK only when WPA2-PSK is explicitly one of the AKMs. This
        // includes transition masks so the caller can reject downgrade to the
        // WPA2 side when the matching BSS also offers SAE. Pure SAE with a PMK
        // is invalid because the SAE password-element exchange needs a
        // passphrase, not a 256-bit PSK/PMK blob.
        const bool hasPSK = (upper & kWpa2Psk) != 0;
        if (!hasPSK || keyVersion != 1 || keyLength != 32 ||
            (cipher != kPmkCcmp && cipher != kPmkTkip))
            return false;
    }

    for (uint32_t i = 0; i < ssidLength; ++i)
        if (!p[20 + i]) return false;
    if (p[52] & 1) return false; // BSSID must be unicast.

    out = {};
    out.mode = 2;
    out.lower = 1;
    out.upper = upper;
    out.ssidLength = ssidLength;
    out.keyLength = keyLength;
    out.cipher = cipher;
    memcpy(out.ssid, p + 20, ssidLength);
    memcpy(out.bssid, p + 52, 6);
    if (keyLength) memcpy(out.key, p + 76, keyLength);
    return true;
}
inline void wipe(void *p,size_t n) {
    volatile uint8_t *q=static_cast<volatile uint8_t *>(p); while(n--) *q++=0;
}
}
