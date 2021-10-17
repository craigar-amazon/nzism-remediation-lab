from zipfile import ZipFile
from zipfile import ZIP_STORED
import tempfile
import os

def make_arc_name(home, file):
    homePrefix = len(home) + 1
    return './' + file[homePrefix:]

def get_all_file_paths(directory_path):
    file_paths = []
  
    for (root, dirnames, files) in os.walk(directory_path):
        for filename in files:
            filepath = os.path.join(root, filename)
            file_paths.append(filepath)

    return file_paths    

def make_zip_file(codePath, zip_file_path, file_paths):
    with ZipFile(zip_file_path, mode='w', compression=ZIP_STORED) as zip:
        for file in file_paths:
            arcname = make_arc_name(codePath, file)
            zip.write(file, arcname)

def bytes_file(file_path):
    f = open(file_path, 'rb')
    byte_array = f.read()
    f.close()
    return byte_array

def getZipCodeBytes(codePath, functionName):
    zipFilePath = os.path.join(tempfile.gettempdir(), functionName+".zip")
    file_paths = get_all_file_paths(codePath)
    make_zip_file(codePath, zipFilePath, file_paths)
    return bytes_file(zipFilePath)
