import clr
import sys
import os
import shutil
import re
import time
# import timeit
# import random as rnd
# import pickle as pl
import os.path as op
import ConfigParser as settingsParser
from datetime import datetime



# todo: this helper could be the main pyRevit module that other script can add and use the classes and functions
clr.AddReference('PresentationCore')
clr.AddReference('RevitAPI')
clr.AddReference('RevitAPIUI')
clr.AddReference('System.Xml.Linq')

from System import *
from System.IO import *
from System.Reflection import *
from System.Reflection.Emit import *
from System.Windows.Media.Imaging import BitmapImage, BitmapCacheOption

from Autodesk.Revit.UI import *
from Autodesk.Revit.Attributes import *
from System.Diagnostics import Process

verbose = False
last_report_type = ''
verbose_disabled_char = '|'

__doc__ = 'Searches the script folders and create buttons for the new script or newly installed extensions.'

def report(message, title=False, newline=True):
    global last_report_type
    if title:
        message = '-' * 100 + '\n' + message + '\n' + '-' * 100
    if newline and  last_report_type == 'disabledverbose':
        message = '\n' + message
    if newline:
        print(message)
    else:
        sys.stdout.write(message)
    last_report_type = 'normal'


def reportv(message, title=False):
    global verbose
    global last_report_type
    global verbose_disabled_char
    if verbose:
        report(message, title)
        last_report_type = 'verbose'
    else:
        report(verbose_disabled_char, newline = False)
        last_report_type = 'disabledverbose'


def find_loader_directory():
    # getting home directory from __file__ provided by RPL
    folder = os.path.dirname(__file__)
    if folder.lower().endswith('.dll'):
        # nope - RplAddin
        folder = os.path.dirname(folder)
    sys.path.append(folder)
    return folder


def find_home_directory():
    # getting home directory from __file__ provided by RPL
    folder = os.path.dirname(os.path.dirname(__file__))
    if folder.lower().endswith('.dll'):
        # nope - RplAddin
        folder = os.path.dirname(folder)
    sys.path.append(folder)
    return folder


def find_init_script_name():
    return op.splitext(op.basename("t://pyrevit//__init__.py"))[0]


def find_user_temp_directory():
    tempfolder = os.getenv('Temp')
    return tempfolder


def get_username():
    uname = __revit__.Application.Username
    uname = uname.split('@')[0]
    uname = uname.replace('.','')
    return uname

# AUXILIARY CLASSES
class Timer:
    def __init__(self):
        self.start = time.time()

    def restart(self):
        self.start = time.time()

    def get_time_hhmmss(self):
        return "%02.2f seconds" % (time.time() - self.start)


# EXCEPTIONS
class PyRevitException(Exception):
    pass


class UnknownAssembly(PyRevitException):
    pass


class UnknownFileNameFormat(PyRevitException):
    pass


# SOOP CLASSES
class PyRevitUISettings:
    pyRevitAssemblyName = 'pyRevit'
    tabPostfix = '.tab'
    panelBundlePostfix = '.panel'
    iconFileFormat = '.png'
    linkButtonTypeName = 'PushButton'
    pushButtonTypeName = 'PushButton'
    smartButtonTypeName = 'SmartButton'
    pulldownButtonTypeName = 'PulldownButton'
    stackedThreeTypeName = 'Stack3'
    stackedTwoTypeName = 'Stack2'
    splitButtonTypeName = 'SplitButton'
    splitPushButtonTypeName = 'SplitPushButton'
    tooltipParameter = '__doc__'
    authorParameter = '__author__'
    pyRevitInitScriptName = '__init__'
    reloadScriptsOverrideGroupName = 'pyRevit'
    reloadScriptsOverrideName = 'reloadScripts'
    masterTabName = 'master'
    logScriptUsage = False
    archivelogfolder = 'T:\[logs]'
    specialcharacters = {' ': '', '~': '',
                         '!': 'EXCLAM',
                         '@': 'AT',
                         '#': 'NUM',
                         '$': 'DOLLAR',
                         '%': 'PERCENT',
                         '^': '',
                         '&': 'AND',
                         '*': 'STAR',
                         '\(': '', '\)': '',
                         '+': 'PLUS',
                         ';': '', ':': '', ',': '', '\"': '', '{': '', '}': '', '[': '', ']': '',
                         '-': 'MINUS',
                         '=': 'EQUALS',
                         '<': '', '>': '',
                         '?': 'QMARK',
                         '.': 'DOT',
                         '\/': '', '\\': ''}

    def __init__(self):
        """Loads settings from settings file."""
        global verbose
        initsectionname = 'init'
        globalsectionname = 'global'

        # find the user config file
        userappdatafolder = os.getenv('appdata')
        pyrevituserappdatafolder = op.join(userappdatafolder, "pyRevit")
        userconfigfile = op.join(pyrevituserappdatafolder, "userdefaults.ini")
        masterconfigfile = op.join(find_loader_directory(), self.pyRevitInitScriptName + ".ini")
        configfileisuser = False
        
        # if a user config file exits, this would be used instead of master.
        if op.exists(userconfigfile):
            configfile = userconfigfile
            configfileisuser = True
        else:
            configfile = masterconfigfile

        if configfileisuser:
            report('Reading settings from user config file...')
        else:
            report('Reading settings from master config file...')
        # if the config file exists then read values and apply
        if op.exists(configfile):        # read file and reapply settings
            try:
                with open(configfile,'r') as udfile:
                    cparser = settingsParser.ConfigParser()          
                    cparser.readfp(udfile)
                    logScriptUsageConfigValue = cparser.get(initsectionname, "logScriptUsage")
                    self.logScriptUsage = True if logScriptUsageConfigValue.lower() == "true" else False
                    self.archivelogfolder = cparser.get(initsectionname, "archivelogfolder")
                    verbose = True if cparser.get(globalsectionname, "verbose").lower() == "true" else False
            except:
                reportv("Can not access existing config file. Skipping saving config file.")
        # else if the config file is not readable then create a user config and fill with default
        else:
            if self.verify_config_folder(pyrevituserappdatafolder):
                try:
                    with open(userconfigfile,'w') as udfile:
                        cparser = settingsParser.ConfigParser()
                        cparser.add_section(globalsectionname)
                        cparser.set(globalsectionname, "verbose", "true" if verbose else "false")
                        cparser.add_section(initsectionname)
                        cparser.set(initsectionname, "logScriptUsage", "true" if self.logScriptUsage else "false")
                        cparser.set(initsectionname, "archivelogfolder", self.archivelogfolder)
                        cparser.write(udfile)   
                        report('Config file saved under: {}\n' \
                               'with default settings.'.format(pyrevituserappdatafolder))
                except:
                    report('Can not create config file under: {}.\n' \
                           'Skipping saving config file.'.format(pyrevituserappdatafolder))
            else:
                report('Can not create config file folder under: {}.\n' \
                       'Skipping saving config file.'.format(pyrevituserappdatafolder))

    def verify_config_folder(self, folder):
        if not op.exists(folder):
            try:
                os.makedirs(folder)
            except:
                return False
        return True


