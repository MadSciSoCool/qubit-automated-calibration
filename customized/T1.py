from .time_domain_calibration import SeqPyCalibration
from seqpy import *
import numpy as np
from math_helpers import exponential, exponential_p0, pca


class CustomizedCalibration(SeqPyCalibration):

    def model(self, x, exp_amp, decay_rate, offset):
        """T1 fitting, expotential decay"""
        return exponential(x, exp_amp, decay_rate, offset)

    def calibrate(self):
        x_data, y_data = self.scan()
        y_data = pca(np.real(y_data), np.imag(y_data))
        p0 = exponential_p0(x_data, y_data)
        return self.fit(x_data, y_data, p0=p0)

    def scan(self, sweep_space):
        self.validate_sequence()
        self.set_sweep('HDAWG - SeqPy - Sweepable 1 Value', sweep_space)
        Meas = self.get_meas()
        Meas.updateValue('HDAWG - SeqPy - Json Path', self.sequence_path)
        return Meas.performMeasurement()

    def dump_sequence(self):
        F, cx = self.get_pi_pulse()
        v = sweepables("v")
        seq = Sequence(n_channels=1)
        seq.register(0, F, cx)
        seq.trigger_pos = v + 2 * F.width * 1e-9
        seq.dump(self.sequence_path)
