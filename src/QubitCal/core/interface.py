from enum import Enum
import numpy as np
import typing


class ParamsType(Enum):
    ITER = 2
    SINGLE = 1
    BAD = 0


class SimpleLogger:
    def __init__(self) -> None:
        self.log = ""

    def log(self, info):
        self.log = self.log + self.formatting(info)

    def dump(self):
        log = self.log
        self.log = ""
        return log

    @staticmethod
    def formatting(text):
        return text


class CalibrationStatus(Enum):
    SUCCESS = 1
    FITTING_FAILURE = -1
    BAD_FITTING = -2


class CalibrationResult(typing.NamedTuple):
    succeeded: bool
    error_code: CalibrationStatus
    calibrated_params: dict


class Calibration:
    """The container for a physical measurement and proceeding data processing.
    given a piece of data, the module determines the parameter inferred from the data,
    or if the data is corrupted alternatively.
    For checking data, it should also implement a test, to determine if a small piece of data is in spec.
    intended to be inherited by user to realize interface to physical device and specific data processing tasks
    """

    def __init__(self, name, param_keys, dependent_param_keys, tolerance, timeout) -> None:
        """
        args:
            name:
            param_keys:
            dependent_param_keys: The parameters this calibration need based upon, which are obtained from other parameters 
            tolerance: a dimensionless tolerance t from 0 ~ +inf: accept target * [1-t, 1+t]
            timeout: duration of the calibration validity, in minute
        """
        self.name = name
        self.logger = SimpleLogger()
        self.param_keys = param_keys
        self.tolerance = tolerance
        self.timeout = timeout

    def scan(self, sweep_space):
        """To make a measurement, with the sweeping parameters given
        args:
            sweep_space: the points to sweep, could be a 0D, 1D, 2D ... array / linear space from numpy
        return:
            data: the measured data, first N dimension should have the same shape of the sweep space, with M dimensional data appended
        """
        return np.zeros(sweep_space.shape)

    def model(self, x, *args):
        """the inference model, let's """
        return x

    def bad_data(self, data):
        """determine if the data is corrupted or """

    def test_in_spec(self, data, target_params):
        """test if the parameter of 
        args:
            data: data to be checked
            target_params: the target parameters of the test
        return:
            result: True if the data pass, or False if the data fails
        """
        test_params = self.analyze(self.data)
        type_check_result = self.type_check(test_params, target_params)
        if type_check_result == ParamsType.BAD:
            raise(Exception("two parameters are of different type"))
        else:
            max_error = self.max_relative_error(
                test_params, target_params, type_check_result)
            if max_error <= self.tolerance:
                return True
            else:
                return False

    def analyze(self, data):
        """infer the parameter from the data, i.e. fitting
        args:
            data: data to be checked
        return:

        """
        return 0

    # helper functions
    @staticmethod
    def type_check(params1, params2):
        type1 = type(params1)
        type2 = type(params2)
        iter_type = [list, np.ndarray, tuple]
        single_type = [int, float, complex]
        if type1 in iter_type and type2 in iter_type:
            if len(params1) == len(params2):
                return ParamsType.ITER
        else:
            if type1 in single_type and type2 in single_type:
                return ParamsType.SINGLE
        return ParamsType.BAD

    @staticmethod
    def max_relative_error(params1, params2, type):
        if type == ParamsType.ITER:
            return
        elif type == ParamsType.SINGLE:
            return np.abs(params2/params1 - 1)
