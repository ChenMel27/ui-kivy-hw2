# HW4 - RSVP Reader with Gesture & Keyboard Support

**Name:** Melanie Chen  
**GT Email:**  mchen658@gatech.edu
**GT Number:**  903901190

## Keyboard Shortcuts

| Key | Action |
|-----|--------|
| Left Arrow | Jump back 10 words |
| Right Arrow | Jump forward 10 words |
| Up Arrow | Speed up (+50 WPM) |
| Down Arrow | Slow down (-50 WPM) |
| + or = | Font bigger (+4) |
| - | Font smaller (-4) |
| Spacebar | Pause / Resume playback |

## Gestures

All gestures are drawn on the RSVP display area (the dark central area where words are shown). A blue stroke is drawn as visual feedback while you draw.

| Gesture | Action |
|---------|--------|
| Swipe Left | Jump back 10 words |
| Swipe Right | Jump forward 10 words |
| Swipe Up | Speed up (+50 WPM) |
| Swipe Down | Slow down (-50 WPM) |
| Draw > (right-pointing chevron) | Font bigger (+4) |
| Draw < (left-pointing chevron) | Font smaller (-4) |
| Draw a Circle | Pause / Resume playback |

### How to perform each gesture

- **Swipe**: Click and drag in the desired direction (left, right, up, or down) across the display area. The swipe must cover a minimum distance to register.
- **Chevron Right (>)**: Start from the upper-left area, draw diagonally down-right to a midpoint, then draw diagonally up-right (forming a ">" shape). The middle of the stroke should bulge to the right of the start/end points.
- **Chevron Left (<)**: Start from the upper-right area, draw diagonally down-left to a midpoint, then draw diagonally up-left (forming a "<" shape). The middle of the stroke should bulge to the left of the start/end points.
- **Circle**: Draw a circular shape (clockwise or counter-clockwise) on the display area.

Press the **?** button in the toolbar to view a quick-reference overlay of all controls.

## What doesn't work / not completed
- N/A

## Implementation Notes

### Gesture Recognition
Uses `kivy.gesture` with `GestureDatabase` for template matching. Two gesture templates are registered: a **circle** (for pause toggle) and a **chevron** (for font size changes). Swipe directions are detected by comparing start/end touch positions when no template matches. The `better_unistroke_normalizer` helper (from the assignment tips) interpolates touch points for reliable matching.

### Focus Character Selection
I picked the focus character based on how spritz does it which is slightly left of center (around a third) instead of dead at the center. For the shorter words (w 1-3 chars) I just use the first letter, for 4-5 char words I use index 1, and for longer words I pick roughly 1/3 of the way in.

### Font Metrics
I used `freetype-py` and `uharfbuzz` (from `kivy_text_metrics.py`) to get the actual ascender/descender vals from font so that the baseline line is correctly in position.

## Build Requirements
- `freetype-py`
- `uharfbuzz`