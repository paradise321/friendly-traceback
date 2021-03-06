"""
console.py
==========

Adaptation of Python's console found in code.py so that it can be
used to show some "friendly" tracebacks.
"""
import builtins
import copy
import os
import platform
import traceback
from code import InteractiveConsole
import codeop  # need to import to exclude from tracebacks

import friendly_traceback

from . import source_cache
from .my_gettext import current_lang

from . import friendly_rich
from .config import session
from . import info_generic
from .path_info import path_utils

BANNER = "\nFriendly Console version {}. [Python version: {}]\n".format(
    friendly_traceback.__version__, platform.python_version()
)

please_comment = (
    "   Do you find these warnings useful?\n"
    "   Comment at https://github.com/aroberge/friendly-traceback/issues/112"
)


def _quote(text):
    """Surrounds text by single quote, or by backquote if formatter
    is markdown type.
    """
    return session.quote(text)


class FriendlyConsole(InteractiveConsole):
    def __init__(self, locals=None, use_rich=False, theme="dark"):
        """This class builds upon Python's code.InteractiveConsole
        so as to provide friendly tracebacks. It keeps track
        of code fragment executed by treating each of them as
        an individual source file.
        """
        _ = current_lang.translate
        friendly_traceback.exclude_file_from_traceback(codeop.__file__)
        self.fake_filename = "<friendly-console:%d>"
        self.counter = 1
        self.old_locals = {}
        self.saved_builtins = {}
        for name in dir(builtins):
            self.saved_builtins[name] = getattr(builtins, name)
        self.rich_console = False
        if friendly_rich.rich_available and use_rich:
            self.rich_console = friendly_rich.init_console(theme)
        elif use_rich:
            print(_("\n    Rich is not installed.\n\n"))

        super().__init__(locals=locals)
        self.check_for_builtins_changes()
        self.check_for_annotations()

    def push(self, line):
        """Push a line to the interpreter.

        The line should not have a trailing newline; it may have
        internal newlines.  The line is appended to a buffer and the
        interpreter's runsource() method is called with the
        concatenated contents of the buffer as source.  If this
        indicates that the command was executed or invalid, the buffer
        is reset; otherwise, the command is incomplete, and the buffer
        is left as it was after the line was appended.  The return
        value is True if more input is required, False if the line was dealt
        with in some way (this is the same as runsource()).
        """
        self.buffer.append(line)
        source = "\n".join(self.buffer)

        # Each valid code sample is saved with its own fake filename.
        # They are numbered consecutively to help understanding
        # the traceback history.
        # If self.counter was not updated, it means that the previous
        # code sample was not valid and we reuse the same file name
        filename = self.fake_filename % self.counter
        source_cache.cache.add(filename, source)

        more = self.runsource(source, filename)
        if not more:
            self.resetbuffer()
            self.counter += 1
        return more

    def runsource(self, source, filename="<input>", symbol="single"):
        """Compile and run some source in the interpreter.

        Arguments are as for compile_command().

        One several things can happen:

        1) The input is incorrect; compile_command() raised an
        exception (SyntaxError or OverflowError).  A syntax traceback
        will be printed .

        2) The input is incomplete, and more input is required;
        compile_command() returned None.  Nothing happens.

        3) The input is complete; compile_command() returned a code
        object.  The code is executed by calling self.runcode() (which
        also handles run-time exceptions, except for SystemExit).

        The return value is True in case 2, False in the other cases (unless
        an exception is raised).  The return value can be used to
        decide whether to use sys.ps1 or sys.ps2 to prompt the next
        line.
        """
        try:
            code = self.compile(source, filename, symbol)
        except (OverflowError, SyntaxError, ValueError):
            # Case 1
            friendly_traceback.explain_traceback()
            return False

        if code is None:
            # Case 2
            return True

        # Case 3
        self.runcode(code)
        return False

    def runcode(self, code):
        """Execute a code object.

        When an exception occurs, friendly_traceback.explain_traceback() is called to
        display a traceback.  All exceptions are caught except
        SystemExit, which, unlike the case for the original version in the
        standard library, cleanly exists the program. This is done
        so as to avoid our Friendly-traceback's exception hook to intercept
        it and confuse the users.

        A note about KeyboardInterrupt: this exception may occur
        elsewhere in this code, and may not always be caught.  The
        caller should be prepared to deal with it.
        """
        _ = current_lang.translate
        try:
            exec(code, self.locals)
        except SystemExit:
            os._exit(1)
        except Exception:
            try:
                friendly_traceback.explain_traceback()
            except Exception:
                print("Friendly-traceback Internal Error")
                print("-" * 60)
                traceback.print_exc()
                print("-" * 60)

        self.check_for_builtins_changes()
        self.check_for_annotations()
        self.old_locals = copy.copy(self.locals)

    def check_for_annotations(self):
        """Attempts to detect code that uses : instead of = by mistake"""
        _ = current_lang.translate
        if "__annotations__" not in self.locals:
            return

        hints = self.locals["__annotations__"]
        if not hints:
            return

        warning_builtins = _(
            "Warning: you added a type hint to the python builtin {name}."
        )
        header_warning = _(
            "Warning: you used a type hint for a variable without assigning it a value.\n"
        )
        suggest_str = _("Instead of {hint}, perhaps you meant {assignment}.")

        for name in hints:
            warning = ""
            if name in dir(builtins):
                warning = warning_builtins.format(name=_quote(name))
                if self.rich_console:
                    warning = "#### " + warning
                    warning = friendly_rich.Markdown(warning)
                    self.rich_console.print(warning)
                    self.rich_console.print(please_comment)
                else:
                    print(warning)
                    print(please_comment)

        wrote_title = False
        warning = ""

        for name in hints:
            if name in dir(builtins):  # Already taken care of these above
                continue
            if (
                name not in self.locals
                or name in self.old_locals
                and self.old_locals[name] == self.locals[name]
            ):
                if not wrote_title:
                    warning = header_warning
                    wrote_title = True
                    if self.rich_console:
                        warning = "#### " + warning
                if not str(f"{hints[name]}").startswith("<"):
                    suggest = suggest_str.format(
                        hint=_quote(f"{name} : {hints[name]}"),
                        assignment=_quote(f"{name} = {hints[name]}"),
                    )
                else:
                    suggest = ""
                if self.rich_console and suggest:
                    suggest = "* " + suggest
                if suggest:
                    warning = warning + suggest + "\n"

        if warning:
            if self.rich_console:
                warning = friendly_rich.Markdown(warning)
                self.rich_console.print(warning)
                self.rich_console.print(please_comment)
            else:
                print(warning)
                print(please_comment)

            self.locals["__annotations__"] = {}

    def check_for_builtins_changes(self):
        """Warning users if they assign a value to a builtin"""
        _ = current_lang.translate
        changed = []
        for name in self.saved_builtins:
            if name.startswith("__") and name.endswith("__"):
                continue

            if (
                name == "pow"
                and "cos" in self.locals
                and "cosh" in self.locals
                and "pi" in self.locals
            ):
                # we likely did 'from math import *' which redefines pow;
                # no warning needed in this case
                continue
            if name in self.locals and self.saved_builtins[name] != self.locals[name]:
                warning = _(
                    "Warning: you have redefined the python builtin {name}."
                ).format(name=_quote(name))
                if self.rich_console:
                    warning = friendly_rich.Markdown("#### " + warning)
                    self.rich_console.print(warning)
                    self.rich_console.print(please_comment)
                else:
                    print(warning)
                    print(please_comment)
                changed.append(name)

        for name in changed:
            self.saved_builtins[name] = self.locals[name]

    # The following two methods are never used in this class, but they are
    # defined in the parent class. The following are the equivalent methods
    # that can be used if an explicit call is desired for some reason.

    def showsyntaxerror(self, filename=None):
        friendly_traceback.explain_traceback()

    def showtraceback(self):
        friendly_traceback.explain_traceback()

    def raw_input(self, prompt=""):
        """Write a prompt and read a line.
        The returned line does not include the trailing newline.
        When the user enters the EOF key sequence, EOFError is raised.
        The base implementation uses the built-in function
        input(); a subclass may replace this with a different
        implementation.
        """
        if self.rich_console:
            return self.rich_console.input("[bold #009999]" + prompt)
        return input(prompt)


