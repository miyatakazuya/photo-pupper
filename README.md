# Pupper Delivery Bot Repo
[![ROS 2 CI](https://github.com/miyatakazuya/photo-pupper/actions/workflows/ros2_ci.yml/badge.svg)](https://github.com/miyatakazuya/photo-pupper/actions/workflows/ros2_ci.yml)

Contributors: Kazuya Miyata, Kane Li, Austin Choi


```
.
├── CMakeLists.txt
├── package.xml
├── photo_pupper // Our Nodes
│   ├── fsm_node.py
│   ├── __init__.py
│   ├── movement_node.py
│   ├── people_detection_node.py
│   ├── photo_processing_node.py
│   ├── printer_node.py
│   ├── screen_node.py
│   └── touch_node.py
├── README.md
├── resource
│   └── photo_pupper
├── setup.cfg
├── setup.py
├── srv
│   └── PrintImage.srv
└── test
    ├── test_copyright.py
    ├── test_flake8.py
    └── test_pep257.py
```

### Configuration
```yaml
# Toggle Nodes (1 is activated)
photobooth_nodes:
  fsm_node: 1
  movement_node: 1
  people_detection_node: 1
  photo_processing_node: 1
  printer_node: 1
  screen_node: 1
  touch_node: 1
```
> The launch file reads the `node_config.yml` file to determine which nodes to run. If a node is not set to `1`, it will not be run. This can be used to test individual functions easier.

### Printer Setup
We used a Phomemo T02 Printer to print, using this [CUPS driver](https://github.com/vivier/phomemo-tools).

To setup, follow the instructions in the above driver repository to download the CUPS driver for the T02. Then the `printer_node.py` should work as intended.

#### Print Image Service (`/print_image`)
The `printer_node` exposes a custom ROS 2 service server to print images dynamically:
* **Service Name**: `/print_image`
* **Type**: `photo_pupper/srv/PrintImage`
* **Interface Specification**:
  * **Request**:
    * `string image_path` - The absolute target path to the image on disk.
    * `string media_size` - Size configuration layout (e.g., `"w50h60"` or `"w50h150"`), falling back to the default node parameter if empty.
  * **Response**:
    * `bool success` - Indicates if the command successfully queued the asset to the CUPS spooler.
    * `string message` - Spooler log message or details on processing failures.