---
name: Technical Sophistication
colors:
  surface: '#0b1326'
  surface-dim: '#0b1326'
  surface-bright: '#31394d'
  surface-container-lowest: '#060e20'
  surface-container-low: '#131b2e'
  surface-container: '#171f33'
  surface-container-high: '#222a3d'
  surface-container-highest: '#2d3449'
  on-surface: '#dae2fd'
  on-surface-variant: '#c7c4d7'
  inverse-surface: '#dae2fd'
  inverse-on-surface: '#283044'
  outline: '#908fa0'
  outline-variant: '#464554'
  surface-tint: '#c0c1ff'
  primary: '#c0c1ff'
  on-primary: '#1000a9'
  primary-container: '#8083ff'
  on-primary-container: '#0d0096'
  inverse-primary: '#494bd6'
  secondary: '#b9c8de'
  on-secondary: '#233143'
  secondary-container: '#39485a'
  on-secondary-container: '#a7b6cc'
  tertiary: '#4edea3'
  on-tertiary: '#003824'
  tertiary-container: '#00885d'
  on-tertiary-container: '#000703'
  error: '#ffb4ab'
  on-error: '#690005'
  error-container: '#93000a'
  on-error-container: '#ffdad6'
  primary-fixed: '#e1e0ff'
  primary-fixed-dim: '#c0c1ff'
  on-primary-fixed: '#07006c'
  on-primary-fixed-variant: '#2f2ebe'
  secondary-fixed: '#d4e4fa'
  secondary-fixed-dim: '#b9c8de'
  on-secondary-fixed: '#0d1c2d'
  on-secondary-fixed-variant: '#39485a'
  tertiary-fixed: '#6ffbbe'
  tertiary-fixed-dim: '#4edea3'
  on-tertiary-fixed: '#002113'
  on-tertiary-fixed-variant: '#005236'
  background: '#0b1326'
  on-background: '#dae2fd'
  surface-variant: '#2d3449'
typography:
  display-lg:
    fontFamily: Inter
    fontSize: 48px
    fontWeight: '700'
    lineHeight: '1.1'
    letterSpacing: -0.02em
  headline-md:
    fontFamily: Inter
    fontSize: 24px
    fontWeight: '600'
    lineHeight: '1.3'
    letterSpacing: -0.01em
  body-base:
    fontFamily: Inter
    fontSize: 14px
    fontWeight: '400'
    lineHeight: '1.5'
    letterSpacing: '0'
  body-sm:
    fontFamily: Inter
    fontSize: 12px
    fontWeight: '400'
    lineHeight: '1.4'
    letterSpacing: '0'
  code-mono:
    fontFamily: JetBrains Mono
    fontSize: 13px
    fontWeight: '450'
    lineHeight: '1.6'
    letterSpacing: '0'
  label-caps:
    fontFamily: JetBrains Mono
    fontSize: 11px
    fontWeight: '600'
    lineHeight: '1'
    letterSpacing: 0.05em
rounded:
  sm: 0.125rem
  DEFAULT: 0.25rem
  md: 0.375rem
  lg: 0.5rem
  xl: 0.75rem
  full: 9999px
spacing:
  base: 4px
  xs: 4px
  sm: 8px
  md: 16px
  lg: 24px
  xl: 32px
  gutter: 12px
  margin-desktop: 24px
---

## Brand & Style
The design system is engineered for high-utility desktop environments where precision and multi-threaded focus are paramount. It targets power users, developers, and researchers who require a high-control interface that feels like a professional instrument rather than a consumer app.

The style is a hybrid of **Modern Corporate** and **Geist-inspired Minimalism**, utilizing high-density layouts and a "hardware-accelerated" aesthetic. The emotional response is one of absolute control, reliability, and technical depth. Visual weight is communicated through structural integrity, subtle translucency (Glassmorphism), and precise, low-contrast outlines. Every element serves a functional purpose, eliminating decorative bloat to maximize the user's cognitive bandwidth for complex data analysis and AI orchestration.

## Colors
The palette is built on a foundation of **Deep Space Charcoal** (#0F172A) to reduce eye strain during long-duration technical work. 

- **Primary (Electric Indigo):** Used sparingly for primary actions, active states, and focus indicators. It provides a high-energy contrast against the dark background.
- **Secondary (Slate Gray):** Utilized for borders, secondary text, and inactive UI chrome. 
- **Success/Tertiary (Emerald):** Reserved for confidence levels, status "Healthy" indicators, and completed terminal processes.
- **Accents:** A range of deep grays and near-blacks create the "Tonal Layering" necessary for high-density modular interfaces.

## Typography
This design system employs a dual-font strategy. **Inter** provides the structural clarity needed for navigation and content, while **JetBrains Mono** is used for all technical outputs, logs, metadata, and labels to reinforce the "developer-first" nature of the workspace.

For high-density layouts, font sizes gravitate toward the 12px-14px range. Large headlines are reserved for empty states or dashboard titles. Use `label-caps` for table headers and section dividers to create a clear, rigid hierarchy.

## Layout & Spacing
The layout uses a **Fluid Grid with fixed-width sidebars**. The central workspace should maximize horizontal area, utilizing 12 columns for data-heavy views.

- **Spacing Rhythm:** A strict 4px baseline grid.
- **Density:** High. Padding within components (like input fields and list items) should be compact (`sm` or `xs`) to allow for maximum information visibility without scrolling.
- **Breakpoints:**
  - **Desktop (1440px+):** 12-column grid, 24px margins.
  - **Laptop (1024px-1439px):** 12-column grid, 16px margins.
  - **Tablet (768px-1023px):** 8-column grid, 16px margins, sidebars collapse into a drawer.

## Elevation & Depth
Depth is created through **Tonal Layering** and **Subtle Translucency** rather than traditional shadows.

1.  **Background (Base):** #020617 (True dark for high contrast).
2.  **Surface (Tier 1):** #0F172A (Standard workspace background).
3.  **Surface-Container (Tier 2):** #1E293B (Active panels, modded overlays).
4.  **Borders:** 1px solid borders using #334155. For active states, use the primary color with a 2px outer glow (0px blur, 2px spread).

Use `backdrop-filter: blur(12px)` for floating command palettes and context menus to maintain context of the underlying code or data.

## Shapes
Shapes are disciplined and functional. A "Soft" roundedness (4px) is applied to standard UI components like buttons and inputs to prevent the interface from feeling "sharp" or hostile, while maintaining a precise, technical look. 

- **Containers:** 8px (rounded-lg) for large dashboard cards or main terminal windows.
- **Interactive Elements:** 4px (base) for buttons, checkboxes, and input fields.
- **Status Indicators:** 0px (sharp) for progress bars and gauges to emphasize mathematical precision.

## Components
- **Buttons:** Primary buttons use a solid Electric Indigo fill. Secondary buttons use a ghost style with a 1px Slate Gray border that highlights on hover.
- **Input Fields:** Darker than the container background (#020617) with a 1px border. The cursor should be a block or high-visibility Indigo.
- **Terminal/Log Lists:** Monospaced text with alternating row highlights. Include "Copy" and "Filter" icons in the top right on hover.
- **Confidence Gauges:** Minimalist horizontal bars. Use a color gradient from Gray to Emerald based on the AI's confidence percentage.
- **Progress Indicators:** Thin (2px) linear bars at the very top of cards or panels, avoiding bulky circular loaders.
- **Chips/Badges:** Small, monospaced text with low-opacity background tints (e.g., Indigo text on 10% Indigo background) for tagging models or languages.