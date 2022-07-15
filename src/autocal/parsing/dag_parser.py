import configparser
import re
from importlib import import_module
from pathlib import Path
from ..core.exceptions import ParsingFailure
from ..core.node import CalibrationNode, BaseNode


"""helper functions"""


def parse_string_list(str):
    return [raw.strip() for raw in str.split(",") if raw.strip() != ""]


def parse_param(str):
    list = [raw.strip() for raw in str.split("-")]
    if len(list) != 2:
        raise ParsingFailure(
            f"{str} is not in correct syntax of a parameter key (\"calibration - name\")")
    return list


base_pattern = r"^Base ?- ?.*\S.*$"


def retrieve_typed_param(string_like):
    """retrieved parameter based on type of string:
    True/false/no/YeS -> bool
    1/2/3 -> int
    1.23/3.14e9 -> float
    sunny/1a2b -> string
    """
    if string_like.lower() in ["true", "yes"]:
        return True
    elif string_like.lower() in ["false", "no"]:
        return False
    else:
        try:
            return int(string_like)
        except ValueError:
            pass
        try:
            return float(string_like)
        except ValueError:
            return string_like


def config2dict(filelike_configuration):
    """To construct a dictionary describing the nodes from the file
        return:
        database_address
        base_directory
        nodes_config:
            |
            -- Base:
            |   |
            |   -- param1:
            |   -- param2:
            -- Node1:
                |
                -- filename:
                -- parameters:
                -- dependent parameters:
                -- tolerance:
                -- timeout:
                -- other_param1:
    """
    config = configparser.ConfigParser(inline_comment_prefixes=(';', '#',))
    config.read(Path(filelike_configuration).resolve())
    base_directory = None
    database_address = None
    nodes_config = dict()
    nodes_config["Base"] = dict()
    for section in config.sections():
        # common configurations
        if section == "General":
            database_address = config[section]["database address"]
            base_directory = config[section]["base directory"]
        else:
            # make a new node
            nodes_config[section] = dict()
            this_node = nodes_config[section]
            this_config = config[section]
            for k, v in this_config.items():
                if k in ("parameters", "dependent parameters",):
                    this_node[k] = parse_string_list(v)
                else:
                    this_node[k] = retrieve_typed_param(v)
    return database_address, base_directory, nodes_config


def topological_sort(dag_dict):
    """topological sorting of DAG"""
    temporary_mark = set()
    permanent_mark = set()
    sorted = list()

    def visit(node, temporary_mark, permanent_mark):
        if node in permanent_mark:
            return
        if node in temporary_mark:
            loop = "-".join(temporary_mark)
            raise ParsingFailure(
                f"the graph is not acyclic, with a loop {loop}")
        temporary_mark |= {node}
        for n in dag_dict[node]:
            try:
                visit(n, temporary_mark, permanent_mark)
            except KeyError:
                raise ParsingFailure(
                    f"node {node} has a unresolved parents {n}")
        temporary_mark.remove(node)
        permanent_mark |= {node}
        sorted.append(node)

    for key in dag_dict.keys():
        visit(key, temporary_mark, permanent_mark)

    return sorted


def imported_calibration(base_path, filelike):
    path = Path(base_path) / filelike
    return import_module(str(path).replace("/", ".").strip(".py")).CustomizedCalibration


keyword_mapping = {"parameters": "param_keys",
                   "dependent parameters": "dependent_param_keys",
                   "bad data threshold": "bad_data_threshold"}


def dict2dag(base_directory, database, nodes_config):
    # resolve a DAG from the dependents
    dag_dict = dict()
    dag_dict["Base"] = list()
    for name, config in nodes_config.items():
        if name != "Base":
            dependents = {parse_param(s)[0]
                          for s in config["dependent parameters"]}
            dag_dict[name] = dependents
    # check the validity of dag during the topological sorting
    sorted = topological_sort(dag_dict)
    dag_container = dict()
    # initialize base node
    dag_container["Base"] = BaseNode(
        database, **nodes_config["Base"])
    # initialize all nodes based on topological sorting
    sorted.remove("Base")
    for nodename in sorted:
        # retrieve arguments, instantiate calibration objects
        this_config = nodes_config[nodename]
        filelike = this_config["filename"]
        # build arguments for the calibration
        kwargs = dict()
        kwargs["name"] = nodename
        for key, value in this_config.items():
            if key == "filename":
                continue
            key = keyword_mapping[key] if key in keyword_mapping.keys(
            ) else key
            kwargs[key] = value
        calibration = imported_calibration(base_directory, filelike)(**kwargs)
        # instantiate calibration nodes objects
        dependents = [dag_container[dep] for dep in dag_dict[nodename]]
        dag_container[nodename] = CalibrationNode(calibration=calibration,
                                                  database=database,
                                                  dependents=dependents)
    return dag_container
