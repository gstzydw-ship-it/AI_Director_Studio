# AI Director Studio Design System

## 1. Visual Theme

AI Director Studio is a production console for short-drama direction workflows. The interface should feel like a focused editing bay: precise, cinematic, calm, and operational. It is not a marketing site.

Use a dark neutral canvas with warm amber command accents, cool cyan progress signals, and restrained green success states. Keep the density high enough for repeated professional use, but preserve clear section boundaries so operators can scan the pipeline at a glance.

## 2. Color Palette

| Role | Hex | Usage |
| --- | --- | --- |
| Background | `#0b0b0d` | App shell and main canvas |
| Surface | `#141416` | Primary panels |
| Raised Surface | `#1d1c1b` | Inputs, output blocks, active rows |
| Border | `#333235` | Default separation |
| Text | `#f4f1eb` | Primary labels and result text |
| Secondary Text | `#a7a29a` | Supporting labels |
| Muted Text | `#736f68` | Empty states and metadata |
| Command Amber | `#f6b73c` | Primary action and active focus |
| Progress Cyan | `#4cc9d8` | Running pipeline and restore actions |
| Success Green | `#35c486` | Completed states |
| Error Red | `#ef615f` | Abort, failure, destructive actions |

## 3. Typography

Use `Noto Sans SC`, `Inter`, and system UI fonts. Font sizes are fixed, not viewport-scaled.

| Element | Size | Weight | Notes |
| --- | --- | --- | --- |
| Page title | 26px | 700 | Single screen title |
| Section title | 16px | 700 | Panels and major regions |
| Control label | 12px | 600 | Form labels, upper/lowercase as written |
| Body | 14px | 400 | Forms and descriptions |
| Dense text | 12px | 400 | Metadata, chips, table details |
| Code/output | 13px | 400 | Result text, prompts |

Letter spacing is always `0`.

## 4. Component Styling

- Buttons use 8px radius or less. Primary commands are amber filled buttons; secondary commands are neutral outline buttons; destructive commands are red outline buttons.
- Panels use 8px radius, 1px borders, and subtle shadows. Avoid nested card styling; inner groups should be bands, grids, rows, or panels with lighter borders.
- Inputs are dark raised surfaces with clear focus rings. Selects and textareas should keep stable dimensions.
- Pipeline steps are compact status tiles with fixed minimum widths, icon/label/status, and color-coded states.
- Output tabs are dense segmented controls. The active tab must be visually strong without increasing size or shifting layout.

## 5. Layout Principles

- The first screen is the usable workspace, not a landing page.
- Workspace layout: left column for source material and controls; right column for pipeline status and output. The right column should remain easy to scan while long prompts scroll inside their own region.
- Configuration layout: provider connection strip first, then primary defaults, then Agent assignment grid.
- Knowledge layout: operational controls and status only.
- Prefer full-width bands and direct grids over decorative stacked cards.

## 6. Responsive Behavior

- Desktop: sidebar + two-column workspace.
- Tablet: sidebar narrows, workspace becomes a single column with output after inputs.
- Mobile: sidebar becomes a top navigation rail, panels stack, buttons use full-width rows, and fixed-width grids collapse to one column.
- Minimum touch target is 40px for controls.

## 7. Do

- Use clear operational nouns: 工作台, 连接, 模型池, 流水线, 输出.
- Keep model configuration scannable by grouping text, image, and embedding providers separately.
- Keep result text readable and copy actions close to the output they affect.
- Show failures as actionable diagnostics, especially for network/model-provider errors.

## 8. Do Not

- Do not use oversized hero sections, decorative blobs, or marketing copy.
- Do not rely on purple/blue gradients as the dominant identity.
- Do not make cards inside cards. Use panels, rows, or grouped fields inside a card.
- Do not let long model names, buttons, or prompt text overflow their containers.
