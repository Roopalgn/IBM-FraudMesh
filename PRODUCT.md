# FraudMesh

<!-- impeccable:product-schema 1 -->

## Platform

web

## Product purpose and constraints

FraudMesh is a synthetic cross-institution fraud-investigation prototype for the
IBM Z Datathon 2026. Investigators compare a selected institution's relationship
contributions with the combined permitted graph, inspect structural findings and
their supporting signals, and export evidence for review.

The audience is investigators and technical judges. The key demonstration is a
cross-bank structure that is incomplete in an institution's contribution. Local
positive and normal controls must also remain accessible. Structural candidates
are decision support, not fraud verdicts. ML-informed review priority is an
uncalibrated policy output, not a probability.

## Submission priority

The user identifies the three-minute demo video as the primary submission
deliverable and wants a competitive, judge-impressing result. Optimize the demo
experience for immediate comprehension, a memorable cross-bank reveal, and
credible working evidence within 180 seconds. A polished dashboard is supporting
material, not the success criterion by itself. This records the user's priority,
not a verified competition scoring weight or a guarantee of winning.

The opening must hook judges before a feature tour. Show why isolated institutions
miss the complete structure, reveal the same synthetic scenario collaboratively,
then demonstrate evidence, ML-informed prioritization and the sharing boundary.
Explain IBM LinuxONE's concrete role and show execution evidence if verified;
server setup alone is not proof that this workflow ran there. Preserve honest
synthetic-data, privacy, model and deployment limits without turning the narration
into a disclaimer recital. See docs/demo/three-minute-submission-brief.md.

The existing vanilla HTML, CSS, JavaScript and SVG frontend integrates the real
FastAPI scenario/analyze flow. Preserve its schemas, HMAC process, ML inference,
graph rules, export projection, explicit fixture provenance, and failure behavior.
There are four computed synthetic scenarios and explicitly selected saved or
authored alternatives. No silent fallback or invented live activity is allowed.

The deployment target is LinuxONE Ubuntu 24.04, s390x, Python 3.12. This preview
is executed on local Windows; LinuxONE execution and confidential execution are
unverified by this interface. The local hash-linked journal is not immutable.
Pseudonyms remain linkable; local visibility is not authentication.

Success means a legible, distinctive investigation canvas, a purposeful reveal
that connects actual signals, working evidence/privacy/audit views, keyboard
access and reduced-motion behavior, and responsive desktop/tablet/mobile use.
The user requests a premium midnight navy/mint IBM-inspired character with bank
colors blue, purple and amber. No IBM endorsement is implied.

Explicit visual priority: the final frontend should strongly impress judges in
the three-minute recording through visible glow, fluid animation and polished
transitions. This is an affirmative request for a more expressive motion/light
treatment, superseding earlier assumptions that restrained effects alone suffice.
Preserve readable evidence and real behavior while pursuing that visual ambition.

The user has authorized finalizing and pushing the frontend to frontend_finalized.
Do not merge to main as part of this task.
