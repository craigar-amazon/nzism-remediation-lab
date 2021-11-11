import tempfile
import os

from zipfile import ZipFile
from zipfile import ZIP_STORED
from lib.rdq import Profile
from lib.rdq.iam import IamClient

from cfg import codeConfig

def requiredProp(cfg, key):
    if key in cfg: return cfg[key]
    raise Exception("Missing required configuration property %s" % key)

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

def get_zip_code_bytes(functionName, mainBase, mainPath, libBase, libPaths):
    zipFilePath = os.path.join(tempfile.gettempdir(), functionName+".zip")
    aggregateFilePairs = []
    main_pairs = get_all_file_pairs(mainBase, mainPath)
    if len(main_pairs) == 0:
        realMainPath = os.path.realpath(mainPath)
        raise Exception("No code files found for {} on path {}".format(functionName, realMainPath))
    aggregateFilePairs.extend(main_pairs)
    for libPath in libPaths:
        lib_pairs = get_all_file_pairs(libBase, libPath)
        aggregateFilePairs.extend(lib_pairs)
    make_zip_file(zipFilePath, aggregateFilePairs)
    return bytes_file(zipFilePath)

def get_lambda_code_bytes(baseFunctionName, libs, isRule):
    codeCfg = codeConfig()
    codeHome = requiredProp(codeCfg, 'CodeHome')
    lambdaFolder = requiredProp(codeCfg, 'LambdaFolder')
    if isRule:
        typeFolder = requiredProp(codeCfg, 'RulesFolder')
    else:
        typeFolder = 'core'
    libFolder = requiredProp(codeCfg, 'LibFolder')
    mainCodePath = os.path.join(codeHome, lambdaFolder, typeFolder, baseFunctionName)
    mainCodeBase = mainCodePath
    libBase = codeHome
    libPaths = []
    for lib in libs:
        libPath = os.path.join(codeHome, libFolder, lib)
        libPaths.append(libPath)
    return get_zip_code_bytes(baseFunctionName, mainCodeBase, mainCodePath, libBase, libPaths)


def getCoreCode(baseFunctionName):
    libs = ['rdq']
    return get_lambda_code_bytes(baseFunctionName, libs, False)

def getRuleCode(baseFunctionName):
    libs = ['rdq']
    return get_lambda_code_bytes(baseFunctionName, libs, True)


