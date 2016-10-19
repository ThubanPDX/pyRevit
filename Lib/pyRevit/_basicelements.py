import os
import os.path as op
import sys
import re

from .exceptions import PyRevitUnknownFormatError, PyRevitNoScriptFileError
from .logger import logger
from .config import PACKAGE_POSTFIX, TAB_POSTFIX, PANEL_POSTFIX, LINK_BUTTON_POSTFIX, PUSH_BUTTON_POSTFIX,             \
                    TOGGLE_BUTTON_POSTFIX, PULLDOWN_BUTTON_POSTFIX, STACKTHREE_BUTTON_POSTFIX, STACKTWO_BUTTON_POSTFIX,\
                    SPLIT_BUTTON_POSTFIX, SPLITPUSH_BUTTON_POSTFIX
from .config import DEFAULT_ICON_FILE, DEFAULT_SCRIPT_FILE, DEFAULT_ALIAS_FILE_NAME, DEFAULT_ON_ICON_FILE,             \
                    DEFAULT_OFF_ICON_FILE
from .config import DOCSTRING_PARAM, AUTHOR_PARAM
from .utils import ScriptFileContents

from .usersettings import user_settings


# tree branch classes (package, tab, panel) ----------------------------------------------------------------------------
# superclass for all tree branches that contain sub-branches
# todo: populate info
class GenericContainer(object):
    def __init__(self, branch_dir):
        self.directory = branch_dir
        if not self._is_valid_dir():
            raise PyRevitUnknownFormatError()

        self.name = None
        self.original_name = self.name
        self.search_path_list = None
        self._sub_components = []

    def _is_valid_dir(self):
        return self.directory.endswith(self.type_id)

    def __iter__(self):
        return iter(self._sub_components)

    def add_component(self, comp):
        self._sub_components.append(comp)


# root class for each package. might contain multiple tabs
class Package(GenericContainer):
    type_id = PACKAGE_POSTFIX

    def __init__(self, package_dir):
        GenericContainer.__init__(self, package_dir)
        self.author = None
        self.version = None

    def get_all_commands(self):
        pass


# class for each tab. might contain multiple panels
class Tab(GenericContainer):
    type_id = TAB_POSTFIX

    def __init__(self, tab_dir):
        GenericContainer.__init__(self, tab_dir)
        self.sort_level = 0

    def has_commands(self):
        pass


# class for each panel. might contain commands or command groups
class Panel(GenericContainer):
    type_id = PANEL_POSTFIX

    def __init__(self, panel_dir):
        GenericContainer.__init__(self, panel_dir)
        self.sort_level = 0

    def get_commands(self):
        return [x for x in self._sub_components if isinstance(x, GenericCommand)]

    def get_command_groups(self):
        return [x for x in self._sub_components if isinstance(x, GenericCommandGroup)]


# command group classes (puu down, split, split pull down, stack2 and stack3) ------------------------------------------
# superclass for all groups of commands.
# todo: populate info
class GenericCommandGroup(object):
    def __init__(self, group_dir):
        self.directory = group_dir
        if not self._is_valid_dir():
            raise PyRevitUnknownFormatError()

        self.name = None
        self.original_name = self.name
        self.sort_level = 0
        self.icon_file = None
        self.search_path_list = None
        self._sub_commands = []

    def _is_valid_dir(self):
        return self.directory.endswith(self.type_id)

    def __iter__(self):
        return iter(self._sub_commands)

    def add_cmd(self, cmd):
        self._sub_commands.append(cmd)

    @staticmethod
    def is_group():
        return True


class PullDownButtonGroup(GenericCommandGroup):
    type_id = PULLDOWN_BUTTON_POSTFIX


class SplitPushButtonGroup(GenericCommandGroup):
    type_id = SPLITPUSH_BUTTON_POSTFIX


class SplitButtonGroup(GenericCommandGroup):
    type_id = SPLIT_BUTTON_POSTFIX


class StackThreeButtonGroup(GenericCommandGroup):
    type_id = STACKTHREE_BUTTON_POSTFIX


class StackTwoButtonGroup(GenericCommandGroup):
    type_id = STACKTWO_BUTTON_POSTFIX


# single command classes (link, push button, toggle button) ------------------------------------------------------------
# todo: populate info
class GenericCommand(object):
    """Superclass for all single commands.
    The information provided by these classes will be used to create a
    push button under Revit UI. However, pyRevit expands the capabilities of push button beyond what is provided by
    Revit UI. (e.g. Toggle button changes it's icon based on its on/off status)
    See LinkButton and ToggleButton classes.
    """
    def __init__(self, cmd_dir):
        self.directory = cmd_dir
        if not self._is_valid_dir():
            raise PyRevitUnknownFormatError()

        self.original_name = self._get_name()
        self.name = user_settings.get_alias(self.original_name)

        self.icon_file = self._verify_file(DEFAULT_ICON_FILE)
        logger.debug('Command {}: Icon file is {}'.format(self.original_name, self.icon_file))

        self.script_file = self._verify_file(DEFAULT_SCRIPT_FILE)
        if self.script_file is None:
            logger.error('Command {}: Does not have script file.'.format(self.original_name))
            raise PyRevitNoScriptFileError()

        script_content = ScriptFileContents(self.get_full_script_address())
        self.doc_string = script_content.extract_param(DOCSTRING_PARAM)
        self.author = script_content.extract_param(AUTHOR_PARAM)

    @staticmethod
    def is_group():
        return False

    def _is_valid_dir(self):
        return self.directory.endswith(self.type_id)

    def _get_full_file_address(self, file_name):
        return op.join(self.directory, file_name)

    def _get_name(self):
        return op.splitext(op.basename(self.directory))[0]

    def _verify_file(self, file_name):
        return file_name if op.exists(op.join(self.directory, file_name)) else None

    def get_full_script_address(self):
        return op.join(self.directory, self.script_file)

    def _get_clean_dict(self):
        return self.__dict__.copy()

    # todo: how to load from cache?
    def _load_from_cache(self, cached_dict):
        for k,v in cached_dict.items():
            self.__dict__[k] = v


class LinkButton(GenericCommand):
    type_id = LINK_BUTTON_POSTFIX

    def __init__(self, cmd_dir):
        GenericCommand.__init__(self, cmd_dir)
        # todo extract assembly and class info


class PushButton(GenericCommand):
    type_id = PUSH_BUTTON_POSTFIX


class ToggleButton(GenericCommand):
    type_id = TOGGLE_BUTTON_POSTFIX

    def __init__(self):
        GenericCommand.__init__(self)
        self.icon_on_file = self._verify_file(DEFAULT_ON_ICON_FILE)
        self.icon_off_file = self._verify_file(DEFAULT_OFF_ICON_FILE)