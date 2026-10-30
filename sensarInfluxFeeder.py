


import sys
import os, time
import unittest
from dateutil.relativedelta import relativedelta


import HandlerSQL
import InfluxDB, PostgreDB
from time import sleep
import datetime

import Log
import GLOBAL





def missingRowsTable(iTable, influxDB):
  if influxDB.tableExists(iTable.name) == False:
    inf = HandlerSQL.Table([], [], [])
  else:
    inf = influxDB.read(iTable.name, "select * from %s" % iTable.name)
  
  aIdSet = [x for x in iTable.getColumn('id') if x not in inf.getColumn('id')]
  return iTable.keepRows('id', aIdSet)

def writeMissingRowsTable(iAllPostgreTable, influxDB, tableName, timestamp):
  influxDB.writeFlatTable(missingRowsTable(iAllPostgreTable[tableName], influxDB), timestamp)


def updateTableInfluxDB(iTable, tableExpandList):
  aTable = iTable
  for tabExIdx in range(len(tableExpandList)):
    aTable = aTable.expandTable(iTable.name, tableExpandList[tabExIdx]['table'], tableExpandList[tabExIdx]['id'], tableExpandList[tabExIdx]['prefix'])
  return aTable

def getTimestampFromTable(iInfluxDB, iTableName, iColumnName):
  aDefaultTimestamp = datetime.datetime.now() + relativedelta(months=-6)
  if iInfluxDB.tableExists(iTableName) == False:
    return aDefaultTimestamp
  aTable = iInfluxDB.read(iTableName, "select * from %s order by timestamp desc limit 1" % iTableName)
  return aTable.get(0, iColumnName) if len(aTable) > 0 else aDefaultTimestamp

def getInputInfo(iPostgreDB, iInfluxDB, iTableName, oAllTable, oTimestampDict):
  oTimestampDict[iTableName] = getTimestampFromTable(iInfluxDB, iTableName, 'timestamp')
  oAllTable     [iTableName] = iPostgreDB.fetchAll(iTableName, "select * from %s where timestamp > '%s'" % (iTableName, oTimestampDict[iTableName]))

def printInfo(iAllTable, iTimestampDict, iIterationCount):
  if iIterationCount == 0:
    print("%6.6s |" % "count", end="")
    for tableName in iAllTable.keys():
      print("%12.12s |" % tableName, end="")
    print()
  print("%6.6s |" % str(iIterationCount), end="")
  for tableName in iAllTable.keys():
    print("%12.12s |" % len(iAllTable[tableName]), end="")
  #print()





