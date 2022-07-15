import unittest
import numpy as np
from example_calibration import ExampleCalibration


class CalibrationTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.calibration = ExampleCalibration(name="example",
                                              param_keys=["a", "b", "a*b"],
                                              dependent_param_keys=[],
                                              tolerance=10,
                                              timeout=1,
                                              bad_data_threshold=5,
                                              downsampling=5,
                                              otherkeyword1=0,
                                              someparam=0)
        a, b = self.calibration.real_a, self.calibration.real_b
        self.real_params = np.array([a, b, a*b])
        return super().setUp()

    def test_calibrate(self):
        result = self.calibration.calibrate()
        self.assertLess(np.linalg.norm(result.calibrated_params - self.real_params), 5,
                        "calibrated params did not pass the test")
        bad_result = self.calibration.calibrate(bad_data=True)
        self.assertTrue(bad_result.bad_data,
                        "did not recognize bad data in calibration")

    def test_check_data(self):
        result = self.calibration.check_data(self.real_params)
        self.assertTrue(result.in_spec)
        result = self.calibration.check_data(10 * self.real_params)
        self.assertFalse(result.in_spec)
        bad_result = self.calibration.check_data(
            self.real_params, bad_data=True)
        self.assertTrue(bad_result.bad_data)


if __name__ == '__main__':
    unittest.main()
