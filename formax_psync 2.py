import sublime, sublime_plugin
import os,sys,subprocess,re
import traceback
import FormaxPsync.simplejson as json
configs = {}
nestingLimit = 30
configName = '.formax_sublime'
isDebug = True
isLoaded = False
# print overly informative messages?
isDebugVerbose = True
debugJson = False
messageTimeout = 250
removeLineComment = re.compile('//.*', re.I)
from time import sleep
class FormaxPsyncCommand(sublime_plugin.WindowCommand):
    def run(self, edit=None):

        # self.window_id =sublime.Window.id(self)
        if hasActiveView() is False:
            file_path = os.path.dirname(guessConfigFile(sublime.active_window().folders()))
        else :
            file_path = os.path.dirname(sublime.active_window().active_view().file_name())

        userConfig = getUserConfig()
        if userConfig is None:
            printMessage("ERROR please init config file!")
            return 
        result = verifyConfig(userConfig)
        if result is not True:
            printMessage(result)
            return
        projectPath =getProjectRoot()
        print(projectPath)
        os.chdir(projectPath)
        # print(userConfig)
        cmd = userConfig['action']
        # cmd = 'bash bin/psync.sh -h {host} -v {version}'.format(**userConfig)
        # result = subprocess.Popen(cmd,shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT).stdout.readlines()
        # for line in result:
        #     print(line.decode())
        try:
            # p=os.popen(cmd) #2.6之后被放弃
            # print(p.read()) #有编码问题
            
            # run_cmd ="python3 cmd.py '"+projectPath+"' '"+cmd+"'"
            # p=os.popen(run_cmd)
            # print(p.read())
            # 拿不到输出
         
      

            p=subprocess.Popen(cmd,shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,executable='/bin/bash')
            p.wait()
            if p.returncode == 0:
                msg =p.stdout.read().decode('utf-8')
                if "失败" in msg :
                    printMessage("Command ["+cmd+"] run failed",status=True)
                    sublime.error_message(msg)
                else :
                    printMessage("Command ["+cmd+"] run succeeded",status=True)
                print(msg)
            else :
                printMessage("Command ["+cmd+"] run failed",status=True)
                # printMessage(p.read())
                print(p.stdout.read().decode('utf-8'))
        except Exception as e:

            printMessage("Command ["+cmd+"] failed!!! [Exception: "+stringifyException(e)+"]")

        # print(output)
      
class AutoPsync(sublime_plugin.EventListener):
    def on_post_save(self,view): 
        print('*'*50)    
         
        userConfig = getUserConfig()
        if userConfig is None :
            return
        if 'action_on_save' not in userConfig or userConfig['action_on_save'] == False:
            return
        print('run psync command')
        sublime.active_window().run_command('formax_psync')

def getUserConfig():
    projectPath = getProjectRoot()
    if projectPath is None:
        return None
    try:
        userConfig = parseJson(projectPath+'/'+configName)
    except Exception as e:
        printMessage("Failed parsing configuration file: {" + file_path + "} (commas problem?) [Exception: " + stringifyException(e) + "]", status=True)
        return None
    return userConfig
def hasActiveView():
    window = sublime.active_window()
    if window is None:
        return False

    view = window.active_view()
    if view is None or view.file_name() is None:
        return False
    return True
# Returns first found config file from folders
#
# @type  folders: list<string>
# @param folders: list of paths to folders to search in
#
# @return config filepath
def guessConfigFile(folders):
    for folder in folders:
        config = getConfigFile(folder)
        if config is not None:
            return config

        for folder in os.walk(folder):
            config = getConfigFile(folder[0])
            if config is not None:
                return config

    return None
# Returns configuration file for a given file
#
# @type  file_path: string
# @param file_path: file_path to the file for which we try to find a config
#
# @return file path to the config file or None
#
# @global configs
def getConfigFile(file_path):
    cacheKey = file_path
    if isString(cacheKey) is False:
        cacheKey = cacheKey.decode('utf-8')

    # try cached
    try:
        if configs[cacheKey] and os.path.exists(configs[cacheKey]) and os.path.getsize(configs[cacheKey]) > 0:
            # printMessage("Loading config: cache hit (key: " + cacheKey + ")")
            
            return configs[cacheKey]
        else:
            raise KeyError

    # cache miss
    except KeyError:
        try:
            folders = getFolders(file_path)

            if folders is None or len(folders) == 0:
                return None

            configFolder = findConfigFile(folders)

            if configFolder is None:
                # printMessage("Found no config for {" + cacheKey + "}", None, True)
                return None

            config = os.path.join(configFolder, configName)
            configs[cacheKey] = config

            return config

        except AttributeError:
            return None
