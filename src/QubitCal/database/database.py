from datetime import datetime


class CalibrationDatabase:
    def __init__(self, db_con) -> None:
        self.db_con = db_con

    def initialize_table(self, table_name, var_keys):
        # Primary key is timestamp
        self.db_con.execute(
            f"""CREATE TABLE IF NOT EXISTS {table_name} (
                timestamp TEXT PRIMARY KEY,
                calibration_log TEXT)""")
        for var_key in var_keys:
            self.db_con.execute(f"ALTER TABLE {table_name} ADD {var_key} REAL")

    def last_timestamp(self, table_name):
        text_format = self.db_con.execute(
            f"SELECT timestamp FROM {table_name} ORDER BY ROWID DESC LIMIT 1").fetchone()[0]
        return datetime.strptime(text_format, '%Y-%m-%d-%H:%M:%S:%f')

    def last_params(self, table_name, *args):
        query_result = list()
        for param_key in args:
            command = f"SELECT {param_key} FROM {table_name} ORDER BY ROWID DESC LIMIT 1"
            query_result.append(self.db_con.execute(command).fetchone()[0])
        return query_result

    def insert(self, table_name, var_dict, measurement_log="", calibration_log=""):
        # create timestamp and a new row
        timestamp = datetime.now().strftime('%Y-%m-%d-%H:%M:%S:%f')
        self.db_con.execute(
            f"INSERT INTO {table_name} (timestamp) values (?)", (timestamp,))
        for var_name, var_value in var_dict.items():
            self.db_con.execute(f"UPDATE {table_name} SET {var_name}=? WHERE timestamp=?",
                                (var_value, timestamp))
        self.db_con.execute(f"UPDATE {table_name} SET calibration_log=? WHERE timestamp=?",
                            (calibration_log, timestamp))