class ButtonIcons:
    def __init__(self, filedir, filename):
        uri = Uri(op.join(filedir, filename))
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


class ScriptTab:
    def __init__(self, tname, tfolder):
        self.tabName = tname.replace(sessionSettings.tabPostfix, '')
        self.tabDirName = tname
        self.tabFolder = tfolder
        self.scriptPanels = []
        self.pyRevitUIPanels = {}
        self.pyRevitUIButtons = {}

    def adopt_panels(self, pyrevitscriptpanels):
        already_adopted_panels = [x.panelName for x in self.scriptPanels]
        for panel in pyrevitscriptpanels:
            if panel.tabName == self.tabName and panel.panelName not in already_adopted_panels:
                reportv('\tcontains: {0}'.format(panel.panelName))
                self.scriptPanels.append(panel)

    def get_sorted_scriptpanels(self):
        return sorted(self.scriptPanels, key=lambda x: x.panelOrder)

    def hascommands(self):
        for p in self.scriptPanels:
            for g in p.scriptGroups:
                if len(g.commands) > 0:
                    return True
        return False


class ScriptPanel:
    def __init__(self, tabdir, fullpanelfilename, tabname, bundledpanel):
        self.panelOrder = 0
        self.panelName = ''
        self.scriptGroups = []
        self.tabName = tabname
        self.tabDir = tabdir
        self.isBundled = bundledpanel

        if self.isBundled:
            self.panelName = fullpanelfilename.replace(sessionSettings.panelBundlePostfix, '')
        else:
            fname, fext = op.splitext(op.basename(fullpanelfilename))
            if ScriptPanel.isdescriptorfile(fname, fext):
                namepieces = fname.rsplit('_')
                namepieceslength = len(namepieces)
                if namepieceslength == 4 or namepieceslength == 6:
                    self.panelOrder, self.panelName = namepieces[0:2]
                    self.panelOrder = int(self.panelOrder[:2])
                    reportv('Panel found: Type: {0}'.format(self.panelName.ljust(20)))
                else:
                    raise UnknownFileNameFormat()
            else:
                raise UnknownFileNameFormat()

    @staticmethod
    def isdescriptorfile(fname, fext):
        return sessionSettings.iconFileFormat == fext.lower() and fname[0:3].isdigit()

    def adoptgroups(self, pyrevitscriptgroups):
        already_adopted_groups = [x.groupName for x in self.scriptGroups]
        for group in pyrevitscriptgroups:
            if group.panelName == self.panelName and group.tabName == self.tabName \
            and group.groupName not in already_adopted_groups:
                reportv('\tcontains: {0}'.format(group.groupName))
                self.scriptGroups.append(group)

    def get_sorted_scriptgroups(self):
        return sorted(self.scriptGroups, key=lambda x: x.groupOrder)


class ScriptGroup:
    def __init__(self, filedir, f, tabname, bundledPanelName):
        self.commands = []
        self.sourceDir = ''
        self.sourceFile = ''
        self.sourceFileName = ''
        self.sourceFileExt = sessionSettings.iconFileFormat
        self.groupOrder = 0
        self.panelName = bundledPanelName
        self.groupType = None
        self.groupName = ''
        self.buttonIcons = None
        self.assemblyName = None
        self.assemblyClassName = None
        self.assemblyLocation = None
        self.tabName = tabname

        fname, fext = op.splitext(op.basename(f))
        if ScriptGroup.isdescriptorfile(fname, fext):
            self.sourceDir = filedir
            self.sourceFile = f
            self.sourceFileName = fname
            self.sourceFileExt = fext
            namepieces = fname.rsplit('_')
            namepieceslength = len(namepieces)
            if namepieces[0].isdigit():
                if namepieceslength == 4 or namepieceslength == 6:
                    self.groupOrder, self.panelName, self.groupType, self.groupName = namepieces[0:4]
                    self.groupOrder = int(self.groupOrder[2:])
                    reportv('Script group found: Type: {0} Name: {1} Parent Panel: {2}'.format(self.groupType.ljust(20),
                                                                                               self.groupName.ljust(20),
                                                                                               self.panelName))
                    self.buttonIcons = ButtonIcons(filedir, f)
                elif namepieceslength == 3:
                    self.groupOrder, self.groupType, self.groupName = namepieces
                    self.groupOrder = int(self.groupOrder)
                    reportv('Script group found: Type: {0} Name: {1} Parent Panel: {2}'.format(self.groupType.ljust(20),
                                                                                               self.groupName.ljust(20),
                                                                                               self.panelName))
                    self.buttonIcons = ButtonIcons(filedir, f)

                # check to see if name has assembly information
                if namepieceslength == 6:
                    self.assemblyName, self.assemblyClassName = namepieces[4:]
                    try:
                        self.assemblyName = ScriptGroup.findassembly(self.assemblyName).GetName().Name
                        self.assemblyLocation = ScriptGroup.findassembly(self.assemblyName).Location
                        reportv('                    Assembly.Class: {0}.{1}'.format(self.assemblyName,
                                                                                     self.assemblyClassName))
                    except UnknownAssembly:
                        raise
        else:
            raise UnknownFileNameFormat()

    def adoptcommands(self, pyrevitscriptcommands, masterTabName):
        already_adopted_commands = [x.fileName for x in self.commands]
        for cmd in pyrevitscriptcommands:
            if cmd.scriptGroupName == self.groupName \
            and (cmd.tabName == self.tabName or cmd.tabName == masterTabName) \
            and cmd.fileName not in already_adopted_commands:
                    reportv('\tcontains: {0}'.format(cmd.fileName))
                    self.commands.append(cmd)

    def islinkbutton(self):
        return self.assemblyName is not None

    @staticmethod
    def isdescriptorfile(fname, fext):
        return sessionSettings.iconFileFormat == fext.lower() and fname[0:2].isdigit()

    @staticmethod
    def findassembly(assemblyname):
        for loadedAssembly in AppDomain.CurrentDomain.GetAssemblies():
            if assemblyname in loadedAssembly.FullName:
                return loadedAssembly
        raise UnknownAssembly()