def updateInfluxFromSQL(iPostgreDB, iInfluxDB, iDateTime, iIterationCount, iCurrentTimestamp):
  aAllPostgreTable = {}
  aAllPostgreTable["pcb"]     = iPostgreDB.fetchAll("pcb"    , "select * from pcb")
  aAllPostgreTable["wheel"]   = iPostgreDB.fetchAll("wheel"  , "select * from wheel")
  aAllPostgreTable["casing"]  = iPostgreDB.fetchAll("casing" , "select * from casing")
  aAllPostgreTable["ripper"]  = iPostgreDB.fetchAll("ripper" , "select * from ripper")
  aAllPostgreTable["stirrup"] = iPostgreDB.fetchAll("stirrup", "select * from stirrup")

  aAllPostgreTable["placed_wheel"]  = iPostgreDB.fetchAll("placed_wheel" , "select * from placed_wheel")
  aAllPostgreTable["placed_ripper"] = iPostgreDB.fetchAll("placed_ripper", "select * from placed_ripper")
 
  iCurrentTimestamp = iDateTime.timestamp()
  writeMissingRowsTable(aAllPostgreTable, iInfluxDB, "pcb"    , iCurrentTimestamp)
  writeMissingRowsTable(aAllPostgreTable, iInfluxDB, "wheel"  , iCurrentTimestamp)
  writeMissingRowsTable(aAllPostgreTable, iInfluxDB, "casing" , iCurrentTimestamp)
  writeMissingRowsTable(aAllPostgreTable, iInfluxDB, "ripper" , iCurrentTimestamp)
  writeMissingRowsTable(aAllPostgreTable, iInfluxDB, "stirrup", iCurrentTimestamp)

  aExtendedPlacedWheel = updateTableInfluxDB(aAllPostgreTable['placed_wheel'], [
                          {'table':aAllPostgreTable['pcb']    , 'id':'id_pcb'   , 'prefix':'pcb'},
                          {'table':aAllPostgreTable['wheel']  , 'id':'id_wheel' , 'prefix':'wheel'},
                          {'table':aAllPostgreTable['casing'] , 'id':'id_casing', 'prefix':'casing'},
                          {'table':aAllPostgreTable['stirrup'], 'id':'id_stirrup', 'prefix':'stirrup'}
                        ])
  aExtendedPlacedWheelMissing = missingRowsTable(aExtendedPlacedWheel, iInfluxDB)
  iInfluxDB.writeFlatTable(aExtendedPlacedWheelMissing, iCurrentTimestamp)
  
  aExtendedPlacedRipper = updateTableInfluxDB(aAllPostgreTable['placed_ripper'], [
                          {'table':aAllPostgreTable['pcb']    , 'id':'id_pcb'    , 'prefix':'pcb'},
                          {'table':aAllPostgreTable['ripper'] , 'id':'id_ripper' , 'prefix':'ripper'},
                          {'table':aAllPostgreTable['casing'] , 'id':'id_casing' , 'prefix':'casing'},
                          {'table':aAllPostgreTable['stirrup'], 'id':'id_stirrup', 'prefix':'stirrup'}
                        ])  
  aExtendedPlacedRipperMissing = missingRowsTable(aExtendedPlacedRipper, iInfluxDB)
  iInfluxDB.writeFlatTable(aExtendedPlacedRipperMissing, iCurrentTimestamp)


  atimeStampDict = {}
  getInputInfo(iPostgreDB, iInfluxDB, "input_wheel"        , aAllPostgreTable, atimeStampDict)
  getInputInfo(iPostgreDB, iInfluxDB, "input_ripper"       , aAllPostgreTable, atimeStampDict)
  getInputInfo(iPostgreDB, iInfluxDB, "input_automaton"    , aAllPostgreTable, atimeStampDict)
  getInputInfo(iPostgreDB, iInfluxDB, "input_maintenance"  , aAllPostgreTable, atimeStampDict)
  getInputInfo(iPostgreDB, iInfluxDB, "input_radio_mesure" , aAllPostgreTable, atimeStampDict)


  writeMissingRowsTable(aAllPostgreTable, iInfluxDB, "input_automaton"  , iCurrentTimestamp)
  writeMissingRowsTable(aAllPostgreTable, iInfluxDB, "input_maintenance" , iCurrentTimestamp)
  writeMissingRowsTable(aAllPostgreTable, iInfluxDB, "input_radio_mesure", iCurrentTimestamp)
  
  aExtendedInputWheel = updateTableInfluxDB(aAllPostgreTable['input_wheel'], 
                                            [{'table':aExtendedPlacedWheel, 'id':'id_placed_wheel', 'prefix':'placed_wheel'}])
  iInfluxDB.writeFlatTable(aExtendedInputWheel, iCurrentTimestamp)  
  #print(aExtendedInputWheel)

  aExtendedInputRipper = updateTableInfluxDB(aAllPostgreTable['input_ripper'], 
                                              [{'table':aExtendedPlacedRipper, 'id':'id_placed_ripper', 'prefix':'placed_ripper'}])
  iInfluxDB.writeFlatTable(aExtendedInputRipper, iCurrentTimestamp)  
  #print(aExtendedInputRipper)


  aWheelAutomaton = aExtendedInputWheel.copy()
  aWheelAutomaton.name = 'wheel_automaton'
  print(aWheelAutomaton)

  aNewColumnValue = []
  aNewColumnValueFind= []
  aMaxTime = int(GLOBAL.config['influx']['max_time_automaton_wheel_link'])
  for aRow in aWheelAutomaton:
    aRefRow = aAllPostgreTable['input_automaton'].getRowByTime('date_creation', aRow['date_creation'], )
    aNewColumnValue.append(aRefRow['row']['id'])
    aNewColumnValueFind.append(aRefRow['diff'] < aMaxTime)
    if aRefRow == None:
      GLOBAL.log(Log.level.ERROR, "Unable to link input_wheel and input_automaton")
      break
  if None not in aNewColumnValue:
    aWheelAutomaton.addColumn('id_automaton', HandlerSQL.eColumnType.INT, aNewColumnValue)
    aWheelAutomaton.addColumn('id_automaton_found', HandlerSQL.eColumnType.BOOL, aNewColumnValueFind)

    aExtendedInputWheelAutomaton = updateTableInfluxDB(aWheelAutomaton, 
                                              [{'table':aAllPostgreTable['input_automaton'], 'id':'id_automaton', 'prefix':'input_automaton'}])
    print(aExtendedInputWheelAutomaton)
    iInfluxDB.writeFlatTable(aExtendedInputWheelAutomaton, iCurrentTimestamp)


  printInfo(aAllPostgreTable, atimeStampDict, iIterationCount)


