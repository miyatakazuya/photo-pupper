#!/usr/bin/env python3
# *************************************************
# * Filename: touch_node.py
# * Student: Kane Li, kal036@ucsd.edu
# * Student: Austin Choi, akc006@ucsd.edu
# * Student: Kazuya Miyata, kamiyata@ucsd.edu
# * 
# * Description: Mini Pupper touch pannel test script.
# *
# * Code Citation: Original code provided by MangDang (Copyright 2023)
# *
# * How to use:
# * Usage:
# *     ros2 run lab2task5 touch_node
# *************************************************
#
# Copyright 2023 MangDang
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
# Description: Mini Pupper touch pannel test script.
#
import rclpy
from rclpy.node import Node
from std_msgs.msg import String

try:
    import RPi.GPIO as GPIO
    HAS_GPIO = True
except (ModuleNotFoundError, ImportError):
    HAS_GPIO = False
    class MockGPIO:
        BCM = 11
        IN = 1
        OUT = 2
        def setmode(self, mode):
            pass
        def setup(self, pin, mode):
            pass
        def input(self, pin):
            return True
        def cleanup(self, pins=None):
            pass
    GPIO = MockGPIO()

# There are 4 areas for touch actions
# Each GPIO to each touch area
touchPin_Front = 6
touchPin_Left = 3

INPUT_CONFIRM = 'INPUT_CONFIRM'
INPUT_NEXT = 'INPUT_NEXT'

TIMER_PERIOD = 0.05
RELEASE_TICKS_REQUIRED = 5

# Use GPIO numbers but not PIN number
GPIO.setmode(GPIO.BCM)

# Set up GPIO numbers to input.
GPIO.setup(touchPin_Front, GPIO.IN)
GPIO.setup(touchPin_Left, GPIO.IN)


class TouchPublisher(Node):

    def __init__(self):
        super().__init__('touch_publisher')
        if not HAS_GPIO:
            self.get_logger().info("RPi.GPIO module not found. Using MOCK GPIO.")
        self.publisher_ = self.create_publisher(String, 'input_event', 10)
        self.touch_is_held = False
        self.release_ticks = RELEASE_TICKS_REQUIRED
        self.timer = self.create_timer(TIMER_PERIOD, self.timer_callback)

    # *************************************************
    # * Name: timer_callback(self)
    # * Purpose: Reads GPIO pins to check touch status and publishes one
    # *          clean interaction event for each new touch press.
    # * @input None.
    # * @return None.
    # *************************************************
    def timer_callback(self):
        touch_event = self.read_touch_event()

        if touch_event is None:
            self.mark_released_tick()
            return

        if self.touch_is_held:
            return

        msg = String()
        msg.data = touch_event
        self.publisher_.publish(msg)
        self.get_logger().info(f'Publishing touch event: {msg.data}')

        self.touch_is_held = True
        self.release_ticks = 0

    def read_touch_event(self):
        active_events = []

        if not GPIO.input(touchPin_Front):
            active_events.append(INPUT_CONFIRM)
        if not GPIO.input(touchPin_Left):
            active_events.append(INPUT_NEXT)

        if len(active_events) != 1:
            return None

        return active_events[0]

    def mark_released_tick(self):
        if self.release_ticks < RELEASE_TICKS_REQUIRED:
            self.release_ticks += 1

        if self.release_ticks >= RELEASE_TICKS_REQUIRED:
            self.touch_is_held = False

    def destroy_node(self):
        GPIO.cleanup([touchPin_Front, touchPin_Left])
        super().destroy_node()


# *************************************************
# * Name: main(args=None)
# * Purpose: Initializes the ROS2 node and spins the touch publisher.
# * @input args, command line arguments.
# * @return None.
# *************************************************
def main(args=None):
    rclpy.init(args=args)

    touch_publisher = TouchPublisher()

    try:
        rclpy.spin(touch_publisher)
    finally:
        touch_publisher.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()