class ScriptFileContents:
    def __init__(self, fileaddress):
        self.filecontents = ''
        with open(fileaddress, 'r') as f:
            self.filecontents = f.readlines()

    def extractparameter(self, param):
        paramstringfound = False
        paramstring = ''
        paramfinder = re.compile(param + '\s*=\s*[\'\"](.*)[\'\"]', flags=re.IGNORECASE)
        paramfinderex = re.compile('^\s*[\'\"](.*)[\'\"]', flags=re.IGNORECASE)
        for thisline in self.filecontents:
            if not paramstringfound:
                values = paramfinder.findall(thisline)
                if values:
                    paramstring = values[0]
                    paramstringfound = True
                continue
            elif paramstringfound:
                values = paramfinderex.findall(thisline)
                if values:
                    paramstring += values[0]
                    continue
                break
        return paramstring.replace('\\\'', '\'').replace('\\"', '\"').replace('\\n', '\n').replace('\\t', '\t')


class ScriptCommand:
    def __init__(self, filedir, f, tabname):
        self.filePath = ''
        self.fileName = ''
        self.tooltip = ''
        self.cmdName = ''
        self.scriptGroupName = ''
        self.className = ''
        self.iconFileName = ''
        self.buttonIcons = None
        self.tabName = tabname
        filecontents = ''

        fname, fext = op.splitext(op.basename(f))

        # custom name adjustments
        if sessionSettings.pyRevitInitScriptName.lower() in fname.lower() and tabname == sessionSettings.masterTabName:
            fname = sessionSettings.reloadScriptsOverrideGroupName + '_' + sessionSettings.reloadScriptsOverrideName

        if not fname.startswith('_') and '.py' == fext.lower():
            self.filePath = filedir
            self.fileName = f

            namepieces = fname.rsplit('_')
            namepieceslength = len(namepieces)
            if namepieceslength == 2:
                self.scriptGroupName, self.cmdName = namepieces
                self.className = tabname + self.scriptGroupName + self.cmdName
                for char, repl in sessionSettings.specialcharacters.items():
                    self.className = self.className.replace(char, repl)
                reportv('Script found: {0} Group: {1} CommandName: {2}'.format(f.ljust(50),
                                                                               self.scriptGroupName.ljust(20),
                                                                               self.cmdName))
                if op.exists(op.join(filedir, fname + sessionSettings.iconFileFormat)):
                    self.iconFileName = fname + sessionSettings.iconFileFormat
                    self.buttonIcons = ButtonIcons(filedir, self.iconFileName)
                else:
                    self.iconFileName = None
                    self.buttonIcons = None
            else:
                raise UnknownFileNameFormat()
            
            scriptContents = ScriptFileContents(self.getfullscriptaddress())
            docstring = scriptContents.extractparameter(sessionSettings.tooltipParameter)
            author = scriptContents.extractparameter(sessionSettings.authorParameter)
            if docstring is not None:
                self.tooltip = '{0}'.format(docstring)
            else:
                self.tooltip = ''
            self.tooltip += '\n\nScript Name:\n{0}'.format(fname + ' ' + fext.lower())
            if author is not None and author != '':
                self.tooltip += '\n\nAuthor:\n{0}'.format(author)
        else:
            raise UnknownFileNameFormat()

    def getfullscriptaddress(self):
        return op.join(self.filePath, self.fileName)

    def getscriptbasename(self):
        return self.scriptGroupName + '_' + self.cmdName


