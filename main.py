"""
[hw Two]!
"""

import os
import sys

custom_config_file = 'kivy_config.ini'


def is_kivy_loaded():
    # Check if any modules that start with 'kivy' are in sys.modules
    for module_name, module in sys.modules.items():
        if module_name.startswith("kivy") and module is not None and module_name != "kivy_config_helper":
            print(f"Loaded kivy module found!!!: {module_name}")
            return True
    return False


if is_kivy_loaded():
    print("ERROR: It looks like kivy has already been loaded before kivy_config_helper's config_kivy() was called!")
    print("Please move import of kivy_config_helper and config_kivy() call to the top of your file and try again!")
    exit(0)


from kivy.config import Config


def write_density():
    # critical that metrics is not loaded until other configuration is set to what we want (esp. window resolution)
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
        # Note the following simulation strategy assumes you want to simulate the same resolution
        # window (e.g. Kivy app in windowed mode) on various devices. If you want to simulate different
        # full screen apps, then some changes are necessary.

        # For some reason, you can only override Kivy's initial DPI and Density
        # via environment variables.

        if not simulate_dpi or not simulate_density:
            raise ValueError("if simulate_device is set to True, then "
                             "simulate_dpi and simulate_density must be set!")

        print(f"Simulating device with density {simulate_density} and dpi {simulate_dpi}")

        os.environ['KIVY_DPI'] = str(simulate_dpi)
        os.environ['KIVY_METRICS_DENSITY'] = str(simulate_density)

        # This scales window size appropriately for simulation
        target_window_width = int(window_width / curr_device_density * simulate_density)
        target_window_height = int(window_height / curr_device_density * simulate_density)
    else:
        # if these are set externally, we'll ignore and use default dpi and density of device
        os.environ.pop('KIVY_DPI', None)
        os.environ.pop('KIVY_METRICS_DENSITY', None)

    if target_window_width != config_window_width or target_window_height != config_window_height:
        print(f"target_window_width: {target_window_width}, target_window_height: {target_window_height}")
        print(f"config_window_width: {config_window_width}, config_window_height: {config_window_height}")

        Config.set('graphics', 'width', str(target_window_width))
        Config.set('graphics', 'height', str(target_window_height))

    if simulate_device:
        target_window_width = window_width
        target_window_height = window_height
        print(f"Simulated resolution: {target_window_width}x{target_window_height}")
    else:
        # we can only get a reliable density if we aren't simulating (due to impact of KIVY_METRICS_DENSITY env var)
        check_density = write_density()

        if curr_device_density != check_density:
            print(f"The current device density ({check_density}) doesn't match the stored "
                  f"configuration ({curr_device_density}).")
            print(f"Therefore, updating the config to use the correct density.")
            print(f"Now exiting, please run again to use the stored configuration.")
            exit(0)

    return target_window_width, target_window_height

config_kivy(window_width=800, window_height=600, simulate_device=False)

from kivy.app import App
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.widget import Widget
from kivy.uix.scrollview import ScrollView
from kivy.graphics import Color, Rectangle, Line
from kivy.metrics import dp
from kivy.properties import NumericProperty, BooleanProperty
import random


# NASA TLX Dimensions
DIMENSIONS = [
    ("Mental Demand", "How mentally demanding was the task?"),
    ("Physical Demand", "How physically demanding was the task?"),
    ("Temporal Demand", "How hurried or rushed was the pace of the task?"),
    ("Performance", "How successful were you in accomplishing what you were asked to do?"),
    ("Effort", "How hard did you have to work to accomplish your level of performance?"),
    ("Frustration", "How insecure, discouraged, irritated, stressed, and annoyed were you?")
]

# Scale descriptions (left to right)
SCALE_LABELS = {
    "Mental Demand": ("Low", "High"),
    "Physical Demand": ("Low", "High"),
    "Temporal Demand": ("Low", "High"),
    "Performance": ("Failure", "Perfect"),  # Flipped per requirements
    "Effort": ("Low", "High"),
    "Frustration": ("Low", "High")
}


def choose_two(lst):
    """Generate all pairwise combinations"""
    res = []
    for i in range(len(lst) - 1):
        for j in range(i + 1, len(lst)):
            tup = (lst[i], lst[j])
            res.append(tup)
    return res


def shuffle(lst):
    """Shuffle a list randomly"""
    clst = lst.copy()
    res = []
    while len(clst) > 0:
        index = random.randint(0, len(clst) - 1)
        res.append(clst[index])
        del clst[index]
    return res


