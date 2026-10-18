---
name: FraudMesh
description: Luminous midnight navy canvas for cross-institution evidence
colors:
  midnight-navy: "#080E18"
  canvas-surface: "#0D1725"
  canvas-border: "#223246"
  canvas-muted: "#91A8BC"
  text: "#F3F7FB"
  mint: "#4BE0C1"
  action-mint: "#6EE9CD"
  bank-a: "#60A5FA"
  bank-b: "#A78BFA"
  bank-c: "#F3B86B"
  alert: "#FF7185"
  action-ink: "#06231D"
  surface-2: "#142135"
  field: "#101C2D"
  field-border: "#31435B"
typography:
  headline:
    fontFamily: "IBM Plex Sans, Segoe UI, Arial, sans-serif"
    fontSize: "39px"
    fontWeight: 500
    lineHeight: 1.06
    letterSpacing: "-0.035em"
  title:
    fontFamily: "IBM Plex Sans, Segoe UI, Arial, sans-serif"
    fontSize: "14px"
    fontWeight: 550
  body:
    fontFamily: "IBM Plex Sans, Segoe UI, Arial, sans-serif"
    fontSize: "14px"
    lineHeight: 1.5
  label:
    fontFamily: "IBM Plex Sans, Segoe UI, Arial, sans-serif"
    fontSize: "11px"
    fontWeight: 600
  metric:
    fontFamily: "IBM Plex Sans, Segoe UI, Arial, sans-serif"
    fontSize: "34px"
    fontWeight: 350
    lineHeight: 1.2
  code:
    fontFamily: "IBM Plex Mono, Consolas, monospace"
    fontSize: "11px"
rounded:
  canvas-token: "2px"
  badge: "3px"
  control: "4px"
  field: "6px"
  rail: "8px"
  workspace: "12px"
spacing:
  compact: "8px"
  control: "10px"
  detail: "12px"
  section: "20px"
  desktop-gutter: "30px"
components:
  button-primary:
    backgroundColor: "{colors.action-mint}"
    textColor: "{colors.action-ink}"
    rounded: "{rounded.control}"
    padding: "10px 16px"
    height: "38px"
  button-subtle:
    backgroundColor: "#132133"
    textColor: "#CFDBE8"
    rounded: "{rounded.control}"
    padding: "10px 15px"
  input:
    backgroundColor: "{colors.field}"
    textColor: "{colors.text}"
    rounded: "{rounded.field}"
    padding: "9px 12px"
  badge-review:
    backgroundColor: "#331D2C"
    textColor: "#FF99A7"
    rounded: "{rounded.badge}"
  institution-card:
    backgroundColor: "#0E1928"
    rounded: "{rounded.control}"
    padding: "19px"
---

# Design System: FraudMesh

## Overview

**Creative North Star: "Midnight navy analytical canvas"**

A midnight navy analytical canvas uses precise rules, luminous entities and bank-coded paths to make permitted relationships inspectable. Mint marks the principal action and investigation emphasis; institution colors retain their attribution meaning. The original mesh logo and vanilla HTML, CSS, JavaScript and SVG construction remain the visual foundation.

The interface is compact, expressive and evidence-led. A bright two-line headline, glowing selected paths and coordinated graph/inspector motion give the investigation a memorable reveal while fine strokes and adjoining surfaces keep dense evidence readable. This records the implemented cascade in frontend/styles.css, frontend/public/canvas.css and frontend/public/motion.css, with presentation behavior in frontend/src/motion.js and frontend/src/app.js. Source descriptions are not runtime performance certification; measured profiling belongs in verification documentation.

**Key Characteristics:**

- Midnight navy surfaces with mint investigation emphasis and stable institution colors.
- Luminous evidence paths, radial node auras and a connected graph/inspector frame.
- Deliberate entity continuity, coordinated reveal and user-controlled ambient motion.

## Colors

The palette is cool, dark and semantic: luminous mint emphasis sits beside three stable institution colors. Sidecar tonal strips are synthesized OKLCH previews for inspection; they are not additional shipped palette tokens.

### Primary

- **Mint:** investigation emphasis, focus outlines, shared-entity marks and the basis of luminous falloff.
- **Action Mint:** the brighter primary-button fill used by the final motion stylesheet.

### Secondary