class PyRevitUISession:
    def __init__(self):
        self.loadedPyRevitScripts = []
        self.loadedPyRevitAssemblies = []
        self.pyRevitScriptPanels = []
        self.pyRevitScriptGroups = []
        self.pyRevitScriptCommands = []
        self.pyRevitScriptTabs = []
        self.sessionname = None

        self.loaderDir = find_loader_directory()
        self.homeDir = find_home_directory()
        report('\nHome Directory is: {0}'.format(self.homeDir))

        self.commandLoaderClass = None
        self.commandLoaderAssembly = None
        self.newAssemblyLocation = None
        self.isrplfound = False
        self.isrplloggerfound = False

        self.userTempFolder = find_user_temp_directory()
        self.revitVersion = __revit__.Application.VersionNumber
        self.username = get_username()
        self.assemblyidentifier = sessionSettings.pyRevitAssemblyName
        self.sessionidentifier = "{0}{1}".format(sessionSettings.pyRevitAssemblyName,
                                                 self.revitVersion)
        self.archivelogfolder = sessionSettings.archivelogfolder

        # collect information about previously loaded assemblies
        report('\nInitializing python script loader...')
        res = self.find_commandloader_class()
        if res:
            self.find_loaded_pyrevit_assemblies()
            if not self.isreloading():
                self.cleanup()
                self.archivelogs()
            else:
                reportv('pyRevit is reloading. Skipping DLL and log cleanup.')

            # find commands, script groups and assign commands
            self.create_reload_button(self.loaderDir)
            report('Searching for tabs, panels, groups, and scripts...')
            self.find_scripttabs(self.homeDir)

            # create assembly dll
            report('Building script executer assembly...')
            self.createassembly()

            # setting up UI
            reportv('Executer assembly saved. Creating pyRevit UI.')
            self.createpyrevitui()
        else:
            report('pyRevit load failed...')
    
    def cleanup(self):
        revitinstances = list(Process.GetProcessesByName('Revit'))
        if len(revitinstances) > 1:
            reportv('Multiple Revit instance are running...Skipping DLL Cleanup')
        elif len(revitinstances) == 1 and not self.isreloading():
            reportv('Cleaning up old DLL files...')
            files = os.listdir(self.userTempFolder)
            for f in files:
                if f.startswith(self.sessionidentifier) and f.endswith('dll'):
                    try:
                        os.remove(op.join(self.userTempFolder, f))
                        reportv('Existing .Dll Removed: {0}'.format(f))
                    except:
                        reportv('Error deleting .DLL file: {0}'.format(f))

    def archivelogs(self):
        if op.exists(self.archivelogfolder):
            revitinstances = list(Process.GetProcessesByName('Revit'))
            if len(revitinstances) > 1:
                reportv('Multiple Revit instance are running...Skipping archiving old log files.')
            elif len(revitinstances) == 1 and not self.isreloading():
                reportv('Archiving old log files...')
                files = os.listdir(self.userTempFolder)
                for f in files:
                    if f.startswith(self.assemblyidentifier) and f.endswith('log'):
                        try:
                            currentfileloc = op.join(self.userTempFolder, f)
                            newloc = op.join(self.archivelogfolder, f)
                            shutil.move(currentfileloc, newloc)
                            reportv('Existing log file archived to: {0}'.format(newloc))
                        except:
                            reportv('Error archiving log file: {0}'.format(f))
        else:
            reportv('Archive log folder does not exist: {0}. Skipping...'.format(self.archivelogfolder))

    def isreloading(self):
        return len(self.loadedPyRevitAssemblies) > 0

    def find_commandloader_class(self):
        # tries to find the revitpythonloader assembly first
        reportv('Asking Revit for RevitPythonLoader Command Loader class...')
        for loadedAssembly in AppDomain.CurrentDomain.GetAssemblies():
            if 'RevitPythonLoader' in loadedAssembly.FullName:
                reportv('RPL Assembly found: {0}'.format(loadedAssembly.GetName().FullName))
                self.commandLoaderClass = loadedAssembly.GetType('RevitPythonLoader.CommandLoaderBase')
                if sessionSettings.logScriptUsage:
                    loaderclass = loadedAssembly.GetType('RevitPythonLoader.CommandLoaderBaseWithLogger')
                    if loaderclass is not None:
                        self.commandLoaderClass = loaderclass
                        reportv('RPL script usage logging is Enabled.')
                        self.isrplloggerfound = True
                    else:
                        self.isrplloggerfound = False
                        reportv('RPL script usage logging is Enabled but can not find base class with logger.')
                else:
                    reportv('RPL script usage logging is Disabled.')
                self.commandLoaderAssembly = loadedAssembly
                self.isrplfound = True
                return True

        # if revitpythonloader doesn't exist tries to find the revitpythonshell assembly
        reportv('Can not find RevitPythonLoader. Asking Revit for RevitPythonShell Command Loader class instead...')
        for loadedAssembly in AppDomain.CurrentDomain.GetAssemblies():
            if 'RevitPythonShell' in loadedAssembly.FullName:
                reportv('RPS Assembly found: {0}'.format(loadedAssembly.GetName().FullName))
                self.commandLoaderClass = loadedAssembly.GetType('RevitPythonShell.CommandLoaderBase')
                self.commandLoaderAssembly = loadedAssembly
                self.isrplfound = False
                return True

        reportv('Can not find RevitPythonShell either. Aborting load...')
        self.commandLoaderClass = None
        self.commandLoaderAssembly = None
        return None

    def find_loaded_pyrevit_assemblies(self):
        reportv('Asking Revit for previously loaded pyRevit assemblies...')
        for loadedAssembly in AppDomain.CurrentDomain.GetAssemblies():
            if sessionSettings.pyRevitAssemblyName in loadedAssembly.FullName:
                reportv('Existing assembly found: {0}'.format(loadedAssembly.FullName))
                self.loadedPyRevitAssemblies.append(loadedAssembly)
                self.loadedPyRevitScripts.extend([ct.Name for ct in loadedAssembly.GetTypes()])

    def find_scriptcommands(self, searchdir, tabname):
        reportv('Searching tab folder for scripts...')
        files = sorted(os.listdir(searchdir))
        for fullfilename in files:
            fullfilepath = op.join(searchdir, fullfilename)
            fname, fext = op.splitext(op.basename(fullfilename))
            if not op.isdir(fullfilepath) and '.py' == fext.lower():
                try:
                    cmd = ScriptCommand(searchdir, fullfilename, tabname)
                    self.pyRevitScriptCommands.append(cmd)
                except UnknownFileNameFormat:
                    reportv('Can not recognize name pattern. skipping: {0}'.format(fullfilename))
                    continue
                except:
                    reportv('Something is wrong. skipping: {0}'.format(fullfilename))
                    continue

        if not len(self.pyRevitScriptCommands) > 0:
            report('No Scripts found...')

    def find_scriptgroups(self, searchdir, tabname, bundledPanelName = ''):
        reportv('Searching content folder for script groups ...')
        self.find_scriptcommands(searchdir, tabname)
        files = os.listdir(searchdir)
        for fullfilename in files:
            fullfilepath = op.join(searchdir, fullfilename)
            fname, fext = op.splitext(op.basename(fullfilename))
            if not op.isdir(fullfilepath) and sessionSettings.iconFileFormat == fext.lower():
                try:
                    scriptgroup = ScriptGroup(searchdir, fullfilename, tabname, bundledPanelName)
                    scriptgroup.adoptcommands(self.pyRevitScriptCommands, sessionSettings.masterTabName)
                    self.pyRevitScriptGroups.append(scriptgroup)
                except UnknownFileNameFormat:
                    if fullfilename in [x.iconFileName for x in self.pyRevitScriptCommands]:
                        reportv('Skipping script icon file: {0}'.format(fullfilename))
                        continue
                    else:
                        reportv('Can not recognize name pattern. skipping: {0}'.format(fullfilename))
                        continue
                except UnknownAssembly:
                    reportv('Unknown assembly error. Skipping: {0}'.format(fullfilename))
                    continue

    def find_scriptpanels(self, tabdir, tabname):
        reportv('Searching content folder for script panels ...')
        self.find_scriptgroups(tabdir, tabname)
        files = os.listdir(tabdir)
        for fullfilename in files:
            fullfilepath = op.join(tabdir, fullfilename)
            fname, fext = op.splitext(op.basename(fullfilename))
            is_panel_bundled = (op.isdir(fullfilepath) \
                              and not fullfilename.startswith(('.','_')) \
                              and fullfilename.endswith(sessionSettings.panelBundlePostfix))
            is_panel_defined_by_png = sessionSettings.iconFileFormat == fext.lower()
            if is_panel_bundled or is_panel_defined_by_png:
                try:
                    scriptpanel = ScriptPanel(tabdir, fullfilename, tabname, is_panel_bundled)
                    if is_panel_bundled:
                        self.find_scriptgroups(fullfilepath, tabname, bundledPanelName = scriptpanel.panelName)

                    collectedscriptpanels = [(x.panelName, x.tabName) for x in self.pyRevitScriptPanels]
                    if (scriptpanel.panelName, scriptpanel.tabName) not in collectedscriptpanels:
                        scriptpanel.adoptgroups(self.pyRevitScriptGroups)
                        self.pyRevitScriptPanels.append(scriptpanel)
                    else:
                        reportv('\tpanel already created and adopted groups.')
                except UnknownFileNameFormat:
                    if fullfilename in [x.iconFileName for x in self.pyRevitScriptCommands]:
                        reportv('Skipping script panel file: {0}'.format(fullfilename))
                        continue
                    else:
                        reportv('Can not recognize panel name pattern. skipping: {0}'.format(fullfilename))
                        continue

    def find_scripttabs(self, homeDir):
        for dirName in os.listdir(homeDir):
            fulltabpath = op.join(homeDir, dirName)
            if op.isdir(fulltabpath) \
            and not dirName.startswith(('.','_')) \
            and dirName.endswith(sessionSettings.tabPostfix):
                reportv('\n')
                report('Searching for scripts under: {0}'.format(fulltabpath), title=True)
                tabnames = {x.tabDirName:x for x in self.pyRevitScriptTabs}
                if dirName not in tabnames.keys():
                    sys.path.append(fulltabpath)
                    scripttab = ScriptTab(dirName, fulltabpath)
                    self.find_scriptpanels(fulltabpath, scripttab.tabName)
                    reportv('\nTab found: {0}'.format(scripttab.tabName))
                    scripttab.adopt_panels(self.pyRevitScriptPanels)
                    self.pyRevitScriptTabs.append(scripttab)
                    
                    reportv('\n')
                else:
                    sys.path.append(fulltabpath)
                    scripttab = tabnames[dirName]
                    self.find_scriptpanels(fulltabpath, scripttab.tabName)
                    reportv('\nTab extension found: {0}'.format(scripttab.tabName))
                    scripttab.adopt_panels(self.pyRevitScriptPanels)
            elif op.isdir(fulltabpath) and not dirName.startswith(('.','_')):
                self.find_scripttabs(fulltabpath)
            else:
                continue

    def create_reload_button(self, loaderDir):
        reportv('Creating "Reload Scripts" button...')
        for fname in os.listdir(loaderDir):
            fulltabpath = op.join(loaderDir, fname)
            if not op.isdir(fulltabpath) and sessionSettings.pyRevitInitScriptName in fname:
                try:
                    cmd = ScriptCommand(loaderDir, fname, sessionSettings.masterTabName)
                    self.pyRevitScriptCommands.append(cmd)
                    reportv('Reload button added.\n')
                except:
                    reportv('\nCould not create reload command.\n')
                    continue

    def createassembly(self):
        # create DLL folder
        # dllfolder = Path.Combine( self.homeDir, sessionSettings.pyRevitAssemblyName )
        # if not os.path.exists( dllfolder ):
        # os.mkdir( dllfolder )
        dllfolder = self.userTempFolder
        # make assembly name
        self.sessionname = "{0}{1}{2}".format(self.sessionidentifier,
                                              "_" + datetime.now().strftime('%y%m%d%H%M%S'),
                                              "_" + self.username
                                              )
        dllname = self.sessionname + '.dll'
        logfilename = self.sessionname + '.log'

        # create assembly
        windowsassemblyname = AssemblyName(Name=self.sessionname, Version=Version(1, 0, 0, 0))
        reportv('Generated assembly name for this session: {0}'.format(self.sessionname))
        reportv('Generated windows assembly name for this session: {0}'.format(windowsassemblyname))
        reportv('Generated DLL name for this session: {0}'.format(dllname))
        reportv('Generated log name for this session: {0}'.format(logfilename))
        assemblybuilder = AppDomain.CurrentDomain.DefineDynamicAssembly(windowsassemblyname,
                                                                        AssemblyBuilderAccess.RunAndSave, dllfolder)
        modulebuilder = assemblybuilder.DefineDynamicModule(self.sessionname, dllname)

        # create command classes
        for cmd in self.pyRevitScriptCommands:
            typebuilder = modulebuilder.DefineType(cmd.className, TypeAttributes.Class | TypeAttributes.Public,
                                                   self.commandLoaderClass)

            # add RegenerationAttribute to type
            regenerationconstrutorinfo = clr.GetClrType(RegenerationAttribute).GetConstructor(
                Array[Type]((RegenerationOption,)))
            regenerationattributebuilder = CustomAttributeBuilder(regenerationconstrutorinfo,
                                                                  Array[object]((RegenerationOption.Manual,)))
            typebuilder.SetCustomAttribute(regenerationattributebuilder)

            # add TransactionAttribute to type
            transactionconstructorinfo = clr.GetClrType(TransactionAttribute).GetConstructor(
                Array[Type]((TransactionMode,)))
            transactionattributebuilder = CustomAttributeBuilder(transactionconstructorinfo,
                                                                 Array[object]((TransactionMode.Manual,)))
            typebuilder.SetCustomAttribute(transactionattributebuilder)

            # call base constructor with script path
            ci = None
            if not sessionSettings.logScriptUsage:
                ci = self.commandLoaderClass.GetConstructor(Array[Type]((str,)))
            elif self.isrplfound and sessionSettings.logScriptUsage:
                if self.isrplloggerfound:
                    ci = self.commandLoaderClass.GetConstructor(Array[Type]((str, str)))
                else:
                    ci = self.commandLoaderClass.GetConstructor(Array[Type]((str,)))

            constructorbuilder = typebuilder.DefineConstructor(MethodAttributes.Public, CallingConventions.Standard,
                                                               Array[Type](()))
            gen = constructorbuilder.GetILGenerator()
            gen.Emit(OpCodes.Ldarg_0)  # Load "this" onto eval stack
            gen.Emit(OpCodes.Ldstr, cmd.getfullscriptaddress())  # Load the path to the command as a string onto stack
            if self.isrplfound and sessionSettings.logScriptUsage and self.isrplloggerfound:
                gen.Emit(OpCodes.Ldstr, logfilename)  # Load log file name into stack
            gen.Emit(OpCodes.Call, ci)  # call base constructor (consumes "this" and the string)
            gen.Emit(OpCodes.Nop)  # Fill some space - this is how it is generated for equivalent C# code
            gen.Emit(OpCodes.Nop)
            gen.Emit(OpCodes.Nop)
            gen.Emit(OpCodes.Ret)
            typebuilder.CreateType()

        # save final assembly
        assemblybuilder.Save(dllname)
        self.newAssemblyLocation = Path.Combine(dllfolder, dllname)

    def create_or_find_pyrevit_panels(self):
        reportv('Searching for existing pyRevit panels...')
        for scriptTab in self.pyRevitScriptTabs:
            # creates pyrevitribbonpanels for existing or newly created panels
            pyrevitribbonpanels = dict()
            if scriptTab.hascommands():
                try:
                    #try creating the ribbon tab
                    reportv('Creating {0} ribbon tab...'.format(scriptTab.tabName))
                    __revit__.CreateRibbonTab(scriptTab.tabName)
                except:
                    #if fails, the tab already exits so let's gather panel info
                    reportv('{0} ribbon tab already created...'.format(scriptTab.tabName))
                    pyrevitribbonpanels = {p.Name: p for p in __revit__.GetRibbonPanels(scriptTab.tabName)}

                #by this point the ribbon tab has either been created or found if existing.
                reportv('Searching for panels...')
                for panel in scriptTab.get_sorted_scriptpanels():
                    if panel.panelName in pyrevitribbonpanels.keys():
                        reportv('Existing panel found: {0}'.format(panel.panelName))
                        scriptTab.pyRevitUIPanels[panel.panelName] = pyrevitribbonpanels[panel.panelName]
                        scriptTab.pyRevitUIButtons[panel.panelName] = list(pyrevitribbonpanels[panel.panelName].GetItems())
                    else:
                        reportv('Creating panel: {0}'.format(panel.panelName))
                        newpanel = __revit__.CreateRibbonPanel(scriptTab.tabName, panel.panelName)
                        scriptTab.pyRevitUIPanels[panel.panelName] = newpanel
                        scriptTab.pyRevitUIButtons[panel.panelName] = []
            else:
                reportv('{0} ribbon tab found but does not include any scripts. ' \
                        'Skipping this tab.'.format(scriptTab.tabName))

    def createui(self):
        newbuttoncount = updatedbuttoncount = 0
        for scriptTab in self.pyRevitScriptTabs:
            for scriptPanel in scriptTab.get_sorted_scriptpanels():
                pyrevitribbonpanel = scriptTab.pyRevitUIPanels[scriptPanel.panelName]
                pyrevitribbonitemsdict = {b.Name: b for b in scriptTab.pyRevitUIButtons[scriptPanel.panelName]}
                reportv('Creating\\Updating ribbon items for panel: {0}'.format(scriptPanel.panelName))
                for scriptGroup in scriptPanel.get_sorted_scriptgroups():
                    # PulldownButton or SplitButton
                    groupispulldownbutton = (scriptGroup.groupType == sessionSettings.pulldownButtonTypeName)
                    groupissplitbutton = (scriptGroup.groupType == sessionSettings.splitButtonTypeName or \
                                          scriptGroup.groupType == sessionSettings.splitPushButtonTypeName )
                    if groupispulldownbutton or groupissplitbutton:
                        # PulldownButton
                        if scriptGroup.groupType == sessionSettings.pulldownButtonTypeName:
                            if scriptGroup.groupName not in pyrevitribbonitemsdict:
                                reportv('\tCreating pulldown button group: {0}'.format(scriptGroup.groupName))
                                ribbonitem = pyrevitribbonpanel.AddItem(
                                    PulldownButtonData(scriptGroup.groupName, scriptGroup.groupName))
                            else:
                                reportv('\tUpdating pulldown button group: {0}'.format(scriptGroup.groupName))
                                ribbonitem = pyrevitribbonitemsdict.pop(scriptGroup.groupName)

                        # SplitButton
                        elif scriptGroup.groupType == sessionSettings.splitButtonTypeName:
                            if scriptGroup.groupName not in pyrevitribbonitemsdict.keys():
                                reportv('\tCreating split button group: {0}'.format(scriptGroup.groupName))
                                ribbonitem = pyrevitribbonpanel.AddItem(
                                    SplitButtonData(scriptGroup.groupName, scriptGroup.groupName))
                            else:
                                reportv('\tUpdating split button group: {0}'.format(scriptGroup.groupName))
                                ribbonitem = pyrevitribbonitemsdict.pop(scriptGroup.groupName)

                        # SplitPushButton
                        elif scriptGroup.groupType == sessionSettings.splitPushButtonTypeName:
                            if scriptGroup.groupName not in pyrevitribbonitemsdict.keys():
                                reportv('\tCreating split button group: {0}'.format(scriptGroup.groupName))
                                ribbonitem = pyrevitribbonpanel.AddItem(
                                    SplitButtonData(scriptGroup.groupName, scriptGroup.groupName))
                            else:
                                reportv('\tUpdating split button group: {0}'.format(scriptGroup.groupName))
                                ribbonitem = pyrevitribbonitemsdict.pop(scriptGroup.groupName)
                            ribbonitem.IsSynchronizedWithCurrentItem = False

                        ribbonitem.Image = scriptGroup.buttonIcons.smallBitmap
                        ribbonitem.LargeImage = scriptGroup.buttonIcons.largeBitmap
                        existingribbonitempushbuttonsdict = {b.ClassName: b for b in ribbonitem.GetItems()}

                        for cmd in scriptGroup.commands:
                            if cmd.className not in existingribbonitempushbuttonsdict:
                                reportv('\t\tCreating push button: {0}'.format(cmd.className))
                                buttondata = PushButtonData(cmd.className, cmd.cmdName, self.newAssemblyLocation,
                                                            cmd.className)
                                buttondata.ToolTip = cmd.tooltip
                                ldesc = 'Class Name:\n{0}\n\nAssembly Name:\n{1}'.format(cmd.className,
                                                                                         self.sessionname)
                                buttondata.LongDescription = ldesc
                                if cmd.buttonIcons:
                                    if groupissplitbutton:
                                        buttondata.LargeImage = cmd.buttonIcons.largeBitmap
                                    else:
                                        buttondata.LargeImage = cmd.buttonIcons.mediumBitmap
                                else:
                                    if groupissplitbutton:
                                        buttondata.LargeImage = scriptGroup.buttonIcons.largeBitmap
                                    else:
                                        buttondata.LargeImage = scriptGroup.buttonIcons.mediumBitmap
                                ribbonitem.AddPushButton(buttondata)
                                newbuttoncount += 1
                            else:
                                reportv('\t\tUpdating push button: {0}'.format(cmd.className))
                                pushbutton = existingribbonitempushbuttonsdict.pop(cmd.className)
                                pushbutton.ToolTip = cmd.tooltip
                                ldesc = 'Class Name:\n{0}\n\nAssembly Name:\n{1}'.format(cmd.className,
                                                                                         self.sessionname)
                                pushbutton.LongDescription = ldesc
                                pushbutton.Enabled = True
                                if sessionSettings.reloadScriptsOverrideName not in pushbutton.Name:
                                    pushbutton.AssemblyName = self.newAssemblyLocation
                                if cmd.buttonIcons:
                                    if groupissplitbutton:
                                        pushbutton.LargeImage = cmd.buttonIcons.largeBitmap
                                    else:
                                        pushbutton.LargeImage = cmd.buttonIcons.mediumBitmap
                                else:
                                    if groupissplitbutton:
                                        pushbutton.LargeImage = scriptGroup.buttonIcons.largeBitmap
                                    else:
                                        pushbutton.LargeImage = scriptGroup.buttonIcons.mediumBitmap
                                updatedbuttoncount += 1
                        for orphanedButtonName, orphanedButton in existingribbonitempushbuttonsdict.items():
                            reportv('\tDisabling orphaned button: {0}'.format(orphanedButtonName))
                            orphanedButton.Enabled = False

                    # StackedButtons
                    elif scriptGroup.groupType == sessionSettings.stackedThreeTypeName:
                        reportv('\tCreating\\Updating 3 stacked buttons: {0}'.format(scriptGroup.groupType))
                        stackcommands = []
                        for cmd in scriptGroup.commands:
                            if cmd.className not in pyrevitribbonitemsdict:
                                reportv('\t\tCreating stacked button: {0}'.format(cmd.className))
                                buttondata = PushButtonData(cmd.className, cmd.cmdName, self.newAssemblyLocation,
                                                            cmd.className)
                                buttondata.ToolTip = cmd.tooltip
                                ldesc = 'Class Name:\n{0}\n\nAssembly Name:\n{1}'.format(cmd.className,
                                                                                         self.sessionname)
                                buttondata.LongDescription = ldesc
                                if cmd.buttonIcons:
                                    buttondata.Image = cmd.buttonIcons.smallBitmap
                                else:
                                    buttondata.Image = scriptGroup.buttonIcons.smallBitmap
                                stackcommands.append(buttondata)
                                newbuttoncount += 1
                            else:
                                reportv('\t\tUpdating stacked button: {0}'.format(cmd.className))
                                ribbonitem = pyrevitribbonitemsdict.pop(cmd.className)
                                ribbonitem.AssemblyName = self.newAssemblyLocation
                                ribbonitem.ClassName = cmd.className
                                ribbonitem.Enabled = True
                                updatedbuttoncount += 1
                                if cmd.buttonIcons:
                                    ribbonitem.Image = cmd.buttonIcons.smallBitmap
                                else:
                                    ribbonitem.Image = scriptGroup.buttonIcons.smallBitmap
                        if len(stackcommands) == 3:
                            pyrevitribbonpanel.AddStackedItems(*stackcommands)

                    # PushButton
                    elif scriptGroup.groupType == sessionSettings.pushButtonTypeName and not scriptGroup.islinkbutton():
                        try:
                            cmd = scriptGroup.commands.pop()
                            if cmd.className not in pyrevitribbonitemsdict:
                                reportv('\tCreating push button: {0}'.format(cmd.className))
                                ribbonitem = pyrevitribbonpanel.AddItem(
                                    PushButtonData(cmd.className, scriptGroup.groupName, self.newAssemblyLocation,
                                                   cmd.className))
                                newbuttoncount += 1
                            else:
                                reportv('\tUpdating push button: {0}'.format(cmd.className))
                                ribbonitem = pyrevitribbonitemsdict.pop(cmd.className)
                                ribbonitem.AssemblyName = self.newAssemblyLocation
                                ribbonitem.ClassName = cmd.className
                                ribbonitem.Enabled = True
                                updatedbuttoncount += 1
                            ribbonitem.ToolTip = cmd.tooltip
                            ldesc = 'Class Name:\n{0}\n\nAssembly Name:\n{1}'.format(cmd.className,
                                                                                     self.sessionname)
                            ribbonitem.LongDescription = ldesc
                            ribbonitem.Image = scriptGroup.buttonIcons.smallBitmap
                            ribbonitem.LargeImage = scriptGroup.buttonIcons.largeBitmap
                        except:
                            reportv(
                                '\tPushbutton has no associated scripts. Skipping {0}'.format(scriptGroup.sourceFile))
                            continue

                    # SmartButton
                    elif scriptGroup.groupType == sessionSettings.smartButtonTypeName \
                    and not scriptGroup.islinkbutton():
                        try:
                            cmd = scriptGroup.commands.pop()
                            if cmd.className not in pyrevitribbonitemsdict:
                                reportv('\tCreating smart button: {0}'.format(cmd.className))
                                ribbonitem = pyrevitribbonpanel.AddItem(
                                    PushButtonData(cmd.className, scriptGroup.groupName, self.newAssemblyLocation,
                                                   cmd.className))
                                reportv('\tSmart button created.')
                                newbuttoncount += 1
                            else:
                                reportv('\tUpdating push button: {0}'.format(cmd.className))
                                ribbonitem = pyrevitribbonitemsdict.pop(cmd.className)
                                ribbonitem.AssemblyName = self.newAssemblyLocation
                                ribbonitem.ClassName = cmd.className
                                ribbonitem.Enabled = True
                                updatedbuttoncount += 1
                            ribbonitem.ToolTip = cmd.tooltip
                            ldesc = 'Class Name:\n{0}\n\nAssembly Name:\n{1}'.format(cmd.className,
                                                                                     self.sessionname)
                            ribbonitem.LongDescription = ldesc
                            importedscript = __import__(cmd.getscriptbasename())
                            importedscript.selfInit(__revit__, cmd.getfullscriptaddress(), ribbonitem)
                            reportv('\tSmart button initialized.')
                        except:
                            reportv(
                                '\tSmart button has no associated scripts. Skipping {0}'.format(scriptGroup.sourceFile))
                            continue

                    # LinkButton
                    elif scriptGroup.groupType == sessionSettings.linkButtonTypeName and scriptGroup.islinkbutton():
                        if scriptGroup.groupName not in pyrevitribbonitemsdict:
                            reportv('\tCreating push button link to other assembly: {0}'.format(scriptGroup.groupName))
                            ribbonitem = pyrevitribbonpanel.AddItem(
                                PushButtonData(scriptGroup.groupName, scriptGroup.groupName,
                                               scriptGroup.assemblyLocation,
                                               scriptGroup.assemblyName + '.' + scriptGroup.assemblyClassName))
                            newbuttoncount += 1
                        else:
                            reportv('\tUpdating push button link to other assembly: {0}'.format(scriptGroup.groupName))
                            ribbonitem = pyrevitribbonitemsdict.pop(scriptGroup.groupName)
                            ribbonitem.AssemblyName = scriptGroup.assemblyLocation
                            ribbonitem.ClassName = scriptGroup.assemblyName + '.' + scriptGroup.assemblyClassName
                            ribbonitem.Enabled = True
                            updatedbuttoncount += 1
                        ribbonitem.Image = scriptGroup.buttonIcons.smallBitmap
                        ribbonitem.LargeImage = scriptGroup.buttonIcons.largeBitmap

                # now disable all orphaned buttons in this panel
                for orphanedRibbonItemName, orphanedRibbonItem in pyrevitribbonitemsdict.items():
                    reportv('\tDisabling orphaned ribbon item: {0}'.format(orphanedRibbonItemName))
                    orphanedRibbonItem.Enabled = False

        # final report
        reportv('\n\n')
        report('{0} buttons created...\n{1} buttons updated...\n\n'.format(newbuttoncount, updatedbuttoncount))

    def createpyrevitui(self):
        # setting up UI
        report('Now setting up ribbon, panels, and buttons...')
        self.create_or_find_pyrevit_panels()
        report('Ribbon tab and panels are ready. Creating script groups and command buttons...')
        self.createui()
        report('All UI items have been added...')


# MAIN
__window__.Width = 1100
# __window__.Close()
# find pyRevit home directory and initialize current session
t = Timer()
report('Running on:\n{0}'.format(sys.version))
sessionSettings = PyRevitUISettings()
session = PyRevitUISession()
report('Load time: {}'.format(t.get_time_hhmmss()))