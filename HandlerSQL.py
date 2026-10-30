

import os

from enum import Enum

import prettytable 

class eColumnType(Enum):
  STRING  = 1
  INT     = 2
  BOOL    = 3
  FLOAT   = 4
  UNKNOWN = 5

class ColumnInfo:

  def __setColumnsName(self, iColumnsName):
    count = 0
    arr = dict()
    #self.columnsName = []
    for i in iColumnsName:
      arr[i] = count
      count +=1
    return arr

  def __init__(self, iColumnName, iColumnType):
    self.name    : list[str]         = iColumnName
    self.type    : list[eColumnType] = iColumnType
    self.position: dict[str, int]    = self.__setColumnsName(iColumnName)

  def __getitem__(self, iColumnName) -> int:
    return self.position[iColumnName]

  def __len__(self):
    return len(self.name)

  def getColumnsWithType(self, iColumnsType):
    aColType = [[aName, aType] for aName, aType in zip(self.name, self.type) if aType in iColumnsType]
    return aColType

  def getType(self, iColumnName):
    return self.type[self.position[iColumnName]]

  def add(self, iColumnsInfo, prefix = ""):
    self.name += [prefix + i for i in iColumnsInfo.name]
    self.type += iColumnsInfo.type
    self.position = self.__setColumnsName(self.name)

  def remove(self, iColumnName):
    if iColumnName in self.name:
      iColumnIndex = self.position[iColumnName]
      self.name.remove(iColumnName)
      self.type.pop(iColumnIndex)
      del self.position[iColumnName]
      for i in range(iColumnIndex, len(self.name)):
        self.position[self.name[i]] -= 1
      return iColumnIndex
    else:
      raise RuntimeError("Try to remove a column that does not exist")

  def __str__(self):
    table = prettytable.PrettyTable(['name', 'type', 'position'])
    for i in range(len(self.name)):
      table.add_row([self.name[i], self.type[i], self.position[self.name[i]]])
    return str(table) + "\n"

  def copy(self):
    return ColumnInfo(self.name.copy(), self.type.copy())

  def getColumnsName(self):
    return self.name


######################################################################################

class Row:
  def __init__(self, iTableName, iColumnsInfo, iRows):
    self.tableName   = iTableName
    self.columnsInfo = iColumnsInfo
    self.data        = iRows

  def addColumns(self, iColumnInfo, iValues):
    self.columnsInfo.add(iColumnInfo)
    self.data += iValues

  def get(self, columnName):
    return self.data[self.columnsInfo[columnName]]

  def __getitem__(self, iColumnName):
    return self.data[self.columnsInfo[iColumnName]]

  def __len__(self):
    return len(self.data)

  def __str__(self):
    aDict = {}
    for cName in self.columnsInfo.getColumnsName():
      aDict[cName] = self.get(cName)
    return str(aDict)

  def copy(self):
    return Row(self.tableName, self.columnsInfo.copy(), self.data.copy())

  def getDeleteString(self):
    aColArr = self.columnsInfo.getColumnsWithType([eColumnType.INT, eColumnType.STRING])
    aExpr = "DELETE FROM " + self.tableName + " WHERE "
    for aName, aType in aColArr:
      if aType == eColumnType.STRING:
        aExpr += aName + " = \'" + self.get(aName) + "\' "
      else:
        aExpr += aName + " = " + self.get(aName) + " "
      aExpr += "and "
    return aExpr[:-4]


  def getWhere(self):
    aColArr = self.columnsInfo.getColumnsWithType([eColumnType.INT, eColumnType.STRING])
    aExpr =""
    for aName, aType in aColArr:
      if aType == eColumnType.STRING:
        aExpr += aName + " = \'" + self.get(aName) + "\' "
      else:
        aExpr += aName + " = " + self.get(aName) + " "
      aExpr += "and "
    return aExpr[:-4]



  def getUpdateString(self, iKeyValArray):
    aExpr = "UPDATE " + self.tableName + " SET "
    for aKey, aValue in iKeyValArray:
      aStrAdd = ""
      if self.columnsInfo.getType(aKey) == eColumnType.STRING:
        aStrAdd = "'"
      aExpr += aKey + " = "+ aStrAdd + aValue + aStrAdd + ", "
    aExpr = aExpr[:-2] + " WHERE " + self.getWhere()
    return aExpr

def RowCreateEmpty( iTableName, iColumnInfo):
  return Row(iTableName, iColumnInfo, [])
    

    



######################################################################################

