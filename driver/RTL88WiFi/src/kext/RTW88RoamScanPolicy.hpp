/* SPDX-License-Identifier: GPL-2.0 OR BSD-3-Clause
 * Small, host-testable policy helpers for bounded associated-STA scans.
 */
#pragma once

#include <stdint.h>
#include <string.h>

namespace RTW88RoamScan {

/* Do not keep an infrastructure STA off-channel for a full-band scan. */
static const uint32_t kMaxMeshChannels = 8;
/* Candidate pools are collected before applying the eight-channel scan cap. */
static const uint32_t kMaxCandidatePoolChannels = 128;
static const uint32_t kMaxCrossBandChannelsPerPass = 1;
/* The radio is single-channel. Visit one alternate channel per CoreWiFi scan
 * request, then rotate, so same-channel BSSIDs are all discovered together
 * without remaining off-channel for a multi-channel burst. */
static const uint32_t kConnectedScanChannelsPerPass = 1;
static const uint64_t kMeshBSSFreshUS = 60ULL * 1000ULL * 1000ULL;
/* A single radio should not repeatedly leave its home channel just because
 * CoreWiFi submits scan requests in a burst. */
static const uint64_t kConnectedScanMinIntervalUS = 15ULL * 1000ULL * 1000ULL;

static inline bool recentlySeen(uint64_t nowUS, uint64_t seenUS)
{
    return seenUS != 0 && nowUS >= seenUS &&
           (nowUS - seenUS) <= kMeshBSSFreshUS;
}

static inline void sortAscending(uint16_t *channels, uint32_t count)
{
    if (!channels) return;
    for (uint32_t i = 1; i < count; ++i) {
        uint16_t value = channels[i];
        uint32_t j = i;
        while (j > 0 && channels[j - 1] > value) {
            channels[j] = channels[j - 1];
            --j;
        }
        channels[j] = value;
    }
}

/* Stable partition: keep channels on the currently associated band first,
 * then sort numerically within each band. This is discovery priority only;
 * roam eligibility still independently rejects cross-band candidates. */
static inline void sortPreferHomeBand(uint16_t *channels, uint32_t count,
                                      uint16_t homeChannel)
{
    if (!channels) return;
    const bool homeIs5GHz = homeChannel > 14;
    for (uint32_t i = 1; i < count; ++i) {
        const uint16_t value = channels[i];
        const bool valueSameBand = ((value > 14) == homeIs5GHz);
        uint32_t j = i;
        while (j > 0) {
            const uint16_t prev = channels[j - 1];
            const bool prevSameBand = ((prev > 14) == homeIs5GHz);
            const bool shouldMove = (prevSameBand < valueSameBand) ||
                (prevSameBand == valueSameBand && prev > value);
            if (!shouldMove) break;
            channels[j] = prev;
            --j;
        }
        channels[j] = value;
    }
}

/* Within the home band, inspect nearby channel numbers first. This keeps a
 * channel-157 station focused on the UNII-3 neighborhood (149/153/161/165)
 * rather than walking from channel 36 upward. It is scan ordering only; the
 * regulatory enabled-channel check remains authoritative in cmdScan(). */
static inline void sortByHomeChannelDistance(uint16_t *channels, uint32_t count,
                                             uint16_t homeChannel)
{
    if (!channels) return;
    for (uint32_t i = 1; i < count; ++i) {
        const uint16_t value = channels[i];
        const uint32_t valueDistance = value > homeChannel ?
            value - homeChannel : homeChannel - value;
        uint32_t j = i;
        while (j > 0) {
            const uint16_t prev = channels[j - 1];
            const uint32_t prevDistance = prev > homeChannel ?
                prev - homeChannel : homeChannel - prev;
            if (prevDistance < valueDistance ||
                (prevDistance == valueDistance && prev < value))
                break;
            channels[j] = prev;
            --j;
        }
        channels[j] = value;
    }
}

/* Merge separately collected same-band and cross-band pools only after each
 * pool is complete. When same-band choices exist, retain one cross-band slot
 * for periodic ESS discovery; if there are no home-band choices, allow the
 * cross-band pool to use the whole budget. */
static inline uint32_t buildPrioritizedChannelList(
    uint16_t *out, uint32_t capacity,
    const uint16_t *sameBand, uint32_t sameBandCount,
    const uint16_t *crossBand, uint32_t crossBandCount,
    uint32_t maxCrossBand = kMaxCrossBandChannelsPerPass)
{
    if (!out || capacity == 0) return 0;
    uint32_t sameLimit = sameBandCount < capacity ? sameBandCount : capacity;
    uint32_t crossLimit = 0;
    if (sameBandCount == 0) {
        crossLimit = crossBandCount < capacity ? crossBandCount : capacity;
    } else if (crossBandCount && sameLimit < capacity) {
        if (sameLimit == capacity) --sameLimit;
        crossLimit = crossBandCount < maxCrossBand ?
            crossBandCount : maxCrossBand;
        const uint32_t room = capacity - sameLimit;
        if (crossLimit > room) crossLimit = room;
    } else if (sameLimit == capacity && crossBandCount && maxCrossBand > 0) {
        --sameLimit;
        crossLimit = capacity > sameLimit ? 1U : 0U;
        if (crossLimit > crossBandCount) crossLimit = crossBandCount;
    }
    uint32_t n = 0;
    for (uint32_t i = 0; sameBand && i < sameLimit; ++i)
        out[n++] = sameBand[i];
    for (uint32_t i = 0; crossBand && i < crossLimit && n < capacity; ++i)
        out[n++] = crossBand[i];
    return n;
}

/* Pending native requests must remain queued while either side believes a
 * scan is active. A controller-only active bit is reconciled only after the
 * backend remains in a stable state for several watchdog observations. */
static inline bool pendingScanMustDefer(bool controllerActive,
                                        bool backendScanning,
                                        bool backendStable)
{
    return backendScanning || (controllerActive && !backendStable);
}

static inline bool staleScanLatchCanRecover(bool controllerActive,
                                            bool backendScanning,
                                            bool backendStable,
                                            uint32_t stableObservations,
                                            uint32_t requiredObservations)
{
    return controllerActive && !backendScanning && backendStable &&
           requiredObservations != 0 &&
           stableObservations >= requiredObservations;
}

static inline bool connectedScanIntervalElapsed(uint64_t nowUS,
                                                uint64_t lastScanUS)
{
    return lastScanUS == 0 || nowUS < lastScanUS ||
           (nowUS - lastScanUS) >= kConnectedScanMinIntervalUS;
}

/* Return a rounded-up millisecond delay until the connected-scan throttle
 * expires. A zero result means the scan may proceed now (or the timestamp is
 * unset/clock moved backwards, matching connectedScanIntervalElapsed()). */
static inline uint32_t connectedScanRemainingMS(uint64_t nowUS,
                                                uint64_t lastScanUS,
                                                uint64_t minIntervalUS = kConnectedScanMinIntervalUS)
{
    if (lastScanUS == 0 || nowUS < lastScanUS) return 0;
    const uint64_t elapsedUS = nowUS - lastScanUS;
    if (elapsedUS >= minIntervalUS) return 0;
    const uint64_t remainingUS = minIntervalUS - elapsedUS;
    const uint64_t remainingMS = (remainingUS + 999ULL) / 1000ULL;
    return remainingMS > 0xffffffffULL ? 0xffffffffU : (uint32_t)remainingMS;
}

static inline uint32_t nextRoundRobinIndex(uint32_t count, uint32_t *cursor)
{
    if (count == 0 || !cursor) return 0;
    const uint32_t index = *cursor % count;
    *cursor = (index + 1U) % count;
    return index;
}

static inline uint32_t mergePendingChannels(uint16_t *pending,
                                            uint32_t pendingCount,
                                            uint32_t capacity,
                                            const uint16_t *incoming,
                                            uint32_t incomingCount)
{
    if (!pending || !incoming || capacity == 0)
        return pendingCount;
    if (pendingCount > capacity)
        pendingCount = capacity;
    for (uint32_t i = 0; i < incomingCount && pendingCount < capacity; ++i) {
        const uint16_t channel = incoming[i];
        if (channel == 0 || channel > 255)
            continue;
        bool duplicate = false;
        for (uint32_t j = 0; j < pendingCount; ++j) {
            if (pending[j] == channel) { duplicate = true; break; }
        }
        if (!duplicate)
            pending[pendingCount++] = channel;
    }
    return pendingCount;
}

static inline bool requestedContains(const uint16_t *requested,
                                     uint32_t requestedCount,
                                     uint16_t channel)
{
    if (!requested || requestedCount == 0)
        return true;
    for (uint32_t i = 0; i < requestedCount; ++i)
        if (requested[i] == channel)
            return true;
    return false;
}

/* Append a valid, non-home, unique channel while respecting the caller's cap. */
static inline bool appendUnique(uint16_t *channels, uint32_t *count,
                                uint32_t capacity, uint16_t channel,
                                uint16_t homeChannel)
{
    if (!channels || !count || channel == 0 || channel == homeChannel ||
        *count >= capacity)
        return false;
    for (uint32_t i = 0; i < *count; ++i)
        if (channels[i] == channel)
            return false;
    channels[(*count)++] = channel;
    return true;
}

} // namespace RTW88RoamScan
