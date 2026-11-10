


import sys
import re
import os, time
import unittest
from dateutil.relativedelta import relativedelta


import HandlerSQL
import InfluxDB, PostgreDB
from time import sleep
import datetime
import calibration
import random

import Log
import GLOBAL



def missingRowsTable(iTable, influxDB: InfluxDB.InfluxDB):
  if influxDB.tableExists(iTable.name) == False:
    inf = HandlerSQL.Table([], [], [])
  else:
    inf = influxDB.read(iTable.name, "select * from %s" % iTable.name)
  
  aIdSet = [x for x in iTable.getColumn('id') if x not in inf.getColumn('id')]
  return iTable.keepRows('id', aIdSet)

def writeMissingRowsTable(iTable, influxDB: InfluxDB.InfluxDB):
  influxDB.writeFlatTable(missingRowsTable(iTable, influxDB))


def updateTableInfluxDB(iTable, tableExpandList):
  aTable = iTable
  for tabExIdx in range(len(tableExpandList)):
    aTable = aTable.expandTable(iTable.name, tableExpandList[tabExIdx]['table'], tableExpandList[tabExIdx]['id'], tableExpandList[tabExIdx]['prefix'])
  return aTable


def printInfo(iAllTable, iIterationCount):
  if iIterationCount == 0:
    print("%6.6s |" % "count", end="")
    for tableName in iAllTable.keys():
      print("%12.12s |" % tableName, end="")
    print()
  print("%6.6s |" % str(iIterationCount), end="")
  for tableName in iAllTable.keys():
    print("%12.12s |" % len(iAllTable[tableName]), end="")
  #print()


def applyCalibration(iTable, iReferenceColumn, iCalibrationColumn):
  data=[]
  for aRow in iTable:
    data.append(calibration.calib(aRow[iReferenceColumn], aRow[iCalibrationColumn]))
  iTable.addColumn("gauge", HandlerSQL.eColumnType.FLOAT, data)

def getNewRows(iPostgreDB: PostgreDB.PostgreDB, iPostgresTable:str, iInfluxDB: InfluxDB.InfluxDB, iInfluxDBTable:str, iPostgreId:str = 'id', iInfluxId:str='id'):
  aLastId = 0
  if iInfluxDB.tableExists(iInfluxDBTable):
    aExistIdTable = iInfluxDB.read(iInfluxDBTable, "SELECT MAX(%s) FROM %s" % (iInfluxId, iInfluxDBTable))
    aLastId = aExistIdTable.getByIndex(0, 0)
  return iPostgreDB.fetchAll(iInfluxDBTable, "SELECT * FROM %s where %s > %s" %  (iPostgresTable, iPostgreId, aLastId))

def getNewRowsFromTable(iPostgresTable:HandlerSQL.Table, iInfluxDB: InfluxDB.InfluxDB, iInfluxDBTable:str):
  aLastId = 0
  if iInfluxDB.tableExists(iInfluxDBTable):
    aExistIdTable = iInfluxDB.read(iInfluxDBTable, "SELECT MAX(id) FROM %s" % iInfluxDBTable)
    aLastId = aExistIdTable.getByIndex(0, 0)
  return iPostgresTable.whereIdhigherThan(aLastId)

def getAllRows(iPostgreDB: PostgreDB.PostgreDB, iPostgresTable:str):
  return iPostgreDB.fetchAll(iPostgresTable, "select * from %s" % iPostgresTable)

