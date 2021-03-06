import wx
import os, threading, subprocess, pickle
import odict
from jinja2 import Environment, PackageLoader, FileSystemLoader
from os.path import abspath, dirname, normcase, normpath, splitdrive
from os.path import join as path_join, commonprefix
import wx.lib.platebtn as platebtn

PLATEBTN_DEFAULT_STYLE = platebtn.PB_STYLE_GRADIENT | platebtn.PB_STYLE_SQUARE 
PLATEBTN_DEFAULT_COLOUR = wx.WHITE
#jinja_env = Environment(loader=PackageLoader('dummy', 'templates'))
jinja_env = Environment(loader=FileSystemLoader('./templates/'))
settings_template = None
project_template = None

def str2int(s):
    if 'x' in s:
        return int(s, 16)
    elif 'b' in s:
        return int(s, 2)
    else:
        return int(s)        

def load_templates():
    global settings_template, project_template
    settings_template = jinja_env.get_template('settings.xml')
    project_template = jinja_env.get_template('project.xml')

def coroutine(func):
    def start(*args, **kwargs):
        cr = func(*args, **kwargs)
        cr.next()
        return cr
    return start
    
class bidict(object):
    
    def __init__(self, d=None):
        d=d or {}
        self.d1 = {}
        self.d2 = {}
        for key, value in d.iteritems():
            self[key] = value
    def __getitem__(self, key):
        try: return self.d1[key]
        except KeyError: return self.d2[key]
                
    def __setitem__(self, key, value):
        self.d1[key] = value
        self.d2[value] = key
    
    def __contains__(self, key):
        return (key in self.d1) or (key in self.d2)
    
    def keys(self, direction=False):
        return self.d1.keys() if not direction else self.d2.keys()
    
    def values(self, direction=False):
        return self.keys(not direction)
    
    def reverse(self):
        self.d1, self.d2 = self.d2, self.d1
        
    def get(self, key, default):
        try:
            return self[key]
        except KeyError:
            return default    
    def iteritems(self, direction=False):
        return self.d1.iteritems() if not direction else self.d2.iteritems()
    
    def pop(self, key):
        try:
            val = self.d1.pop(key)
            self.d2.pop(val)
            return val
        except KeyError:
            val = self.d2.pop(key)
            self.d1.pop(val)
            return val
        
    def __str__(self):
        return 'b' + str(self.d1)
    
class PersistedFrame(wx.Frame):
    
    def __init__(self, *args, **kwargs):
        super(PersistedFrame, self).__init__(*args, **kwargs)
        self.Bind(wx.EVT_CLOSE, self.on_persist)
        import settings
        try:
            (maximized, x, y, width, height) = settings.session_get(str(self.__class__))
            self.SetPosition((x,y))
            self.SetSize((width, height))
            if maximized:
                self.Maximize()
        except Exception, e:
            print "Couldn't load persisted window data: %s" % e
        
    def on_persist(self, evt):
        maximized = self.IsMaximized()
        x,y = self.GetPosition()
        width,height = self.GetSize()
        print (maximized, x, y, width, height)
        import settings
        if not self.IsIconized():
            try:
                settings.session_set(str(self.__class__), (maximized, x, y, width, height))
                settings.save_session()
            except Exception, e:
                print "Couldn't persist window: %s" % e
            finally:
                evt.Skip()
        else:
            evt.Skip()

def get_text(parent, question, title="", default=""):
    dlg = wx.TextEntryDialog(parent,question, title)
    dlg.SetValue(default)
    if dlg.ShowModal() == wx.ID_OK:
        return dlg.GetValue()
    else:
        return None
    dlg.Destroy()
  
def launch(file):
    if os.name == 'posix':
        os.system('xdg-open %s' % file)
    elif os.name == 'nt':
        os.startfile(str(file))
    elif os.name == 'mac':
        os.system('open "%s"' % file)
    else:
        return
    
def shell(path):
    if os.name == 'posix':
        print "Don't know what to do here yet"
    elif os.name == 'nt':
        cmd = 'start cmd /K "cd %s"' % path
        print cmd
        os.system(cmd)
    elif os.name == 'mac':
        print "Don't know what to do here yet."
    else:
        print "Can't handle os %s" % os.name
        
       
def rgb(r,g,b,a=255):
    return wx.Colour(r,g,b,a)

class Updater(object):
    def __init__(self):
        self.__listeners = []
        
    def post_update(self):
        for listener in self.__listener:
            if callable(listener):
                listener(self)
                
