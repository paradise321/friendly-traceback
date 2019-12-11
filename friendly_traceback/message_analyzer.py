"""message_analyser.py

Collection of functions that examine SyntaxError messages and
return relevant information to users.
"""
from keyword import kwlist
import re
import tokenize

from .my_gettext import current_lang
from . import utils
from . import bracket_analyzer
from .friendly_exception import FriendlyException


MESSAGE_ANALYZERS = []


def analyze_message(message="", line="", linenumber=0, source_lines=None, offset=0):
    for case in MESSAGE_ANALYZERS:
        cause = case(
            message=message,
            line=line,
            linenumber=linenumber,
            source_lines=source_lines,
            offset=offset,
        )
        if cause:
            return cause


def add_python_message(func):
    """A simple decorator that adds a function the the list of functions
       that process a message given by Python.
    """
    MESSAGE_ANALYZERS.append(func)

    def wrapper(**kwargs):
        return func(**kwargs)

    return wrapper


@add_python_message
def assign_to_keyword(message="", line="", **kwargs):
    _ = current_lang.translate
    if not (
        message == "can't assign to keyword"  # Python 3.6, 3.7
        or message == "assignment to keyword"  # Python 3.6, 3.7
        or message == "cannot assign to keyword"  # Python 3.8
        or message == "cannot assign to None"  # Python 3.8
        or message == "cannot assign to True"  # Python 3.8
        or message == "cannot assign to False"  # Python 3.8
        or message == "cannot assign to __debug__"  # Python 3.8
    ):
        return

    tokens = utils.collect_tokens(line)
    while True:
        for token in tokens:
            word = token.string
            if word in kwlist or word == "__debug__":
                break
        else:
            raise FriendlyException("analyze_syntax.assign_to_keyword")
        break

    if word in ["None", "True", "False", "__debug__"]:
        return _(
            "{keyword} is a constant in Python; you cannot assign it a value.\n" "\n"
        ).format(keyword=word)
    else:
        return _(
            "You were trying to assign a value to the Python keyword '{keyword}'.\n"
            "This is not allowed.\n"
            "\n"
        ).format(keyword=word)


@add_python_message
def assign_to_function_call(message="", line="", **kwargs):
    _ = current_lang.translate
    if (
        message == "can't assign to function call"  # Python 3.6, 3.7
        or message == "cannot assign to function call"  # Python 3.8
    ):
        if line.count("=") > 1:
            # we have something like  fn(a=1) = 2
            # or fn(a) = 1 = 2, etc.  Since there could be too many
            # combinations, we use some generic names
            fn_call = _("my_function(...)")
            value = _("some value")
            return _(
                "You wrote an expression like\n"
                "    {fn_call} = {value}\n"
                "where {fn_call}, on the left hand-side of the equal sign, is\n"
                "a function call and not the name of a variable.\n"
            ).format(fn_call=fn_call, value=value)

        info = line.split("=")
        fn_call = info[0].strip()
        value = info[1].strip()
        return _(
            "You wrote the expression\n"
            "    {fn_call} = {value}\n"
            "where {fn_call}, on the left hand-side of the equal sign, either is\n"
            "or includes a function call and is not simply the name of a variable.\n"
        ).format(fn_call=fn_call, value=value)


@add_python_message
def assign_to_literal(message="", line="", **kwargs):
    _ = current_lang.translate
    if (
        message == "can't assign to literal"  # Python 3.6, 3.7
        or message == "cannot assign to literal"  # Python 3.8
    ):
        info = line.split("=")
        literal = info[0].strip()
        name = info[1].strip()

        if name.isidentifier():
            # fmt: off
            suggest = _(
                " Perhaps you meant to write:\n"
                "    {name} = {literal}\n"
                "\n"
            ).format(literal=literal, name=name)
            # fmt: on
        else:
            suggest = "\n"

        return (
            _(
                "You wrote an expression like\n"
                "    {literal} = {name}\n"
                "where <{literal}>, on the left hand-side of the equal sign, is\n"
                "or includes an actual number or string (what Python calls a 'literal'),\n"
                "and not the name of a variable."
            ).format(literal=literal, name=name)
            + suggest
        )


@add_python_message
def break_outside_loop(message="", **kwargs):
    _ = current_lang.translate
    if "'break' outside loop" in message:
        return _(
            "The Python keyword 'break' can only be used "
            "inside a for loop or inside a while loop.\n"
        )


@add_python_message
def continue_outside_loop(message="", **kwargs):
    _ = current_lang.translate
    if "'continue' not properly in loop" in message:
        return _(
            "The Python keyword 'continue' can only be used "
            "inside a for loop or inside a while loop.\n"
        )