def updateWheelAutomaton(iPostgreDB: PostgreDB.PostgreDB, iInfluxDB: InfluxDB.InfluxDB, iAllPostgreTable):
  aWheelAutomaton = getNewRows(iPostgreDB, 'input_wheel', iInfluxDB, "wheel_automaton", 'id', 'input_wheel__id')
  aWheelAutomaton = processExtendedTable(aWheelAutomaton, iAllPostgreTable)
  if len(aWheelAutomaton) == 0:
    return
  aWheelAutomaton.prefixColumns('input_wheel__', True)
  aDateTime = aWheelAutomaton.findLowest('input_wheel__timestamp')
  aDateTime -= relativedelta(minutes=2)
  aNewColumnValue = []
  aNewColumnValueFind= []
  aTableAutomaton = iPostgreDB.fetchAll('input_automaton', "select * from input_automaton where timestamp > '%s'" % (aDateTime.isoformat()))
  aMaxTime = int(GLOBAL.config['influx']['max_time_automaton_wheel_link'])
  for aRow in aWheelAutomaton:
    aRefRow = aTableAutomaton.getRowByTime('timestamp', aRow['input_wheel__timestamp'])
    if aRefRow == None:
      GLOBAL.log(Log.level.ERROR, "Unable to link input_wheel and input_automaton")
      break
    aNewColumnValue.append(aRefRow['row']['id'])
    aNewColumnValueFind.append(aRefRow['diff'])
  if None not in aNewColumnValue:
    aWheelAutomaton.addColumn('id_automaton', HandlerSQL.eColumnType.INT, aNewColumnValue)
    aWheelAutomaton.addColumn('sec_diff_wheel_automaton', HandlerSQL.eColumnType.FLOAT, aNewColumnValueFind)

    aExtendedInputWheelAutomaton = updateTableInfluxDB(aWheelAutomaton, 
                                              [{'table':aTableAutomaton, 'id':'id_automaton', 'prefix':'input_automaton'}])
    iInfluxDB.writeFlatTable(aExtendedInputWheelAutomaton)

def process(iPostgreDB: PostgreDB.PostgreDB, iInfluxDB: InfluxDB.InfluxDB, iTableStr:str, iAllTable:dict):
  aTable = iPostgreDB.fetchAll(iTableStr, "select * from %s" % iTableStr)
  iAllTable[iTableStr] = processExtendedTable(aTable, iAllTable)
  writeMissingRowsTable(iAllTable[iTableStr], iInfluxDB)

def processPartial(iPostgreDB: PostgreDB.PostgreDB, iInfluxDB: InfluxDB.InfluxDB, iTableStr:str, iAllTable:dict):
  aTable = getNewRows(iPostgreDB, iTableStr, iInfluxDB, iTableStr)
  iAllTable[iTableStr] = processExtendedTable(aTable, iAllTable)
  iInfluxDB.writeFlatTable(iAllTable[iTableStr])


def processExtendedTable(iTable:HandlerSQL.Table, iAllTable:dict):
  aExtendInfo = []
  for iColName in iTable.getColumnsName():
    aMatch = re.search('id_[a-z]+', iColName)
    if aMatch:
      aExtTableName = iColName[3:]
      aExtendInfo.append({'table':iAllTable[aExtTableName], 'id':iColName, 'prefix':aExtTableName})
  return updateTableInfluxDB(iTable, aExtendInfo)


def updateInfluxFromSQL(iPostgreDB:PostgreDB.PostgreDB, iInfluxDB: InfluxDB.InfluxDB, iIterationCount):
  aAllPostgreTable = {}
  process(iPostgreDB, iInfluxDB, "pcb"    , aAllPostgreTable)
  process(iPostgreDB, iInfluxDB, "wheel"  , aAllPostgreTable)
  process(iPostgreDB, iInfluxDB, "casing" , aAllPostgreTable)
  process(iPostgreDB, iInfluxDB, "ripper" , aAllPostgreTable)
  process(iPostgreDB, iInfluxDB, "stirrup", aAllPostgreTable)

  process(iPostgreDB, iInfluxDB, "placed_ripper", aAllPostgreTable)
  process(iPostgreDB, iInfluxDB, "placed_wheel" , aAllPostgreTable)

  processPartial(iPostgreDB, iInfluxDB, "input_automaton"    , aAllPostgreTable)
  processPartial(iPostgreDB, iInfluxDB, "input_maintenance"  , aAllPostgreTable)
  processPartial(iPostgreDB, iInfluxDB, "input_radio_mesure" , aAllPostgreTable)
  processPartial(iPostgreDB, iInfluxDB, "input_ripper"       , aAllPostgreTable)


  aInputWheelTable = getNewRows(iPostgreDB, "input_wheel", iInfluxDB, "input_wheel")
  aAllPostgreTable['input_wheel'] = processExtendedTable(aInputWheelTable, aAllPostgreTable)
  applyCalibration(aAllPostgreTable['input_wheel'], 'min_d', 'placed_wheel__calibration')
  print(aAllPostgreTable['input_wheel'])
  iInfluxDB.writeFlatTable(aAllPostgreTable['input_wheel'])

  updateWheelAutomaton(iPostgreDB, iInfluxDB, aAllPostgreTable)

  printInfo(aAllPostgreTable, iIterationCount)


