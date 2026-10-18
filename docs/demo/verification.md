# Local frontend review - 18 October 2026

Release review update: the replay comparison now counts only alerts supported by
the current step; reset/partial steps and actual API local/cross-bank distinctions
have regression coverage (41 frontend tests). LinuxONE wording/narration references
the recorded backend 3058fb8 run rather than calling it only a target. Evidence is
transcribed from user-supplied logs/screenshots in
frontend/public/linuxone-run-evidence.json, not independently retrieved or attested.
The revised UI still needs a VM smoke check. The notes below preserve the earlier
component review, including its then-unverified platform statements and word counts.

Base: integrated main at 3058fb8. Delivery branch: frontend_finalized. The user
has authorized finalization and push; main is not merged by this task. Backend,
API schemas, model, HMAC, graph rules and journal implementation are unchanged.

## Final luminous frontend

- Title: Follow the money. Reveal the network.
- Actual evidence paths use bank-colored light/bloom; entities have luminous
  selection and hover treatment. Background light/orbits are decorative only.
- Local/combined reveal, bank focus and case changes preserve previous entity
  positions. Reveal 780ms; inspector/views 420ms; zoom 260ms; controls 180ms.
- Motion toggle and OS reduced-motion preferences supported. Ambient effects
  pause when hidden/offscreen. Browser verified motion-off state and offscreen
  pause. No fabricated live traffic or latency claim.
- Official IBM Plex Sans WOFF2 files served locally with SIL OFL license. Service
  logs show successful requests for Light, Regular, Medium and SemiBold.
- Optimized repaint cost by removing full-panel blur and animated inset shadow.
  Repeated local browser sample: 161 frame intervals, median 6.1ms, p95 12.1ms,
  maximum 18.3ms. This is one local Windows/IAB sample, not a universal frame-rate
  guarantee, detector latency, or a LinuxONE measurement.
- 39 frontend tests pass after final UI changes. 71 Python tests pass. JS syntax
  checks and Git whitespace checks pass. No application dependency was added.
- All four API scenarios returned expected actual findings/cases/recommendations:
  common 2/1/1; ring 1/1/1; normal 0/0/0; local control 1/0/1. Journal verification
  returned local chain consistent. Browser error/warning log was empty.
- Final viewport captures are .impeccable/review/desktop.jpg, mobile.jpg and
  mobile-bottom.jpg (ignored), with a first-frame deliverable in
  output/frontend-preview/final-desktop.jpg. Mobile usable client width 377px,
  document scroll width 377px, export right 363.7px, content right 360.7px; no
  horizontal overflow. The window width includes its reserved scrollbar.
- Independent Impeccable finish reviewer scored all four material fixes resolved;
  disposition ship applies to those scored fixes, not a certification of the
  entire application. Static captures do not prove a finished cinematic film.
- Narration, shot list and captions are 180-second rehearsal drafts. Narration
  is 356 words, approximately 153 seconds at 140 words/minute before pauses;
  aim for 2:45-3:00. read-aloud.txt contains only the exact spoken paragraphs.
  No narration audio or finished video was recorded.

The notes below preserve earlier review evidence and should be read in that
historical context. Current entry: http://127.0.0.1:8018/?scenario=ring&scope=local.

## Canvas 02 revision

The user's first-pass feedback requested a stronger visual composition and
purposeful animation. The revised canvas moves counters into the compact heading,
puts the graph and case inspector first, and uses bank-coded SVG relationships.
The added public/canvas.css is served through the existing public mount; no
backend route was added. The preview launcher now uses a distinct loopback port:
http://127.0.0.1:8018/?preview=canvas-02, labeled Canvas / 02 in the header.

User-triggered local/combined transitions trace actual SVG paths and move existing
entities from their previous coordinates over 680 ms. Reduced motion removes
spatial animation while preserving scope/status text. There is no fabricated
stream, continuous decorative loop, or page-load choreography. Reveal explicitly
selects a cross-bank candidate when available, so a previously selected local
finding does not hide the combined result.

Impeccable 4.3.1 guidance was applied (Operate, motion, craft floor). The context
launcher could not initialize its engine cache; no engine detector or automated
Impeccable score is claimed. A separate finish reviewer inspected desktop/mobile
captures and frontend sources. Product and surface context are recorded locally.

