import os
import json
import re
import maya.cmds as cmds
import maya.OpenMayaUI as omui

try:
    from shiboken2 import wrapInstance
    from PySide2 import QtWidgets, QtCore, QtGui
except ImportError:
    from shiboken6 import wrapInstance
    from PySide6 import QtWidgets, QtCore, QtGui

# ---------------- Settings ----------------
settings_file_path = os.path.join(cmds.internalVar(userAppDir=True), "theme_settings.json")

def save_settings(settings):
    with open(settings_file_path, 'w') as f:
        json.dump(settings, f)

def load_settings():
    if os.path.exists(settings_file_path):
        with open(settings_file_path, 'r') as f:
            return json.load(f)
    return {}

# ---------------- Paint-driven Widgets ----------------
PAINT_DRIVEN_CLASSES = [
    "QmayaColorSliderLabel",
    "QmayaColorSliderGrp",
    "QmayaGradientControl",
    "QmayaRenderView",
    "QmayaGLWidget",
    "QmayaSwatchWidget",
    "QmayaColorEditor"
]

def clear_paint_driven_styles(widget):
    if widget is None:
        return
    for child in widget.findChildren(QtWidgets.QWidget):
        if child.metaObject().className() in PAINT_DRIVEN_CLASSES:
            child.setStyleSheet("")
            child.setAttribute(QtCore.Qt.WA_StyledBackground, False)
            child.update()
            child.repaint()

def defer_clear(widget):
    if widget is None:
        return
    QtCore.QTimer.singleShot(0, lambda: clear_paint_driven_styles(widget))

TARGET_WINDOWS = [
    "colorPreferenceWindow",
    "hyperShadePanel1Window",
    "rampNodeAttributeEditor",
    "AttributeEditor"
]

def clear_target_windows():
    for widget in QtWidgets.QApplication.topLevelWidgets():
        if isinstance(widget, QtWidgets.QWidget) and widget.objectName() in TARGET_WINDOWS:
            defer_clear(widget)
            if widget.objectName() == "colorPreferenceWindow":
                try:
                    from maya.plugin.evaluator import cache_ui
                    cache_ui.cache_ui_colour_preferences_update()
                except Exception:
                    pass
            elif widget.objectName() == "hyperShadePanel1Window":
                for child in widget.findChildren(QtWidgets.QWidget):
                    if child.metaObject().className() == "QmayaColorSliderGrp":
                        try:
                            child.updateValue()
                        except Exception:
                            child.update()

# ---------------- Theme Loader ----------------
def apply_styles(selected_theme=None, font_size=None):
    settings = load_settings()
    
    # Resolve Theme
    if selected_theme is None:
        selected_theme = settings.get('selected_theme', 'Maya Default')
    
    # Resolve Font Size
    if font_size is None:
        font_size = settings.get('font_size', 'Auto')

    maya_script_dir = os.path.join(cmds.internalVar(userScriptDir=True), "MayaUIChanger/")
    qss_file = os.path.join(maya_script_dir, f"{selected_theme.lower().replace(' ', '')}_stylesheet.qss")

    if not os.path.exists(qss_file):
        cmds.warning(f"Style file not found: {qss_file}")
        return

    with open(qss_file, "r") as file:
        style_sheet = file.read()

    # Modify Font Size
    if font_size == 'Auto':
        def remove_font_size(match):
            content = match.group(0)
            return re.sub(r'font-size:\s*[^;]+;', '', content, flags=re.IGNORECASE)

        style_sheet = re.sub(r'QWidget\s*\{[^}]+\}', remove_font_size, style_sheet, flags=re.IGNORECASE)
        
    else:
        def replace_font_size(match):
            content = match.group(0)
            if 'font-size:' in content:
                return re.sub(r'font-size:\s*[^;]+;', f'font-size: {font_size};', content, flags=re.IGNORECASE)
            else:
                return content[:-1] + f' font-size: {font_size}; }}'

        style_sheet = re.sub(r'QWidget\s*\{[^}]+\}', replace_font_size, style_sheet, flags=re.IGNORECASE)


    # Global QSS
    app = QtWidgets.QApplication.instance()
    app.setStyleSheet(style_sheet)

    clear_target_windows()

    # Save Settings
    settings['selected_theme'] = selected_theme
    settings['font_size'] = font_size
    save_settings(settings)

# ---------------- Theme Browser UI ----------------