class FontEnumerator(wx.FontEnumerator):
    def __init__(self):
        super(FontEnumerator, self).__init__()
        self.fonts = []
        self.EnumerateFacenames(fixedWidthOnly=True)
    def OnFacename(self, name):
        self.fonts.append(name)
        return True
        
def get_fonts():
    fonts = FontEnumerator().fonts
    fonts.sort()
    return fonts
    
def get_font():
    preferred_fonts = [
        'Bitstream Vera Sans Mono',
        'Courier New',
        'Courier',
    ]
    fonts = get_fonts()
    for font in preferred_fonts:
        if font in fonts:
            return font
    return fonts[0] if fonts else None
def menu_item(window, menu, label, func, icon=None, kind=wx.ITEM_NORMAL, toolbar=None, registries=None, enabled=True):
    item = wx.MenuItem(menu, -1, label, kind=kind)
    if func:
        window.Bind(wx.EVT_MENU, func, id=item.GetId())
    if icon:
        item.SetBitmap(get_icon(icon))
        item.SetDisabledBitmap(get_icon('blank.png'))
    menu.AppendItem(item)
    if toolbar and icon:
        tool_item = toolbar.AddSimpleTool(-1, get_icon(icon), label)
        if func:
            window.Bind(wx.EVT_TOOL, func, id=tool_item.GetId())
    if registries != None:
        for registry in registries:
            if item not in registry:
                registry.append(item)
    item.Enable(bool(enabled))
    return item
    
def tool_item(window, toolbar, label, func, icon):
    item = toolbar.AddSimpleTool(-1, get_icon(icon), label)
    if func:
        window.Bind(wx.EVT_TOOL, func, id=item.GetId())
    return item

def button(window, label='', func=None, icon=None, id=-1):
    if icon:
        if isinstance(icon, str): icon = get_icon(icon)
        button = wx.BitmapButton(window, id=id, bitmap=icon)
    else:
        button = wx.Button(window, id, label)
    if func:
        button.Bind(wx.EVT_BUTTON, func)
    return button

def plate_button(window, label='', func=None, icon=None, id=wx.ID_ANY, style=PLATEBTN_DEFAULT_STYLE):
    if os.name == "posix":
        if icon and not label:
            return button(window, '', func, icon, id=wx.ID_ANY)
        else:
            return button(window, label, func, None, id)
    else:
        if icon:
            if isinstance(icon, str): icon=get_icon(icon)
            btn = platebtn.PlateButton(window, id, label=label, bmp=icon, style=style)
        else:
            btn = platebtn.PlateButton(window, id, label=label, style=style)
            btn.SetPressColor(PLATEBTN_DEFAULT_COLOUR)
        if func:
            window.Bind(wx.EVT_BUTTON, func, btn)
        return btn

def checkbox(window, label='', func=None, id=wx.ID_ANY):
    item = wx.CheckBox(window, id=id, label=label)
    if func:
        window.Bind(wx.EVT_CHECKBOX, func)
    return item

def padded(window, padding, sides=wx.ALL):
    sizer = wx.BoxSizer(wx.VERTICAL)
    sizer.Add(window, 1, wx.EXPAND|sides, padding)
    return sizer

def get_icon(file):
    file = 'icons/%s' % file
    return wx.Bitmap(file)

def has_icon(file):
    return os.path.exists('icons/%s' % file)

# Taken from http://code.activestate.com/recipes/302594/

def commonpath(a, b):
    """Returns the longest common to 'paths' path.

    Unlike the strange commonprefix:
    - this returns valid path
    - accepts only two arguments
    """
    a = normpath(normcase(a))
    b = normpath(normcase(b))

    if a == b:
        return a

    while len(a) > 0:
        if a == b:
            return a

        if len(a) > len(b):
            a = dirname(a)
        else:
            b = dirname(b)

    return None

def relpath(target, base_path):
    """
    Return a relative path to the target from either the current directory
    or an optional base directory.

    Base can be a directory specified either as absolute or relative
    to current directory.
    """

    base_path = normcase(abspath(normpath(base_path)))
    target = normcase(abspath(normpath(target)))

    if base_path == target:
        return '.'

    # On the windows platform the target may be on a different drive.
    if splitdrive(base_path)[0] != splitdrive(target)[0]:
        return None

    common_path_len = len(commonpath(base_path, target))

    # If there's no common prefix decrease common_path_len should be less by 1
    base_drv, base_dir = splitdrive(base_path)
    if common_path_len == len(base_drv) + 1:
        common_path_len -= 1

    # if base_path is root directory - no directories up
    if base_dir == os.sep:
        dirs_up = 0
    else:
        dirs_up = base_path[common_path_len:].count(os.sep)

    ret = os.sep.join([os.pardir] * dirs_up)
    if len(target) > common_path_len:
        ret = path_join(ret, target[common_path_len + 1:])

    return ret