- **Bank A Blue / Bank B Purple / Bank C Amber:** institution contributions in graph paths, node auras, legends, markers and the original logo.

### Tertiary

- **Alert Rose:** error feedback; Review badges use a related pale rose on a dark rose surface. Review means investigation, not a verdict.

### Neutral

- **Midnight Navy:** page foundation beneath ambient light.
- **Canvas Surface / Canvas Border / Canvas Muted:** inherited surface, rule and secondary-text tokens.
- **Text:** high-contrast primary reading color.
- **Surface 2 / Field / Field Border:** control hover and input separation.
- **Action Ink:** text on the bright primary action.

**The Attribution Rule.** Use blue, purple and amber for institution attribution; shared entities and investigation emphasis use mint. Preserve text labels alongside color.

The frontmatter retains the reused canvas tokens. Final components also use local navy/teal surface fills and lighter mint highlights rather than forcing every surface into one fill. These source overrides describe the same approved visual world; their presence does not authorize unrelated palette replacement.

## Typography

**Body and interface font:** IBM Plex Sans, then Segoe UI, Arial and sans-serif. Light, Regular, Medium and SemiBold WOFF2 faces (300, 400, 500 and 600) are bundled locally with the OFL license in frontend/public/fonts. **Code and entity font:** the declared IBM Plex Mono, Consolas and monospace stack; Plex Mono is not bundled. Font synthesis is disabled.

The headline reads “Follow the money. Reveal the network.” with its second line in luminous mint. The default headline is Medium (39px, weight 500, line-height 1.06, tracking -0.035em), rising to 44px at wide screens, becoming 35px at compact widths, 32px at the stacking breakpoint and 35px on mobile. Metrics use light tabular numerals (34px, requested weight 350, line-height 1.2); the browser matches requested intermediate weights to the locally available static faces. Panel titles are compact (14px, requested weight 550), and the inspector title uses Medium (20px, rising to 22px on mobile). The body baseline is 14px with line-height 1.5; dense investigation prose uses 11–12px. Supporting labels vary by role rather than following a geometric scale.

SVG entity labels scale within their viewBox. Mobile uses 23-unit entity numerals and 22-unit external labels, with contributor information in the HTML legend and selection details. Do not reuse the smallest incidental captions as general-purpose text sizes.

## Layout

The desktop shell has a fixed icon rail (76px), a top bar (68px), and a fluid main region capped at 1900px with horizontal gutters (30px). The relationship atlas and inspector share one outlined frame. The default inspector is 310px wide, with independently scrolling content and a maximum panel height (650px). Graph height follows `clamp(300px, calc(100dvh - 480px), 510px)`.

At widths up to 1279px, gutters reduce to 24px and the inspector to 280px. At widths up to 1000px, the inspector stacks beneath the graph, loses its height cap and the graph becomes 410px high. At widths up to 620px, the rail becomes fixed bottom navigation (63px), main gutters become 16px, graph height becomes 320px, and institution cards stack. Bottom padding (76px) reserves navigation space. At 1600px and above, gutters become 40px and the inspector becomes 340px; the final graph clamp still applies.

Metrics form a compact two-column group beside the headline (400px wide by default, 440px wide, 350px compact and 285px at the stacking breakpoint), then become a full-width four-column strip on mobile. Recurring small gaps and padding include 8px, 10px, 12px and 20px; these are extracted steps rather than an enforced global spacing scale. Evidence tables retain a minimum width (610px) inside their own scroll container.

## Elevation & Depth

Tonal layering, fine borders and purposeful light carry hierarchy together. The joined investigation frame has no broad drop shadow; its navy/teal panels sit behind radial node auras and blurred bloom on actual highlighted evidence paths. Selected nodes brighten their cores and orbit strokes. A dotted field, radial ambient washes and slow dashed orbits establish depth without generating additional data. The inspector uses a static diagonal surface gradient with luminous mint accents around the priority meter and selected evidence.

The primary action has a mint outer glow and inset highlight, with a brighter glow and slight lift on hover. Selected tabs, segmented controls and rail items echo that language at smaller scale. The toast retains a diffuse dark shadow. No full-panel animated blur or animated inset shadow is used; the scene's ambient light animates opacity and a small translation, and its orbit animates dash offset.

**The Evidence Light Rule.** Give the selected case and its actual relationships the strongest light; keep labels, controls and provenance readable through the effect.

