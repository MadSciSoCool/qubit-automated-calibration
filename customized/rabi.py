from autocal import LabberCalibration
from seqpy import *
from math_helpers import sinusoidal_p0, sinusoidal, pca
import numpy as np


class CustomizedCalibration(LabberCalibration):
    def model(self, x, rabi_amp, rabi_freq, phase, offset):
        """Rabi oscillation, sinusoidal function"""
        return sinusoidal(x, rabi_amp, rabi_freq, phase, offset)

    def calibrate(self):
        x_data, y_data = self.scan()
        y_data = pca(np.real(y_data), np.imag(y_data))
        p0 = sinusoidal_p0(x_data, y_data)
        return self.fit(x_data, y_data, p0=p0)

    def scan(self, sweep_space):
        self.validate_sequence()
        self.set_sweep('HDAWG - SeqPy - Sweepable 1 Value', sweep_space)
        Meas = self.get_meas()
        Meas.updateValue('HDAWG - SeqPy - Json Path', self.sequence_path)
        return Meas.performMeasurement()

    def dump_sequence(self):
        v = sweepables("v")
        Control = control_amp * \
            Gaussian(width=control_pi_width/10.*1e-9, plateau=v).shift(-v/2)
        seq = Sequence(n_channels=1)
        seq.register(-control_pi_width/5.*1e-9, Control, cx)
        seq.trigger_pos = 0
        seq.dump(self.sequence_path)