class ScaleWidget(Widget):
    """Custom widget for NASA TLX scale with canvas drawing"""
    value = NumericProperty(None, allownone=True)
    visited = BooleanProperty(False)
    
    def __init__(self, dimension_name, **kwargs):
        super().__init__(**kwargs)
        self.dimension_name = dimension_name
        self.size_hint_y = None
        self.height = dp(42)
        self.bind(pos=self.update_canvas, size=self.update_canvas, value=self.update_canvas, visited=self.update_canvas)
        self.update_canvas()
    
    def update_canvas(self, *args):
        self.canvas.clear()
        
        with self.canvas:
            # Draw background with visited indicator
            if self.visited:
                Color(0.9, 0.95, 1.0, 1)  # Light blue tint when visited
            else:
                Color(0.97, 0.97, 0.97, 1)
            Rectangle(pos=self.pos, size=self.size)
            
            # Calculate scale area
            scale_left = self.x + dp(60)
            scale_width = self.width - dp(120)
            scale_y = self.center_y
            
            # Draw value bar if value is set
            if self.value is not None:
                bar_width = scale_width * (self.value / 100.0)
                Color(0.2, 0.5, 0.8, 0.8)
                Rectangle(pos=(scale_left, scale_y - dp(8)), size=(bar_width, dp(16)))
            
            # Draw scale marks
            Color(0.3, 0.3, 0.3, 1)
            for i in range(0, 101, 5):
                x_pos = scale_left + (scale_width * i / 100.0)
                # Middle mark is taller
                if i == 50:
                    Line(points=[x_pos, scale_y - dp(12), x_pos, scale_y + dp(12)], width=dp(2.5))
                else:
                    Line(points=[x_pos, scale_y - dp(8), x_pos, scale_y + dp(8)], width=dp(1.5))
            
            # Draw horizontal line
            Line(points=[scale_left, scale_y, scale_left + scale_width, scale_y], width=dp(2.5))
            
            # Draw border if visited
            if self.visited:
                Color(0.2, 0.5, 0.8, 0.6)
                Line(rectangle=(self.x + dp(1), self.y + dp(1), self.width - dp(2), self.height - dp(2)), width=dp(2))
    
    def on_touch_down(self, touch):
        if self.collide_point(*touch.pos):
            self.set_value_from_touch(touch)
            return True
        return super().on_touch_down(touch)
    
    def on_touch_move(self, touch):
        if self.collide_point(*touch.pos):
            self.set_value_from_touch(touch)
            return True
        return super().on_touch_move(touch)
    
    def set_value_from_touch(self, touch):
        left_pad = dp(60)
        right_pad = dp(60)
        scale_left = self.x + left_pad
        scale_width = self.width - (left_pad + right_pad)

        # Calculate value from touch position
        relative_x = touch.x - scale_left
        relative_x = max(0, min(scale_width, relative_x))
        raw_value = (relative_x / scale_width) * 100

        # Snap to increments of 5
        self.value = round(raw_value / 5) * 5
        self.visited = True