class ThreadWorker(threading.Thread):
    def __init__(self, callable, *args, **kwargs):
        super(ThreadWorker, self).__init__()
        self.callable = callable
        self.args = args
        self.kwargs = kwargs
        self.setDaemon(True)

    def run(self):
        try:
            self.callable(*self.args, **self.kwargs)
        except wx.PyDeadObjectError:
            pass
        except Exception, e:
            print "omg exception"
            print e
            raise

class Process(subprocess.Popen):
    def __init__(self, cmd, start=None, stdout=None, stderr=None, end=None, cwd=os.curdir, callafter=False):
        self.start = start
        self.stdout_func = stdout
        self.stderr_func = stderr
        self.end = end
        self.done = False
        self.callafter = callafter
        try:
            #import win32process
            #flags = win32process.CREATE_NEW_PROCESS_GROUP
            flags = 0
        except:
            flags = 0
        super(Process, self).__init__(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, stdin=subprocess.PIPE, cwd=cwd, creationflags = flags)
        if start:
            self.start()


        self.stdoutworker = ThreadWorker(self.monitor_stream, self.stdout_func, self.stdout, end=True)
        self.stderrworker = ThreadWorker(self.monitor_stream, self.stderr_func, self.stderr)

        self.stderrworker.start()
        self.stdoutworker.start()        

    def monitor_stream(self, func, stream, end=False):
        while True:
            try:
                data = stream.readline()
            except IOError, e:
                print e
                break
            if data:
                if self.callafter:
                    wx.CallAfter(func,data)
                else:
                    func(data)
            else:
                self.done = True
                break
        
        if end and self.end:
            wx.CallAfter(self.end)

    def sigint(self):        
        try:
            import win32api, win32con
            win32api.GenerateConsoleCtrlEvent(win32con.CTRL_C_EVENT, self.pid)
        except:
            pass
        
class Event(wx.PyEvent):
    def __init__(self, event_object, type):
        super(Event, self).__init__()
        self.SetEventType(type.typeId)
        self.SetEventObject(event_object)
       
class Category(object):

    def __init__(self, name='', parent=None):
        self.parent = parent
        self.items = odict.OrderedDict()
        self.name = str(name)
        self.__modified = False
    
    def __contains__(self, item):
        return item in self.items
    
    def reset(self):
        self.modified = False

    def __get_modified(self):
        return self.__modified

    def __set_modified(self, x):
        if x: # If modified, all our ancestors should be modified
            if self.parent:
                self.parent.modified = True
            self.__modified = True
        else: # If not modified, all our children should be not modified
            for item in self:
                if isinstance(item, Category):
                    item.modified = False
            self.__modified = False
    modified = property(__get_modified, __set_modified)
        
    def __getattr__(self, attr):
        try:
            return self.items[str(attr)]
        except KeyError:
            raise AttributeError(attr)
       
    def __getitem__(self, idx):
        names = idx.split(".")
        if len(names) == 1:
            return self.items[idx]
        else:
            next = self.items[names[0]]
            return next[".".join(names[1:])]

    def __setitem__(self, idx, val):
        names = idx.split(".")
        if len(names) == 1:
            self.items[idx] # Force a KeyError if not already a member
            self.items[idx] = val
            self.modified = True
        else:
            next = self.items[names[0]]
            next[".".join(names[1:])] = val
    
    def add_category(self, name):
        if name in self:
            raise ProjectError("Already a category called '%s'" % name)
        newcat = Category(name, parent=self)
        self.add_item(name, newcat)
        self.modified = True
        return newcat
    
    def add_item(self, key, value):
        self.items[key] = value
        self.modified = True
        
    def walk(self):
        for key, item in self:
            if isinstance(item, Category):
                for subitem in item.walk():
                    yield subitem
            else:
                yield item
                
    def __iter__(self):
        return iter(self.items.iteritems())

    def __str__(self):
        return "<Category '%s' : %s>" % (self.name, self.items)
    def __repr__(self):
        return str(self)

    def __get_children(self):
        return self.items.keys()
    children = property(__get_children)
    