@add_python_message
def delete_function_call(message="", line=None, **kwargs):
    _ = current_lang.translate
    if (
        message == "can't delete function call"  # Python 3.6, 3.7
        or message == "cannot delete function call"  # Python 3.8
    ):
        tokens = utils.collect_tokens(line)
        if (
            tokens[0].string == "del"
            and tokens[1].type == tokenize.NAME
            and tokens[2].string == "("
            and tokens[-1].string == ")"
        ):
            correct = "del {name}".format(name=tokens[1].string)
        else:
            line = "del function()"
            correct = "del function"
        return _(
            "You attempted to delete a function call\n"
            "    {line}\n"
            "instead of deleting the function's name\n"
            "    {correct}\n"
        ).format(line=line, correct=correct)


@add_python_message
def eol_while_scanning_string_literal(message="", **kwargs):
    _ = current_lang.translate
    if "EOL while scanning string literal" in message:
        return _(
            "You starting writing a string with a single or double quote\n"
            "but never ended the string with another quote on that line.\n"
        )


@add_python_message
def expression_cannot_contain_assignment(message="", **kwargs):
    _ = current_lang.translate
    if "expression cannot contain assignment, perhaps you meant" in message:
        return _(
            "One of the following two possibilities could be the cause:\n"
            "1. You meant to do a comparison with == and wrote = instead.\n"
            "2. You called a function with a named argument:\n\n"
            "       a_function(invalid=something)\n\n"
            "where 'invalid' is not a valid variable name in Python\n"
            "either because it starts with a number, or is a string,\n"
            "or contains a period, etc.\n"
            "\n"
        )


@add_python_message
def keyword_cannot_be_expression(message="", **kwargs):
    _ = current_lang.translate
    if "keyword can't be an expression" in message:
        return _(
            "You likely called a function with a named argument:\n\n"
            "   a_function(invalid=something)\n\n"
            "where 'invalid' is not a valid variable name in Python\n"
            "either because it starts with a number, or is a string,\n"
            "or contains a period, etc.\n"
            "\n"
        )


@add_python_message
def invalid_character_in_identifier(message="", **kwargs):
    _ = current_lang.translate
    if "invalid character in identifier" in message:
        return _(
            "You likely used some unicode character that is not allowed\n"
            "as part of a variable name in Python.\n"
            "This includes many emojis.\n"
            "\n"
        )


@add_python_message
def mismatched_parenthesis(
    message="", source_lines=None, linenumber=None, offset=None, **kwargs
):
    # Python 3.8; something like:
    # closing parenthesis ']' does not match opening parenthesis '(' on line
    _ = current_lang.translate
    pattern1 = re.compile(
        r"closing parenthesis '(.)' does not match opening parenthesis '(.)' on line (\d+)"
    )
    match = re.search(pattern1, message)
    if match is None:
        lineno = None
        pattern2 = re.compile(
            r"closing parenthesis '(.)' does not match opening parenthesis '(.)'"
        )
        match = re.search(pattern2, message)
        if match is None:
            return
    else:
        lineno = match.group(3)

    opening = match.group(2)
    closing = match.group(1)

    if lineno is not None:
        response = _(
            "Python tells us that the closing '{closing}' on the last line shown\n"
            "does not match the opening '{opening}' on line {lineno}.\n\n"
        ).format(closing=closing, opening=opening, lineno=lineno)
    else:
        response = _(
            "Python tells us that the closing '{closing}' on the last line shown\n"
            "does not match the opening '{opening}'.\n\n"
        ).format(closing=closing, opening=opening)

    additional_response = bracket_analyzer.look_for_mismatched_brackets(
        source_lines, linenumber, offset
    )

    if additional_response:
        response += (
            _("I will attempt to be give a bit more information.\n\n")
            + additional_response
        )

    return response


@add_python_message
def unterminated_f_string(message="", **kwargs):
    _ = current_lang.translate
    if "f-string: unterminated string" in message:
        return _(
            "Inside an f-string, which is a string prefixed by the letter f, \n"
            "you have another string, which starts with either a\n"
            "single quote (') or double quote (\"), without a matching closing one.\n"
        )


@add_python_message
def name_is_parameter_and_global(message="", line="", **kwargs):
    # something like: name 'x' is parameter and global
    _ = current_lang.translate
    if "is parameter and global" in message:
        name = message.split("'")[1]
        if name in line and "global" in line:
            newline = line
        else:
            newline = f"global {name}"
        return _(
            "You are including the statement\n\n"
            "    {newline}\n\n"
            "indicating that '{name}' is a variable defined outside a function.\n"
            "You are also using the same '{name}' as an argument for that\n"
            "function, thus indicating that it should be variable known only\n"
            "inside that function, which is the contrary of what 'global' implied.\n"
        ).format(newline=newline, name=name)


