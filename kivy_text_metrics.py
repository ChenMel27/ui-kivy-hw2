"""
kivy_text_metrics.py

Uses freetype-py and uharfbuzz to measure text metrics that are not
available through the Kivy API alone.  Works with the SDL2 text provider
that Kivy uses by default.

Usage:
    metrics = TextMetrics(font_path, font_size_px)
    glyph_attribs, ascender, descender = metrics.get_text_extents(text, texture_size)

Each element in *glyph_attribs* is a dict with keys:
    char, x_offset, y_offset, x_advance, width, height, bearing_x, bearing_y
"""

import freetype
import uharfbuzz as hb
import os


class TextMetrics:
    def __init__(self, font_path, font_size):
        """
        Parameters
        ----------
        font_path : str
            Path to the .ttf / .otf font file.
        font_size : float
            Font size in *pixels* (the same value you pass to Kivy's
            ``font_size`` after dp‑scaling).
        """
        self.font_path = font_path
        self.font_size = font_size

        # ── freetype face ─────────────────────────────────────
        self.ft_face = freetype.Face(font_path)
        self.ft_face.set_char_size(int(font_size * 64))  # 26.6 fixed‑point

        # ── harfbuzz font / face ──────────────────────────────
        with open(font_path, 'rb') as f:
            self._font_data = f.read()

        self.hb_blob = hb.Blob(self._font_data)
        self.hb_face = hb.Face(self.hb_blob)
        self.hb_font = hb.Font(self.hb_face)
        self.hb_font.scale = (int(font_size * 64), int(font_size * 64))

    # ── public API ────────────────────────────────────────────
    def get_text_extents(self, text, texture_size=None):
        """Return (glyph_attribs, ascender, descender).

        Parameters
        ----------
        text : str
            The string to measure.
        texture_size : tuple[int, int] | None
            (width, height) of the Kivy texture, used only for
            informational purposes (not required).

        Returns
        -------
        glyph_attribs : list[dict]
            Per‑glyph metrics.
        ascender : float
            Distance from baseline to top of tallest glyph (positive).
        descender : float
            Distance from baseline to bottom of lowest glyph (positive
            value, measured downward).
        """
        ft = self.ft_face
        size_metrics = ft.size

        # Ascender / descender in pixels (26.6 → float)
        ascender = size_metrics.ascender / 64.0
        descender = abs(size_metrics.descender / 64.0)

        # ── shape with harfbuzz ───────────────────────────────
        buf = hb.Buffer()
        buf.add_str(text)
        buf.guess_segment_properties()
        hb.shape(self.hb_font, buf)

        infos = buf.glyph_infos
        positions = buf.glyph_positions

        glyph_attribs = []
        x_cursor = 0.0
        for info, pos in zip(infos, positions):
            cluster = info.cluster
            ch = text[cluster] if cluster < len(text) else '?'

            # Load glyph in freetype for bearing / width / height
            gid = info.codepoint
            ft.load_glyph(gid, freetype.FT_LOAD_DEFAULT)
            glyph = ft.glyph
            bm_metrics = glyph.metrics

            glyph_attribs.append({
                'char': ch,
                'x_offset': pos.x_offset / 64.0 + x_cursor,
                'y_offset': pos.y_offset / 64.0,
                'x_advance': pos.x_advance / 64.0,
                'width': bm_metrics.width / 64.0,
                'height': bm_metrics.height / 64.0,
                'bearing_x': bm_metrics.horiBearingX / 64.0,
                'bearing_y': bm_metrics.horiBearingY / 64.0,
            })

            x_cursor += pos.x_advance / 64.0

        return glyph_attribs, ascender, descender
