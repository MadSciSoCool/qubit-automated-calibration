from autocal import LabberCalibration
from seqpy import *
import numpy as np
from math_helpers import damped_sinusoidal, damped_sinusoid_p0, pca


class CustomizedCalibration(LabberCalibration):
    def __init__(self, name, param_keys, dependent_param_keys, tolerance, timeout,
                 bad_data_threshold, downsampling, sequence_path) -> None:
        super.__init__(name, param_keys, dependent_param_keys,
                       tolerance, timeout, bad_data_threshold, downsampling)
        self.sequence_path = sequence_path

    def model(self, x, a, gamma, freq, phi, offset):
        """T2R fitting, damped sinusoidal function"""
        return damped_sinusoidal(x, a, gamma, freq, phi, offset)

    def calibrate(self):
        x_data, y_data = self.scan()
        y_data = pca(np.real(y_data), np.imag(y_data))
        p0 = damped_sinusoidal(x_data, y_data)
        return self.fit(x_data, y_data, p0=p0)

    def scan(self, sweep_space):
        self.set_sweep('HDAWG - SeqPy - Sweepable 1 Value', sweep_space)
        Meas = self.get_meas()
        Meas.updateValue('HDAWG - SeqPy - Json Path', self.sequence_path)
        return Meas.performMeasurement()

    def dump_sequence(self):
        v = sweepables("v")
        seq = Sequence(n_channels=1)
        seq.register(0, H, cx)
        seq.register(v, H, cxr)
        seq.trigger_pos = v + 2*control_pi_width*1e-9
        seq.dump(self.sequence_path)
