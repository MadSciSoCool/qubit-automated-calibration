import configparser
import re
from importlib import import_module
from pathlib import Path
from ..core.exceptions import ParsingFailure
from ..core.node import CalibrationNode, BaseNode


conversion = {"int": int, "float": float, "string": lambda x: x}

"""helper functions"""


def parse_string_list(str):
    return [raw.strip() for raw in str.split(",")]


def parse_param(str):
    list = [raw.strip() for raw in str.split("-")]
    if len(list) != 2:
        raise ParsingFailure(
            f"{str} is not in correct syntax of a parameter key (\"calibration - name\")")


base_pattern = r"^Base ?- ?.*\S.*$"


def config2dict(filelike_configuration):
    """To construct a dictionary describing the nodes from the file
    """
    config = configparser.ConfigParser()
    config.read(Path(filelike_configuration).resolve().open())
    general_config = dict()
    nodes_config = dict()
    for section in config.sections():
        if section == "Common":
            for key in ("base directory", ):
                general_config[key] = config[section][key]
        if re.match(base_pattern, section):
            node, param = parse_param(section)
            nodes_config
        if "-" in section:
            node, param = parse_param(section)
            type = config[section]["type"].lower()
            # switch case by the type of parameter
            if type == "boolean" or "bool":
                value = config[section].getboolean("value")
            elif type in conversion.keys():
                value = conversion[type](config[section]["value"])
            else:
                raise ParsingFailure
            # raise a parsing failure when the main section is not found before the subsection
            try:
                nodes_config[node][param] = value
            except KeyError:
                raise ParsingFailure(
                    f"{node} is not declared before {section}")
        else:
            # make a new node
            nodes_config[section] = dict()
            this_node = nodes_config[section]
            this_config = config[section]
            this_node["filename"] = this_config["filename"]
            for i in ("parameters", "dependent parameters"):
                this_node[i] = parse_string_list(this_config[i])
            for i in ("tolerance", "timeout"):
                this_node[i] = float(this_config[i])
    return general_config, nodes_config


def topological_sort(dag_dict):
    """topological sorting of DAG"""
    temporary_mark = set()
    permanent_mark = set()
    sorted = list()

    def visit(node):
        if node in permanent_mark:
            return
        if node in temporary_mark:
            loop = "-".join(temporary_mark)
            raise ParsingFailure(
                f"the graph is not acyclic, with a loop {loop}")
        temporary_mark |= {node}
        for n in dag_dict[node]:
            try:
                visit(n)
            except KeyError:
                raise ParsingFailure(
                    f"node {node} has a unresolved parents {n}")
        temporary_mark.remove(node)
        permanent_mark |= {node}
        sorted.append(node)

    for key in dag_dict.keys():
        visit(key)

    return sorted


def imported_calibration(base_path, filelike):
    path = Path(base_path) / filelike
    return import_module(path).Calibration


def dict2dag(general_config, nodes_config, database):
    # extract information from general config
    base_path = general_config["base directory"]
    # resolve a DAG from the dependents
    dag_dict = dict()
    for name, config in nodes_config.items():
        dependents = [parse_param(s)[0]
                      for s in config[name]["dependent parameters"]]
        dag_dict[name] = dependents
    # check the validity of dag during the topological sorting
    sorted = topological_sort(dag_dict)
    dag_container = dict()
    # initialize base node
    dag_container["Base"] = BaseNode(database, **nodes_config["Base"])
    # initialize all nodes based on topological sorting
    for key in sorted.remove("Base"):
        # retrieve arguments, instantiate calibration objects
        filelike = nodes_config["filename"]
        param_keys = nodes_config["parameters"]
        dependent_param_keys = nodes_config["dependent parameters"]
        tolerance = nodes_config["tolerance"]
        timeout = nodes_config["timeout"]
        args = (key, param_keys, dependent_param_keys, tolerance, timeout)
        calibration = imported_calibration(base_path, filelike)(*args)
        # instantiate calibration nodes objects
        dependents = [dag_container[dep] for dep in dag_dict[key]]
        dict[key] = CalibrationNode(calibration=calibration,
                                    database=database,
                                    dependents=dependents)
    return dag_container