@add_python_message
def name_assigned_to_prior_global(message="", **kwargs):
    # something like: name 'p' is assigned to before global declaration
    _ = current_lang.translate
    if "is assigned to before global declaration" in message:
        name = message.split("'")[1]
        return _(
            "You assigned a value to the variable '{name}'\n"
            "before declaring it as a global variable.\n"
        ).format(name=name)


@add_python_message
def name_used_prior_global(message="", **kwargs):
    # something like: name 'p' is used prior to global declaration
    _ = current_lang.translate
    if "is used prior to global declaration" in message:
        name = message.split("'")[1]
        return _(
            "You used the variable '{name}'\n"
            "before declaring it as a global variable.\n"
        ).format(name=name)


@add_python_message
def name_assigned_to_prior_nonlocal(message="", **kwargs):
    # something like: name 'p' is assigned to before global declaration
    _ = current_lang.translate
    if "is assigned to before nonlocal declaration" in message:
        name = message.split("'")[1]
        return _(
            "You assigned a value to the variable '{name}'\n"
            "before declaring it as a nonlocal variable.\n"
        ).format(name=name)


@add_python_message
def name_used_prior_nonlocal(message="", **kwargs):
    # something like: name 'q' is used prior to nonlocal declaration
    _ = current_lang.translate
    if "is used prior to nonlocal declaration" in message:
        name = message.split("'")[1]
        return _(
            "You used the variable '{name}'\n"
            "before declaring it as a nonlocal variable.\n"
        ).format(name=name)


@add_python_message
def unexpected_character_after_continuation(message="", **kwargs):
    _ = current_lang.translate
    if "unexpected character after line continuation character" in message:
        return _(
            "You are using the continuation character '\\' outside of a string,\n"
            "and it is followed by some other character(s).\n"
            "I am guessing that you forgot to enclose some content in a string.\n"
            "\n"
        )


@add_python_message
def unexpected_eof_while_parsing(
    message="", source_lines=None, linenumber=None, offset=None, **kwargs
):
    # unexpected EOF while parsing
    _ = current_lang.translate
    if "unexpected EOF while parsing" not in message:
        return
    response = _(
        "Python tells us that the it reached the end of the file\n"
        "and expected more content.\n\n"
        "I will attempt to be give a bit more information.\n\n"
    )

    response += bracket_analyzer.look_for_missing_bracket(
        source_lines, linenumber, offset
    )
    return response


@add_python_message
def unmatched_parenthesis(message="", linenumber=None, **kwargs):
    _ = current_lang.translate
    # Python 3.8
    if message == "unmatched ')'":
        bracket = bracket_analyzer.name_bracket(")")
    elif message == "unmatched ']'":
        bracket = bracket_analyzer.name_bracket("]")
    elif message == "unmatched '}'":
        bracket = bracket_analyzer.name_bracket("}")
    else:
        return
    return _(
        "The closing {bracket} on line {linenumber} does not match anything.\n"
    ).format(bracket=bracket, linenumber=linenumber)


@add_python_message
def position_argument_follows_keyword_arg(message="", **kwargs):
    _ = current_lang.translate
    if "positional argument follows keyword argument" not in message:
        return
    return _(
        "In Python, you can call functions with only positional arguments\n\n"
        "    test(1, 2, 3)\n\n"
        "or only keyword arguments\n\n"
        "    test(a=1, b=2, c=3)\n\n"
        "or a combination of the two\n\n"
        "    test(1, 2, c=3)\n\n"
        "but with the keyword arguments appearing after all the positional ones.\n"
        "According to Python, you used positional arguments after keyword ones.\n"
    )


@add_python_message
def non_default_arg_follows_default_arg(message="", **kwargs):
    _ = current_lang.translate
    if "non-default argument follows default argument" not in message:
        return
    return _(
        "In Python, you can define functions with only positional arguments\n\n"
        "    def test(a, b, c): ...\n\n"
        "or only keyword arguments\n\n"
        "    def test(a=1, b=2, c=3): ...\n\n"
        "or a combination of the two\n\n"
        "    def test(a, b, c=3): ...\n\n"
        "but with the keyword arguments appearing after all the positional ones.\n"
        "According to Python, you used positional arguments after keyword ones.\n"
    )


@add_python_message
def python2_print(message="", **kwargs):
    _ = current_lang.translate
    if not message.startswith(
        "Missing parentheses in call to 'print'. Did you mean print("
    ):
        return
    message = message[59:-2]
    return _(
        "Perhaps you need to type print({message})?\n\n"
        "In older version of Python, 'print' was a keyword.\n"
        "Now, 'print' is a function; you need to use parentheses to call it.\n"
    ).format(message=message)