class Table:

  def __init__(self, iTableName, iColumnInfo, iRows):
    self.name            = iTableName
    self.columnsInfo     = iColumnInfo
    self.rows            = iRows

  def copy(self): 
    return Table(self.name, self.columnsInfo.copy(), self.rows.copy())
  
  def getColumnsName(self):
    return self.columnsInfo.name

  def getColumnsType(self):
    return self.columnsInfo.type
  
  def addData(self, rows):
    self.rows += rows

  def getRowIndex(self, aId):
    for i in range(len(self.rows)):
      if self.rows[i][self.columnsInfo['id']] == aId:
        return i
    raise RuntimeError("id %d not found in table %s" % (aId, self.name))
  
  def getRowByTime(self, iColumnName, iDate):
    aResult = None
    aDist = 2000000
    for aRow in self:
      aDiff = abs((aRow[iColumnName] - iDate).total_seconds())
      if aDist > aDiff:
        aDist = aDiff
        aResult = aRow
    return { 'row' : aResult, 'diff' : aDist }
  
  def getRow(self, rowIndex):
    return Row(self.name, self.columnsInfo, self.rows[rowIndex])

  def getRowCopy(self, rowIndex):
    return Row(self.name, self.columnsInfo.copy(), self.rows[rowIndex].copy())
    
  def get(self, rowIndex, columnName):
    return self.rows[rowIndex][self.columnsInfo[columnName]]

  def __getitem__(self, rowIndex):
    return Row(self.name, self.columnsInfo, self.rows[rowIndex])

  def __len__(self):
    return len(self.rows)


  def getColumn(self, iColumnName):
    return [row[iColumnName] for row in self]

  def columnExist(self, iColumnName):
    return iColumnName in self.columnsInfo.name

  def removeColumn(self, iColumnName):
    if iColumnName in self.columnsInfo.name:
      iColumnIndex = self.columnsInfo.remove(iColumnName)
      for row in self.rows:
        del row[iColumnIndex]
    else:
      raise RuntimeError("Try to remove a column that does not exist")

  def addColumns(self, iColumnName, iColumnType, iColumnData):
    for aColName in iColumnName:
      if aColName in self.columnsInfo.name:
        raise RuntimeError("Try to add a column that already exist")
    
    self.columnsInfo.add(ColumnInfo(iColumnName, iColumnType))
    for aColData in iColumnData:
      for aRowIndex in range(len(self.rows)):
        self.rows[aRowIndex].append(aColData[aRowIndex])

  def addColumn(self, iColumnName, iColumnType, iColumnData):
    if iColumnName in self.columnsInfo.name:
      raise RuntimeError("Try to add a column that already exist")
    if len(iColumnData) != len(self):
      raise RuntimeError("Column size is NOT the same as table rows count")

    
    self.columnsInfo.add(ColumnInfo([iColumnName], [iColumnType]))
    for aRowIndex in range(len(self.rows)):
      self.rows[aRowIndex].append(iColumnData[aRowIndex])

  def __str__(self):
    table = prettytable.PrettyTable(self.columnsInfo.name)
    for row in self.rows:
        table.add_row(row)
    return str(self.columnsInfo) + str(table)

  def keepRows(self, iColumnKey, iRowsKey):
    aRows           = [i for i in self.rows if i[self.columnsInfo[iColumnKey]] in iRowsKey]
    return Table(self.name, self.columnsInfo, aRows)

  def removeRows(self, iColumnKey, iRowsKey):
    aRows           = [i for i in self.rows if i[self.columnsInfo[iColumnKey]] not in iRowsKey]
    return Table(self.name, self.columnsInfo, aRows)


  def expandTable(self, aTableName, aTable, aIdColumn, aTablePrefix):
    aNewColumnsName =  [aTablePrefix + '__' + i for i in aTable.columnsInfo.name]
    aColumnsName = self.columnsInfo.name + aNewColumnsName
    aColumnsType = self.columnsInfo.type + aTable.columnsInfo.type
    aColumnsInfo = ColumnInfo(aColumnsName, aColumnsType)
    aNewTable = Table(aTableName, aColumnsInfo, [])
    #print(aNewTable)
    for row in self:
      aRow = row.data.copy()
      aFkId = row.get(aIdColumn)
      aRow +=  aTable.getRow(aTable.getRowIndex(aFkId)).data
      aNewTable.rows.append(aRow)
    aNewTable.removeColumn(aIdColumn)
    return aNewTable
    


TableError : Table = Table('TableError', ColumnInfo([],[]), [])