# Finds a config file in given folders
#
# @type  folders: list<string>
# @param folders: list of paths to folders to filter
#
# @return list<string> of file paths
#
# @global configName
def findConfigFile(folders):
    return findFile(folders, configName)
def getProjectRoot():
    if hasActiveView() is False:
        file_path = os.path.dirname(guessConfigFile(sublime.active_window().folders()))
        
    else :
        file_path = os.path.dirname(sublime.active_window().active_view().file_name())
    temp = getConfigFile(file_path)
    if temp is  None:
        return temp
    return os.path.dirname(getConfigFile(file_path))
        

# Returns path of file from its config file
#
# @type  file_path: string
# @param file_path: file path to the file of which we want the hash
#
# @return string file path from settings root
def getRootPath(file_path, prefix = ''):
    return prefix + os.path.relpath(file_path, os.path.dirname(getConfigFile(file_path))).replace('\\', '/')


# Returns a file path associated with view
#
# @type  file_path: string
# @param file_path: file path to the file of which we want the hash
#
# @return string file path
def getFileName(view):
    return view.file_name()

def verifyConfig(config):
    if type(config) is not dict:
        return "Config is not a {dict} type"
    keys = ['action','action_on_save']
    for key in keys:
        if key not in config:
            return "Config is missing a {" + key + "} key"
    if config['action'] is not None and isString(config['action']) is False:
        return "Config entry 'action' must be null or string, " + str(type(config['action'])) + " given"
    # if config['version'] is not None and isString(config['version']) is False:
    #     return "Config entry 'version' must be null or string, " + str(type(config['version'])) + " given"
    return True
# Finds a real file path among given folder paths
# and returns the path or None
#
# @type  folders: list<string>
# @param folders: list of paths to folders to look into
# @type  file_name: string
# @param file_name: file name to search
#
# @return string file path or None
def findFile(folders, file_name):
    if folders is None:
        return None

    for folder in folders:
        if isString(folder) is False:
            folder = folder.decode('utf-8')

        if os.path.exists(os.path.join(folder, file_name)) is True:
            return folder

    return None
def isString(var):
    var_type = type(var)

    if sys.version[0] == '3':
        return var_type is str or var_type is bytes
    else:
        return var_type is str or var_type is unicode
# Get all folders paths from given path upwards
#
# @type  file_path: string
# @param file_path: absolute file path to return the paths from
#
# @return list<string> of file paths
#
# @global nestingLimit
def getFolders(file_path):
    if file_path is None:
        return []

    folders = [file_path]
    limit = nestingLimit

    while True:
        split = os.path.split(file_path)

        # nothing found
        if len(split) == 0:
            break

        # get filepath
        file_path = split[0]
        limit -= 1

        # nothing else remains
        if len(split[1]) == 0 or limit < 0:
            break

        folders.append(split[0])

    return folders
# Prints a special message to console and optionally to status bar
#
# @type  text: string
# @param text: message to status bar
# @type  name: string|None
# @param name: comma-separated list of connections or other auxiliary info
# @type  onlyVerbose: boolean
# @param onlyVerbose: print only if config has debug_verbose enabled
# @type  status: boolean
# @param status: show in status bar as well = true
#
# @global isDebug
# @global isDebugVerbose
def printMessage(text, name=None, onlyVerbose=False, status=False):
    message = "Formax_Sublime"

    if name is not None:
        message += " [" + name + "]"

    message += " > "
    message += text

    if isDebug and (onlyVerbose is False or isDebugVerbose is True):
        # print (message.encode('utf-8'))
        print (message)

    if status:
        dumpMessage(message)
# Issues a system notification for certian event
#
# @type text: string
# @param text: notification message
def systemNotify(text):
    try:
        import subprocess

        text = "Formax_Sublime > " + text

        if sys.platform == "darwin":
            """ Run Grown Notification """
            cmd = '/usr/local/bin/growlnotify -a "Sublime Text 3" -t "psync message" -m "'+text+'"'
            subprocess.call(cmd,shell=True)
        elif sys.platform == "linux2":
            subprocess.call('/usr/bin/notify-send "Sublime Text 3" "'+text+'"',shell=True)
        elif sys.platform == "win32":
            """ Find the notifaction platform for windows if there is one"""

    except Exception as e:
        printMessage("Notification failed")
        handleExceptions(e)
# Schedules a single message to be logged/shown
#
# @type  text: string
# @param text: message to status bar
#
# @global messageTimeout
def dumpMessage(text):
    sublime.set_timeout(lambda: statusMessage(text), messageTimeout)

