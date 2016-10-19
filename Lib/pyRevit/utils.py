import os
import os.path as op
import subprocess as sp
import time


class Timer:
    """Timer class using python native time module."""
    def __init__(self):
        self.start = time.time()

    def restart(self):
        self.start = time.time()

    def get_time_hhmmss(self):
        return "%02.2f seconds" % (time.time() - self.start)


class ScriptFileContents:
    def __init__(self, file_address):
        self.filecontents = ''
        with open(file_address, 'r') as f:
            self.filecontents = f.readlines()

    def extract_param(self, param):
        param_str_found = False
        param_str = ''
        param_finder = re.compile(param + '\s*=\s*[\'\"](.*)[\'\"]', flags=re.IGNORECASE)
        param_finder_ex = re.compile('^\s*[\'\"](.*)[\'\"]', flags=re.IGNORECASE)
        for thisline in self.filecontents:
            if not param_str_found:
                values = param_finder.findall(thisline)
                if values:
                    param_str = values[0]
                    param_str_found = True
                continue
            elif param_str_found:
                values = param_finder_ex.findall(thisline)
                if values:
                    param_str += values[0]
                    continue
                break
        cleaned_param_str = param_str.replace('\\\'', '\'').replace('\\"', '\"').replace('\\n', '\n').replace('\\t', '\t')
        if '' != cleaned_param_str:
            return cleaned_param_str
        else:
            return None


def assert_folder(folder):
    """Checks if the folder exists and if not creates the folder.
    Returns OSError on folder making errors."""
    if not op.exists(folder):
        try:
            os.makedirs(folder)
        except OSError as err:
            raise err
    return True


def get_parent_directory(path):
    return op.dirname(path)


def run_process(proc, cwd=''):
    return sp.Popen(proc, stdout=sp.PIPE, stderr=sp.PIPE, cwd=cwd, shell=True)