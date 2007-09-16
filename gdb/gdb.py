import wx
import os, threading, time, logging
import antlr3, GDBMILexer, GDBMIParser
import util, odict

def escape(s):
    return s.replace("\\", "\\\\")

class GDBEvent(wx.PyEvent):
    def __init__(self, type, object=None, data=None):
        super(GDBEvent, self).__init__()
        self.SetEventType(type.typeId)
        self.SetEventObject(object)
        self.data = data


EVT_GDB_STARTED = wx.PyEventBinder(wx.NewEventType())
EVT_GDB_FINISHED = wx.PyEventBinder(wx.NewEventType())

EVT_GDB_ERROR = wx.PyEventBinder(wx.NewEventType())
EVT_GDB_UPDATE = wx.PyEventBinder(wx.NewEventType())

EVT_GDB_UPDATE_BREAKPOINTS = wx.PyEventBinder(wx.NewEventType())
#EVT_GDB_EXECUTE_UPDATE
#EVT_GDB_LOCALS_UPDATE
#EVT_GDB_MEMORY_UPDATE

EVT_GDB_RUNNING = wx.PyEventBinder(wx.NewEventType())
EVT_GDB_STOPPED = wx.PyEventBinder(wx.NewEventType())

class GDB(wx.EvtHandler):

    def __init__(self, cmd="arm-elf-gdb -n -q -i mi", mi_log=None, console_log=None, target_log=None, log_log=None):
        wx.EvtHandler.__init__(self)
        self.attached = False
        
        # Console streams
        self.mi_log = mi_log
        self.console_log = console_log
        self.target_log = target_log
        self.log_log = log_log

        # Parser for GDBMI commands
        self.cmd = cmd

    def start(self):
        self.__clear()
        self.subprocess = util.Process(self.cmd, start=self.on_start, stdout=self.on_stdout, end=self.on_end)

    def __clear(self):
        self.buffer = ''
        self.pending = {} # Pending commands
        self.token = 1    # Command token (increments on each command
        self.breakpoints = BreakpointTable(self)
        self.__lexer = GDBMILexer.GDBMILexer(None)
        self.__parser = GDBMIParser.GDBMIParser(None)
        
    def __parse(self, string):
        '''
        Parse a SINGLE gdb-mi response, returning a GDBMIResponse object
        '''
        stream = antlr3.ANTLRStringStream(unicode(string))
        self.__lexer.setCharStream(stream)
        tokens = antlr3.CommonTokenStream(self.__lexer)
        self.__parser.setTokenStream(tokens)
        output = self.__parser.output().response
        return output

    def __console_log(self, txt):
        if self.console_log:
            self.console_log.log(logging.INFO,txt )

    def __target_log(self, txt):
        if self.target_log:
            self.target_log.log(logging.INFO, txt)
    
    def __log_log(self, txt):
        if self.log_log:
            self.log_log.log(logging.INFO, txt )
   
    def __mi_log(self, txt):
        if self.mi_log:
            self.mi_log.log(logging.INFO, txt)

    def on_start(self):
        self.attached = True
        self.post_event(GDBEvent(EVT_GDB_STARTED, self))
    
    def on_end(self):
        self.attached = False
        self.post_event(GDBEvent(EVT_GDB_FINISHED, self))

    def on_stdout(self, line):
        self.__mi_log(line)
        self.buffer += line
        if line.strip() == '(gdb)':
            response = self.__parse(self.buffer)
            self.handle_response(response)
            self.buffer = ''

    def handle_response(self, response):
        # Deal with the console streams in the response
        for txt in response.console:
            self.__console_log(txt)
        for txt in response.target:
            self.__target_log(txt)
        for txt in response.log:
            self.__log_log(txt)

        results = (response.result, response.exc, response.status, response.notify)
        for result in results:
            if result != None: 
                if result.token:
                    # Call any function setup to be called as a result of this.... result.
                    if result.token in self.pending:
                        callback, internal_callback = self.pending[result.token]
                        if callable(internal_callback):
                            internal_callback(result)
                        if callable(callback):
                            callback(result)
                        
                # Post an event on error
                if result.cls == 'error':
                    self.post_event(GDBEvent(EVT_GDB_ERROR, self, data=result.msg))
                elif result.cls == 'stopped':
                    self.post_event(GDBEvent(EVT_GDB_STOPPED, self, data=result))
                    self.__update_breakpoints()
                elif result.cls == 'running':
                    self.post_event(GDBEvent(EVT_GDB_RUNNING, self, data=result))
                else:
                    self.post_event(GDBEvent(EVT_GDB_UPDATE, self, data=result))

    def __update_breakpoints(self, data=None):
        self.__cmd('-break-list\n', self.__process_breakpoint_update)
    def __process_breakpoint_update(self, data):
        print data
        if hasattr(data, 'BreakpointTable'):
            self.breakpoints.clear()
            for item in data.BreakpointTable.body:
                item = item.get('bkpt', None)
                if item:
                    number = int(item['number'])
                    address = int(item['addr'], 16)
                    fullname = item.get('fullname', '<Unknown File>')
                    enabled = True if (item['enabled'].upper() == 'Y' or item['enabled'] == '1') else False
                    line = int(item.get('line', -1))
                    bp = Breakpoint(number, fullname, line, enabled=enabled, address=address)
                    self.breakpoints[number] = bp
        wx.PostEvent(self, GDBEvent(EVT_GDB_UPDATE_BREAKPOINTS, self, data=self.breakpoints))
                
    def post_event(self, evt):
        wx.PostEvent(self, evt)
    
    def __send(self, data):
        self.__mi_log(data)
        self.subprocess.stdin.write(data)

    def __cmd(self, cmd, callback=None, internal_callback=None):
        if cmd[-1] != '\n':
            cmd += '\n'
        if callback:
            self.__send(str(self.token) + cmd)
            self.pending[self.token] = (callback, internal_callback)
            self.token += 1
        else:
            self.__send(cmd)

    # Utility Stuff
    def command(self, cmd, callback=None):
        self.__cmd('-interpreter-exec console "%s"' % cmd, callback)
   
    def stack_list_locals(self, callback=None):
        self.__cmd('-stack-list-locals 1', callback)

    def file_list_globals(self, file='', callback=None):
        self.__cmd('-symbol-list-variables', callback)

    def exec_continue(self, callback=None):
        self.__cmd('-exec-continue\n', callback)

    def exec_step(self, callback=None):
        self.__cmd('-exec-step\n', callback)
   
    def exec_finish(self, callback=None):
        self.__cmd('-exec-finish\n', callback)
   
    def exec_until(self, file, line, callback=None):
        line = int(line)
        file = str(file)
        self.__cmd('-exec-until %s:%d\n' % (file, line), callable)

    def exec_interrupt(self, callable=None):
        self.__cmd('-exec-interrupt\n', callable)

    def target_download(self, callback=None):
        self.__cmd('-target-download\n', callback)

    def sig_interrupt(self):
        self.sigint()
        
    def quit(self):
        self.__cmd('-gdb-exit\n')
    
    def read_memory(self, start_addr, stride, count, callback=None):
        self.__cmd('-data-read-memory 0x%x u %d %d 1\n' % (start_addr, stride, count), callback)
        
    def break_list(self, callback=None):
        self.__cmd('-break-list\n', callback)

    def get_register_names(self):
        self.command('-data-list-register-names')
        
    def break_insert(self, file, line, hardware=False, temporary=False, callback=None):
        self.__cmd('-break-insert %s %s %s:%d' % ("-h" if hardware else "", "-t" if temporary else "", os.path.normpath(file), line), callback=callback, internal_callback=self.__update_breakpoints)
        
