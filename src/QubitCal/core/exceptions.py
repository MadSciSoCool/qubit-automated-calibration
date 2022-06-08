from platform import node


class CalibrationFailure(Exception):
    pass


class MaintainFailure(Exception):
    def __init__(self, node_failed) -> None:
        message = f"Maintenance failed, due to failure of proper calibration at node {node_failed}"
        super().__init__(message)


class DiagnoseFailure(Exception):
    def __init__(self, node_failed, *args: object) -> None:
        self.node_failed = node_failed
        super().__init__(*args)
