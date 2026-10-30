import unittest

from HandlerSQL import Row, Table, eColumnType, ColumnInfo


class TestHandlerSQL(unittest.TestCase):
    def setUp(self):
        self.table = Table("test_table",
            ColumnInfo(["id", "name", "value"], [eColumnType.INT, eColumnType.STRING, eColumnType.INT]),
            [
                [1, "alpha", 10],
                [2, "beta", 20],
            ],
        )

    def test_row_getters_and_len(self):
        row = Row("test", {"id": 0, "name": 1, "value": 2}, [1, "alpha", 10])

        self.assertEqual(row.get("id"), 1)
        self.assertEqual(row.get("name"), "alpha")
        self.assertEqual(row["value"], 10)
        self.assertEqual(len(row), 3)

    def test_table_accessors_and_basic_queries(self):
        self.assertEqual(self.table.get(0, "name"), "alpha")
        self.assertEqual(self.table[1].get("name"), "beta")
        self.assertEqual(self.table.getColumnsName(), ["id", "name", "value"])
        self.assertEqual(
            self.table.getColumnsType(),
            [eColumnType.INT, eColumnType.STRING, eColumnType.INT],
        )
        self.assertEqual(len(self.table), 2)
        self.assertEqual(self.table.getColumn("name"), ["alpha", "beta"])
        self.assertIn("name", str(self.table))

    def test_add_data_and_column_manipulation(self):
        self.table.addData([
            [3, "gamma", 30],
            [4, "delta", 40],
        ])
        print(self.table)
        self.assertEqual(len(self.table), 4)
        self.assertEqual(self.table.get(0, "name"), "alpha")
        self.assertEqual(self.table.get(2, "name"), "gamma")
        self.assertEqual(self.table.get(3, "value"), 40)

        self.table.addColumns(["active"], [eColumnType.INT], [[1, 0, 1, 0]])
        self.assertEqual(self.table.get(0, "active"), 1)
        self.assertEqual(self.table.getColumnsName()[-1], "active")

        with self.assertRaises(RuntimeError):
            self.table.addColumns(["active"], [eColumnType.INT], [[1, 0, 1, 0]])

        self.table.removeColumn("name")
        self.assertNotIn("name", self.table.getColumnsName())
        self.assertEqual(self.table.getColumn("value"), [10, 20, 30, 40])
        self.assertEqual(self.table[1]["active"], 0)

        with self.assertRaises(RuntimeError):
            self.table.removeColumn("missing")

    def test_subtable_filters_by_id(self):
        sub = self.table.keepRows('id', {2})

        self.assertEqual(len(sub), 1)
        self.assertEqual(sub.get(0, "id"), 2)
        self.assertEqual(sub.getColumnsName(), ["id", "name", "value"])
