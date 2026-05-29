import os
from glob import glob
from setuptools import find_packages, setup

package_name = 'photo_pupper'

setup(
    name=package_name,
    version='0.0.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        # Install launch files
        (os.path.join('share', package_name, 'launch'), glob(os.path.join('launch', '*.py'))),
        # Install config files
        (os.path.join('share', package_name, 'config'), glob(os.path.join('config', '*.yml'))),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='root',
    maintainer_email='root@todo.todo',
    description='TODO: Package description',
    license='TODO: License declaration',
    extras_require={
        'test': [
            'pytest',
        ],
    },
    entry_points={
        'console_scripts': [
            'fsm_node = photo_pupper.fsm_node:main',
            'movement_node = photo_pupper.movement_node:main',
            'people_detection_node = photo_pupper.people_detection_node:main',
            'photo_processing_node = photo_pupper.photo_processing_node:main',
            'printer_node = photo_pupper.printer_node:main',
            'screen_node = photo_pupper.screen_node:main',
            'touch_node = photo_pupper.touch_node:main',
        ],
    },
)
