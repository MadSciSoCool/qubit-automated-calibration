from enum import Enum
import numpy as np
import typing
import warnings
from scipy.optimize import curve_fit, OptimizeWarning


class ParamsType(Enum):
    ITER = 2
    SINGLE = 1
    BAD = 0


class MiniLogger:
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


class CheckDataResult(typing.NamedTuple):
    bad_data: bool
    in_spec: bool


class CalibrationResult(typing.NamedTuple):
    bad_data: bool
    succeeded: bool
    error_message: str
    calibrated_params: list

# simplified methods for generating different calibration results


def bad_data_result():
    return CalibrationResult(bad_data=True,
                             succeeded=False,
                             error_message="bad data detected",
                             calibrated_params=dict())


def succeeded_result(calibrated_params):
    return CalibrationResult(bad_data=True,
                             succeeded=True,
                             error_message="",
                             calibrated_params=calibrated_params)


def regression_error_result(error_message):
    return CalibrationResult(bad_data=False,
                             succeeded=False,
                             error_message=error_message,
                             calibrated_params=dict())


class Calibration:
    """The container for a physical measurement and proceeding data processing.
    given a piece of data, the module determines the parameter inferred from the data,
    or if the data is corrupted alternatively.
    For checking data, it should also implement a test, to determine if a small piece of data is in spec.
    intended to be inherited by user to realize interface to physical device and specific data processing tasks
    """

    def __init__(self, name, param_keys, dependent_param_keys, timeout) -> None:
        """
        args:
            name:
            param_keys:
            dependent_param_keys: The parameters this calibration need based upon, which are obtained from other parameters 
            timeout: duration of the calibration validity, in minute
        """
        self.name = name
        self.logger = MiniLogger()
        self.param_keys = param_keys
        self.dependent_param_keys = dependent_param_keys
        self.dependent_params = np.zeros(len(dependent_param_keys))
        self.timeout = timeout

    def check_data(self, param):
        """To implement the check data behavior: if the acquired data
        return:
            CheckDataResult, a named tuple with:
                bad_data: bool
                in_spec: bool
        """
        self.logger.log(
            "check_data method is not inherited and thus not valid")
        return CheckDataResult(False, True)

    def calibrate(self):
        """To implement the calibration behavior
        return:
            CalibratedResult, a named tuple with:
                bad_data: bool
                succeeded: bool
                error_code: str
                calibrated_params: dict
        """
        self.logger.log("calibrate method is not inherited and thus not valid")
        calibrated_params = np.zeros[len(self.param_keys)]
        return CalibrationResult(False, False, "default", calibrated_params)


class PhysicalCalibration(Calibration):
    """implement helper functions for basic data analysis
    One implement one model for regression/prediction: y = f(x, theta), 
    and the derived (output) parameters: theta' = g(theta), where theta and theta' are arrays
    Then the fitting is: given dataset x, y ---> theta -g-> theta'
    The test is given by 
    """

    def __init__(self, name, param_keys, dependent_param_keys, timeout, tolerance, bad_data_threshold, downsampling) -> None:
        super().__init__(name, param_keys, dependent_param_keys, timeout)
        self.tolerance = tolerance
        self.bad_data_threshold = bad_data_threshold
        self.downsampling = downsampling

    def scan(self, sweep_space, downsampling=1):
        """the physical data acquisition process
        return:
            (x_data, y_data): tuple of x and y axis of the acquired data, 
        """
        return (sweep_space, sweep_space)

    def model(self, x):
        """the physical model of regression, assume the data is in the gaussian form of y = N(model(x), sigma)
        """
        return x

    def derive(self, model_params):
        """derive the output parameters from the fitting parameters 
        """
        output_params = model_params
        return output_params

    def inv_derive(self, output_params):
        """derive the fitting parameters from the model parameters inversely 
        """
        model_params = output_params
        return model_params

    def test_in_spec(self, x_data, y_data, target_params):
        """test if the given data (x_data, y_data) satisfies the target parameters 
        args:
            x_data: x-axis of the data to be checked
            y_data: y-axis of the data to be checked
            target_params: the target parameters of the test
        return:
            result: True if the data pass, or False if the data fails
        """
        if self.bad_data(x_data, y_data):
            return CheckDataResult(bad_data=True,
                                   in_spec=False)  # bad data
        model_params = self.inv_derive(target_params)
        y_baseline = self.model(x_data, *model_params)
        if self.max_relative_error(y_data, y_baseline) < self.tolerance:
            return CheckDataResult(bad_data=False,
                                   in_spec=True)
        else:
            return CheckDataResult(bad_data=False,
                                   in_spec=False)

    def fit(self, x_data, y_data, p0=None):
        if self.bad_data(x_data, y_data):
            return bad_data_result()
        with warnings.catch_warnings():
            warnings.simplefilter("error", OptimizeWarning)
            try:
                popt, pcov = curve_fit(self.model, x_data, y_data, p0=p0)
                calibrated_params = self.derive(popt)
                return succeeded_result(calibrated_params)
            except ValueError:
                return regression_error_result("either ydata or xdata contain NaNs, or incompatible options are used")
            except OptimizeWarning:
                return regression_error_result("covariance of the parameters can not be estimated")
            except RuntimeError:
                return regression_error_result("least-squares minimization failed")

    def bad_data(self, x_data, y_data):
        """determine if the data is corrupted, 
        this implementation is just to determine if a 1D data array is flat
        """
        std_var = np.std(y_data)
        if std_var > self.bad_data_threshold:
            return False
        else:
            return True

    @staticmethod
    def max_relative_error(data1, data2):
        return np.max(np.abs(data1-data2))
