import tempfile
import os

from zipfile import ZipFile
from zipfile import ZIP_STORED

from cfg.installer import folderConfig

class CodePathError(Exception):
    def __init__(self, message):
        self._message = message

    def __str__(self):
        return self._message
    
    @property
    def message(self):
        return self._message


def requiredProp(cfg, key):
    if key in cfg: return cfg[key]
    raise CodePathError("Missing required configuration property %s" % key)

def get_all_file_pairs(base_path, home_path):
    file_pairs = []
    base_offset = len(base_path) + 1
    for (root, dirnames, files) in os.walk(home_path):
        for filename in files:
            srcpath = os.path.join(root, filename)
            dstpath = './' + srcpath[base_offset:]
            pair = {'src':srcpath, 'dst':dstpath}
            file_pairs.append(pair)
    return file_pairs    

def make_zip_file(zip_file_path, file_pairs):
    with ZipFile(zip_file_path, mode='w', compression=ZIP_STORED) as zip:
        for pair in file_pairs:
            zip.write(pair['src'], pair['dst'])

def bytes_file(file_path):
    f = open(file_path, 'rb')
    byte_array = f.read()
    f.close()
    return byte_array

def get_zip_code_bytes(functionName, mainBase, mainPath, auxBase, auxPaths):
    zipFilePath = os.path.join(tempfile.gettempdir(), functionName+".zip")
    aggregateFilePairs = []
    main_pairs = get_all_file_pairs(mainBase, mainPath)
    if len(main_pairs) == 0:
        realMainPath = os.path.realpath(mainPath)
        raise CodePathError("No code files found for {} on path {}".format(functionName, realMainPath))
    aggregateFilePairs.extend(main_pairs)
    for auxPath in auxPaths:
        aux_pairs = get_all_file_pairs(auxBase, auxPath)
        aggregateFilePairs.extend(aux_pairs)
    sortedFilePairs = sorted(aggregateFilePairs, key=(lambda pair: pair['src']))
    make_zip_file(zipFilePath, sortedFilePairs)
    return bytes_file(zipFilePath)

def get_lambda_code_bytes(baseFunctionName, libs, includeCfg, typeFolder):
    folderCfg = folderConfig()
    codeHome = requiredProp(folderCfg, 'CodeHome')
    lambdaFolder = requiredProp(folderCfg, 'LambdaFolder')
    libFolder = requiredProp(folderCfg, 'LibFolder')
    cfgFolder = requiredProp(folderCfg, 'CfgFolder')
    mainCodePath = os.path.join(codeHome, lambdaFolder, typeFolder, baseFunctionName)
    mainCodeBase = mainCodePath
    auxPaths = []
    for lib in libs:
        libPath = os.path.join(codeHome, libFolder, lib)
        auxPaths.append(libPath)
    if includeCfg:
        cfgPath = os.path.join(codeHome, cfgFolder)
        auxPaths.append(cfgPath)
    return get_zip_code_bytes(baseFunctionName, mainCodeBase, mainCodePath, codeHome, auxPaths)

def getAvailableRules():
    folderCfg = folderConfig()
    codeHome = requiredProp(folderCfg, 'CodeHome')
    lambdaFolder = requiredProp(folderCfg, 'LambdaFolder')
    typeFolder = requiredProp(folderCfg, 'RulesFolder')
    ruleMain = requiredProp(folderCfg, 'RuleMain')
    searchPath = os.path.join(codeHome, lambdaFolder, typeFolder)
    ruleNames = []
    for (root, dirnames, files) in os.walk(searchPath):
        for filename in files:
            if filename == ruleMain:
                (rhead, rtail) = os.path.split(root)
                if rtail:
                    ruleNames.append(rtail)
    return ruleNames    

def getCoreCode(baseFunctionName):
    libs = ['base', 'rdq', 'lambdas']
    includeCfg = True
    typeFolder = 'core'
    return get_lambda_code_bytes(baseFunctionName, libs, includeCfg, typeFolder)

def getRuleCode(baseFunctionName):
    libs = ['base', 'rdq', 'rule', 'cfn']
    includeCfg = False
    folderCfg = folderConfig()
    typeFolder = requiredProp(folderCfg, 'RulesFolder')
    return get_lambda_code_bytes(baseFunctionName, libs, includeCfg, typeFolder)

def getTestCode(baseFunctionName):
    libs = ['base', 'rdq', 'rule', 'cfn']
    includeCfg = True
    typeFolder = 'test'
    return get_lambda_code_bytes(baseFunctionName, libs, includeCfg, typeFolder)
