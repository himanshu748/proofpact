---
name: ProofPact
description: Warm editorial precision for agreements and inspectable proof.
colors:
  lp-paper: "#f6f4ed"
  lp-white: "#fffefa"
  lp-ink: "#252b24"
  lp-muted: "#6d7468"
  lp-line: "#dedfd3"
  lp-olive: "#6d7b4f"
  lp-pale: "#e8ecde"
  lp-violet: "#65609a"
  lp-teal: "#3e7666"
  canvas: "#f6f4ef"
  surface: "#ffffff"
  ink: "#191c23"
  line: "#e7e5df"
  strong-line: "#d6d5cf"
  client: "#4d4bc4"
  client-soft: "#eeeeff"
  builder: "#08705f"
  builder-soft: "#e8f7f3"
  success: "#147a55"
  success-soft: "#e8f7f0"
  danger: "#b42f3a"
  danger-soft: "#fdecee"
  amber: "#8a4f0a"
  amber-soft: "#fff3df"
  blue: "#2358c5"
typography:
  display:
    fontFamily: "Instrument Serif, Georgia, serif"
    fontSize: "clamp(62px, 6.8vw, 91px)"
    fontWeight: 400
    lineHeight: 1.015
    letterSpacing: "-0.035em"
  headline:
    fontFamily: "Instrument Serif, Georgia, serif"
    fontSize: "51px"
    fontWeight: 400
    lineHeight: 1.12
    letterSpacing: "-0.03em"
  title:
    fontFamily: "Geist Variable, sans-serif"
    fontSize: "22px"
    fontWeight: 540
    letterSpacing: "-0.7px"
  body:
    fontFamily: "Geist Variable, -apple-system, BlinkMacSystemFont, Segoe UI, sans-serif"
    fontSize: "14px"
    fontWeight: 420
    lineHeight: 1.55
  label:
    fontFamily: "Geist Variable, sans-serif"
    fontSize: "11px"
    fontWeight: 500
rounded:
  chip: "3px"
  control: "6px"
  document: "8px"
  panel: "9px"
spacing:
  compact: "8px"
  small: "12px"
  regular: "16px"
  roomy: "24px"
  panel: "28px"
  section-gap: "48px"
components:
  button-primary:
    backgroundColor: "{colors.lp-ink}"
    textColor: "{colors.lp-white}"
    rounded: "{rounded.control}"
    padding: "15px 20px"
  document:
    backgroundColor: "{colors.lp-white}"
    textColor: "{colors.lp-ink}"
    rounded: "{rounded.document}"
    padding: "22px 28px 0"
  input:
    textColor: "{colors.ink}"
    rounded: "{rounded.control}"
    padding: "10px 12px"
---

# Design System: ProofPact

## Overview

**Creative North Star: "Warm editorial precision"**

Warm editorial precision gives agreements the presence of a well-kept paper record. Instrument Serif supplies the human voice; Geist keeps prices, criteria, controls, and evidence easy to scan. Quiet olive accents sit alongside distinct violet client and teal builder identities.

Surfaces use fine rules, restrained corners, and occasional ambient shadows. Spacious public storytelling and denser workspace tools share the same typographic pairing and semantic roles. Interaction reveals explicit state changes and keeps human authority visible.

**Key Characteristics:**

- Warm paper and dark ink.
- Expressive serif headlines with precise sans-serif records.
- Violet client and teal builder identities.
- Evidence and state labels remain readable beside interactive controls.

## Colors

### Primary

Paper, warm white, and dark olive ink establish the landing page. Olive emphasizes editorial italics, selected controls, and focus; pale olive supports quiet information surfaces.

### Secondary

Violet denotes the client; teal denotes the builder. Landing role tokens are deliberately softer than their workspace counterparts. Preserve the contextual palette rather than substituting one set globally.

### Neutral

Landing paper, white, muted text, and fine dividing lines live under the `lp-` namespace. Workspace canvas, surface, ink, and line tokens live on the document root. Status colors in the workspace distinguish success, danger, and pending attention; blue supplies the general focus outline.

**The Role Continuity Rule.** Client and builder colors retain their meaning across surfaces; status must also be named in text.

## Typography

**Display Font:** Instrument Serif, with Georgia and serif fallbacks. Upright and italic faces are locally packaged.

