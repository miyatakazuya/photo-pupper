# *************************************************
# * Filename: photobooth_launch.py
# * Student: Kazuya Miyata, kamiyata@ucsd.edu
# *
# * Description: ROS2 launch file that reads node_config.yml and
# *              launches the configured photo booth nodes with
# *              their parameters.
# *
# * How to use:
# * Usage:
# *     ros2 launch photo_pupper photobooth_launch.py
# *************************************************
import os
import yaml
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch_ros.actions import Node


# *************************************************
# * Name: generate_launch_description()
# * Purpose: Reads node configuration from YAML and builds a
# *          LaunchDescription with the enabled nodes.
# * @input None.
# * @return LaunchDescription with configured node actions.
# *************************************************
def generate_launch_description():
    pkg_share = get_package_share_directory("photo_pupper")
    node_config_path = os.path.join(pkg_share, "config", "node_config.yml")
    
    try:
        with open(node_config_path, "r") as f:
            config = yaml.safe_load(f)
            nodes_to_run = config.get("photobooth_nodes", {})
            print("\n==========================================")
            print(f"Loading node_config: {node_config_path}")
            for node, cfg in nodes_to_run.items():
                print(f"  - {node}: {cfg}")
            print("==========================================\n")
    except Exception as e:
        print(f"ERROR loading node_config: {e}")
        return LaunchDescription()

    launch_actions = []

    for node_name, node_cfg in nodes_to_run.items():
        enabled = 1
        pkg = "photo_pupper"
        executable = f"{node_name}.py"
        node_params = []

        # Parse node configuration which can be a simple active toggle (0/1) or a dictionary
        if isinstance(node_cfg, dict):
            enabled = node_cfg.get("enabled", 1)
            pkg = node_cfg.get("package", pkg)
            executable = node_cfg.get("executable", executable)
            params_dict = node_cfg.get("parameters", {})
            if params_dict:
                node_params.append(params_dict)
        else:
            enabled = node_cfg

        if enabled:
            launch_actions.append(
                Node(
                    package=pkg,
                    executable=executable,
                    name=node_name,
                    parameters=node_params if node_params else None,
                    output="screen",
                )
            )

    return LaunchDescription(launch_actions)
