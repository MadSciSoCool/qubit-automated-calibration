from sys import maxunicode
from ..core.interface import PhysicalCalibration
from labber import ScriptTools, Scenario
from pathlib import PurePath


class LabberCalibration:
    def __init__(self, name, param_keys, dependent_param_keys, tolerance,
                 timeout, bad_data_threshold, downsampling, setup_path, data_path) -> None:
        super().__init__(name, param_keys, dependent_param_keys,
                         tolerance, timeout, bad_data_threshold, downsampling)
        self.setup_path = PurePath(setup_path)
        self.data_path = PurePath(data_path)

    def get_num_file_name(self):
        max_num = 0
        for file in self.data_path.glob(f"*_{self.name}.hdf5"):
            try:
                key = int(file[:5])
            except ValueError:
                key = 0
            max_num = key if key > max_num else max_num
        return self.data_path / f"{max_num+1:05d}_{self.name}.hdf5"

    def get_meas(self):
        return ScriptTools.MeasurementObject(self.setup_path, self.get_num_file_name())

    def set_sweep(self, sweep_variable, sweep_space):
        """To add/modify step in the setup file (Thus to be called before )
        """
        s = Scenario()
        s.load(self.setup_path)
        try:
            # TODO: investigate the error raised by get_step
            s.get_step(sweep_variable).update_from_values(sweep_space)
        except Exception:
            s.add_step(sweep_variable, sweep_space)
        s.save(self.setup_path)