**Body Font:** Geist Variable, with system sans-serif fallbacks. Default text uses the body token; compact labels use the label token.

**Label/Mono Font:** Receipt identifiers use `ui-monospace, SFMono-Regular, monospace`.

Display and headline tokens carry editorial statements; document titles use the sans-serif title token. Hero copy is slightly larger (15px, line-height 1.9) with a restrained measure (390px). Prices use tabular numerals. Metadata is compact, usually 11px, with explicit darker local colors where needed on tinted surfaces.

**The Record Clarity Rule.** Use serif for editorial hierarchy and sans-serif for controls, criteria, amounts, and state information.

## Layout

The landing shell caps navigation and hero at 1320px; supporting sections cap near 1220px. The desktop hero uses two near-equal columns (`1fr 1.04fr`) with a 55px gap and broad outer gutters. The paired private views flank a narrower connector. Spacing values in frontmatter are observed recurring intervals, not a replacement for each component's fitted spacing.

Landing breakpoints are 1199px, 959px, and 699px maximum widths, plus a 1600px minimum-width expansion. Tablet progressively reduces gutters, type, and gaps. Below 700px, the hero becomes one column with 24px side padding, a fluid display (59–83px), and simplified navigation retaining the workspace action. Desktop public sections have generous vertical spacing; mobile compresses it while retaining clear section boundaries. Workspace responsive rules separately use 1279px, 1023px, and 767px.

## Elevation & Depth

Fine borders and tonal paper layers supply most depth. The agreement has a faint ambient shadow (`0 16px 42px #2a391a07`) and a slightly rotated backing sheet. Notes use a small shadow (`0 7px 18px #26321b0c`). Primary-button hover adds a restrained lift (`0 5px 15px #303d251a`). This is a paper metaphor, not a general floating-panel treatment.

**The Uncovered Record Rule.** Informational notes occupy layout space and must not cover exclusions, criteria, or approval details.

## Shapes

Controls use gently curved corners; document and larger panel radii are slightly larger. Fine one-pixel borders define records and dividers. Compact rectangular chips carry statuses. Circles are reserved for initials, step controls, and receipt seals. A small diamond mark appears in document context labels.

## Components

### Buttons

Primary actions use dark landing ink on warm white text, the control radius, and fitted inline icon gaps. Hover darkens toward olive (`#414c36`) over 200ms. Secondary navigation actions use an outlined light surface; tertiary actions are underlined text. Landing focus is a visible olive outline (2px, offset 5px); workspace focus uses blue (3px, offset 3px).

### Chips

Compact state labels use a small radius and semantic tint. Pending is warm neutral, verified is pale green, and failure is warm rust. Words and adjacent icons communicate meaning alongside color.

### Cards / Containers

Agreement records use warm white, a fine border, quiet top accent, and ruled sections. Role panels use violet or green-tinted surfaces. Their interior typography is compact and aligned to maintain comparison. Advocate notes sit below the artifact in normal flow.

### Inputs / Fields

Workspace fields use a nearly white background (`#fdfdfb`), strong-line border, control radius, and compact padding. Textareas resize vertically. Disabled fields use a subdued warm surface and muted text. General keyboard focus remains explicit.

### Navigation

Desktop navigation is a quiet horizontal row with the workspace action outlined. Reduced layouts remove secondary section links before hiding all non-CTA links on mobile. The skip link becomes visible on focus.

### Agreement Walkthrough

Six manually selected stages use buttons with tab semantics, a visible selected marker, previous/next controls, and a polite live region for the changed record. Endpoint controls are disabled with reduced opacity. The CSV repair demonstration changes explicit counts and status. No autoplay is used. Small hover and selection transitions run for 200ms; reduced-motion preferences suppress landing animation and transitions. Advocate notes remain static after the overlay correction.

## Do's and Don'ts

### Do:

- **Do** preserve the Instrument Serif and Geist pairing.
- **Do** keep advocate notes in their own layout space so document contents remain visible.
- **Do** pair status colors with explicit words and icons.
- **Do** preserve keyboard focus, manual walkthrough controls, and reduced-motion behavior.

### Don't:

- **Don't** use role colors interchangeably.
- **Don't** turn muted metadata into illegible decoration.
- **Don't** conceal exclusions or evidence beneath floating notes.
- **Don't** present synthetic walkthrough states as live activity.
