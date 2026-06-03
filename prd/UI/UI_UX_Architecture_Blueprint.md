# StudyAI — UI/UX Architecture & Visual Blueprint

This document defines the strict visual and interaction architecture for the StudyAI frontend. It entirely discards the modern "SaaS AI wrapper" aesthetic in favor of **Academic Brutalism**—a premium, high-density, editorial interface engineered specifically to optimize cognitive load for university-level mathematical and theoretical study.

*Note: This document governs the presentation layer only. All data fetching, state management, and backend logic are handled independently.*

---

## 1. Visual Identity: "Academic Brutalism"

The visual language emulates the authority of a peer-reviewed scientific journal or a perfectly typeset LaTeX document, augmented with superhuman interactivity. Zero gradients, zero soft shadows, zero decorative elements.

### 1.1 Color Theory (Surgical Precision)
The palette is calibrated to eliminate eye strain during intense exam preparation, relying on absolute contrast and semantic meaning.

* **Vantablack Canvas:** `hsl(0, 0%, 4%)` — The core background. Deep, light-absorbing black.
* **Elevated Paper:** `hsl(0, 0%, 8%)` — Used for note blocks and active read areas.
* **Structural Gridlines:** `rgba(255, 255, 255, 0.08)` — Borders are strictly 1px. No `border-radius` (or `rounded-sm` at most) to enforce a brutal, technical structure.
* **Primary Ink:** `hsl(0, 0%, 96%)` — High-contrast text.
* **Metadata Ink:** `hsl(0, 0%, 55%)` — Dimmed text for structural labels.

### 1.2 Typography & Editorial Scale
Typography is the primary UI. The spacing, tracking, and leading are mathematically defined.

* **The Reading Workspace (Serif):** **Playfair Display** (or Charter). 
    * *Mechanics:* Set to `leading-relaxed` (1.75). The text column is strictly locked to a maximum of `65ch` (characters) wide to optimize saccadic eye movements. 
* **System & Controls (Sans):** **Inter / Geist**. 
    * *Mechanics:* Used exclusively for UI controls, buttons, and high-level navigation. Set with tight tracking.
* **Data & Telemetry (Mono):** **JetBrains Mono**. 
    * *Mechanics:* Used for UPCs, exam years, and exact syllabus phrasing. Set to `text-[11px]` and uppercase.
* **Mathematics:** **Computer Modern (KaTeX)**. Preserved flawlessly to ensure equations feel rigorous and authoritative.

---

## 2. Animation & Interaction Model: "Micro-Physics"

Animations are functional tools used to preserve spatial awareness and communicate UI state seamlessly.

### 2.1 The Ghost Layout (Skeletons)
To prevent layout shifts during content load, the UI claims deterministic space. 
* Based on content weight, we render pre-sized blocks (e.g., a heavy topic instantly reserves a `min-h-[480px]` structural frame).
* **Ink-Reveal Transition:** Text payloads use a Framer Motion linear mask reveal—fading in smoothly from top to bottom over `300ms`, resembling ink settling onto paper.

### 2.2 Forced Active Recall (The "Friction Engine")
* **The Interaction:** "Quick Checks" present a prompt and a stark, etched input field (`border-b-2 border-dashed`). There is no "Show Answer" button.
* **The State Machine:** The student must physically type their mental draft into the field. Only upon typing does the Self-Assessment Console fade in, presenting a stark UI slider: `[ Unsure ] — [ Partial ] — [ Full Marks ]`.
* **The Reward Physics:** Rating a topic as "Full Marks" locks the input, dims the draft to 60% opacity, and triggers a crisp, localized monochrome particle burst at the cursor coordinates.

### 2.3 Dense Mathematics Navigation
* **Click-to-Isolate:** Clicking a complex display equation triggers a Framer Motion `layoutId` expansion. The background dims (`backdrop-blur-md`), and the equation elevates, revealing a monospaced "Dependency Drawer" that breaks down the variables below it.

---

## 3. The Trust Layer: Visualizing Authority

To establish ultimate confidence, StudyAI uses distinct visual language for all trust indicators.

### 3.1 Verified Badges
* **Single Verification (`✓`):** Renders as a crisp, solid green outline badge (`border border-emerald-500/30 bg-emerald-500/5 text-emerald-400`). Indicates independent processing.
* **Dual Verification (`✓✓`):** Renders with a premium double-tick and an active micro-sparkle transition. Indicates perfect consensus between models.
* **Proof Verified Badge:** Styled as a classic Q.E.D. symbol (`■`) with a Radix Tooltip detailing the exact logical chain verified.

### 3.2 The Paper DNA Sidebar
A sticky right-rail component. As the user scrolls, `IntersectionObserver` tracks which NoteBlock is at the center of the viewport. The DNA Sidebar dynamically updates to highlight the exact Examiner Phrasing and Combination Risks relevant to the *currently read* topic.

---

## 4. Component UI Strategy

### 4.1 The Pipeline Visualizer
* **Layout Design:** Renders a vertical technical grid.
* **Visual States:**
    * *Idle:* Static thin grey border, low opacity.
    * *Active:* Pulsing white dashed border, JetBrains Mono ticker showing active execution metrics.
    * *Complete:* Transition to standard UI accent with a clean `0.15s` scale-up spring.

### 4.2 The Calibrated Note Block
* **The Surgical Divider:** A persistent `1px` vertical line runs down the left margin of the reading text. This acts as the anchor. If an examiner's note applies to a specific sentence, a microscopic horizontal hash mark extends from this line, linking the annotation to the text without breaking the reading flow.
* **Hover Flagging:** No bulky floating action buttons. A microscopic `[ ! ]` in JetBrains Mono appears in the right-hand margin only on hover, opening a sheer Radix Popover.

---

## 5. UI Tech Stack Requirements
* **Tailwind CSS:** For applying the exact HSL variables and grid lines.
* **Framer Motion:** For ink-reveals, layout morphs, and micro-physics.
* **Radix UI:** For unstyled, accessible primitives (Popovers, Tooltips) formatted to the Brutalist aesthetic.
* **Lenis (`@studio-freight/react-lenis`):** For smooth, programmatic scrolling across dense mathematical content.