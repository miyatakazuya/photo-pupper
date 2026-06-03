import os
import yaml
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch_ros.actions import Node

def generate_launch_description():
    
    pkg_share = get_package_share_directory('photo_pupper')
    
    node_config_path = os.path.join(pkg_share, 'config', 'node_config.yml')
    try:
        with open(node_config_path, 'r') as f:
            config = yaml.safe_load(f)
            nodes_to_run = config['photobooth_nodes']
    except Exception as e:
        print(f"ERROR loading node_config: {e}")
        return LaunchDescription()

    launch_actions = []

    # Define the nodes in the photobooth system
    nodes_info = [
        ('fsm_node.py', 'fsm_node'),
        ('gamepad_node.py', 'gamepad_node'),
        ('movement_node.py', 'movement_node'),
        ('people_detection_node.py', 'people_detection_node'),
        ('photo_processing_node.py', 'photo_processing_node'),
        ('printer_node.py', 'printer_node'),
        ('screen_node.py', 'screen_node'),
        ('touch_node.py', 'touch_node'),
        ('speaker_node.py', 'speaker_node')
    ]

    for executable_name, config_key in nodes_info:
        if nodes_to_run.get(config_key, 1):
            launch_actions.append(Node(
                package='photo_pupper',
                executable=executable_name,
                name=config_key,
                output='screen'
            ))

    return LaunchDescription(launch_actions)
