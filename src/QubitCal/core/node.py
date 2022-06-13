from enum import Enum
from datetime import datetime, timedelta
from .interface import CalibrationStatus
from .exceptions import DiagnoseFailure, MaintainFailure, CalibrationFailure


class CheckDataResult(Enum):
    IN_SPEC = 1
    OUT_OF_SPEC = 0
    BAD_DATA = -1


class Node:
    """To encapsulate basic functions as a node in a DAG"""

    def __init__(self, name, dependents) -> None:
        """ initialize a calibration node,
        args:
            table_name: name corresponding to the table in database record
            dependents: list of Node, the dependent nodes in DAG
        """
        self.name = name
        self.dependents = dependents


class CalibrationNode(Node):
    """To Store one calibration as a node in a DAG, perform the functions of:
    Properties:
    1) a measurement object, whose scan could be tuned to different range and sparseness
    2) a calibration object, for the post process of data
    Methods:
    1) manually invoke a calibration (full check)
    2) check if a calibration needs to be done (fast check)
    3) pass and store parameters into database
    4) timestamps, used for determining if a calibration is needed
    """

    def __init__(self, calibration, database, dependents):
        """ initialize a calibration node,
        args:
            calibration:
            database:
            dependents: list of CalibrationNode, the dependent calibrations
        """
        super().__init__(calibration.name, dependents)
        # name with timestamp, corresponds to the database table name
        self.table_name = f"{calibration.name}_{datetime.now().strftime('%Y-%m-%d-%H:%M:%S')}"
        self.calibration = calibration
        self.database = database
        self.database.initialize(self.table_name, self.calibration.param_keys)
        self.period_of_validity = timedelta(minutes=calibration.timeout)
        self.recalibrated = False
        # flags for DFS traversing
        self.calibration_failed = False
        self.discovered = False

    def check_data(self):
        """check if a calibration needs to be done, by taking limited data"""
        self.retrieve_dependent_params()
        acquired_data = self.calibration.scan()
        if self.calibration.bad_data(acquired_data):
            return CheckDataResult.BAD_DATA
        last_params = self.database.last_params(
            self.table_name, *self.calibration.param_keys)
        if self.calibration.test_in_spec(acquired_data, last_params):
            # if check_data is passed, also generated a database record to refresh the timestamp
            self.update_params(last_params)
            return CheckDataResult.IN_SPEC
        else:
            return CheckDataResult.OUT_OF_SPEC

    def check_state(self):
        """
        Based on prior knowledge (without data), determine if a calibration needs to be done
        True <-> passed check, not necessary to calibrate
        False <-> failed check, need to calibrate
        """
        if self.timeout or self.calibration_failed:
            return False  # fail if timed out or just failed an calibration
        if not all([p.check_state() for p in self.parents]):
            return False  # fail if one of the parents failed
        if any([p.recalibrated for p in self.parents]):
            return False  # fail if one parent has been recalibrated in this run
        return True

    def update_params(self, param_dict):
        self.database.insert(table_name=self.table_name,
                             var_dict=param_dict,
                             calibration_log=self.calibration.logger.dump())

    @staticmethod
    def parse_param_key(key):
        raw = key.split("-")
        if len(raw) != 2:
            raise Exception(
                f"{key} is not in correct syntax of a parameter key (\"calibration - name\")")
        return [s.strip() for s in raw]

    def retrieve_dependent_params(self):
        retrieved_dependent_params = list()
        for key in self.calibration.dependent_param_keys:
            node_name, param_key = self.parse_param_key(key)  # parse
            table_name = None
            for p in self.dependents:
                if p.name == node_name:
                    table_name = p.table_name
            if table_name:
                retrieved_dependent_params.append(
                    *self.database.last_params(table_name, param_key))
            else:
                raise CalibrationFailure(
                    f"{node_name} not resolved in parents")
        # update
        self.calibration.dependent_params = retrieved_dependent_params

    @property
    def timeout(self):
        """return True if the calibration has timed out and need to be redone"""
        last_calibrated_time = self.database.last_timestamp(self.table_name)
        if datetime.now() - last_calibrated_time > self.period_of_validity:
            return True
        else:
            return False

    def diagnose(self):
        """
        return:
            recalibrated: true if the diagnostic is done with a recalibration
        """
        check_data_result = self.check_data()
        # if already in spec, return without any calibration
        if check_data_result == CheckDataResult.IN_SPEC:
            return False
        # if bad data, check whether dependents needs recalibration:
        # if none needs to do so, return a failure (the reason for acquiring bad data is not found)
        elif check_data_result == CheckDataResult.BAD_DATA:
            recalibrated = [n.diagnose() for n in self.dependents]
        if not any(recalibrated):
            raise DiagnoseFailure(self.calibration.name)
        # if out of spec / dependents already been recalibrated, just do a calibration on this node and update parameters
        self.update_params(self.calibrate())
        self.recalibrated = True
        return True

    def reset_flags(self):
        """reset all upper branch recalibrated flag to false"""
        for node in self.dependents:
            node.reset_flags()
        self.recalibrated = False
        self.discovered = False

    # exposed interfaces

    def _maintain(self, reset=False):
        """real and hidden implementation of maintain function
        args:
            reset: whether to reset calibrated flag in the end
        """
        if not self.discovered:
            self.discovered = True
            # recursive maintain dependent nodes
            for n in self.dependents:
                n._maintain()
            # check_state
            if self.check_state():
                return
            # check_data
            try:
                self.diagnose()
            except DiagnoseFailure as e:
                # fails if the diagnose of the node fails
                raise MaintainFailure(self, e.node_failed)
        if reset:
            self.reset_flags()

    def maintain(self):
        """maintain the single node all upper branch nodes by DFS recursion
        if maintenance could not be finished, a MaintainFailure will be raised.
        """
        self._maintain(reset=True)

    def calibrate(self):
        """
        manually invoke a calibration, taking the data needed experimentally
        for a node which represents a measurement, calibrate also means manually invoke a measurement
        return:
            dictionary contains the mapping: parameter name -> parameter value 
        """
        self.retrieve_dependent_params()
        acquired_data = self.calibration.scan()
        if self.calibration.bad_data(acquired_data):
            self.calibration_failed = True
            raise CalibrationFailure(
                "Bad data in a real calibration, manual inspection is required")
        else:
            result = self.calibration.analyze(acquired_data)
            if result.succeeded:
                return dict(zip(self.calibration.param_keys, result.calibrated_params))
            else:
                self.calibration_failed = True
                if result.status == CalibrationStatus.FITTING_FAILURE:
                    raise CalibrationFailure(
                        "Not able to fit the acquired data")
                elif result.status == CalibrationStatus.BAD_FITTING:
                    raise CalibrationFailure(
                        "Fitted the acquired data, but with ")


class BaseNode(Node):
    def __init__(self, database, **kwargs):
        super().__init__(name="Base", dependents=[])
        self.table_name = f"Base_{datetime.now().strftime('%Y-%m-%d-%H:%M:%S')}"
        # write up all parameters in the database
        database.insert(table_name=self.table_name,
                        var_dict=kwargs,
                        calibration_log="Base parameters insertion")