def readable_files_in_directory(dir):
    files = os.listdir(dir)
    retval = []
    for file in files:
        full_path = os.path.join(dir, file)
        if os.path.isfile(full_path) and os.access(full_path, os.F_OK | os.R_OK):
            retval.append(full_path)
    return retval
        
                                                    
def pickle_file(data, path):
    # Safe pickling functions courtesy of mike!
    tmp_path = '%s.tmp' % path
    bak_path = '%s.bak' % path
    # Write tmp file
    with open(tmp_path, 'wb') as file:
        pickle.dump(data, file, -1)
    # Copy existing file to bak file
    try:
        os.remove(bak_path)
    except Exception:
        pass
    try:
        os.rename(path, bak_path)
    except Exception:
        pass
    # Rename tmp file to actual file
    os.rename(tmp_path, path)
    # Remove bak file
    try:
        os.remove(bak_path)
    except Exception:
        pass
        

def unpickle_file(path):
    tmp_path = '%s.tmp' % path
    bak_path = '%s.bak' % path
    for p in (path, bak_path, tmp_path):
        try:
            with open(p, 'rb') as file:
                return pickle.load(file)
        except Exception:
            pass
    raise Exception('Unable to load: %s' % path)

def human_size(size_in_bytes):
    K = 1024
    M = K*1024
    G = M*1024
    if size_in_bytes < K:
        return "%d Bytes" % size_in_bytes
    elif size_in_bytes < M:
        return "%0.1f kB" % (size_in_bytes/float(K))
    elif size_in_bytes < G:
        return "%0.1f MB" % (size_in_bytes/float(M))
    else:
        return "%0.1f GB" % (size_in_bytes/float(G))
    
class ArtListMixin(object):
    def __init__(self, *args, **kwargs):
        self.__art = {}
        self.__image_list = wx.ImageList(16,16)
        self.__args = args
        self.__kwargs = kwargs
    
    def get_art(self):
        return self.__art
    art = property(get_art)
    
    def clear_art(self):
        self.__art = {}
        self.__image_list = wx.ImageList(16,16)
        self.SetImageList(self.image_list) 
    
    def get_art(self, name):
        il = self.GetImageList(*self.__args, **self.__kwargs)
        return il.GetBitmap(self.__art[name])
        
    def get_art_idx(self, name):
        return self.__art[name]
    
    def add_art(self, *arts):
        for art in arts:
            if art not in self.__art:
                self.__art[art] = self.__image_list.Add(get_icon(art))
        self.SetImageList(self.__image_list, *self.__args, **self.__kwargs)

class TreeItemKey(object):
    def __init__(self, parent):
        self.parent = parent
        
    def is_ok(self):
        return self in self.parent._items

