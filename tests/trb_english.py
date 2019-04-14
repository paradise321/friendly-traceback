"""Creates a version of traceback_en.rst to insert in the documentation.
"""

# When creating a new translation, you need to:
# 1. Make a copy of this file
# 2. Change the value of LANG as well as 'intro_text' so that they reflect the
#    appropriate language
# 3. Change the first line of this file so that the name of the rst file
#    is correct!


import os
import sys
import platform
import friendly_traceback


# Make it possible to find docs and tests source
this_dir = os.path.dirname(__file__)
root_dir = os.path.abspath(os.path.join(this_dir, ".."))

# sys.path.insert(0, root_dir)

LANG = "en"
friendly_traceback.install(lang=LANG)

sys.path.insert(0, this_dir)


import trb_common  # noqa

target = os.path.normpath(os.path.join(root_dir, f"docs/source/tracebacks_{LANG}.rst"))

intro_text = """
Friendly tracebacks - in English
======================================

Friendly-traceback aims to provide friendlier feedback when an exception
is raised than what is done by Python.
Below, we can find some examples. SyntaxError cases are
shown in a separate page.
Ideally, an example of each case handled by friendly-traceback
should be included here.

.. note::

     The content of this page is generated by running
     {name} located in the ``tests/`` directory.
     This needs to be done explicitly, independently of updating the
     documentation using Sphinx.
     On Windows, if Sphinx is installed on your computer, it is suggested
     instead to run make_tb.bat in the root directory as it will create
     similar files for all languages *and* update the documentation.

Friendly-traceback version: {friendly}
Python version: {python}

""".format(
    friendly=friendly_traceback.version.__version__, python=platform.python_version(), name=__file__
)


trb_common.create_tracebacks(target, intro_text)