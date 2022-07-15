from typing import Sequence
from pathlib import Path
import hashlib
from sympy import sequence
from autocal import LabberCalibration
from seqpy import *


def hash_file(filename, blocksize=65536):
    with open(filename, "rb") as f:
        file_hash = hashlib.blake2b()
        for block in iter(lambda: f.read(blocksize), b""):
            file_hash.update(block)
    return file_hash.hexdigest()


class SeqPyCalibration(LabberCalibration):
    def __init__(self, name, param_keys, dependent_param_keys, tolerance, timeout,
                 bad_data_threshold, downsampling, sequence_path) -> None:
        super.__init__(name, param_keys, dependent_param_keys,
                       tolerance, timeout, bad_data_threshold, downsampling)
        self.sequence_path = Path(sequence_path)
        self.dump_sequence()
        self.seq_hash = hash_file(self.sequence_path)

    def dump_sequence(self):
        seq = Sequence()
        seq.dump(self.sequence_path)

    def validate_sequence(self):
        if hash_file(self.sequence_path) != self.seq_hash:
            self.dump_sequence()

    def get_carrier(self):
        freq = self.search_dependent_params("pi pulse width")
        cx = Carrier(frequencies=freq, phases=0)
        cy = Carrier(frequencies=freq, phases=90)
        return cx, cy

    def get_pi_pulse(self):
        width = self.search_dependent_params("pi pulse width")
        plateau = self.search_dependent_params("pi pulse plateau")
        amp = self.search_dependent_params("pi pulse amplitude")
        pi_pulse = amp * Gaussian(width, plateau)
        return pi_pulse

    def search_dependent_params(self, key):
        return
