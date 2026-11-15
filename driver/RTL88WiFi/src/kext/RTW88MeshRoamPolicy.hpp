/* SPDX-License-Identifier: GPL-2.0 OR BSD-3-Clause
 * Conservative connected-ESS roaming policy. Kept independent of IOKit so
 * thresholds and cache freshness can be tested on the host.
 */
#pragma once
#include <stdint.h>

namespace RTW88MeshRoam {
static constexpr int kTriggerRSSIDbm = -70;
static constexpr int kMinimumImprovementDb = 12;
static constexpr int kMinimumCandidateRSSIDbm = -82;
/* A one-channel-per-request sweep may take several scan intervals to cover
 * every candidate channel. Keep observations fresh long enough for a full
 * eight-channel rotation without accepting stale BSSID information. */
static constexpr uint64_t kCandidateFreshUS = 60ULL * 1000ULL * 1000ULL;
static constexpr uint64_t kAttemptCooldownUS = 45ULL * 1000ULL * 1000ULL;
static constexpr uint64_t kLowRateStableUS = 20ULL * 1000ULL * 1000ULL;
static constexpr uint32_t kLowRateTriggerKbps = 24000U;
static constexpr uint32_t kRateRecoveredKbps = 36000U;
static constexpr int kRateRoamCandidateRSSIDbm = -72;
static constexpr int kRateRoamImprovementDb = 8;
static constexpr uint64_t kRateRecoveryCooldownUS = 90ULL * 1000ULL * 1000ULL;

inline bool isBroadcastBSSID(const uint8_t *bssid)
{
    if (!bssid) return false;
    for (unsigned i = 0; i < 6; ++i)
        if (bssid[i] != 0xff) return false;
    return true;
}

inline bool isValidUnicastBSSID(const uint8_t *bssid)
{
    if (!bssid || (bssid[0] & 1U)) return false;
    bool any = false;
    for (unsigned i = 0; i < 6; ++i) any |= bssid[i] != 0;
    return any;
}

inline bool isFresh(uint64_t nowUS, uint64_t seenUS)
{
    return seenUS != 0 && nowUS >= seenUS &&
           (nowUS - seenUS) <= kCandidateFreshUS;
}

/* Only evaluate an automatic/cache-wide roam after the current AP is weak
 * and the alternative is materially stronger.  Explicit BSSID requests are
 * validated separately and are not constrained by this threshold. */
inline bool isRateDegraded(uint64_t nowUS, uint64_t lowRateSinceUS,
                           int currentRSSI, uint32_t txRateKbps)
{
    return lowRateSinceUS != 0 && nowUS >= lowRateSinceUS &&
           (nowUS - lowRateSinceUS) >= kLowRateStableUS &&
           currentRSSI < 0 && currentRSSI >= -67 &&
           txRateKbps != 0 && txRateKbps <= kLowRateTriggerKbps;
}

inline bool isBetterCandidate(int currentRSSI, int candidateRSSI,
                              bool persistentRateDegradation = false)
{
    /* RSSI is represented in dBm by the RX status path. Reject missing or
     * placeholder values instead of treating 0/+ values as an ideal AP. */
    if (currentRSSI >= 0 || currentRSSI < -127 ||
        candidateRSSI >= 0 || candidateRSSI < -127)
        return false;

    /* When the firmware's live PHY rate stays <=24 Mbps for 20 s despite a
     * strong signal, allow a less severe RSSI gate for a same-ESS node. Still
     * require a real 8 dB improvement and a usable candidate to prevent
     * ping-pong between near-equal BSSIDs. */
    if (persistentRateDegradation)
        return candidateRSSI >= kRateRoamCandidateRSSIDbm &&
               candidateRSSI >= currentRSSI + kRateRoamImprovementDb;

    return currentRSSI <= kTriggerRSSIDbm &&
           candidateRSSI >= kMinimumCandidateRSSIDbm &&
           candidateRSSI >= currentRSSI + kMinimumImprovementDb;
}

inline bool cooldownElapsed(uint64_t nowUS, uint64_t lastAttemptUS)
{
    return lastAttemptUS == 0 || nowUS < lastAttemptUS ||
           (nowUS - lastAttemptUS) >= kAttemptCooldownUS;
}
} // namespace RTW88MeshRoam
