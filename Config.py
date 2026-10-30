

import sys
import configparser
import Log
import re
import os





def checkSectionConfig(iConfig, iSectionName):
  if iSectionName not in iConfig:
    return [[Log.level.ERROR, "[Config] Missing section '%s'" % (iSectionName)]]
  return []

def checkItemConfig(iConfig, iSectionName, iItemName):
  if iItemName not in iConfig[iSectionName]:
    return [[Log.level.ERROR, "[Config] Missing section '%s', item '%s'" % (iSectionName, iItemName)]]
  if iConfig[iSectionName][iItemName] == "":
    return [[Log.level.ERROR, "[Config] Missing section '%s', item '%s'" % (iSectionName, iItemName)]]
  return []

def check(iConfig):
  aValidConfig = []
  aSectionName = "default"
  aValidConfig += checkSectionConfig(iConfig, aSectionName)
  aValidConfig += checkItemConfig(iConfig,aSectionName, "sleep_time_second")
  aValidConfig += checkItemConfig(iConfig,aSectionName, "log_directory")

  aSectionName = "influx"
  aValidConfig += checkSectionConfig(iConfig,aSectionName)
  aValidConfig += checkItemConfig(iConfig, aSectionName, "url")
  aValidConfig += checkItemConfig(iConfig, aSectionName, "token")
  aValidConfig += checkItemConfig(iConfig, aSectionName, "org")

  aSectionName = "postgre"
  aValidConfig += checkSectionConfig(iConfig, aSectionName)
  aValidConfig += checkItemConfig(iConfig, aSectionName, "database")
  aValidConfig += checkItemConfig(iConfig, aSectionName, "user")
  aValidConfig += checkItemConfig(iConfig, aSectionName, "password")
  aValidConfig += checkItemConfig(iConfig, aSectionName, "host")
  aValidConfig += checkItemConfig(iConfig, aSectionName, "port")
  return aValidConfig

def fromEnv(iConfig):
  for aSection in iConfig:
    for aItem in iConfig[aSection]:
      for aEnv in re.findall(r"\${(\w+)}", iConfig[aSection][aItem]):
        if os.getenv(aEnv):
          iConfig[aSection][aItem] = iConfig[aSection][aItem].replace("${%s}" % aEnv, os.getenv(aEnv))
        else:
          iConfig[aSection][aItem] = ""


def init(iConfigPath):
  aConfig = configparser.ConfigParser()
  aConfig.read(iConfigPath)
  fromEnv(aConfig)
  return {"errors": check(aConfig), "object" : aConfig }