## Shapes

Controls and institution cards use tight corners (4px), badges use 3px, fields and priority cards use 6px, rail buttons use 8px and the enclosing investigation frame uses 12px. Adjoining panels remain square within that frame. Circular graph entities, orbit strokes, numbered evidence markers and legend dots distinguish relationships from rectangular controls. Keep the original mesh-logo paths, circles and bank-color mapping rather than substituting a new symbol.

## Components

### Buttons and fields

The principal action uses Action Mint with dark Action Ink, compact padding (10px 16px) and minimum height (38px). Its glow, border highlight, hover sheen and small upward hover movement make the reveal action visually prominent. Pressed buttons compress slightly. The secondary action uses a dark blue fill and fine border, with a subtle mint glow on hover. Routine control transitions use 180ms. The global focus treatment is a mint outline (2px) with offset (4px). Disabled buttons reduce opacity to 0.4. Inputs use a dark fill, a fine border and the same focus treatment; the scenario picker instead uses a transparent fill and bottom rule.

### Navigation and status

Tabs use a glowing mint underline and brighter selected text. Active rail items and selected visibility controls use tinted fields, inset rules and a subtle outer glow. Mobile navigation exposes labels beneath icons. Institution legend controls underline the focused institution and retain textual bank names. Neutral source badges and rose Review badges encode provenance or review state. The graph scene-state text explicitly distinguishes the active visibility scope.

### Relationship atlas and inspector

Graph entities and paths are keyboard-selectable SVG elements with accessible names; selection details also appear in HTML. Multiple institution contributors produce a mint entity, while single-contributor entities keep their bank color. Node auras and path bloom follow these actual identities and relationships. On small screens, contributor tags are removed from the SVG and readable HTML legend and selected-entity text carry attribution. The inspector contains supporting links, explicit uncalibrated review priority, evidence actions and provenance details.

**The Evidence Motion Rule.** Animate actual scope and selection changes with continuity. Motion explains entity positions and relationship evidence; it does not imply a transaction stream or measured detection speed.

The reveal captures existing entity coordinates before rendering, then moves matched entities from their previous position (780ms, `cubic-bezier(.16,1,.3,1)`). Newly entering entities assemble; actual relationship paths trace over 780ms, with a brief travelling highlight and evidence bloom. Case changes, institution focus and scope changes also capture prior coordinates before rendering. The inspector settles through transform and opacity (420ms, with a 100ms delay during reveal); entity/relationship selection updates use the same panel treatment. The default animation duration is 260ms for view/camera movement, while view changes currently use the 420ms panel helper. The reveal class clears after 920ms. Slow ambient washes (9s, 12s on mobile) and an orbit dash (24s) sustain the scene between user actions.

**The Motion Access Rule.** Keep the same selected evidence and explicit status feedback when motion is disabled. The Motion on/off control disables animation and transitions; an OS reduced-motion preference forces that state and disables the toggle. Hidden pages pause CSS animation and cancel tracked presentation animations; offscreen graph scenes and non-network views pause ambient animation.

**The Source Rule.** Keep provenance, scope and interpretation text visible in the investigation flow. Visual priority must not turn a structural candidate into a fraud verdict or an uncalibrated score into a probability.

## Do's and Don'ts

### Do:

- **Do** preserve the original mesh SVG and institution color mapping.
- **Do** use luminous selected evidence, node auras and coordinated reveal motion within the midnight navy/mint world.
- **Do** retain keyboard focus, textual contributor details and reduced-motion final-state feedback.
- **Do** keep the graph and case inspector visually connected, with evidence details reachable from both.
- **Do** pause ambient animation when the scene is offscreen, another view is active or the page is hidden.

### Don't:

- **Don't** fabricate live activity or let effects obscure evidence.
- **Don't** imply IBM endorsement, verified LinuxONE execution or a production privacy guarantee.
- **Don't** propagate incidental eyebrow labels as reusable type roles.
- **Don't** treat source-level animation choices as measured runtime performance or inference latency.

Not canonized: incidental small captions and legacy unused scene-label/eyebrow rules are not reusable typography roles. The intermediate static-font weight requests are documented as matching behavior, not a promise of variable-font interpolation. Verification in this document is source inspection and sidecar structure checking; capture and runtime profiling results belong in verification documentation. Presentation changes do not alter backend behavior.