class ThemeBrowser(QtWidgets.QDialog):
    def __init__(self, parent=None):
        super(ThemeBrowser, self).__init__(parent)
        self.setWindowTitle("Theme Explorer")
        self.setWindowFlags(self.windowFlags() & ~QtCore.Qt.WindowContextHelpButtonHint)
        self.resize(500, 400)
        
        self.themes = [
            'Maya Default', 'Blender Light', 'Blender Dark', 'Edgerunners', 'easyBLUE', 'Apple Pro', 'Zbrush', 'Unreal', 'Umbra', 'Modo', 'Retro Macos', 'Retro Macos Dark'
        ]
        
        # Debounce Timer
        self.debounce_timer = QtCore.QTimer()
        self.debounce_timer.setSingleShot(True)
        self.debounce_timer.setInterval(200) # 200ms delay
        self.debounce_timer.timeout.connect(self.execute_update)

        self.build_ui()
        self.load_current_state()

    def build_ui(self):
        main_layout = QtWidgets.QHBoxLayout(self)

        # --- Sidebar (Theme List) ---
        sidebar_layout = QtWidgets.QVBoxLayout()
        self.theme_list = QtWidgets.QListWidget()
        self.theme_list.addItems(self.themes)
        self.theme_list.currentItemChanged.connect(self.on_theme_changed)
        sidebar_layout.addWidget(QtWidgets.QLabel("Themes:"))
        sidebar_layout.addWidget(self.theme_list)
        
        # Font Size Control in Sidebar
        font_layout = QtWidgets.QFormLayout()
        self.font_combo = QtWidgets.QComboBox()
        self.font_combo.addItem("Auto (Respect Maya)", "Auto")
        for i in range(9, 21):
             self.font_combo.addItem(f"{i}pt", f"{i}pt")
        
        self.font_combo.currentIndexChanged.connect(self.on_font_changed)
        font_layout.addRow("Font Size:", self.font_combo)
        sidebar_layout.addLayout(font_layout)
        
        main_layout.addLayout(sidebar_layout, 1) # Flex 1

        # --- Preview Area (Sample Widgets) ---
        preview_group = QtWidgets.QGroupBox("Preview & Test Area")
        preview_layout = QtWidgets.QVBoxLayout(preview_group)
        
        preview_layout.addWidget(QtWidgets.QLabel("This is how your UI looks."))
        preview_layout.addWidget(QtWidgets.QPushButton("Sample Button"))
        preview_layout.addWidget(QtWidgets.QCheckBox("Sample Checkbox"))
        
        radio_layout = QtWidgets.QHBoxLayout()
        radio_layout.addWidget(QtWidgets.QRadioButton("Option 1"))
        radio_layout.addWidget(QtWidgets.QRadioButton("Option 2"))
        preview_layout.addLayout(radio_layout)
        
        input_layout = QtWidgets.QHBoxLayout()
        input_layout.addWidget(QtWidgets.QLabel("Input:"))
        input_layout.addWidget(QtWidgets.QLineEdit("Sample Text"))
        preview_layout.addLayout(input_layout)

        preview_layout.addWidget(QtWidgets.QSlider(QtCore.Qt.Horizontal))
        
        preview_layout.addStretch()

        # Close Button
        self.close_btn = QtWidgets.QPushButton("Close Explorer")
        self.close_btn.clicked.connect(self.accept) # self.accept closes QDialog
        preview_layout.addWidget(self.close_btn)
        
        main_layout.addWidget(preview_group, 2) # Flex 2

    def load_current_state(self):
        settings = load_settings()
        current_theme = settings.get('selected_theme', 'Maya Default')
        current_font = settings.get('font_size', 'Auto')
        
        # Select Theme in List
        items = self.theme_list.findItems(current_theme, QtCore.Qt.MatchExactly)
        if items:
            self.theme_list.setCurrentItem(items[0])
            
        # Select Font in Combo
        index = self.font_combo.findData(current_font)
        if index >= 0:
            self.font_combo.setCurrentIndex(index)

    def on_theme_changed(self, current, previous):
        if current:
            self.apply_update()

    def on_font_changed(self, index):
        self.apply_update()

    def apply_update(self):
        # Restart timer (debounce)
        self.debounce_timer.start()

    def execute_update(self):
        theme_item = self.theme_list.currentItem()
        if not theme_item:
            return
        
        theme = theme_item.text()
        font_size = self.font_combo.currentData()
        
        apply_styles(selected_theme=theme, font_size=font_size)


def show_picker():
    ptr = omui.MQtUtil.mainWindow()
    parent = wrapInstance(int(ptr), QtWidgets.QWidget)
    # Ensure only one instance
    for child in parent.children():
        if isinstance(child, ThemeBrowser):
            child.close()
            
    browser = ThemeBrowser(parent)
    browser.show()

# ---------------- Theme Menu ----------------
def create_menu():
    def make_theme_changer(theme):
        return lambda *args: apply_styles(selected_theme=theme)
    
    def make_font_changer(size):
        return lambda *args: apply_styles(font_size=size)

    if cmds.menu('myMenu', exists=True):
        cmds.deleteUI('myMenu', menu=True)

    main_window_ptr = omui.MQtUtil.mainWindow()
    if main_window_ptr:
        wrapInstance(int(main_window_ptr), QtWidgets.QWidget)
        main_menu = cmds.menu('myMenu', label='Themes', parent='MayaWindow', tearOff=True)

        cmds.menuItem(label="High Level Explorer...", command=lambda *args: show_picker(), parent=main_menu)
        cmds.menuItem(divider=True)

        # Theme List
        for theme in [
            'Maya Default', 'Blender Light', 'Blender Dark', 'Edgerunners', 'easyBLUE', 'Apple Pro', 'Zbrush', 'Unreal', 'Umbra', 'Modo', 'Retro Macos', 'Retro Macos Dark'
        ]:
            cmds.menuItem(label=theme, command=make_theme_changer(theme))
        
        cmds.menuItem(divider=True)
        
        # Font Size Submenu
        font_menu = cmds.menuItem(subMenu=True, label='Font Size', parent=main_menu)
        
        cmds.menuItem(label='Auto (Respect Maya)', command=make_font_changer('Auto'), parent=font_menu)
        cmds.menuItem(divider=True, parent=font_menu)
        for size in [9, 10, 11, 12, 13, 14, 16, 18, 20]:
            label = f"{size}pt"
            cmds.menuItem(label=label, command=make_font_changer(label), parent=font_menu)

    else:
        cmds.warning("Failed to find main Maya window.")

# ---------------- Run Loader ----------------
def run():
    create_menu()
    settings = load_settings()
    # Apply saved settings
    apply_styles()

run()
