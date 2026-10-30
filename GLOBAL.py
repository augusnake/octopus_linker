


import Log
import Config



def initConfig(iConfigPath):
  global config 
  config = Config.init(iConfigPath)
  if config['errors'] != []:
    for aLevel, aString in config['errors']:
      log(aLevel, aString)
    log(Log.level.FATAL, "[Config] Missing configuration items, file : %s" % (iConfigPath))
    return False
  config = config['object']
  return True

def initLog():
  global log
  log = Log.LogClass()
  return True
