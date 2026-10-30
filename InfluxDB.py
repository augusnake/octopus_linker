import os, time
from influxdb_client_3 import InfluxDBClient3, WritePrecision, InfluxDBError
from datetime import datetime
from time import mktime

from datetime import datetime, timezone
#from influxdb_client import InfluxDBClient, Point, WritePrecision
#from influxdb_client.client.write_api import SYNCHRONOUS, ASYNCHRONOUS
import pandas
import pyarrow
import HandlerSQL
from enum import Enum

import Log
import GLOBAL


class InfluxDB:
  def __getClient(self):
    return InfluxDBClient3(host=self.url, token=self.token, database=self.database)

  def __getWriteAPI(self):
    return self.client.write_api(write_options=SYNCHRONOUS)

  def __getReadAPI(self):
    return self.client.query_api()

  def __init__(self, iURL, iDB, iToken):
    self.token          = iToken
    self.database       = iDB
    self.url            = iURL
    self.client         = self.__getClient()
    self.existingTables = self.client.query("SHOW TABLES", language="sql")
    self.dryRun         = False
    self.writeCount     = 0
    self.readCount      = 0
    self.errorCount     = 0
    self.errorCountMax  = 3

    self.processTime    = 0

  def getAvgProcessTime(self):
    aCount = self.readCount + self.writeCount
    return int(self.processTime*1000 / aCount) if aCount > 0 else 0 
  
  def tableExists(self, tableName):
    return tableName in self.existingTables.column("table_name").to_pylist()

  def close(self):
    self.client.close()


  def write(self, aInsertString):
    #'pcb,id=1 uid="ynDvIV4RGOEBV6NejuEg",version_major=1,version_minor=0 1790869900'
    aTimerStart = time.time()
    self.writeCount += 1
    if self.dryRun:
      print("Write : ", aInsertString)
    else:
      try:
        self.client.write(aInsertString, write_precision=WritePrecision.MS)
      except InfluxDBError as exc:
        self.errorCount += 1
        if self.errorCount < self.errorCountMax:
          GLOBAL.log(Log.level.ERROR, "Failed to write to INFLUX-DB database "+ self.database)
          GLOBAL.log(Log.level.INFO , "   | > Input : \"" + aInsertString    + "\"")
          GLOBAL.log(Log.level.INFO , "   +-> Error : \"" + str(exc.message) + "\"")
    self.processTime += time.time() - aTimerStart

  def formatKeyValue(self, iKey, iValue, iType):
    if iType == HandlerSQL.eColumnType.STRING:
      return str(iKey)+"=\""+str(iValue)+"\""
    elif iType == HandlerSQL.eColumnType.INT:
      return str(iKey)+"="+str(int(iValue))+"i"
    elif iType == HandlerSQL.eColumnType.BOOL:
      return str(iKey)+"="+str(iValue)
    elif iType == HandlerSQL.eColumnType.FLOAT:
      return str(iKey)+"="+str(iValue)
    else:
      return str(iKey)+"=\""+str(iValue)+"\""

  def writeFlatRow(self, iTable, colInfo, colType, row, iLastTimestamp):
    item = str(iTable.name) + ' ' #+ ',str_id=' + str(row['id']) + ' '
    for (key,value,typ) in zip(colInfo, row.data, colType):
      item += self.formatKeyValue(key, value, typ) + ','
    item = item[:-1]
    #if iTable.columnExist('date_creation'):
    #  item += ' ' + datetime.isoformat(row['date_creation'])
    #else: 
    item += ' ' + str(int(datetime.now().timestamp() * 1000))
    self.write(item)

  def writeFlatTable(self, iTable, iLastTimestamp):
    for row in iTable:
      print("%s - row %s" % (iTable.name, row['id']))
      self.writeFlatRow(iTable, iTable.getColumnsName(), iTable.getColumnsType(), row, iLastTimestamp)

  def computeColumnsInfo(self, data):
    count = 0
    aColumnsName = []
    aColumnsType = []
    for i in data.schema:
      aColumnsName.append(i.name)
      if pyarrow.types.is_integer(i.type):
        aColumnsType.append(HandlerSQL.eColumnType.INT)
      elif pyarrow.types.is_string(i.type): 
        aColumnsType.append(HandlerSQL.eColumnType.STRING)
      elif pyarrow.types.is_floating(i.type): 
        aColumnsType.append(HandlerSQL.eColumnType.FLOAT)
      elif pyarrow.types.is_boolean(i.type): 
        aColumnsType.append(HandlerSQL.eColumnType.BOOL)
      else:
        aColumnsType.append(HandlerSQL.eColumnType.UNKNOWN)
      count +=1
    return HandlerSQL.ColumnInfo(aColumnsName, aColumnsType)

  def formatValue(self, iType, value):
    if iType == HandlerSQL.eColumnType.INT:
      return int(value)
    #elif type == aColumnsType.append(HandlerSQL.eColumnType.STRING)
    else:
      return value


  def computeRows(self, iColumnsType, iColumnsName, iData):
    if iColumnsName == 0:
      return []
    aResult = []
    for rowCount in range(iData.num_rows):
      aRow = []
      for aName, aType in zip(iColumnsName, iColumnsType):
        aRow.append(self.formatValue(aType, iData[aName][rowCount].as_py()))
      aResult.append(aRow)
    return aResult

  def read(self, iTableName, iQuery):
    aTimerStart = time.time()
    try:
      aData = self.client.query(query = iQuery, language = "sql", timeout = 2)
    except InfluxDBError as exc:
      self.errorCount += 1
      if self.errorCount < self.errorCountMax:
        GLOBAL.log(Log.level.ERROR, "Failed to read to INFLUX-DB database "+ self.database)
        GLOBAL.log(Log.level.INFO , "   | > Input : \"" + iQuery           + "\"")
        GLOBAL.log(Log.level.INFO , "   +-> Error : \"" + str(exc.message) + "\"")
    self.processTime += time.time() - aTimerStart
    if not aData:
      return HandlerSQL.TableError
    aColumnInfo = self.computeColumnsInfo(aData)
    aRows = self.computeRows(aColumnInfo.type, aColumnInfo.name, aData)
    self.readCount += 1
    return HandlerSQL.Table(iTableName, aColumnInfo, aRows)

  class eLogType(Enum):
    INFO     = 0
    WARNING  = 1
    ERROR    = 2
    FATAL    = 3
  def log(self, iLevel, iText):
    self.write("log,level=%s text=\"%s\" %s" % (iLevel.name, iText, int(datetime.now().timestamp())))



