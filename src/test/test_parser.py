import unittest
from src.autocal.parsing.dag_parser import *
from src.autocal.core.exceptions import ParsingFailure
from src.autocal.database import CalibrationDatabase
from pathlib import Path
import sqlite3 as sq


class ParserTestCase(unittest.TestCase):
    config_path = r"src/test/example_config.ini"

    def setUp(self) -> None:
        return super().setUp()

    def test_helpers(self):
        # parse string list
        ls = parse_string_list("a, b, 123, ")
        self.assertEqual(ls, ["a", "b", "123"])
        # parse param
        ls = parse_param("a- b")
        self.assertEqual(ls, ["a", "b"])

    def test_config2dict(self):
        database_address, base_directory, nodes_config = config2dict(
            self.config_path)
        self.assertTrue(Path(database_address).absolute() == Path(
            "src/test/test.db").absolute())
        self.assertTrue(Path(base_directory).absolute() == Path(
            "src/test").absolute())
        self.assertEqual(nodes_config["Base"]["param1"], 3.14e9)
        self.assertEqual(nodes_config["Base"]["param2"], "some string")
        self.assertEqual(nodes_config["Test"]["parameters"], [
                         "a", "b", "a_times_b"])
        self.assertEqual(nodes_config["Test"]["dependent parameters"], [
                         "Base - param1", "Base- param2"])
        self.assertEqual(nodes_config["Test"]["tolerance"], 0.1)
        self.assertEqual(nodes_config["Test"]["timeout"], 60)
        self.assertEqual(nodes_config["Test"]["otherkeyword1"], True)
        self.assertEqual(nodes_config["Test"]["someparam"], 1)

    def test_topological_sort(self):
        """ Example DAG:
        |---|
        a-b-c
          |-d-e-f
              |-g
            Counter Example:
            add g to a connection 
        """
        example_dag = {"a": "bc",
                       "b": "cd",
                       "c": "",
                       "d": "e",
                       "e": "fg",
                       "f": "",
                       "g": ""}
        graph_with_loop = {"a": "bc",
                           "b": "cd",
                           "c": "",
                           "d": "e",
                           "e": "fg",
                           "f": "",
                           "g": "a"}
        sorted = topological_sort(example_dag)
        for letter in "abcdefg":
            self.assertIn(letter, sorted)
        self.assertEqual(len(sorted), 7)
        for u, vs in example_dag.items():
            for v in vs:
                self.assertLess(sorted.index(v), sorted.index(u))
        with self.assertRaises(ParsingFailure) as ecm:
            topological_sort(graph_with_loop)
        self.assertIn("acyclic", str(ecm.exception))

    def test_dict2dag(self):
        database_address, base_directory, nodes_config = config2dict(
            self.config_path)
        with sq.connect(database_address) as db_con:
            calibration_database = CalibrationDatabase(db_con)
            dag_container = dict2dag(
                base_directory, calibration_database, nodes_config)


if __name__ == "__main__":
    unittest.main()
