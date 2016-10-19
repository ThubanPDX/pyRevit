from .config import SCRIPT_FILE_FORMAT
from .logger import logger

# dotnet imports
import clr
clr.AddReference('PresentationCore')
clr.AddReference('RevitAPI')
clr.AddReference('RevitAPIUI')
clr.AddReference('System.Xml.Linq')
from System import *
from System.IO import *
from System.Windows.Media.Imaging import BitmapImage, BitmapCacheOption

# revit api imports
from Autodesk.Revit.UI import *
from Autodesk.Revit.Attributes import *


class ButtonIcons:
    def __init__(self, file_address):
        uri = Uri(file_address)

        self.smallBitmap = BitmapImage()
        self.smallBitmap.BeginInit()
        self.smallBitmap.UriSource = uri
        self.smallBitmap.CacheOption = BitmapCacheOption.OnLoad
        self.smallBitmap.DecodePixelHeight = 16
        self.smallBitmap.DecodePixelWidth = 16
        self.smallBitmap.EndInit()

        self.mediumBitmap = BitmapImage()
        self.mediumBitmap.BeginInit()
        self.mediumBitmap.UriSource = uri
        self.mediumBitmap.CacheOption = BitmapCacheOption.OnLoad
        self.mediumBitmap.DecodePixelHeight = 24
        self.mediumBitmap.DecodePixelWidth = 24
        self.mediumBitmap.EndInit()

        self.largeBitmap = BitmapImage()
        self.largeBitmap.BeginInit()
        self.largeBitmap.UriSource = uri
        self.largeBitmap.CacheOption = BitmapCacheOption.OnLoad
        self.largeBitmap.EndInit()


# todo
class _PyRevitRibbonElement(object):
    def __init__(self):
        self.name = None
        self.children = []

    @staticmethod
    def make_tooltip(cmd):
        tooltip = cmd.doc_string
        tooltip += '\n\nScript Name:\n{0}'.format(cmd.name + ' ' + SCRIPT_FILE_FORMAT)
        tooltip += '\n\nAuthor:\n{0}'.format(cmd.author)
        return tooltip


# todo
class _PyRevitPanel(_PyRevitRibbonElement):
    def retrieve_ribbon_item(self, item):
        pass


# todo
class _PyRevitTab(_PyRevitRibbonElement):
    def retrieve_ribbon_panel(self, panel):
        pass


# todo
class PyRevitUI(_PyRevitRibbonElement):
    def retrieve_ribbon_tab(self, tab):
        pass

    # todo create and add to existing tabs
    @staticmethod
    def create_ribbon_tab(self, pkg_tab):
        """Create revit ribbon tab from pkg_tab data"""
        try:
            return __revit__.CreateRibbonTab(pkg_tab.name)
        except:
            raise RevitRibbonTabExists()


def update_revit_ui(parsed_pkg, pkg_asm_location):
    """Updates/Creates pyRevit ui for the given package and provided assembly dll address.
    This functions has been kept outside the PyRevitUI class since it'll only be used
    at pyRevit startup and reloading, and more importantly it needs a properly created dll assembly.
    See pyRevit.session.load() for requesting load/reload of the pyRevit package.
    """

    # Collect exising ui elements and update/create
    current_ui = PyRevitUI()

    # Traverse thru the package and create necessary ui elements
    for tab in parsed_pkg:
        # creates pyrevit ribbon-panels for given tab data
        # A package might contain many tabs. Some tabs might not temporarily include any commands
        # So a ui tab is create only if it includes commands
        #  Level 1: Tabs -----------------------------------------------------------------------------------------------
        if tab.has_commands():
            if not current_ui.contains(tab):
                current_ui.create_ribbon_tab(tab)

            # Level 2: Panels (under tabs) -----------------------------------------------------------------------------
            for panel in tab:
                if not current_ui.tab(tab).contains(panel):
                    current_ui.tab(tab).create_ribbon_panel(panel)

                # Level 3: Ribbon items (simple push buttons or more complex button groups) ----------------------------
                for item in panel:
                    if current_ui.panel(panel).contains(item):
                        # update the ribbon_item that are single buttons (e.g. PushButton) or
                        # updates the icon for ribbon_items that are groups of buttons  (e.g. PullDownButton)
                        current_ui.panel(panel).update_ribbon_item(item)

                        # then update/create the sub items if any
                        # Level 4: Ribbon items that include other push buttons (e.g. PullDownButton) ------------------
                        if item.is_group():
                            for button in item:
                                if current_ui.ribbon_item(item).contains(button):
                                    current_ui.ribbon_item(item).update_button(button)
                                else:
                                    current_ui.ribbon_item(item).create_button(button, pkg_asm_location)

                            # current_ui.ribbon_item(item) now includes updated or new buttons.
                            # so cleanup all the remaining existing buttons that are not in this package anymore.
                            current_ui.ribbon_item(item).cleanup_orphaned_buttons()
                    else:
                        current_ui.panel(panel).create_ribbon_item(item, pkg_asm_location)

                # current_ui.panel(panel) now includes updated or new ribbon_items.
                # so cleanup all the remaining existing items that are not in this package anymore.
                current_ui.panel(panel).cleanup_orphaned_ribbon_items()

            # current_ui.tab(tab) now includes updated or new ribbon_panels.
            # so cleanup all the remaining existing panels that are not in this package anymore.
            current_ui.tab(tab).cleanup_orphaned_ribbon_panels()
        else:
            logger.debug('Tab {} does not have any commands. Skipping.'.format(tab.name))

    # current_ui.tab(tab) now includes updated or new ribbon_tabs.
    # so cleanup all the remaining existing tabs that are not available anymore.
    current_ui.cleanup_orphaned_ribbon_tabs(parsed_pkg)