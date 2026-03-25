import os
import sys

custom_config_file = 'kivy_config.ini'


def is_kivy_loaded():
    for module_name, module in sys.modules.items():
        if module_name.startswith("kivy") and module is not None and module_name != "kivy_config_helper":
            return True
    return False


if is_kivy_loaded():
    print("ERROR: Kivy loaded before config_kivy() was called!")
    exit(0)


from kivy.config import Config


def write_density():
    from kivy.metrics import Metrics
    if not Config.has_section('simulation'):
        Config.add_section('simulation')
    Config.set('simulation', 'density', str(Metrics.dp))
    Config.write()
    return Metrics.dp


def config_kivy(window_width=None, window_height=None,
                simulate_device=False,
                simulate_dpi=None, simulate_density=None):

    target_window_width = int(window_width)
    target_window_height = int(window_height)

    config_window_width = Config.getint('graphics', 'width')
    config_window_height = Config.getint('graphics', 'height')

    if not os.path.isfile(custom_config_file):
        with open(custom_config_file, 'w+') as f:
            pass

    Config.read(custom_config_file)

    if Config.has_section('simulation') and Config.has_option('simulation', 'density'):
        curr_device_density = Config.getfloat('simulation', 'density')
    else:
        curr_device_density = write_density()
        print(f"The current device density ({curr_device_density}) has been stored in the configuration")
        print(f"Now exiting, please run again to use the stored configuration.")
        exit(0)

    if simulate_device:
        if not simulate_dpi or not simulate_density:
            raise ValueError("if simulate_device is set to True, then "
                             "simulate_dpi and simulate_density must be set!")

        print(f"Simulating device with density {simulate_density} and dpi {simulate_dpi}")

        os.environ['KIVY_DPI'] = str(simulate_dpi)
        os.environ['KIVY_METRICS_DENSITY'] = str(simulate_density)

        target_window_width = int(window_width / curr_device_density * simulate_density)
        target_window_height = int(window_height / curr_device_density * simulate_density)
    else:
        os.environ.pop('KIVY_DPI', None)
        os.environ.pop('KIVY_METRICS_DENSITY', None)

    if target_window_width != config_window_width or target_window_height != config_window_height:
        Config.set('graphics', 'width', str(target_window_width))
        Config.set('graphics', 'height', str(target_window_height))

    if simulate_device:
        target_window_width = window_width
        target_window_height = window_height
        print(f"Simulated resolution: {target_window_width}x{target_window_height}")
    else:
        check_density = write_density()
        if curr_device_density != check_density:
            print(f"The current device density ({check_density}) doesn't match the stored "
                  f"configuration ({curr_device_density}).")
            print(f"Therefore, updating the config to use the correct density.")
            print(f"Now exiting, please run again to use the stored configuration.")
            exit(0)

    return target_window_width, target_window_height


# config w simulation off
config_kivy(window_width=800, window_height=600, simulate_device=False)

# imports
from kivy.app import App
from kivy.lang import Builder
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.togglebutton import ToggleButton
from kivy.uix.spinner import Spinner
from kivy.uix.slider import Slider
from kivy.uix.popup import Popup
from kivy.uix.filechooser import FileChooserListView
from kivy.uix.widget import Widget
from kivy.graphics import Color, Rectangle, Line, InstructionGroup
from kivy.clock import Clock
from kivy.metrics import dp, Metrics
from kivy.properties import (StringProperty, NumericProperty, BooleanProperty,
                              ListProperty, ObjectProperty)
from kivy.core.text import Label as CoreLabel
from kivy.core.window import Window
from kivy.gesture import Gesture, GestureDatabase
import math
from kivy_text_metrics import TextMetrics

# font paths - using the ones from the class resources repo
FONTS = {
    'OpenDyslexic': './Fonts/OpenDyslexicAlta-Regular.ttf',
    'APHont': './Fonts/APHont-Regular_q15c.ttf',
}

# this picks which character in the word to highlight (the "focus" char).
# spritz seems to put it kinda towards the beginning but not the very first letter
# for longer words, so I tried to mimic that. short words just use first char.
def get_focus_index(word):
    length = len(word)
    if length <= 1:
        return 0
    elif length <= 3:
        return 0  # for short words just highlight first letter
    elif length <= 5:
        return 1
    else:
        # for longer words put it around 1/3 from start
        idx = length // 3 - 1
        if idx < 1:
            idx = 1
        return idx


