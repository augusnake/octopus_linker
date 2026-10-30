

import os, time
import tempfile
from datetime import datetime

from enum import Enum

import prettytable 

class level(Enum):
  INFO     = 0
  WARNING  = 1
  ERROR    = 2
  FATAL    = 3


class LogClass:

  def __init__(self):
    self.call = []

  def addFunc(self, iFunc):
    self.call.append(iFunc)


  def __call__(self, iType, iString):
    for aFunc in self.call:
      aFunc(iType, iString)

#def init():
#  global aGlobalLog
#  aGlobalLog = LogClass()

#def input(iType, iString):
#  aGlobalLog(iType, iString)



class LogInScreen:

  def __call__(self, iLogLevel, iString):
    aLogLine = "%s | %7s | %s" % (datetime.now().replace(microsecond=0).isoformat(), iLogLevel.name, iString)
    print(aLogLine)



class LogInFile:

  def getFileName(self):
    return self.path + "\\" + self.fileName + "_" + datetime.now().replace(microsecond=0).isoformat().replace(" ", "_").replace(":", "-") + ".log"

  def openNewFile(self):
    try:
      self.file = open(self.getFileName(), "a")
    except FileNotFoundError:
      print("Error: The file", self.getFileName(), "was not found.")
    except PermissionError:
      print("Error: Permission denied. Unable to access the file ", self.getFileName())
    except Exception as e:
      print("An unexpected error occurred when opening file", self.getFileName(), " : {e}")
    

  def __init__(self, iPath, iFileName, iMaxSize):
    os.makedirs(iPath, exist_ok=True)
    self.path = iPath 
    self.fileName = iFileName
    self.size = iMaxSize
    self.openNewFile()
    
  def check(self):
    if self.file.tell() >= self.size:
      self.file.close()
      self.openNewFile()

  def __call__(self, iLogLevel, iString):
    self.check()
    try:
      self.file.write(datetime.now().replace(microsecond=0).isoformat() + " | " + iLogLevel.name + " | " + iString + "\n")
    except (IOError):
      print("IO Error when writing in file", self.getFileName()) 
    except (OSError):
      print("OS Error when writing in file", self.getFileName()) 