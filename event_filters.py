from qgis.PyQt.QtCore import QObject, QEvent, pyqtSignal
from qgis.utils import iface


class KeypressEmitter(QObject):
    signal = pyqtSignal(int)

class KeypressFilter(QObject):
    def __init__(self, emitter):
        super(KeypressFilter, self).__init__()
        self.emitter = emitter

    def eventFilter(self, obj, event):
        """
        obj : QObject whose event is intercepted
        event: QEvent received

        returns:
            bool
        """
        if event.type() == QEvent.KeyRelease:
            self.emitter.signal.emit(event.key())
            return True
        return False

class KeypressShortcut:
    """
    Supports functions as either strings that will be evaluated or callables with dynamic arguments
    Supports function with arguments of the following types -> function without args, string, int, float
    """
    def __init__(self, shortcut_dict):
        # Any Keyboard shortcut should have the following
        self.function = shortcut_dict.get("function", None)
        self.function_args = shortcut_dict.get("function_args", [])
        self.key_code = shortcut_dict.get("key_code", None)
        self.name = shortcut_dict.get("name", None)
        self.shortcut_type = shortcut_dict.get("shortcut_type", None)

        self.callable_string = None
        self.generate_callable_string()

    def generate_callable_string(self):
        # Generate a string from the given arguments
        args_string = ""
        for i in range(len(self.function_args)):
            arg = self.function_args[i]
            # If there are callables in the function args, add method to call them before eval
            if callable(arg):
                args_string += arg.__qualname__ + "(), "
            # If there is a string in the args, add quotes around it
            elif isinstance(arg, type("str")):
                args_string += "'{}'".format(arg) + ","
            # Else convert arg to string
            else:
                args_string += str(arg) + ","

        if self.function_args:
            self.callable_string = "self.function({})".format(args_string)

    def run(self):
        if not self.function:
            return None
        if self.callable_string:
            eval(self.callable_string)
        elif isinstance(self.function, type("str")):
            eval(self.function)
        else:
            self.function()