class PairComparisonScreen(Screen):
    """Screen for comparing two dimensions"""
    def __init__(self, pair, pair_num, total_pairs, **kwargs):
        super().__init__(**kwargs)
        self.pair = pair
        self.pair_num = pair_num
        self.total_pairs = total_pairs
        self.selection = None
        
        layout = BoxLayout(orientation='vertical', padding=dp(20), spacing=dp(15))
        
        # Title with better formatting
        title = Label(
            text=f"NASA TLX - Pair {pair_num} of {total_pairs}\n\nWhich factor contributed MORE to the workload?",
            size_hint_y=0.25,
            font_size=dp(16),
            halign='center',
            valign='middle'
        )
        title.bind(size=lambda *args: setattr(title, 'text_size', title.size))
        layout.add_widget(title)
        
        # Pair buttons with padding
        button_container = BoxLayout(orientation='vertical', size_hint_y=0.55)
        button_container.add_widget(Widget(size_hint_y=0.1))  # Top padding
        
        button_layout = BoxLayout(orientation='horizontal', spacing=dp(30), size_hint_y=0.8, padding=[dp(40), 0])
        
        self.btn1 = Button(
            text=pair[0],
            font_size=dp(18),
            background_color=(0.85, 0.85, 0.85, 1),
            background_normal='',
            bold=True
        )
        self.btn1.bind(on_press=lambda x: self.select_option(0))
        
        self.btn2 = Button(
            text=pair[1],
            font_size=dp(18),
            background_color=(0.85, 0.85, 0.85, 1),
            background_normal='',
            bold=True
        )
        self.btn2.bind(on_press=lambda x: self.select_option(1))
        
        button_layout.add_widget(self.btn1)
        button_layout.add_widget(self.btn2)
        button_container.add_widget(button_layout)
        button_container.add_widget(Widget(size_hint_y=0.1))  # Bottom padding
        
        layout.add_widget(button_container)
        
        # Navigation buttons
        nav_layout = BoxLayout(size_hint_y=0.2, spacing=dp(20), padding=[dp(10), 0])
        
        self.prev_btn = Button(
            text="Previous",
            font_size=dp(14),
            background_color=(0.7, 0.7, 0.7, 1),
            background_normal=''
        )
        self.prev_btn.bind(on_press=self.go_previous)
        nav_layout.add_widget(self.prev_btn)
        
        self.next_btn = Button(
            text="Next",
            font_size=dp(14),
            disabled=True,
            background_color=(0.5, 0.5, 0.5, 1),
            background_normal=''
        )
        self.next_btn.bind(on_press=self.go_next)
        nav_layout.add_widget(self.next_btn)
        
        layout.add_widget(nav_layout)
        self.add_widget(layout)
    
    def on_enter(self):
        # Restore selection state
        if self.selection is not None:
            self.update_selection_visual()
    
    def select_option(self, choice):
        self.selection = choice
        self.update_selection_visual()
        self.next_btn.disabled = False
        self.next_btn.background_color = (0.2, 0.5, 0.8, 1)
    
    def update_selection_visual(self):
        if self.selection == 0:
            self.btn1.background_color = (0.2, 0.5, 0.8, 1)
            self.btn2.background_color = (0.85, 0.85, 0.85, 1)
        elif self.selection == 1:
            self.btn1.background_color = (0.85, 0.85, 0.85, 1)
            self.btn2.background_color = (0.2, 0.5, 0.8, 1)
    
    def go_previous(self, instance):
        self.manager.transition.direction = 'right'
        self.manager.current = self.manager.previous()
    
    def go_next(self, instance):
        if not self.next_btn.disabled:
            self.manager.transition.direction = 'left'
            self.manager.current = self.manager.next()


class ScaleValueScreen(Screen):
    """Screen for rating all dimensions"""
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.scales = {}
        
        layout = BoxLayout(orientation='vertical', padding=dp(10), spacing=dp(5))
        
        # Title
        title = Label(
            text="Rate Each Factor (0-100)",
            size_hint_y=0.08,
            font_size=dp(12),
            halign='center',
            valign='middle'
        )
        title.bind(size=lambda *args: setattr(title, 'text_size', title.size))
        layout.add_widget(title)
        
        # Scrollable scale container
        scroll = ScrollView(size_hint_y=0.78)
        scale_container = BoxLayout(orientation='vertical', spacing=dp(10), size_hint_y=None)
        scale_container.bind(minimum_height=scale_container.setter('height'))
        
        for dim_name, desc in DIMENSIONS:
            # Dimension box
            dim_box = BoxLayout(orientation='vertical', spacing=dp(2), size_hint_y=None, height=dp(62))
            
            # Label with better formatting
            left_label, right_label = SCALE_LABELS[dim_name]
            label_text = f"[b]{dim_name}[/b]\n{left_label} ← → {right_label}"
            dim_label = Label(
                text=label_text,
                size_hint_y=None,
                height=dp(24),
                font_size=dp(10),
                markup=True
            )
            dim_box.add_widget(dim_label)
            
            # Scale widget
            scale = ScaleWidget(dim_name)
            self.scales[dim_name] = scale
            dim_box.add_widget(scale)
            
            scale_container.add_widget(dim_box)
        
        scroll.add_widget(scale_container)
        layout.add_widget(scroll)
        
        # Navigation
        nav_layout = BoxLayout(size_hint_y=0.14, spacing=dp(20), padding=[dp(10), dp(3)])
        
        prev_btn = Button(
            text="Previous",
            font_size=dp(14),
            background_color=(0.7, 0.7, 0.7, 1),
            background_normal=''
        )
        prev_btn.bind(on_press=self.go_previous)
        nav_layout.add_widget(prev_btn)
        
        self.next_btn = Button(
            text="View Results",
            font_size=dp(14),
            disabled=True,
            background_color=(0.5, 0.5, 0.5, 1),
            background_normal=''
        )
        self.next_btn.bind(on_press=self.go_next)
        nav_layout.add_widget(self.next_btn)
        
        layout.add_widget(nav_layout)
        self.add_widget(layout)
    
    def on_enter(self):
        self.check_all_visited()
    
    def check_all_visited(self, *args):
        all_visited = all(scale.visited for scale in self.scales.values())
        self.next_btn.disabled = not all_visited
        if all_visited:
            self.next_btn.background_color = (0.2, 0.5, 0.8, 1)
        # Schedule repeated check
        if not all_visited:
            from kivy.clock import Clock
            Clock.schedule_once(self.check_all_visited, 0.2)
    
    def go_previous(self, instance):
        self.manager.transition.direction = 'right'
        self.manager.current = self.manager.previous()
    
    def go_next(self, instance):
        if not self.next_btn.disabled:
            self.manager.transition.direction = 'left'
            self.manager.current = self.manager.next()