#    def break_insert(self, file, line, hardware=False, temporary=False,  callback=None, *args, **kwargs):
#        self.__cmd('-break-insert %s %s %s:%d' % ("-h" if hardware else "", "-t" if temporary else "", os.path.normpath(file), line), callback, *args, **kwargs)
        
    def break_delete(self, num, callback=None):
        self.__cmd("-break-delete %d" % int(num), callback, internal_callback=self.__update_breakpoints)

    def break_disable(self, num, callback=None):
        self.__cmd("-break-disable %d" % int(num), callback, internal_callback=self.__update_breakpoints)

    def break_enable(self, num, callback=None):
        self.__cmd("-break-enable %d" % int(num), callback, internal_callback=self.__update_breakpoints)
        
    # Set Executable
    def set_exec(self, file):
        self.__cmd('-file-exec-and-symbols "%s"\n' % escape(file))


    def OnTerminate(self, *args, **kwargs):
        self.post_event(GDBEvent(EVT_GDB_FINISHED, self))


class BreakpointTable(object):
    def __init__(self, parent):
        self.breakpoints = odict.OrderedDict()
        self.parent = parent
        
    def __setitem__(self, key, bp):
        self.breakpoints[int(key)] = bp
        
    def __str__(self):
        return '\n'.join([str(self.breakpoints[num]) for num in sorted(self.breakpoints)])
        
    def clear(self):
        self.breakpoints = {}
    
    def __iter__(self):
        return iter([self.breakpoints[key] for key in sorted(self.breakpoints.keys())])
    
class Breakpoint(object):
    
    def __init__(self, number, fullname, line, enabled=True, address=None):
        self.number = number
        self.line = line
        self.fullname = fullname
        self.enabled = enabled
        self.address = address
        
    def __str__(self):
        return "%s[%d]%s%d" % ('+' if self.enabled else ' ', self.number, self.fullname, self.line) 
        
