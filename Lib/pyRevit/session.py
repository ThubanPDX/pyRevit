""" Module name: session.py
Copyright (c) 2014-2016 Ehsan Iran-Nejad
Python scripts for Autodesk Revit

This file is part of pyRevit repository at https://github.com/eirannejad/pyRevit

pyRevit is a free set of scripts for Autodesk Revit: you can redistribute it and/or modify
it under the terms of the GNU General Public License version 3, as published by
the Free Software Foundation.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

See this link for a copy of the GNU General Public License protecting this package.
https://github.com/eirannejad/pyRevit/blob/master/LICENSE


~~~
Description:
pyRevit library has 4 main modules for handling parsing, assembly creation, ui, and caching.
This module provide a series of functions to create and manage a pyRevit session under Revit (using the 4 modules).
Each time Revit is run, the loader script imports pyRevit.session and creates a session. The session (this module)
then calls the parser, assembly maker, and lastly ui maker to create the buttons in Revit.
Each pyRevit session will have its own .dll and log file.
"""

from .logger import logger

from ._cache import is_cache_valid, get_cached_package, update_cache
from ._parser import get_installed_packages, get_parsed_package
from ._assemblies import create_assembly
from ._ui import update_revit_ui, PyRevitUI


def load(root_dir):
    """Handles loading/reloading of the pyRevit addin and extension packages.
    To create a proper ui, pyRevit needs to be properly parsed and a dll assembly needs to be created.
    This function handles both tasks through private interactions with ._parser and ._ui

    Usage Example:
        import pyRevit.session as current_session
        current_session.load()
    """
    # for every package of installed packages, create an assembly, and create a ui
    # parser, assembly maker, and ui creator all understand ._commandtree classes. (They speak the same language)
    # the session.load() function (this function) only moderates the communication and handles errors.
    # Session, creates an independent dll and ui for every package. This isolates other packages from any errors that
    # might occur when setting up a package.

    # get_installed_packages() returns a list of discovered packages in root_dir
    for pkg_info in get_installed_packages(root_dir):
        # test if cache is valid for this package
        # it might seem unusual to create a package and then re-load it from cache but minimum information
        # about the package needs to be passed to the cache module for proper hash calculation and package recovery.
        # Also package object is very small and its creation doesn't add much overhead.
        if is_cache_valid(pkg_info):
            # if yes, load the cached package and add the cached tabs to the new package
            logger.debug('Cache is valid for: {}'.format(pkg_info))
            logger.debug('Loading package from cache...')
            package = get_cached_package(pkg_info)

        else:
            logger.debug('Cache is NOT valid for: {}'.format(pkg_info))
            package = get_parsed_package(pkg_info)

            # update cache with newly parsed package and its components
            logger.debug('Updating cache for package: {}'.format(package))
            update_cache(package)

        logger.debug('Package successfuly added to this session: {}'.format(package))

        # create a dll assembly. parsed_pkg will be updated with assembly information
        create_assembly(package)
        # and update ui (needs the assembly to link button actions to commands saved in the dll)
        # update_revit_ui(parsed_pkg)


# todo: session object will have all the functionality for the user to interact with the session
# todo: e.g. providing a list of installed packages, handling ui, and others
# todo: user is not expected to use _cache, _parser, _commandtree, _assemblies, or _ui
# ----------------------------------------------------------------------------------------------------------------------
def get_this_command():
    """Returns read only info about the caller python script.
    Example:
        this_script = pyRevit.session.get_this_command()
        print(this_script.script_file_address)
    """
    # todo
    pass


def current_ui():
    """Revit UI Wrapper class for interacting with current pyRevit UI.
    Returned class provides min required functionality for user interaction
    Example:
        current_ui = pyRevit.session.current_ui()
        this_script = pyRevit.session.get_this_command()
        current_ui.update_button_icon(this_script, new_icon)
    """
    return PyRevitUI()