# ============================================
#
# Functions defined to be used in the console
#
# ============================================


def explain(include="explain"):
    """Shows the previously recorded traceback info again,
    with the specified verbosity level.
    """
    old_include = friendly_traceback.get_include()
    friendly_traceback.set_include(include)
    session.show_traceback_info_again()
    friendly_traceback.set_include(old_include)


def _info():
    """Debugging tool: shows the complete content of traceback info."""
    if session.saved_traceback_info is None:
        print("No recorded traceback\n")
        return
    print("Recorded traceback information:\n")
    if session.use_rich:  # will automatically pretty print
        return session.saved_traceback_info

    for item in session.saved_traceback_info:
        print(f"{item}: {session.saved_traceback_info[item]}")


def more():
    """Used to display information additional to the minimal traceback,
    with the exception of the generic information.
    Potentially useful for advanced users.
    """
    explain("more")


def what(exception=None, lang="en", pre=False):
    """If known, shows the generic explanation about a given exception."""

    if exception is not None:
        if hasattr(exception, "__name__"):
            exception = exception.__name__
        if lang is not None:
            old_lang = friendly_traceback.get_lang()
            friendly_traceback.set_lang(lang)
        result = info_generic.get_generic_explanation(exception)
        if lang is not None:
            friendly_traceback.set_lang(old_lang)
        if pre:  # for documentation
            lines = result.split("\n")
            for line in lines:
                session.write_err("    " + line + "\n")
            session.write_err("\n")
        else:
            session.write_err(result)
        return

    explain("what")


