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
import RPi.GPIO as GPIO
from rclpy.node import Node
from std_msgs.msg import String

# There are 4 areas for touch actions
# Each GPIO to each touch area
touchPin_Front = 6
touchPin_Left = 3
touchPin_Right = 16

# The 3 touch events used by the interaction FSM.
FRONT_CONFIRM = 'FRONT_CONFIRM'
LEFT_PREV = 'LEFT_PREV'
RIGHT_NEXT = 'RIGHT_NEXT'

TIMER_PERIOD = 0.05
# 4 timer ticks at 0.05 seconds for a 0.2 second debounce window.
DEBOUNCE_TICKS = 4

# Use GPIO numbers but not PIN number
GPIO.setmode(GPIO.BCM)

# Set up GPIO numbers to input.
GPIO.setup(touchPin_Front, GPIO.IN)
GPIO.setup(touchPin_Left, GPIO.IN)
GPIO.setup(touchPin_Right, GPIO.IN)


class TouchPublisher(Node):

    def __init__(self):
        super().__init__('touch_publisher')
        self.publisher_ = self.create_publisher(String, 'touch', 10)
        self.last_touch_event = None
        self.debounce_ticks_remaining = 0
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
            self.last_touch_event = None
            self.tick_debounce()
            return

        if self.last_touch_event is not None:
            return

        if self.debounce_ticks_remaining > 0:
            return

        msg = String()
        msg.data = touch_event
        self.publisher_.publish(msg)
        self.get_logger().info(f'Publishing touch event: {msg.data}')

        self.last_touch_event = touch_event
        self.debounce_ticks_remaining = DEBOUNCE_TICKS

    def read_touch_event(self):
        active_events = []

        if not GPIO.input(touchPin_Front):
            active_events.append(FRONT_CONFIRM)
        if not GPIO.input(touchPin_Left):
            active_events.append(LEFT_PREV)
        if not GPIO.input(touchPin_Right):
            active_events.append(RIGHT_NEXT)

        if len(active_events) != 1:
            return None

        return active_events[0]

    def tick_debounce(self):
        if self.debounce_ticks_remaining > 0:
            self.debounce_ticks_remaining -= 1

    def destroy_node(self):
        GPIO.cleanup([touchPin_Front, touchPin_Left, touchPin_Right])
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