# Parses given config and adds default values to each connection entry
#
# @type  file_path: string
# @param file_path: file path to the file of which we want the hash
#
# @return config dict or None
#
# @global isLoaded
# @global coreConfig
# @global projectDefaults
def loadConfig(file_path):

    if isLoaded is False:
        printMessage("FTPSync is not loaded (just installed?), please restart Sublime Text")
        return None

    if isString(file_path) is False:
        printMessage("LoadConfig expects string, " + str(type(file_path)) + " given")
        return None

    if os.path.exists(file_path) is False:
        return None

    # parse config
    try:
        config = parseJson(file_path)
    except Exception as e:
        printMessage("Failed parsing configuration file: {" + file_path + "} (commas problem?) [Exception: " + stringifyException(e) + "]", status=True)
        handleException(e)
        return None

    result = {}

    # merge with defaults and check
    for name in config:
        if type(config[name]) is not dict:
            printMessage("Failed using configuration: contents are not dictionaries but values", status=True)
            return None

        result[name] = dict(list(projectDefaults.items()) + list(config[name].items()))
        result[name]['file_path'] = file_path

        # fix path
        if len(result[name]['path']) > 1 and result[name]['path'][-1] != "/":
            result[name]['path'] = result[name]['path'] + "/"

        # merge nested
        for index in nested:
            list1 = list(list(projectDefaults.items())[index][1].items())
            list2 = list(result[name][list(projectDefaults.items())[index][0]].items())

            result[name][list(projectDefaults.items())[index][0]] = dict(list1 + list2)
        try:
            if result[name]['debug_extras']['dump_config_load'] is True:
                print(result[name])
        except KeyError:
            pass

        # add passwords
        if file_path in passwords and name in passwords[file_path] and passwords[file_path][name] is not None:
            result[name]['password'] = passwords[file_path][name]

        result[name] = updateConfig(result[name])

        verification_result = verifyConfig(result[name])

        if verification_result is not True:
            printMessage("Invalid configuration loaded: <" + str(verification_result) + ">", status=True)

    # merge with generics
    final = dict(list(coreConfig.items()) + list({"connections": result}.items()))

    # override by overridingConfig
    if file_path in overridingConfig:
        for name in overridingConfig[file_path]['connections']:
            if name in final['connections']:
                for item in overridingConfig[file_path]['connections'][name]:
                    final['connections'][name][item] = overridingConfig[file_path]['connections'][name][item]

    return final
# Parses JSON-type file with comments stripped out (not part of a proper JSON, see http://json.org/)
#
# @type  file_path: string
#
# @return dict|None
#
# @global removeLineComment
def parseJson(file_path):
    attempts = 3
    succeeded = False

    while attempts > 0:
        attempts = attempts - 1
        try:
            json = parseJsonInternal(file_path)
            if debugJson:
                printMessage("Type returned: " + str(type(json)))
                printMessage("Is empty: " + str(bool(json)))

            succeeded = type(json) is dict and bool(json) is True
            break
        except Exception as e:
            handleException(e)
            printMessage("Retrying reading config... (remaining " + str(attempts) + ")")
            sleep(0.1)

    if succeeded:
        return json
    else:
        printMessage("Failed to read settings from file: " + str(file_path))
        return {}

# Parses JSON-type file with comments stripped out (not part of a proper JSON, see http://json.org/)
#
# @type  file_path: string
#
# @return dict
#
# @global removeLineComment
def parseJsonInternal(file_path):
    if isString(file_path) is False:
        raise Exception("Expected filepath as string, " + str(type(file_path)) + " given")

    if os.path.exists(file_path) is False:
        raise IOError("File " + str(file_path) + " does not exist")

    if os.path.getsize(file_path) == 0:
        raise IOError("File " + str(file_path) + " is empty")

    contents = ""

    try:
        file = open(file_path, 'r')

        for line in file:
            contents += removeLineComment.sub('', line).strip()
    finally:
        file.close()

    decoder = json.JSONDecoder()

    if debugJson:
        printMessage("Debug JSON:")
        print ("="*86)
        print (contents)
        print ("="*86)

    if len(contents) > 0:
        return decoder.decode(contents)
    else:
        raise IOError('Content read from ' + str(file_path) + ' is empty')
# Safer print of exception message
def stringifyException(exception):
    return str(exception)
# Dumps the exception to console
def handleException(exception):
    print ("Formax_Sublime > Exception in user code:")
    print ('-' * 60)
    traceback.print_exc(file=sys.stdout)
    print ('-' * 60)

def statusMessage(text):
    sublime.status_message(text)
