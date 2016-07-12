import os
import subprocess
import re
import logging

class ScriptExecutor:
    _logger = logging.getLogger(__name__)

    def __init__(self, path, script_name, suffix_list=['', '.py', '.sh'], path_overrides=[]):
        self.path = path
        self.script_name = script_name
        self.suffix_list = suffix_list
        self.path_overrides = path_overrides
        try:
            self.check()
        except Exception as err:
            raise err

    def check(self):
        allpaths = self.path_overrides + [self.path]

        match=False
        matchcmd = None 
        for p in allpaths:
            for cmd in [ '/'.join([p, self.script_name]) + x for x in self.suffix_list ]:
                if os.path.exists(cmd) and os.access(cmd, os.R_OK ^ os.X_OK): 
                    if not match:
                        match=True
                        matchcmd = cmd
                    else:
                        # ambiguous
                        raise ValueError("input script is ambiguous: match cmd=" + str(cmd) + " previous match="+str(matchcmd))
                if matchcmd:
                    continue
                
        if matchcmd:
            self.thecmd = matchcmd
        else:
            raise Exception("cannot locate executable input script: " + self.script_name + "("+'|'.join(self.suffix_list)+")")

        return(True)
        
    def execute(self, capture_output=False, cmdline=None, **kwargs):
        output = list()
        script = self.thecmd
        if not os.access(script, os.R_OK ^ os.X_OK) or re.match(".*~$", script):
            raise Exception("Command not executable or is invalid filename: " + script)

        if cmdline:
            cmd = [script] + cmdline.split()
        else:
            cmd = [script]

        self._logger.debug('Executing script: %s' % ' '.join(cmd))

        if capture_output:
            try:
                output.append((' '.join(cmd), 0, subprocess.check_output(cmd, stderr=subprocess.STDOUT, **kwargs)))
            except subprocess.CalledProcessError as e:
                output.append((' '.join(cmd), e.returncode, e.output))
        else:
            output.append((' '.join(cmd), subprocess.call(cmd, **kwargs), None))

        self._logger.debug('%s return code %d, output: %s' % output[-1])

        return(output[0])

class ScriptSetExecutor:
    """
    A script module is a module for executing a set of user-provided scripts found in a specific directory in
    lexicographically sorted order

    """
    _logger = logging.getLogger(__name__)

    def __init__(self, path, file_prefix='', ascending=True, suffix_list=['', '.sh', '.py'], path_overrides=[]):
        assert path is not None

        self.inputdir = path
        self.prefix = file_prefix
        self.sort_ascending = ascending
        self.path_overrides = path_overrides
        self.suffix_list = suffix_list
        self.allpaths = list()
        try:
            self.check()
        except Exception as err:
            raise err

    def check(self, init_if_missing=False):
        """
        Check the path and construct if not found and init_if_missing=True
        :param init_if_missing: create the path if not found
        :return: true if exists false if not
        """

        
        for d in self.path_overrides + [self.inputdir]:            
            if os.path.exists(d):
                self.allpaths.append(d)
        if len(self.allpaths) > 0:
            return(True)

        if init_if_missing:
            os.makedirs(self.inputdir)
            return True

    def get_scripts(self):
        """
        Get the scripts at the path in sorted order as set in the module properties
        :return: a sorted list of scripts
        """
        ret = list()
        for d in self.allpaths:
            scripts = filter(lambda x: x.startswith(self.prefix), os.listdir(d))
            scripts.sort(reverse=(not self.sort_ascending))
            ret = ret + [os.path.join(d, x) for x in scripts]

        return(ret)

    def execute(self, capture_output=False, fail_fast=False, cmdline=None, **kwargs):
        """
        Pass in the kwargs as --<name> <value> pairs.
        :param capture_output: if True then return output of script in return dict. If False, only return code
        :param fail_fast:if True then quit execution after first non-zero return code, else execute all
        :returns list of (script, returncode, stdout) tuples in order of execution
        """

        scripts = self.get_scripts()
        output = []

        for script in scripts:
            if not os.access(script, os.R_OK ^ os.X_OK) or re.match(".*~$", script):
                # Skip any that are not executable (e.g. README or txt files)
                continue

            self._logger.debug('Executing script: %s' % script)

            if cmdline:
                cmd = [script] + cmdline.split()
            else:
                cmd = [script]

            if capture_output:
                try:
                    outstr = subprocess.check_output(cmd, stderr=subprocess.STDOUT, **kwargs)
                    outstr = outstr.decode('utf8')
                    #outstr = rawstr.encode('utf8')
                    output.append((' '.join(cmd), 0, outstr))
                except subprocess.CalledProcessError as e:
                    outstr = e.output.decode('utf8')
                    #outstr = rawstr.encode('utf8')
                    output.append((' '.join(cmd), e.returncode, outstr))
            else:
                output.append((' '.join(cmd), subprocess.call(cmd, **kwargs), None))

            self._logger.debug('%s return code %d, output: %s' % output[-1])

            if fail_fast and output[-1][1]:
                break

        return output

