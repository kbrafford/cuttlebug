import wx
import util
from options import *
import os, pickle
session = {}

def load_session(filename='.session'):
    global session
    session = util.unpickle_file(filename)
    if not isinstance(session, dict):
        session = {}
        
def save_session(filename = '.session'):
    global session
    util.pickle_file(session,filename)

def session_get(key):
    global session
    return session.get(key, None)

def session_set(key, value):
    global session
    session[key] = value
    
class Settings(util.Category):

    def __init__(self):
        super(self.__class__, self).__init__()
        self.filename = ''
        # Overview
        editor = self.add_category('editor')
        editor.add_item('view_whitespace', False)
        editor.add_item('line_visible', False)

        editor.add_item('fold', True)
        editor.add_item('fold_margin_size', 16)

        cursor = editor.add_category('cursor')
        cursor.add_item('visible', True)
        cursor.add_item('period', 1000)
        cursor.add_item('width', 1)
        cursor.add_item('foreground_color', (0,0,0))
        cursor.add_item('background_color', (255,255,255))
        cursor.add_item('selection_foreground_color', (0,0,255))
        cursor.add_item('selection_background_color', (255,0,0))

        page = editor.add_category('page')
        page.add_item('wrap', False)
        page.add_item('edge_column', 1)
        page.add_item('edge_mode', 0)
        page.add_item('end_at_last_line', False)
        page.add_item('horizontal_scrollbar', True)
        page.add_item('margin_left', 0)
        page.add_item('margin_right', 0)
        page.add_item('show_line_numbers', True)
        indent = editor.add_category('indent')
        indent.add_item('backspace_unindents', True)
        indent.add_item('indentation_guides', True)
        indent.add_item('tab_indents', True)
        indent.add_item('tab_width', 4)
        indent.add_item('use_tabs', False)

        debug = self.add_category('debug')
        debug.add_item('jump_to_exec_location', False)

    @staticmethod
    def load(filename):
        print "loading settings from %s" % filename
        path = os.path.abspath(filename)
        fp = open(path, 'r')
        object = pickle.load(fp)
        fp.close()
        if not isinstance(object, Settings):
            raise Exception("Could not load %s.  It does not appear to be a settings file." % filename)
        object.filename = path
        return object
    
    @staticmethod
    def create(filename):
        settings = Settings()
        settings.filename = os.path.abspath(filename)
        settings.save()
        return settings
    
    def save(self):
        fp = open(self.filename,'w')
        pickle.dump(self, fp)
        fp.close()

class SettingsDialog(OptionsDialog):

    def __init__(self, parent, title="Settings", size=(600,400), settings=None):
        OptionsDialog.__init__(self, parent, title=title, size=size, data=settings, icons=["style.png"])
        self.create_style_panels()

    def create_style_panels(self):
        # Main  Panel
        editor_panel = OptionsPanel(self, "Editor")
        editor_panel.add("Misc", "Show Whitespace", CheckboxWidget, key="editor.view_whitespace")
        editor_panel.add("Misc", "Code Folding", CheckboxWidget, key="editor.fold")
        
        # Cursor
        cursor_panel = OptionsPanel(self, "Cursor")
        cursor_panel.add("Selection", "Selection Background Color", ColorWidget, key="editor.cursor.background_color")
        cursor_panel.add("Selection", "Selection Foreground Color", ColorWidget, key="editor.cursor.foreground_color")
        editor_panel.add("Selection", "Hilight Current Line", CheckboxWidget, key="editor.line_visible")
        cursor_panel.add("Cursor", "Cursor Visible", CheckboxWidget, key="editor.cursor.visible")
        cursor_panel.add("Cursor", "Cursor Period (ms)", SpinWidget, key="editor.cursor.period")

        # Page
        page_panel = OptionsPanel(self, "Page")
        page_panel.add("Margins", "Left Margin (px)", SpinWidget, key="editor.page.margin_left")
        page_panel.add("Margins", "Right Margin (px)", SpinWidget, key="editor.page.margin_right")
        page_panel.add("Margins", "Show Line Numbers", CheckboxWidget, key="editor.page.show_line_numbers")
        page_panel.add("Wrap", "Wrap", CheckboxWidget, key="editor.page.wrap", label_on_right=True)
        page_panel.add("Wrap", "Horizontal Scrollbar", CheckboxWidget, key="editor.page.horizontal_scrollbar", label_on_right=True)

        debug_panel = OptionsPanel(self, "Debug")
        debug_panel.add("Runninig", "Jump to Execution Location on HALT", CheckboxWidget, key="debug.jump_to_exec_location")
        
        self.add_panel(editor_panel, icon='style.png')
        self.add_panel(cursor_panel, parent=editor_panel, icon='textfield_rename.png')
        self.add_panel(page_panel, parent=editor_panel, icon='page.png')
        self.add_panel(debug_panel, icon='bug.png')
     
    @staticmethod
    def show(parent, settings=None):
        dialog = SettingsDialog(parent, settings=settings)
        dialog.Centre()
        dialog.ShowModal() 

if __name__ == "__main__":
    
    #settings = Settings.create(".settings_test")
    #print settings.__dict__
    settings = Settings.load(".settings_test")
    settings.save()

