---
name: Technical Precision
colors:
  surface: '#131317'
  surface-dim: '#131317'
  surface-bright: '#39393d'
  surface-container-lowest: '#0e0e12'
  surface-container-low: '#1b1b1f'
  surface-container: '#1f1f23'
  surface-container-high: '#2a292e'
  surface-container-highest: '#353439'
  on-surface: '#e4e1e7'
  on-surface-variant: '#c8c4d7'
  inverse-surface: '#e4e1e7'
  inverse-on-surface: '#303034'
  outline: '#928ea0'
  outline-variant: '#474554'
  surface-tint: '#c6bfff'
  primary: '#c6bfff'
  on-primary: '#2800a0'
  primary-container: '#8c80ff'
  on-primary-container: '#22008d'
  inverse-primary: '#5846d4'
  secondary: '#4edf92'
  on-secondary: '#00391e'
  secondary-container: '#00b56c'
  on-secondary-container: '#003e22'
  tertiary: '#ffb86e'
  on-tertiary: '#492900'
  tertiary-container: '#ce7e17'
  on-tertiary-container: '#402300'
  error: '#ffb4ab'
  on-error: '#690005'
  error-container: '#93000a'
  on-error-container: '#ffdad6'
  primary-fixed: '#e4dfff'
  primary-fixed-dim: '#c6bfff'
  on-primary-fixed: '#160066'
  on-primary-fixed-variant: '#3f29bc'
  secondary-fixed: '#6efdac'
  secondary-fixed-dim: '#4edf92'
  on-secondary-fixed: '#002110'
  on-secondary-fixed-variant: '#00522e'
  tertiary-fixed: '#ffdcbd'
  tertiary-fixed-dim: '#ffb86e'
  on-tertiary-fixed: '#2c1600'
  on-tertiary-fixed-variant: '#693c00'
  background: '#131317'
  on-background: '#e4e1e7'
  surface-variant: '#353439'
typography:
  headline-sm:
    fontFamily: DM Sans
    fontSize: 20px
    fontWeight: '600'
    lineHeight: 28px
  body-base:
    fontFamily: DM Sans
    fontSize: 15px
    fontWeight: '400'
    lineHeight: 22px
  body-secondary:
    fontFamily: DM Sans
    fontSize: 13px
    fontWeight: '400'
    lineHeight: 18px
  label-caps:
    fontFamily: DM Sans
    fontSize: 11px
    fontWeight: '600'
    lineHeight: 16px
    letterSpacing: 0.05em
  mono-base:
    fontFamily: JetBrains Mono
    fontSize: 13px
    fontWeight: '400'
    lineHeight: 20px
  mono-sm:
    fontFamily: JetBrains Mono
    fontSize: 11px
    fontWeight: '400'
    lineHeight: 16px
rounded:
  sm: 0.125rem
  DEFAULT: 0.25rem
  md: 0.375rem
  lg: 0.5rem
  xl: 0.75rem
  full: 9999px
spacing:
  container-padding: 24px
  element-gap: 20px
  stack-tight: 8px
  stack-loose: 12px
---

## Brand & Style
The design system is engineered for high-performance utility, targeting power users who require speed and clarity. The aesthetic is inspired by contemporary developer tools, prioritizing a "pro-tool" feel that is both premium and calm. 

The visual language follows a **Modern Minimalist** approach with a focus on high density and structural logic. It avoids decorative flourishes like gradients or glows, relying instead on purposeful color application, strict border logic, and refined typography to communicate hierarchy. The interface should feel intentional, stable, and deeply functional.

## Colors
The palette is rooted in a deep, desaturated dark-mode foundation. Surfaces are tiered to create a sense of depth without the use of shadows.

- **Foundations:** Use the background color for the primary canvas. Level 1 surfaces are for main content containers, while Level 2 surfaces are reserved for elevated modals, popovers, or inset UI elements.
- **Accents:** The Violet primary color is the sole driver of action and focus.
- **Semantics:** Color is used functionally to indicate state. Green (Safe), Amber (Caution), and Red (Risk) must be used sparingly to maintain the calm atmosphere of the system.
- **Borders:** All interactive and structural elements use a consistent border color to define boundaries against the dark background.

## Typography
The typography system uses a dual-font approach to balance approachability with technical rigor.

- **Primary UI:** DM Sans handles all interface text. Use the `body-base` for standard reading and `body-secondary` for metadata or less critical information. 
- **Labels:** Small labels use uppercase with slight tracking to ensure legibility at high density.
- **Technical Values:** JetBrains Mono is used for any data that requires precise character alignment, such as IDs, code snippets, timestamps, or numerical values.

## Layout & Spacing
The layout system is built on a high-density grid that maintains readability through generous internal whitespace.

- **Internal Padding:** Main containers and cards must utilize a fixed 24px internal padding to provide "breathing room" for dense data.
- **Gaps:** A standard 20px gap is used between primary layout blocks (e.g., sidebar to main content, card to card).
- **Density:** Use 8px and 12px increments for tighter vertical stacks within components.
- **Adaptation:** On mobile devices, the 24px padding scales down to 16px, and the 20px gaps scale to 12px to maximize screen real estate.

## Elevation & Depth
This design system rejects shadows in favor of **Tonal Layering**. 

Depth is communicated through the stacking of surfaces and the use of hard borders. Level 1 surfaces sit on the background, and Level 2 surfaces sit on Level 1. To further differentiate layers, a 1px border is applied to all containers. In cases where extreme focus is required (such as a modal), a subtle backdrop dim is used, but the surface remains flat without glows or blurs.

## Shapes
The shape language is structured and varied to create a clear visual taxonomy between element types.

- **Cards:** Standard content containers use an 8px radius.
- **Panels & Drawers:** Larger structural elements like side panels or drawers use a more pronounced 14px radius to frame the layout.
- **Pills & Badges:** Indicators, tags, and status badges always use a full 999px pill shape to distinguish them from interactive buttons or cards.

## Components
- **Buttons:** Flat surfaces with the Primary Accent color. Text should be `body-secondary` weight 600. No shadows or gradients. On hover, the background color should lighten by 5%.
- **Input Fields:** Use the Level 1 surface with a Level 2 border. Focus states are indicated by a 1px Primary Accent border. Use `mono-base` for input text if values are technical.
- **Chips/Badges:** Use the Pill shape. For semantic states (Local, Hybrid, External), use a subtle 10% opacity fill of the semantic color with a 100% opacity text color.
- **Lists:** Rows should be separated by a 1px border. Use `body-base` for titles and `body-secondary` for descriptions.
- **Cards:** Utilize Level 1 surfaces, 8px corners, and 24px internal padding.
- **Checkboxes:** Small 14px squares with a 2px radius. When checked, use the Primary Accent color with a white checkmark.