def where():
    """Shows the information about where the exception occurred"""
    explain("where")


def why():
    """Shows the likely cause of the exception."""
    explain("why")


def hint():
    """Shows hint/suggestion if available."""
    explain("hint")


def friendly_tb():
    """Shows the friendly traceback, which includes the hint/suggestion
    if available.
    """
    explain("friendly_tb")


def python_tb():
    """Shows the Python traceback, excluding files from friendly-traceback
    itself.
    """
    explain("python_tb")


def debug_tb():
    """Shows the true Python traceback, which includes
    files from friendly-traceback itself.
    """
    explain("debug_tb")


def debug():
    """This functions displays the true traceback recorded, that
    includes friendly-traceback's own code.
    It also adds the suggestion/hint from friendly-traceback
    and sets a debug flag for the current session.
    """
    session._debug = True
    explain("debug_tb")


def start_console(
    local_vars=None,
    use_rich=False,
    include="friendly_tb",
    lang="en",
    banner=None,
    theme="dark",
):
    """Starts a console; modified from code.interact"""
    from . import config

    if banner is None:
        banner = BANNER
    if theme != "light":
        theme = "dark"
    if use_rich:
        config.session.set_formatter("rich", theme=theme)

    console_defaults = {
        "explain": explain,
        "what": what,
        "where": where,
        "why": why,
        "more": more,
        "get_lang": friendly_traceback.get_lang,
        "set_lang": friendly_traceback.set_lang,
        "get_include": friendly_traceback.get_include,
        "set_include": friendly_traceback.set_include,
        "hint": hint,
        "friendly_tb": friendly_tb,
        "python_tb": python_tb,
        "debug_tb": debug_tb,
        "debug": debug,
        "show_paths": path_utils.show_paths,
        "_info": _info,
    }
    if not friendly_traceback.is_installed():
        friendly_traceback.install(include=include, lang=lang)
    if local_vars is None:
        local_vars = console_defaults
    else:
        local_vars.update(console_defaults)

    console = FriendlyConsole(locals=local_vars, use_rich=use_rich, theme=theme)
    console.interact(banner=banner)