# figure out how long to show a word on screen given a target WPM.
# i scale based on word length and add extra time for punctuation
# since it felt weird without the pauses at sentence ends
def calc_word_duration(word, wpm):
    base_time = 60.0 / wpm  # seconds per word at this wpm
    # scale by how long the word is relative to avg (5 chars)
    len_scale = len(word) / 5.0
    if len_scale < 1.0:
        len_scale = 1.0
    # add extra pause for end-of-sentence punctuation
    extra = 0.0
    if word and word[-1] in '.!?':
        extra = base_time * 0.6
    elif word and word[-1] in ',;:':
        extra = base_time * 0.3
    return base_time * len_scale + extra


# -------- Constants for gesture/key actions --------
JUMP_WORDS = 10
WPM_STEP = 50
FONT_STEP = 4
MIN_WPM = 50
MAX_WPM = 800
MIN_FONT = 12
MAX_FONT = 120
MIN_GESTURE_DIST = 40  # minimum dp distance for a gesture stroke


def euclidean_distance(p1, p2):
    """Compute Euclidean distance between two points."""
    return math.sqrt((p2[0] - p1[0])**2 + (p2[1] - p1[1])**2)


def better_unistroke_normalizer(pts, total_pts=32):
    """Normalize a unistroke to have exactly total_pts points."""
    if len(pts) < 2:
        raise ValueError("At least two distinct points are required.")
    total_length = sum(euclidean_distance(pts[i], pts[i + 1])
                       for i in range(len(pts) - 1))
    if total_length == 0:
        raise ValueError("Total length of stroke is zero. Invalid input.")
    segment_length = total_length / (total_pts - 1)
    new_pts = [pts[0]]
    accumulated_dist = 0.0
    for i in range(1, len(pts)):
        p1, p2 = pts[i - 1], pts[i]
        dist = euclidean_distance(p1, p2)
        if dist == 0:
            continue
        while accumulated_dist + dist >= segment_length:
            t = (segment_length - accumulated_dist) / dist
            new_x = p1[0] + t * (p2[0] - p1[0])
            new_y = p1[1] + t * (p2[1] - p1[1])
            new_pts.append((new_x, new_y))
            accumulated_dist = 0.0
            p1 = (new_x, new_y)
            dist = euclidean_distance(p1, p2)
        accumulated_dist += dist
    if len(new_pts) < total_pts:
        new_pts.append(pts[-1])
    assert len(new_pts) == total_pts, \
        f"Expected {total_pts} points, got {len(new_pts)}"
    return new_pts[:total_pts]


def create_gesture(name, point_list):
    """Create a named gesture from a list of points."""
    pts = better_unistroke_normalizer(point_list)
    g = Gesture()
    g.add_stroke(point_list=pts)
    g.normalize()
    g.name = name
    return g


# -------- Gesture database with templates --------
gesture_db = GestureDatabase()

# Circle gesture template (for pause toggle)
_n_circle = 36
_circle_pts = [(math.cos(2 * math.pi * i / _n_circle) * 50 + 50,
                math.sin(2 * math.pi * i / _n_circle) * 50 + 50)
               for i in range(_n_circle + 1)]
gesture_db.add_gesture(create_gesture('circle', _circle_pts))

# Chevron ">" gesture template (for font bigger / font smaller)
# Direction (> vs <) is determined by touch-point analysis after matching
_chevron_pts = [(0, 100), (100, 50), (0, 0)]
gesture_db.add_gesture(create_gesture('chevron', _chevron_pts))