def insertSqlFromInflux(iPostgreDB, iInfluxDB, iTimestamp):
  #iInfluxDB.write("input_sql,key=2 table=\"stirrup\",values=\"uid='input_sql_2',description='desc_input_sql_2'\" 1791361444")
  #iInfluxDB.write("input_sql,key=3 table=\"casing\",values=\"arm=2,radius=2,name='naming'\" 1791361444")
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
    #iInfluxDB.write("input_sql_execution,key=%s time_execution='%s',issue='%s'" % (aRow.get('key'), iTimestamp.isoformat(), aIssue))




initInflux = True
initPostgre = True
def initDB():
  token = GLOBAL.config['influx']['token']
  org   = GLOBAL.config['influx']['org']
  url   = GLOBAL.config['influx']['url']
  aInfluxDB = InfluxDB.InfluxDB(url, org, token)
  aPostgreDB = PostgreDB.PostgreDB()

  return aPostgreDB, aInfluxDB


def closeDB(iPostgreDB, iInfluxDB):
  if initPostgre:
    iPostgreDB.close()
  if initInflux:
    iInfluxDB.close()


def loop(iIterationCount, iCurrentTimestamp):
  
  s = time.time()

  aDTNow = datetime.datetime.now().replace(microsecond=0)

  aPostgreDB, aInfluxDB = initDB()

  insertSqlFromInflux(aPostgreDB, aInfluxDB, aDTNow)
  updateInfluxFromSQL(aPostgreDB, aInfluxDB, aDTNow, iIterationCount, iCurrentTimestamp)


  #aInfluxDB.log(aInfluxDB.eLogType.INFO, "Test=logrrez e r eccs ")
  e = time.time()
  print("Process Time:", e - s)
  aInfluxDB.write("stat process_time_ms=%si,influx_read=%si,influx_write=%si,influx_process_time_ms=%si,postgre_read=%si,postgre_write=%si,postgre_process_time_ms=%si %s"
                  % (int((e - s)*1000), aInfluxDB.readCount, aInfluxDB.writeCount, int(aInfluxDB.processTime*1000), aPostgreDB.readCount, aPostgreDB.writeCount, int(aPostgreDB.processTime*1000), int(aDTNow.timestamp())))
  closeDB(aPostgreDB, aInfluxDB)

  
# .\influxdb3.exe create table --database "sensarInflux" --tags uid --fields id:int64,version_major:int64,version_minor:int64 pcb

if __name__ == '__main__':
  GLOBAL.initLog()
  GLOBAL.log.addFunc(Log.LogInScreen())
  GLOBAL.log.addFunc(Log.LogInFile(os.getcwd()+"\\log\\", "feeder", 1000000))
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


  aTimestamp = datetime.datetime.now() #+ relativedelta(months=-6)
  aIterationCount:int = 0
  while True:
    loop(aIterationCount, aTimestamp)
    aIterationCount+=1
    aTimestamp += datetime.timedelta(0, int(GLOBAL.config['default']['sleep_time_second']))
    aSleepTime = (aTimestamp - datetime.datetime.now())
    sleep(aSleepTime.seconds + aSleepTime.microseconds/1000000)
    #sleep(int(GLOBAL.config['default']['sleep_time_second']))