def insertSqlFromInflux(iPostgreDB, iInfluxDB: InfluxDB.InfluxDB):
  if iInfluxDB.tableExists('input_sql') == False:
    return
  aInputInfluxTable  = iInfluxDB.read('input_sql', "select * from input_sql")
  aInputPostgreTable = iPostgreDB.fetchAll('input_user', "select * from input_user")
  aInputInfluxTable = aInputInfluxTable.removeRows('key', [str(id) for id in aInputPostgreTable.getColumn('id_influx')])
  for aRow in aInputInfluxTable:
    aKeyArray = []
    aValArray = []
    for aKeyValue in aRow.get('values').split(','):
      aKey, aVal = aKeyValue.split('=')
      aKeyArray.append(aKey)
      aValArray.append(aVal)
    aQueryRes = iPostgreDB.insert(aRow.get('table'), aKeyArray, aValArray)
    iPostgreDB.insert('input_user', ['id_influx', 'table_name', 'table_values', 'issue'], [aRow.get('key'), "'"+aRow.get('table')+"'", "$$"+aRow.get('values')+"$$", "$$"+aQueryRes['errorString']+"$$"])




initInflux = True
initPostgre = True
def initDB() -> tuple[PostgreDB.PostgreDB, InfluxDB.InfluxDB]:
  token = GLOBAL.config['influx']['token']
  org   = GLOBAL.config['influx']['org']
  url   = GLOBAL.config['influx']['url']
  aInfluxDB = InfluxDB.InfluxDB(url, org, token)
  aPostgreDB = PostgreDB.PostgreDB()

  return aPostgreDB, aInfluxDB


def closeDB(iPostgreDB, iInfluxDB: InfluxDB.InfluxDB):
  if initPostgre:
    iPostgreDB.close()
  if initInflux:
    iInfluxDB.close()


def loop(iIterationCount):
  
  s = time.time()

  aPostgreDB, aInfluxDB = initDB()

  insertSqlFromInflux(aPostgreDB, aInfluxDB)
  updateInfluxFromSQL(aPostgreDB, aInfluxDB, iIterationCount)
  
  e = time.time()
  print("Process Time:", e - s)
  aInfluxDB.write("stat process_time_ms=%si,influx_read=%si,influx_write=%si,influx_process_time_ms=%si,postgre_read=%si,postgre_write=%si,postgre_process_time_ms=%si"
                  % (int((e - s)*1000), aInfluxDB.readCount, aInfluxDB.writeCount, int(aInfluxDB.processTime*1000), aPostgreDB.readCount, aPostgreDB.writeCount, int(aPostgreDB.processTime*1000)))
  aInfluxDB.writeBuffer()
  closeDB(aPostgreDB, aInfluxDB)


if __name__ == '__main__':
  GLOBAL.initLog()
  GLOBAL.log.addFunc(Log.LogInScreen())
  GLOBAL.log.addFunc(Log.LogInFile(os.getcwd()+"/log/", "feeder", 1000000))
  GLOBAL.log(Log.level.INFO, "Initialized GLOBAL : log")

  if len(sys.argv) != 2:
    Log.input(Log.level.FATAL, "Python script take only one argument, config file path, given : %s" % ("\"".join(sys.argv)))
    exit(1)

  if not GLOBAL.initConfig(sys.argv[1]):
    exit(2)
  GLOBAL.log(Log.level.INFO, "Initialized GLOBAL : config")

  GLOBAL.log(Log.level.INFO, "Hello world of log !")
  suite = unittest.defaultTestLoader.discover(
    start_dir="test",
    pattern="HandlerSQL_test.py"
  )
  result = unittest.TextTestRunner().run(suite)
  if not result.wasSuccessful():
      raise SystemExit(1)
  GLOBAL.log(Log.level.INFO, "Unit test passed successfully")
  GLOBAL.log(Log.level.WARNING, "Unit test passed successfully")
  GLOBAL.log(Log.level.ERROR, "Unit test passed successfully")


  aTimestamp = datetime.datetime.now()
  aIterationCount:int = 0
  while not GLOBAL.config.getboolean('default','close_asap'):
    loop(aIterationCount)

    aIterationCount+=1
    aTimestamp += datetime.timedelta(0, int(GLOBAL.config['default']['sleep_time_second']))
    aTtNow = datetime.datetime.now()
    if(aTtNow < aTimestamp):
      aSleepTime = (aTimestamp - aTtNow)
      sleep(aSleepTime.seconds + aSleepTime.microseconds/1000000)

    if not GLOBAL.initConfig(sys.argv[1]):
      break