# -------- KV string for the layout --------
KV_STRING = '''
#:import dp kivy.metrics.dp
#:import Metrics kivy.metrics.Metrics

<RSVPDisplay>:
    canvas.before:
        Color:
            rgba: 0.12, 0.12, 0.14, 1
        Rectangle:
            pos: self.pos
            size: self.size

<RootWidget>:
    orientation: 'vertical'
    padding: dp(10)
    spacing: dp(6)

    # toolbar at top
    BoxLayout:
        size_hint_y: None
        height: dp(40)
        spacing: dp(8)

        Button:
            id: settings_btn
            text: '\u2699  Settings'
            size_hint_x: None
            width: dp(120)
            font_size: dp(13)
            on_release: root.open_settings_dialog()

        Button:
            id: file_btn
            text: 'Open File...'
            size_hint_x: None
            width: dp(120)
            font_size: dp(13)
            on_release: root.open_file_chooser()

        Label:
            id: file_label
            text: 'No file loaded'
            font_size: dp(12)
            text_size: self.size
            halign: 'left'
            valign: 'middle'
            shorten: True
            shorten_from: 'left'

        ToggleButton:
            id: play_btn
            text: '\\u25B6  Play'
            size_hint_x: None
            width: dp(110)
            font_size: dp(14)
            disabled: True
            on_state: root.on_play_toggle(self.state)

        Button:
            id: help_btn
            text: '?'
            size_hint_x: None
            width: dp(35)
            font_size: dp(16)
            bold: True
            on_release: root.show_gesture_help()

    BoxLayout:
        size_hint_y: None
        height: dp(20)
        spacing: dp(4)

        Label:
            id: progress_label
            text: '0 / 0'
            size_hint_x: None
            width: dp(90)
            font_size: dp(11)

        Slider:
            id: progress_slider
            min: 0
            max: 1
            value: 0
            disabled: True
            size_hint_x: 1
            on_touch_up: root.on_slider_released(self, args[1])

    RSVPDisplay:
        id: rsvp_display

    Label:
        id: status_label
        text: 'Load a text file to begin.'
        size_hint_y: None
        height: dp(22)
        font_size: dp(11)
        color: 0.6, 0.6, 0.6, 1
'''

Builder.load_string(KV_STRING)


