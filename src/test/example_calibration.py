from src.autocal.core.interface import PhysicalCalibration
import numpy as np


class CustomizedCalibration(PhysicalCalibration):
    real_a = 10
    real_b = 20
    sigma = 1
    sweep_space = np.linspace(0, 10, 101)

    def __init__(self, otherkeyword1, someparam="default", **kwargs) -> None:
        super().__init__(**kwargs)
        self.otherkeyword1 = otherkeyword1
        self.someparam = someparam

    def check_data(self, param, bad_data=False):
        x_data, y_data = self.scan(
            self.sweep_space, downsampling=self.downsampling, bad_data=bad_data)
        return self.test_in_spec(x_data, y_data, param)

    def calibrate(self, bad_data=False):
        x_data, y_data = self.scan(self.sweep_space, bad_data=bad_data)
        return self.fit(x_data, y_data)

    def model(self, x, a, b):
        return a*x+b

    def scan(self, sweep_space, downsampling=1, bad_data=False):
        sweep_space = sweep_space[::int(downsampling)]
        if not bad_data:
            return sweep_space, self.real_a * sweep_space + self.real_b + self.sigma * np.random.randn(*sweep_space.shape)
        else:
            return sweep_space, self.sigma * np.random.randn(*sweep_space.shape)

    def derive(self, model_params):
        a, b = model_params
        # an artificial third parameter a * b
        return np.append(model_params, a * b)

    def inv_derive(self, output_params):
        return output_params[:2]  # remove the artificial parameter
