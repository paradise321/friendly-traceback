"""info_specific.py

Attempts to provide some specific information about the likely cause
of a given exception.
"""

from .my_gettext import current_lang

get_cause = {}


def get_likely_cause(etype, value, info, frame):
    """Gets the likely cause of a given exception based on some information
    specific to a given exception.
    """
    _ = current_lang.translate
    cause = None
    if etype.__name__ in get_cause:
        cause = get_cause[etype.__name__](value, info, frame)
        if cause is not None:
            info["cause_header"] = _(
                "Likely cause based on the information given by Python:"
            )
            info["cause"] = cause
    return


def register(error_name):
    """Decorator used to record as available an explanation for a given exception"""

    def add_exception(function):
        get_cause[error_name] = function

        def wrapper(value, info, frame):
            return function(value, info, frame)

        return wrapper

    return add_exception


@register("AttributeError")
def _attribute_error(value, info, frame):
    from .runtime_errors import attribute_error

    return attribute_error.get_cause(value, info, frame)


@register("FileNotFoundError")
def file_not_found_error(value, info, frame):
    _ = current_lang.translate
    # str(value) is expected to be something like
    #
    # fileNotFoundError: No module named 'does_not_exist'
    #
    # By splitting value using ', we can extract the module name.
    return _(
        "In your program, the name of the\n"
        "file that cannot be found is `{filename}`.\n"
    ).format(filename=str(value).split("'")[1])


@register("ImportError")
def _import_error(value, info, frame):
    from .runtime_errors import import_error

    return import_error.get_cause(value, info, frame)


@register("KeyError")
def key_error(value, info, frame):
    _ = current_lang.translate
    # str(value) is expected to be something like
    #
    # KeyError: 'c'
    return _(
        "In your program, the key that cannot be found is `{key_name!r}`.\n"
    ).format(key_name=value.args[0])


@register("ModuleNotFoundError")
def _module_not_found_error(value, info, frame):

    from .runtime_errors import module_not_found_error

    return module_not_found_error.get_cause(value, info, frame)


@register("NameError")
def name_error(value, info, frame):

    from .runtime_errors import name_error

    return name_error.get_cause(value, info, frame)


@register("OverflowError")
def overflow_error(*args):
    return  # TODO: check to see if additional information can be provided
    # for real test cases


@register("TypeError")
def _type_error(value, info, frame):
    from .runtime_errors import type_error

    return type_error.get_cause(value, info, frame)


@register("UnboundLocalError")
def _unbound_local_error(value, info, frame):
    from .runtime_errors import unbound_local_error

    return unbound_local_error.get_cause(value, info, frame)


@register("ZeroDivisionError")
def zero_division_error(*args):
    return  # No additional information can be provided
