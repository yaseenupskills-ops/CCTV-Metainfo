# CCTV Forensic Analyzer — Forensic Methodology

## 1. Purpose

This document explains the forensic principles and analysis methods used by the system. It defines what the system can and cannot claim, and provides guidance for investigators interpreting results.

## 2. Core Principle: Automated Analysis Is an Aid, Not Proof

Automated analysis produces **potential indicators**. Only a trained investigator, with knowledge of the case, the recording device, and the context, can reach conclusions.

**The system must never state:**
- "This video is definitely manipulated."
- "This video is fake."
- "This video has a X% probability of being tampered with."

**The system may state:**
- "Potential indicators of modification were detected."
- "An anomaly indicator score of 65/100 was calculated from the following factors..."
- "Integrity mismatch: the current hash does not match the recorded hash."

## 3. Terminology Standard

| Term | Meaning |
|------|---------|
| Potential anomaly | A detected deviation that may or may not indicate manipulation |
| Possible modification indicator | An observation consistent with modification but not proof of it |
| Suspicious transition | A frame difference / discontinuity of interest |
| Integrity mismatch | A cryptographic hash does not match a previously recorded value |
| Possible re-encoding | Encoding parameters inconsistent with original container metadata |
| Metadata inconsistency | Metadata fields that conflict with each other or with observed content |

## 4. Evidence Integrity Methodology

### Hashing
- SHA-256 is the primary integrity algorithm; SHA-512 is recorded as secondary.
- MD5 is NOT used for integrity claims (collision weakness). It may be reported for legacy comparison only, clearly labeled.
- Hash is always computed from the actual stored original bytes, in streaming fashion (1 MB chunks).
- Integrity is a property of the file copy, NOT proof of content truthfulness. A video can be perfectly hashed yet contain manipulated content.

### Storage
- Original uploaded file: written once, read-only.
- All processing uses working copies.
- The system records file size and upload timestamp at ingestion.

## 5. Metadata Analysis

Metadata is the easiest thing to forge and the least reliable evidence. It is collected because it is often useful, never because it is definitive.

Uses:
- Container format and codec consistency checks.
- Creation-time / encoder tag reporting.
- Cross-field consistency (e.g., claimed duration vs. frame count vs. fps).

Limitations:
- Metadata can be stripped or rewritten trivially.
- Absence of metadata is not evidence of tampering.
- Metadata from CCTV/NVR systems varies wildly across manufacturers.

## 6. Video Structure Analysis

Analyzes container and stream structure via FFprobe:

- Duration, frame count, fps, bitrate.
- Video/audio codecs, pixel format, stream count.
- Keyframe positions and GOP structure (when available).
- Encoder and encoding parameters.
- Packet timestamps (PTS/DTS) when cheap to obtain.

Interpretation:
- Repeated GOP irregularities may indicate frame removal or insertion.
- A drop in frame count relative to duration may indicate dropped frames.
- Changes are indicators only; NVR recording can produce irregular structures legitimately.

## 7. Frame Analysis

### Sampling
- Configurable sampling: 1, 2, or 5 frames per second.
- For each sampled frame: frame number, timestamp, perceptual hash, image statistics (mean, std), luma histogram.
- Frames are NOT bulk-stored as images. Image files are stored only for anomaly events (evidence frames).

### Scene / Frame Change Detection
Deterministic methods:

1. **Mean Absolute Difference (MAD)** — pixel-level difference between consecutive frames.
2. **Histogram difference** — distribution shift between frames; robust to small motion.
3. **Structural similarity (SSIM)** — perceptual similarity (used when enabled).
4. **Perceptual hash distance** — compact image signature comparison.

A configurable threshold marks a frame pair as a significant difference.

**CRITICAL:** A frame difference is NOT automatically tampering. Legitimate scene cuts, lighting changes, camera movement, and compression artifacts produce large differences. The UI always labels these "Potential anomaly."

### Interpreting Difference Events
- Isolated large differences at scene boundaries → expected, low weight.
- Dense clusters of differences at unusual positions (e.g., mid-scene) → higher weight (possible frame insertion/removal).
- Repeated near-black transitions → could indicate recording gaps.
- Each event records: timestamp, previous frame, current frame, difference score, detection method, severity.

## 8. Video Comparison (Original vs Suspected)

Compares metadata and integrity between two files:

- File size, duration, resolution, fps, codec, bitrate, frame count.
- Metadata fields and available timestamps.
- Hash equality.

Status per field: MATCH / DIFFERENCE / NOT_AVAILABLE.

Interpretation:
- Identical hashes → identical byte sequences (same file). This does not prove content truth.
- Different hashes but identical metadata → possibly re-encoded or container rewritten.
- Duration differs → possible trimming/insertion — or simply different recordings.
- Frame-level comparison is future work.

## 9. Anomaly Indicator Scoring

The score is an **explainable composite**, not a probability.

| Factor | Weight |
|--------|--------|
| Metadata inconsistency | +15 |
| Duration difference (in comparison) | +20 |
| Frame discontinuity | +25 |
| Encoding difference (in comparison) | +15 |
| Unnatural frame-difference cluster | +15 |
| Isolated scene changes (natural) | +5 max |

Categories:

| Score | Label |
|-------|-------|
| 0–20 | Low indicators |
| 21–50 | Moderate indicators |
| 51–75 | High indicators |
| 76–100 | Very high indicators |

Every score stores its contributing factors, so the UI can show exactly why the number is what it is. The label "Anomaly Indicator Score" is used — never "Probability of Tampering."

## 10. Reporting Standards

Reports separate three layers:

1. **OBSERVED FACTS** — raw measurements: hashes, file size, duration, frame counts, metadata values, difference scores. These are objective outputs of tools.
2. **AUTOMATED INTERPRETATIONS** — the system's indicator labels: "possible re-encoding," "potential anomaly," category labels. Clearly machine-generated.
3. **INVESTIGATOR CONCLUSIONS** — the human analyst's conclusions. The report has a dedicated space for these, and the system never fabricates them.

A disclaimer is always included stating the limitations of automated analysis.

## 11. Chain of Custody

The system records an audit trail of who did what, when, and on which evidence. Chain of custody is a procedural matter as much as a technical one; the system supports it by:

- Logging every action with user, timestamp, entity, and request context.
- Making audit logs append-only.
- Recording hash values over time so that any divergence is detectable.

## 12. Known Limitations (Honest Disclosure)

- The system cannot determine the authenticity of video content by itself.
- Frame differences, metadata, and structure analysis all have legitimate explanations.
- Re-encoding is common (social media, format conversion) and not necessarily malicious.
- Timestamp differences can be caused by timezone, clock drift, or NVR configuration.
- No automated system can rule out skilled manipulation.
- Expert interpretation is always required.
- Frame-level (per-frame pixel) comparison between original and suspected videos is not yet implemented; comparison is limited to hashes and technical metadata.
- The statistical tampering model is explicitly out of scope until validated against a labelled corpus.
- The anomaly indicator score is a weighted, explainable heuristic — it is not a calibrated probability and must never be presented as such.
- Frame sampling is fixed to 1/2/5 fps; very brief (sub-second) events may fall between samples.
- Exif/container-timestamp cross-checks against NVR systems are not automated.

## 13. References and Further Reading

- ENFSI guidelines on digital evidence handling.
- ISO/IEC 27037 (identification, collection, acquisition, preservation of digital evidence).
- NIST guidelines on digital evidence and media forensics (NIST SP 800-86).
- SIFT work on video integrity (e.g., frame removal detection literature).