class KeyTree(object):
    def __init__(self):
        self._items = {}
            
    def append_item(self, parent_key, name):
        try:
            parent = self._items[parent_key]
            item = self.AppendItem(parent, name)
            key = TreeItemKey(self)
            self._items[key] = item
            self.SetItemPyData(item, (key, None))
        except Exception, e:
            print "There was a problem appending item:"
            print e
            print parent_key
            print name
            
            
        return key
    
    def hit_test(self, pos):
        item, flags = self.HitTest(pos)
        if item.IsOk():
            return self.get_key(item), flags
        else:
            return TreeItemKey(), flags
    '''
    def walk(self, key):
        first, cookie = self.get_first_child(key)
        if first.is_ok(): 
            yield first
            next, cookie = self.get_next_child(key, cookie)
            while next.is_ok(): 
                for child in self.walk(next): yield child
                yield next
                next, cookie = self.get_next_child(key, cookie)
    '''
    
    def walk(self, top_item, include_root=True):
        retval = [top_item] if include_root else []
        child, cookie = self.get_first_child(top_item)
        while child.is_ok():
            retval.extend(self.walk(child))
            child, cookie = self.get_next_child(top_item, cookie)
        return retval
        
    def walk_expanded(self, top_item, include_root=True):
        if self.get_children_count(top_item) == 0:
            yield top_item
        else:
            if self.is_expanded(top_item):
                for child in self.children(top_item):
                    for item in self.walk_expanded(child, include_root=True):
                        yield item
        if include_root:
            yield top_item
        
    def get_parent(self, key):
        item = self._items[key]
        item = self.GetItemParent(item)
        if item.IsOk():
            return self.get_key(item)
        else:
            return TreeItemKey(self)
    
    def is_descendent(self, child_key, parent_key):
        parent = self.get_parent(child_key)
        while parent.is_ok():
            if parent == parent_key:
                return True
            parent = self.get_parent(parent)
        return False
    
    def is_expanded(self, key):
        item = self._items[key]
        return self.IsExpanded(item)
    
    def get_first_child(self, key):
        item = self._items[key]
        i, cookie = self.GetFirstChild(item)
        if i.IsOk():
            return self.get_key(i), cookie
        else:
            return TreeItemKey(self), cookie # Return a key that's NOT ok
        
    def get_next_child(self, key, cookie):
        item = self._items[key]
        i, cookie = self.GetNextChild(item, cookie)
        if i.IsOk():
            return self.get_key(i), cookie
        else:
            return TreeItemKey(self), cookie
        
    def children(self, key):
        child, cookie = self.get_first_child(key)
        while child.is_ok():
            yield child
            child, cookie = self.get_next_child(key, cookie)
            
    def get_children_count(self, key, recursive=True):
        item = self._items[key]
        return self.GetChildrenCount(item, recursive)
        
    def get_key(self, item):
        if item.IsOk():
            return self.GetItemPyData(item)[0]
        else:
            raise KeyError
        
    def get_event_item(self, evt):
        return self.get_key(evt.GetItem())
    
    def get_item_data(self, key):
        item = self._items[key]
        return self.GetItemPyData(item)[1]

    def get_item_text(self, key, col):
        item = self._items[key]
        return self.GetItemText(item, col)
    
    def set_item_data(self, key, data):
        item = self._items[key]
        key, old_data = self.GetItemPyData(item)
        self.SetItemPyData(item, (key, data))
        
    def set_item_image(self, key, image, style=wx.TreeItemIcon_Normal):
        item = self._items[key]
        self.SetItemImage(item, image, style)
        
    def set_item_has_children(self, key, has_children):
        item = self._items[key]
        self.SetItemHasChildren(item, has_children)
    
    def set_item_text(self, key, text, column=0):
        try:
            item = self._items[key]
        except:
            print "couldn't set item text."
            print key
            print text
            print self._items
            return
        self.SetItemText(item, text, column)
        
    def set_item_bold(self, key, bold):
        item = self._items[key]
        self.SetItemBold(item, bold)

    def set_item_text_colour(self, key, colour):
        item = self._items[key]
        self.SetItemTextColour(item, colour)
        
    def add_root(self, name):
        item = self.AddRoot(name)
        key = TreeItemKey(self)
        self._items[key] = item
        self.SetItemPyData(item, (key, None))
        return key
    
    def delete(self, key):
        item = self._items[key]
        if self.get_children_count(key) > 0:            
            for child in list(self.children(key)):
                self.delete(child)
        
        item = self._items.pop(key)
        self.Delete(item)
                    
    
    def delete_children(self, key):
        item = self._items[key]
        to_be_removed = list(self.children(key))
        self.DeleteChildren(item)
        for key in to_be_removed:
            self._items.pop(key)
    
    def collapse(self, key):
        item = self._items[key]
        self.Collapse(item)

    def expand(self, key):
        item = self._items[key]
        self.Expand(item)
                
    def select_item(self, key):
        item = self._items[key]
        self.SelectItem(item)

import os
bindings = {
        '.c': 'file_c.png',        
        '.s': 'file_s.png',
        '.ld': 'file_link.png',
        '.cmd': 'file_link.png',
        '.bz2': 'file_archive.png',
        '.gz': 'file_archive.png',
        '.zip': 'file_archive.png',
        '.tar': 'file_archive.png',
        '.ini': 'file_wrench.png',
        '.cfg': 'file_wrench.png',
        '.py': 'file_py.png',
        '.h': 'file_h.png',
        '.png': 'file_picture.png',
        '.jpg': 'file_picture.png',
        '.gif': 'file_picture.png',
        '.tif': 'file_picture.png',
        '.tiff': 'file_picture.png',
        '.sh': 'file_gear.png',
        '.script': 'file_gear.png', 
        '.xml' : 'file_markup.png',
        '.html' : 'file_world.png',
        '.htm' : 'file_world.png',
        '.xhtml' : 'file_world.png',
        '.sgml' : 'file_markup.png',
        '.pdf': 'file_acrobat.png',
        '.java' : 'file_java.png',
        '.doc': 'file_word.png' ,
        '.rtf': 'file_word.png' }

def get_file_icon(filename):
    ext = ""
    try:
        file = os.path.split(filename)[1]
        if file.strip().lower() == "makefile":
            return "file_gear.png"
        fn, ext = os.path.splitext(file)
        return bindings.get(ext.lower(), 'file_white.png')
    except:
        return 'file_white.png'
