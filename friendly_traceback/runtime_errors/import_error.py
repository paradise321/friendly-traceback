"""Getting specific information for ImportError"""

import re
import sys

from ..my_gettext import current_lang
from ..utils import get_similar_words
from ..path_info import path_utils


def get_cause(value, info, frame):
    _ = current_lang.translate

    message = str(value)

    # Python 3.8+
    pattern1 = re.compile(
        r"cannot import name '(.*)' from partially initialized module '(.*)'"
    )
    match = re.search(pattern1, message)
    if match:
        if "circular import" in message:
            return cannot_import_name_from(
                match.group(1), match.group(2), info, frame, add_circular_hint=False
            )
        return cannot_import_name_from(match.group(1), match.group(2), info, frame)

    # Python 3.7+
    pattern2 = re.compile(r"cannot import name '(.*)' from '(.*)'")
    match = re.search(pattern2, message)
    if match:
        return cannot_import_name_from(match.group(1), match.group(2), info, frame)

    # Python 3.6
    pattern3 = re.compile(r"cannot import name '(.*)'")
    match = re.search(pattern3, message)
    if match:
        return cannot_import_name(match.group(1), info, frame)

    return _(
        "No information is known about this exception.\n"
        "Please report this example to\n"
        "https://github.com/aroberge/friendly-traceback/issues\n"
    )


def cannot_import_name_from(name, module, info, frame, add_circular_hint=True):
    _ = current_lang.translate

    circular_info = find_circular_import(module, info)
    if circular_info and add_circular_hint:
        info["suggest"] = _("You have a circular import.\n")
        # Python 3.8+ adds a similar hint on its own.

    cause = _(
        "The object that could not be imported is `{name}`.\n"
        "The module or package where it was \n"
        "expected to be found is `{module}`.\n"
    ).format(name=name, module=module)

    if circular_info:
        return cause + "\n" + circular_info
    elif not add_circular_hint:
        return (
            cause
            + "\n"
            + _(
                "Python indicated that you have a circular import.\n"
                "This can occur if executing the code in module 'A'\n"
                "results in executing the code in module 'B' where\n"
                "an attempt to import a name from module 'A' is made\n"
                "before the execution of the code in module 'A' had been completed.\n"
            )
        )

    try:
        mod = sys.modules[module]
    except Exception:
        return cause
    similar = get_similar_words(name, dir(mod))
    if not similar:
        return cause

    if len(similar) == 1:
        info["suggest"] = _("Did you mean `{name}`?\n").format(name=similar[0])
        return _(
            "Perhaps you meant to import `{correct}` (from `{module}`) "
            "instead of `{typo}`\n"
        ).format(correct=similar[0], typo=name, module=module)
    else:
        # transform ['a', 'b', 'c'] in "[`a`, `b`, `c`]"
        candidates = ["{c}".format(c=c.replace("'", "")) for c in similar]
        candidates = ", ".join(candidates)
        info["suggest"] = _("Did you mean one of the following: `{names}`?\n").format(
            names=candidates
        )
        return _(
            "Instead of trying to import `{typo}` from `{module}`, \n"
            "perhaps you meant to import one of \n"
            "the following names which are found in module `{module}`:\n"
            "`{candidates}`\n"
        ).format(candidates=candidates, typo=name, module=module)

    return _(
        "The object that could not be imported is `{name}`.\n"
        "The module or package where it was \n"
        "expected to be found is `{module}`.\n"
    ).format(name=name, module=module)


def cannot_import_name(name, info, frame):
    # Python 3.6 does not give us the name of the module
    _ = current_lang.translate
    pattern = re.compile(r"from (.*) import")
    match = re.search(pattern, info["bad_line"])
    if match:
        return cannot_import_name_from(name, match.group(1), info, frame)

    return _("The object that could not be imported is `{name}`.\n").format(name=name)


def find_circular_import(name, info):
    """This attempts to find circular imports."""
    _ = current_lang.translate

    pattern_file = re.compile(r'^File "(.*)", line', re.M)
    pattern_from = re.compile(r"^from (.*) import", re.M)
    pattern_import = re.compile(r"^import (.*)", re.M)
    modules_imported = []
    tb_lines = info["simulated_python_traceback"].split("\n")
    current_file = ""
    for line in tb_lines:
        line = line.strip()
        match_file = re.search(pattern_file, line)
        match_from = re.search(pattern_from, line)
        match_import = re.search(pattern_import, line)

        if match_file:
            current_file = path_utils.shorten_path(match_file.group(1))
        elif match_from or match_import:
            if match_from:
                modules_imported.append((current_file, match_from.group(1)))
            else:
                module = match_import.group(1)
                if "," in module:  # multiple modules imported on same line
                    modules = module.split(",").replace("(", "").strip()
                    for mod in modules:
                        modules_imported.append((current_file, mod))
                else:
                    modules_imported.append((current_file, module))
            current_file = ""

    last_file, last_module = modules_imported[-1]

    for file, module in modules_imported[:-1]:
        if module == last_module:
            return _(
                "The problem was likely caused by what is known as a 'circular import'.\n"
                "First, Python imported and started executing the code in file\n"
                "   '{file}'.\n"
                "which imports module `{last_module}`.\n"
                "During this process, the code in another file,\n"
                "   '{last_file}'\n"
                "was executed. However in this last file, an attempt was made\n"
                "to import the original module `{last_module}`\n"
                "a second time, before Python had completed the first import.\n"
            ).format(
                file=file, last_file=last_file, module=module, last_module=last_module
            )
