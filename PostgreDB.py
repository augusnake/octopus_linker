
import time

import psycopg2
import random
import string
import array
import pandas
#import pandas


from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from itertools import chain
import pyarrow

import HandlerSQL
import GLOBAL
import Log


class PostgreDB:

  def __init__(self):
    self.database       = GLOBAL.config['postgre']['database']
    aUser               = GLOBAL.config['postgre']['user']
    aHost               = GLOBAL.config['postgre']['host']
    aPort               = GLOBAL.config['postgre']['port']
    aPassword           = GLOBAL.config['postgre']['password']
    self.connector      = psycopg2.connect(database = self.database, user = aUser, host= aHost, password = aPassword, port = aPort)
    self.cursor         = self.connector.cursor()
    self.writeCount     = 0
    self.readCount      = 0
    self.processTime    = 0
    self.errorCount     = 0
    self.errorCountMax  = 3
    self.dryRun         = False

  def getAvgProcessTime(self) -> int:
    aCount = self.readCount + self.writeCount
    return int(self.processTime*1000 / aCount) if aCount > 0 else 0 
    

  def close(self):
    self.cursor.close()
    self.connector.close()

  def randString(self, aLength):
    return ''.join(random.choices(string.ascii_letters + string.digits, k=aLength))

  def __executeRequest(self, iQuery, aCommitNeeded = False):
    aTimerStart = time.time()
    try:
      self.cursor.execute(iQuery)
      if aCommitNeeded:
        self.writeCount += 1
        self.connector.commit()
    except psycopg2.Error as err:
      if aCommitNeeded:
        self.connector.rollback()
      GLOBAL.log(Log.level.ERROR, "Query failed to POSTGRE-DB database "+ self.database)
      GLOBAL.log(Log.level.INFO , "   | > Input : \"" + iQuery    + "\"")
      GLOBAL.log(Log.level.INFO , "   +-> Error : \"" + str(err.pgerror.split("\n")[0]) + "\"")
      self.errorCount += 1
      self.processTime += time.time() - aTimerStart
      return { "errorCode": err.pgcode, "errorString" :err.pgerror}
    self.processTime += time.time() - aTimerStart
    return { "errorCode": 0, "errorString" : 'none'}

  
  def executeRequest(self, iQuery, iCommitNeeded=False):
    if self.dryRun:
      print(iQuery, ";")
      self.processTime += 1
      return { "errorCode": 0, "errorString" : 'none' }
    else:
      return self.__executeRequest(iQuery, iCommitNeeded)
      


  def flatten(self, iResultDB):
    arr = []
    for i in iResultDB:
      arr.append([r for r in i])
    return arr


  def computeColumnsInfo(self, iDescription):
    count = 0
    aColumnsName = []
    aColumnsType = []
    for i in iDescription:
      aColumnsName.append(i[0])
      #print("%s is type %s" %(i[0], i[1]))
      match i[1]:
        case 23 | 20 | 21:
          aColumnsType.append(HandlerSQL.eColumnType.INT)
        case 1042:
          aColumnsType.append(HandlerSQL.eColumnType.STRING)
        case 16:
          aColumnsType.append(HandlerSQL.eColumnType.BOOL)
        case 701:
          aColumnsType.append(HandlerSQL.eColumnType.FLOAT)
        case _:
          aColumnsType.append(HandlerSQL.eColumnType.UNKNOWN)
      count +=1
    return HandlerSQL.ColumnInfo(aColumnsName, aColumnsType)

  def fetchAllUpdate(self, iTable, iTimestamp):
    return self.fetchAll(iTable, "select * from %s where date_creation > '%s'" % (iTable, iTimestamp), True)


  def fetchAll(self, iTableName, iQuery):
    aTimerStart = time.time()
    aQueryResponse = self.__executeRequest(iQuery)
    self.processTime += time.time() - aTimerStart
    self.readCount += 1
    if aQueryResponse['errorCode'] :
      return HandlerSQL.TableError
    res = self.cursor.fetchall()
    aColumnInfo = self.computeColumnsInfo(self.cursor.description)
    return HandlerSQL.Table(iTableName, aColumnInfo, self.flatten(res))

  def formatType(self, aValueArray):
    return [i if type(i) is not str else "'"+i+"'" for i in aValueArray]

  def insert(self, iTableName, aKeyArray, aValueArray):
    aInsertString = "INSERT INTO %s(%s) VALUES (%s)" % (iTableName, ", ".join(aKeyArray), ", ".join(aValueArray) )
    return self.executeRequest(aInsertString, True)
    