The independent review identified mobile annotation legibility, a central-label
collision, and a redundant dialog eyebrow. All three scored fixes were resolved;
the final verdict was `ship` for those fixes, not a certification of the entire
application. Final full-page captures at CSS 1440x900 and 390x844 are kept under
ignored .impeccable/review/. Mobile contributor details use a readable HTML legend
and selection feedback; tiny overlapping SVG tags are omitted at that breakpoint.

Re-ran all 37 frontend tests after the revision; all passed. JS syntax and Git
whitespace checks passed. Actual browser checks exercised common/ring/normal/local
API scenarios, local-to-combined reveal, evidence filtering, and the real journal
verification endpoint. Backend/model/HMAC/graph implementations remain unchanged.
The earlier Python/ML/runtime verification below belongs to the initial frontend
pass, not a fresh LinuxONE run.

## Implemented

- Midnight/mint tokens, readable typography, responsive sidebar/bottom navigation,
  original inline SVG brand, standalone dark/monochrome marks and cohesive icons.
- Four live scenario choices, explicit saved alternatives, loading and failure
  feedback, scope-aware counts and preserved export/provenance flow.
- Local/combined reveal (680 ms, reduced-motion aware), clickable contributor
  legend, pan/zoom/reset, deterministic positions, keyboard nodes/relationships.
- Case brief with contributing institutions, actual triage value, reason codes,
  supporting evidence and selected signal/entity details.
- Searchable/contributor-filtered evidence table with graph-linked selection.
- Preserved retention/sharing disclosures and new computed GET /audit/status
  verification, clearly distinct from the visual evidence trail.
- Local preview launcher and 150-second voiceover, shot list, storyboard,
  recording instructions and subtitle draft.

## Executed automated verification

Python 3.12.2, isolated .venv on Windows AMD64. Existing pinned project
requirements installed in that environment. No new application dependency.

| Command | Actual result |
|---|---|
| python -B -m unittest discover -s tests -v | 71 passed |
| python -B scripts/train_ml_baseline.py | Model reproduced; 832 test records, precision 0.497041, recall 0.700000, F1 0.581315 |
| python -B scripts/verify_runtime.py | Passed; report records this Windows host, all four scenario checks |
| node --test frontend/tests/*.test.mjs | 37 passed (30 existing + 7 presentation regressions) |
| node --check frontend/src/app.js | Passed |
| git diff --check | Passed |

API test processes initially stalled under the socket-restricted sandbox; the
same tests passed outside it. FastAPI TestClient emits an upstream Starlette
httpx deprecation warning, not a test failure. No assertions were weakened.

## Browser checks on the actual loopback service

- Common: two combined findings, one cross-bank case, one recommended review.
- Ring: local Bank B has zero complete findings; reveal shows one cross-bank
  cycle and one recommended review.
- Normal: zero findings, cases and recommendations.
- Local positive control: one local cycle, zero cross-bank cases.
- Evidence search for lt_1k, relationship selection and selected-signal details.
- Live journal returned Local chain consistent; refresh uses the real endpoint.
- Invalid API endpoint explicitly reported failure and retained the previous API
  snapshot/source badge; no saved fixture was silently substituted.
- JSON export triggered the download and success feedback; projection behavior
  is covered by existing model/adapter tests.
- Navigation, mobile graph framing, local selector and reveal checked visually.

No page-wide horizontal overflow at measured CSS sizes 1440x900, 1280x720,
390x844 and the tablet boundary (767/769x1024). The user's browser is zoomed
110%; integer viewport overrides bracket 768 rather than produce it exactly.
Screenshot files before.jpg, desktop-1280.jpg, desktop-1440-graph.jpg,
tablet-near-768.jpg, mobile-390-top.jpg, mobile-390-graph.jpg and audit-desktop.jpg
are saved under ignored output/frontend-preview/. The evidence table intentionally
scrolls internally. The mobile graph has a separate framing and larger labels.

## Recording and limits

No video or narration audio was recorded: available browser tooling exposes
screenshots, not recording. The executable 150-second recording package and SRT
draft are supplied. Current evidence is local Windows execution, not LinuxONE
s390x deployment or acceleration. No confidential execution, external audit
attestation, production authentication or real-world fraud effectiveness is
claimed. Current Canvas 02 preview: http://127.0.0.1:8018/?preview=canvas-02.