class ResultsScreen(Screen):
    """Screen displaying final results"""
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        
        layout = BoxLayout(orientation='vertical', padding=dp(25), spacing=dp(15))
        
        # Title
        title = Label(
            text="NASA TLX Workload Assessment Results",
            size_hint_y=0.12,
            font_size=dp(20),
            bold=True,
            color=(0.2, 0.2, 0.2, 1)
        )
        layout.add_widget(title)
        
        # Results label with better formatting
        self.results_label = Label(
            text="",
            size_hint_y=0.88,
            font_size=dp(13),
            halign='left',
            valign='top',
            markup=True
        )
        self.results_label.bind(size=self.update_text_size)
        layout.add_widget(self.results_label)
        
        self.add_widget(layout)
    
    def update_text_size(self, *args):
        self.results_label.text_size = self.results_label.size
    
    def on_enter(self):
        app = App.get_running_app()
        self.calculate_and_display_results(app)
    
    def calculate_and_display_results(self, app):
        # Count selections for each dimension
        tally = {dim: 0 for dim, _ in DIMENSIONS}
        
        for screen_name in app.sm.screen_names:
            if screen_name.startswith('pair_'):
                screen = app.sm.get_screen(screen_name)
                if screen.selection is not None:
                    selected_dim = screen.pair[screen.selection]
                    tally[selected_dim] += 1
        
        # Get ratings
        scale_screen = app.sm.get_screen('scales')
        ratings = {dim: scale_screen.scales[dim].value for dim, _ in DIMENSIONS}
        
        # Calculate weights
        total_tally = sum(tally.values())
        weights = {dim: tally[dim] / total_tally if total_tally > 0 else 0 for dim in tally}
        
        # Calculate weighted workload score
        workload_score = sum(ratings[dim] * weights[dim] for dim in tally if ratings[dim] is not None)
        
        # Format results with markup for better appearance
        result_text = "[b]Dimension Results:[/b]\n" + "_" * 70 + "\n\n"
        
        for dim, _ in DIMENSIONS:
            rating = ratings[dim] if ratings[dim] is not None else 0
            weight = weights[dim]
            t = tally[dim]
            result_text += f"[b]{dim}:[/b]\n"
            result_text += f"    Tally: {t}    Weight: {weight:.3f}    Rating: {rating}/100\n\n"
        
        result_text += "_" * 70 + "\n\n"
        result_text += f"[b][size=16]Overall Workload Score: {workload_score:.2f}[/size][/b]\n"
        
        self.results_label.text = result_text


class NASATLXApp(App):
    def build(self):
        self.sm = ScreenManager()
        
        # Generate randomized pairs
        dimension_names = [dim for dim, _ in DIMENSIONS]
        pairs = choose_two(dimension_names)
        shuffled_pairs = shuffle(pairs)
        
        # Randomize order within each pair
        for i in range(len(shuffled_pairs)):
            if random.random() < 0.5:
                shuffled_pairs[i] = (shuffled_pairs[i][1], shuffled_pairs[i][0])
        
        self.pairs = shuffled_pairs
        
        # Create pair comparison screens
        for i, pair in enumerate(self.pairs):
            screen = PairComparisonScreen(
                pair=pair,
                pair_num=i + 1,
                total_pairs=len(self.pairs),
                name=f'pair_{i}'
            )
            # Hide previous button on first screen
            if i == 0:
                screen.prev_btn.opacity = 0
                screen.prev_btn.disabled = True
            self.sm.add_widget(screen)
        
        # Create scale value screen
        scale_screen = ScaleValueScreen(name='scales')
        self.sm.add_widget(scale_screen)
        
        # Create results screen
        results_screen = ResultsScreen(name='results')
        self.sm.add_widget(results_screen)
        
        Config.set('graphics', 'resizable', False)
        
        return self.sm


if __name__ == '__main__':
    NASATLXApp().run()