class RSVPDisplay(Widget):
    """widget that handles drawing the current word with the focus char highlighted"""
    current_word = StringProperty('')
    focus_index = NumericProperty(0)
    font_name = StringProperty(FONTS['OpenDyslexic'])
    font_size_val = NumericProperty(36)
    focus_color = ListProperty([1, 0.2, 0.2, 1])  # red for focus char
    normal_color = ListProperty([1, 1, 1, 1])  # white for the rest

    def __init__(self, **kw):
        super().__init__(**kw)
        # instruction groups for layered canvas rendering
        self._word_ig = InstructionGroup()
        self._gesture_ig = InstructionGroup()
        self.canvas.after.add(self._word_ig)
        self.canvas.after.add(self._gesture_ig)
        # gesture tracking state
        self._touch_points = []
        # redraw whenever any of these change
        self.bind(pos=self.redraw, size=self.redraw,
                  current_word=self.redraw, focus_index=self.redraw,
                  font_name=self.redraw, font_size_val=self.redraw)

    def get_text_metrics(self, word, fontsize):
        # use the TextMetrics helper from kivy_text_metrics.py 
        # to get freetype/harfbuzz measurements
        tm = TextMetrics(self.font_name, fontsize)
        lbl = CoreLabel(text=word, font_name=self.font_name, font_size=fontsize)
        lbl.refresh()
        glyphs, asc, desc = tm.get_text_extents(word, lbl.texture.size)
        return glyphs, asc, desc

    def redraw(self, *args):
        self._word_ig.clear()
        word = self.current_word

        if not word:
            # no word yet, just draw the guide lines
            yb = self.center_y
            self._word_ig.add(Color(0.5, 0.5, 0.5, 0.6))
            self._word_ig.add(Line(points=[self.x + dp(20), yb,
                                           self.right - dp(20), yb], width=1))
            self._word_ig.add(Color(1, 0.2, 0.2, 0.8))
            xf = self.center_x
            self._word_ig.add(Line(points=[xf, yb - dp(12),
                                           xf, yb + dp(12)], width=1.2))
            return

        fs = self.font_size_val * Metrics.dp  # use dp scaling
        fi = min(self.focus_index, len(word) - 1)

        # grab ascender/descender from freetype
        _, ascender, descender = self.get_text_metrics(word, fs)
        abs_descender = abs(descender)

        # render each character individually so we can color the focus one differently
        # also need individual widths to position everything
        textures = []
        widths = []
        for c in word:
            cl = CoreLabel(text=c, font_name=self.font_name, font_size=fs)
            cl.refresh()
            t = cl.texture
            textures.append(t)
            widths.append(t.size[0])

        # position so focus char is centered at center_x
        focus_center_x = sum(widths[:fi]) + widths[fi] / 2.0
        start_x = self.center_x - focus_center_x

        # compute where baseline should be drawn
        total_h = ascender + abs_descender
        block_bottom = self.center_y - total_h / 2.0
        baseline_y = block_bottom + abs_descender

        # draw baseline line and the vertical focus indicator
        self._word_ig.add(Color(0.35, 0.35, 0.40, 0.8))
        self._word_ig.add(Line(points=[self.x + dp(20), baseline_y,
                                       self.right - dp(20), baseline_y], width=1))
        self._word_ig.add(Color(1, 0.2, 0.2, 0.9))
        cx = self.center_x
        self._word_ig.add(Line(points=[cx, baseline_y - dp(14),
                                       cx, baseline_y + dp(14)], width=1.3))

        # now draw each character
        tex_y = baseline_y - abs_descender
        cur_x = start_x
        for i, c in enumerate(word):
            if i == fi:
                color = self.focus_color
            else:
                color = self.normal_color
            tex = textures[i]
            tw, th = tex.size

            # subtle background highlight behind focus char
            if i == fi:
                self._word_ig.add(Color(1, 0.2, 0.2, 0.12))
                self._word_ig.add(Rectangle(pos=(cur_x - dp(2), tex_y),
                                            size=(tw + dp(4), th)))

            self._word_ig.add(Color(*color))
            self._word_ig.add(Rectangle(texture=tex, pos=(cur_x, tex_y),
                                        size=(tw, th)))

            cur_x += widths[i]

    # -------- Gesture touch handling --------

    def on_touch_down(self, touch):
        if self.collide_point(*touch.pos):
            touch.grab(self)
            self._touch_points = [(touch.x, touch.y)]
            return True
        return super().on_touch_down(touch)

    def on_touch_move(self, touch):
        if touch.grab_current is self:
            self._touch_points.append((touch.x, touch.y))
            self._draw_stroke()
            return True
        return super().on_touch_move(touch)

    def on_touch_up(self, touch):
        if touch.grab_current is self:
            touch.ungrab(self)
            self._touch_points.append((touch.x, touch.y))
            self._clear_stroke()
            self._process_gesture()
            return True
        return super().on_touch_up(touch)

    def _draw_stroke(self):
        """Draw the gesture stroke as the user draws (visual feedback)."""
        self._gesture_ig.clear()
        if len(self._touch_points) > 1:
            self._gesture_ig.add(Color(0.3, 0.7, 1.0, 0.4))
            flat = [c for pt in self._touch_points for c in pt]
            self._gesture_ig.add(Line(points=flat, width=dp(2)))

    def _clear_stroke(self):
        """Clear the gesture stroke overlay."""
        self._gesture_ig.clear()

    def _process_gesture(self):
        """Analyze the drawn gesture and dispatch the corresponding action."""
        pts = self._touch_points
        if len(pts) < 2:
            return

        # compute total stroke distance
        total_dist = sum(euclidean_distance(pts[i], pts[i + 1])
                         for i in range(len(pts) - 1))
        if total_dist < dp(MIN_GESTURE_DIST):
            return  # too short to be a meaningful gesture

        # build a Gesture object from the touch points
        try:
            norm_pts = better_unistroke_normalizer(pts)
        except (ValueError, AssertionError):
            return

        g = Gesture()
        g.add_stroke(point_list=norm_pts)
        g.normalize()

        # try matching against registered gesture templates
        best = gesture_db.find(g, minscore=0.65)

        root = self.parent
        if not root:
            return

        if best:
            score, matched = best
            if matched.name == 'circle':
                root.handle_action('pause_toggle', 'gesture')
                return
            elif matched.name == 'chevron':
                # determine chevron direction (> vs <) by analysing
                # whether the middle of the stroke bulges right or left
                n = len(pts)
                mid_start = n // 3
                mid_end = 2 * n // 3
                mid_pts = pts[mid_start:mid_end] if mid_end > mid_start else pts
                avg_mid_x = sum(p[0] for p in mid_pts) / len(mid_pts)
                avg_end_x = (pts[0][0] + pts[-1][0]) / 2.0
                if avg_mid_x > avg_end_x:
                    root.handle_action('font_bigger', 'gesture')
                else:
                    root.handle_action('font_smaller', 'gesture')
                return

        # no template match → treat as a directional swipe
        dx = pts[-1][0] - pts[0][0]
        dy = pts[-1][1] - pts[0][1]
        if abs(dx) > abs(dy):
            # horizontal swipe
            if dx > 0:
                root.handle_action('jump_forward', 'gesture')
            else:
                root.handle_action('jump_back', 'gesture')
        else:
            # vertical swipe (kivy y-axis points upward)
            if dy > 0:
                root.handle_action('speed_up', 'gesture')
            else:
                root.handle_action('slow_down', 'gesture')


