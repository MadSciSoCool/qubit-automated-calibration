from enum import Enum
from datetime import datetime, timedelta
from .interface import CalibrationStatus
from .exceptions import DiagnoseFailure, MaintainFailure, CalibrationFailure


class CheckDataResult(Enum):
    IN_SPEC = 1
    OUT_OF_SPEC = 0
    BAD_DATA = -1


class DiagnoseResult(Enum):
    SUCCESS = 1
    FAILURE = -1
    SUCCESS_WITH_RECALIBRATION = 0


class CalibrationNode:
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
        name = calibration.name
        timeout = calibration.timeout
        self.dependents = dependents
        self.table_name = f"{name}_{datetime.now().strftime('%Y-%m-%d-%H:%M:%S')}"
        self.calibration = calibration
        self.database = database
        self.database.initialize(self.table_name, self.calibration.param_keys)
        self.period_of_validity = timedelta(minutes=timeout)
        self.recalibrated = False
        self.calibration_failed = False

    def check_data(self):
        """check if a calibration needs to be done, by taking limited data"""
        acquired_data = self.calibration.scan()
        if self.calibration.bad_data(acquired_data):
            return CheckDataResult.BAD_DATA
        last_params = self.database.last_params(
            self.table_name, *self.calibration.param_keys)
        if self.calibration.test_in_spec(acquired_data, last_params):
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
        # if none needs to do so, return a failure (reason for bad data not found)
        elif check_data_result == CheckDataResult.BAD_DATA:
            recalibrated = [n.diagnose() for n in self.dependents]
        if not any(recalibrated):
            raise DiagnoseFailure()
        # if out of spec / dependents already been recalibrated, just do a calibration on this node and update parameters
        self.update_params(self.calibrate())
        return True

    # exposed interfaces

    def maintain(self):
        """
        maintain the single node and possible all upper branch nodes by recursion
        return:
            maintain status: SUCCESS(1) all nodes maintained / not necessary to maintain
            FAILURE(0) means unable to maintain
        """
        # recursive maintain dependent nodes
        for n in self.dependents:
            n.maintain()
        # check_state
        if self.check_state():
            return
        self.recalibrated = False
        # check_data
        diagnose_result = self.diagnose()
        if diagnose_result == DiagnoseResult.FAILURE:
            # fails if the diagnose of the node fails
            raise MaintainFailure("")

    def calibrate(self):
        """
        manually invoke a calibration, taking the data needed experimentally
        for a node which represents a measurement, calibrate also means manually invoke a measurement
        return:
            dictionary contains the mapping: parameter name -> parameter value 
        """
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