class RootWidget(BoxLayout):

    words = ListProperty([])
    word_index = NumericProperty(0)
    wpm = NumericProperty(250)
    is_playing = BooleanProperty(False)
    selected_font = StringProperty('OpenDyslexic')
    selected_size = NumericProperty(36)
    _clock_event = ObjectProperty(None, allownone=True)

    def open_settings_dialog(self):
        # build the settings popup with spinners for font, size, wpm
        box = BoxLayout(orientation='vertical', spacing=dp(12), padding=dp(12))

        # font row
        frow = BoxLayout(size_hint_y=None, height=dp(40), spacing=dp(8))
        frow.add_widget(Label(text='Font:', size_hint_x=None, width=dp(70),
                              font_size=dp(13)))
        font_sp = Spinner(text=self.selected_font,
                          values=['OpenDyslexic', 'APHont'],
                          size_hint_x=1, font_size=dp(13))
        frow.add_widget(font_sp)
        box.add_widget(frow)

        # size row
        srow = BoxLayout(size_hint_y=None, height=dp(40), spacing=dp(8))
        srow.add_widget(Label(text='Font Size:', size_hint_x=None, width=dp(70),
                              font_size=dp(13)))
        size_sp = Spinner(text=str(self.selected_size),
                          values=['18','24','30','36','42','48','60','72'],
                          size_hint_x=1, font_size=dp(13))
        srow.add_widget(size_sp)
        box.add_widget(srow)

        # wpm row
        wrow = BoxLayout(size_hint_y=None, height=dp(40), spacing=dp(8))
        wrow.add_widget(Label(text='WPM:', size_hint_x=None, width=dp(70),
                              font_size=dp(13)))
        wpm_sp = Spinner(text=str(self.wpm),
                         values=['100','150','200','250','300','400','500'],
                         size_hint_x=1, font_size=dp(13))
        wrow.add_widget(wpm_sp)
        box.add_widget(wrow)

        box.add_widget(Widget())  # spacer

        close_btn = Button(text='Close', size_hint_y=None, height=dp(40),
                           font_size=dp(14))
        box.add_widget(close_btn)

        popup = Popup(title='Settings', content=box,
                      size_hint=(0.65, 0.55))

        # bind spinner changes to update our settings in real time
        font_sp.bind(text=lambda sp, val: self.change_font(val))
        size_sp.bind(text=lambda sp, val: self.change_size(val))
        wpm_sp.bind(text=lambda sp, val: self.change_wpm(val))
        close_btn.bind(on_release=lambda x: popup.dismiss())
        popup.open()

    def change_font(self, name):
        self.selected_font = name
        self.ids.rsvp_display.font_name = FONTS.get(name, FONTS['OpenDyslexic'])

    def change_size(self, val):
        try:
            s = int(val)
        except ValueError:
            return
        self.selected_size = s
        self.ids.rsvp_display.font_size_val = s

    def change_wpm(self, val):
        try:
            self.wpm = int(val)
        except ValueError:
            pass

    def open_file_chooser(self):
        layout = BoxLayout(orientation='vertical', spacing=dp(8), padding=dp(8))

        # try to default to the Texts folder if it exists
        txt_dir = os.path.join(os.path.dirname(__file__), 'Texts')
        if not os.path.isdir(txt_dir):
            txt_dir = os.path.dirname(__file__) or '.'

        chooser = FileChooserListView(path=txt_dir,
                                      filters=['*.txt'],
                                      size_hint_y=1)
        layout.add_widget(chooser)

        btns = BoxLayout(size_hint_y=None, height=dp(40), spacing=dp(8))
        sel_btn = Button(text='Select', font_size=dp(14))
        can_btn = Button(text='Cancel', font_size=dp(14))
        btns.add_widget(sel_btn)
        btns.add_widget(can_btn)
        layout.add_widget(btns)

        popup = Popup(title='Choose a text file',
                      content=layout, size_hint=(0.85, 0.85))

        def do_select(btn):
            if chooser.selection:
                self.load_file(chooser.selection[0])
            popup.dismiss()

        sel_btn.bind(on_release=do_select)
        can_btn.bind(on_release=lambda b: popup.dismiss())
        popup.open()

    def load_file(self, path):
        try:
            with open(path, 'r', encoding='utf-8') as f:
                raw = f.read()
        except Exception as e:
            self.ids.status_label.text = 'Error: ' + str(e)
            return

        self.words = [w for w in raw.split() if w.strip()]
        self.word_index = 0

        fname = os.path.basename(path)
        self.ids.file_label.text = fname
        self.ids.play_btn.disabled = False
        self.ids.progress_slider.disabled = False
        self.ids.progress_slider.max = max(len(self.words) - 1, 1)
        self.ids.progress_slider.value = 0
        self.update_progress()
        self.ids.status_label.text = 'Loaded ' + str(len(self.words)) + ' words from ' + fname

        # if we were already playing, stop first
        if self.is_playing:
            self.stop_playback()
            self.ids.play_btn.state = 'normal'

        self.show_word()

    def on_play_toggle(self, state):
        if state == 'down':
            # start playing
            self.is_playing = True
            self.ids.play_btn.text = '\u275A\u275A  Pause'
            if self.word_index >= len(self.words):
                self.word_index = 0  # wrap around if at end
            self.schedule_next()
        else:
            # pause
            self.is_playing = False
            self.ids.play_btn.text = '\u25B6  Play'
            self.stop_playback()

    def schedule_next(self):
        # cancel any existing scheduled event first
        if self._clock_event:
            self._clock_event.cancel()
            self._clock_event = None
        if self.word_index < len(self.words):
            self.show_word()
            dur = calc_word_duration(self.words[self.word_index], self.wpm)
            self._clock_event = Clock.schedule_once(self.go_next_word, dur)

    def go_next_word(self, dt):
        self.word_index += 1
        if self.word_index >= len(self.words):
            # reached the end of the text
            self.stop_playback()
            self.is_playing = False
            self.ids.play_btn.state = 'normal'
            self.ids.play_btn.text = '\u25B6  Play'
            self.ids.status_label.text = 'Finished.'
            self.update_progress()
            return
        self.update_progress()
        self.schedule_next()

    def stop_playback(self):
        if self._clock_event:
            self._clock_event.cancel()
            self._clock_event = None

    def show_word(self):
        if 0 <= self.word_index < len(self.words):
            w = self.words[self.word_index]
            display = self.ids.rsvp_display
            display.current_word = w
            display.focus_index = get_focus_index(w)
        self.update_progress()

    def update_progress(self):
        total = len(self.words)
        cur = min(self.word_index, total)
        self.ids.progress_label.text = str(cur) + ' / ' + str(total)
        if total > 1:
            self.ids.progress_slider.value = cur

    def on_slider_released(self, slider, touch):
        if not slider.collide_point(*touch.pos):
            return
        if not self.words:
            return
        idx = int(round(slider.value))
        if idx < 0:
            idx = 0
        if idx >= len(self.words):
            idx = len(self.words) - 1
        self.word_index = idx
        self.show_word()
        # if we're playing, restart scheduling from the new position
        if self.is_playing:
            self.stop_playback()
            self.schedule_next()

    # -------- Action methods (gesture + keyboard) --------

    def handle_action(self, action, source='key'):
        """Central dispatcher for all gesture/keyboard actions."""
        method = getattr(self, action, None)
        if method:
            method()
        tag = 'gesture' if source == 'gesture' else 'key'
        info = {
            'jump_back': f'\u2190 Jumped back {JUMP_WORDS} words  |  Word {self.word_index}',
            'jump_forward': f'\u2192 Jumped forward {JUMP_WORDS} words  |  Word {self.word_index}',
            'speed_up': f'\u2191 Speed: {self.wpm} WPM',
            'slow_down': f'\u2193 Speed: {self.wpm} WPM',
            'font_bigger': f'+ Font size: {self.selected_size}',
            'font_smaller': f'- Font size: {self.selected_size}',
            'pause_toggle': 'Paused' if not self.is_playing else 'Playing',
        }
        self.ids.status_label.text = info.get(action, action) + f'  [{tag}]'

    def jump_back(self):
        if not self.words:
            return
        self.word_index = max(0, self.word_index - JUMP_WORDS)
        self.show_word()
        if self.is_playing:
            self.stop_playback()
            self.schedule_next()

    def jump_forward(self):
        if not self.words:
            return
        self.word_index = min(len(self.words) - 1, self.word_index + JUMP_WORDS)
        self.show_word()
        if self.is_playing:
            self.stop_playback()
            self.schedule_next()

    def speed_up(self):
        self.wpm = min(MAX_WPM, self.wpm + WPM_STEP)
        if self.is_playing:
            self.stop_playback()
            self.schedule_next()

    def slow_down(self):
        self.wpm = max(MIN_WPM, self.wpm - WPM_STEP)
        if self.is_playing:
            self.stop_playback()
            self.schedule_next()

    def font_bigger(self):
        self.selected_size = min(MAX_FONT, self.selected_size + FONT_STEP)
        self.ids.rsvp_display.font_size_val = self.selected_size

    def font_smaller(self):
        self.selected_size = max(MIN_FONT, self.selected_size - FONT_STEP)
        self.ids.rsvp_display.font_size_val = self.selected_size

    def toggle_pause(self):
        if not self.words:
            return
        if self.ids.play_btn.disabled:
            return
        if self.is_playing:
            self.ids.play_btn.state = 'normal'
        else:
            self.ids.play_btn.state = 'down'

    def on_key_down(self, instance, key, scancode, codepoint, modifiers):
        """Handle keyboard shortcuts."""
        if key == 276:  # left arrow
            self.handle_action('jump_back', 'key')
            return True
        elif key == 275:  # right arrow
            self.handle_action('jump_forward', 'key')
            return True
        elif key == 273:  # up arrow
            self.handle_action('speed_up', 'key')
            return True
        elif key == 274:  # down arrow
            self.handle_action('slow_down', 'key')
            return True
        elif key == 32:  # spacebar
            self.handle_action('pause_toggle', 'key')
            return True
        elif codepoint in ('+', '='):
            self.handle_action('font_bigger', 'key')
            return True
        elif codepoint == '-':
            self.handle_action('font_smaller', 'key')
            return True
        return False

    def show_gesture_help(self):
        """Show a popup explaining available gestures and keyboard shortcuts."""
        help_text = (
            '[b]Keyboard Shortcuts:[/b]\n'
            '  Left Arrow  \u2192  Jump Back\n'
            '  Right Arrow  \u2192  Jump Forward\n'
            '  Up Arrow  \u2192  Speed Up\n'
            '  Down Arrow  \u2192  Slow Down\n'
            '  + or =  \u2192  Font Bigger\n'
            '  -  \u2192  Font Smaller\n'
            '  Space  \u2192  Pause / Resume\n\n'
            '[b]Gestures (draw on display area):[/b]\n'
            '  Swipe Left  \u2192  Jump Back\n'
            '  Swipe Right  \u2192  Jump Forward\n'
            '  Swipe Up  \u2192  Speed Up\n'
            '  Swipe Down  \u2192  Slow Down\n'
            '  Draw > (chevron right)  \u2192  Font Bigger\n'
            '  Draw < (chevron left)  \u2192  Font Smaller\n'
            '  Draw Circle  \u2192  Pause / Resume\n'
        )
        content = BoxLayout(orientation='vertical', padding=dp(12))
        lbl = Label(text=help_text, markup=True, font_size=dp(13),
                    halign='left', valign='top')
        lbl.bind(size=lbl.setter('text_size'))
        content.add_widget(lbl)
        close_btn = Button(text='Close', size_hint_y=None, height=dp(40),
                           font_size=dp(14))
        content.add_widget(close_btn)
        popup = Popup(title='Controls & Gestures', content=content,
                      size_hint=(0.7, 0.7))
        close_btn.bind(on_release=lambda x: popup.dismiss())
        popup.open()


class RSVPApp(App):
    def build(self):
        self.title = 'RSVP Reader'
        root = RootWidget()
        Window.bind(on_key_down=root.on_key_down)
        return root


if __name__ == '__main__':
    RSVPApp().run()
