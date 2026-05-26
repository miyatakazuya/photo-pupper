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
import time
import rclpy
import RPi.GPIO as GPIO
from rclpy.node import Node
from std_msgs.msg import String

# There are 4 areas for touch actions
# Each GPIO to each touch area
touchPin_Front = 6
touchPin_Left  = 3
touchPin_Right = 16
touchPin_Back  = 2

# Use GPIO number but not PIN number
GPIO.setmode(GPIO.BCM)

# Set up GPIO numbers to input
GPIO.setup(touchPin_Front, GPIO.IN)
GPIO.setup(touchPin_Left,  GPIO.IN)
GPIO.setup(touchPin_Right, GPIO.IN)
GPIO.setup(touchPin_Back,  GPIO.IN)

class TouchPublisher(Node):

	def __init__(self):
		super().__init__('touch_publisher')
		self.publisher_ = self.create_publisher(String, 'touch', 10)
		timer_period = 1.0
		self.timer = self.create_timer(timer_period, self.timer_callback)

	# *************************************************
	# * Name: timer_callback(self)
	# * Purpose: Reads GPIO pins to check touch status and publishes a 
	# *          concatenated string of active touch locations.
	# * @input None.
	# * @return None.
	# *************************************************
	def timer_callback(self):
		touchValue_Front = GPIO.input(touchPin_Front)
		touchValue_Back  = GPIO.input(touchPin_Back)
		touchValue_Left  = GPIO.input(touchPin_Left)
		touchValue_Right = GPIO.input(touchPin_Right)

		msg = String()
		if not touchValue_Front:
			msg.data += ' Front'
		if not touchValue_Back:
			msg.data += ' Back'
		if not touchValue_Left:
			msg.data += ' Left'
		if not touchValue_Right:
			msg.data += ' Right'
		self.publisher_.publish(msg)


# *************************************************
# * Name: main(args=None)
# * Purpose: Initializes the ROS2 node and spins the touch publisher.
# * @input args, command line arguments.
# * @return None.
# *************************************************
def main(args=None):
	rclpy.init(args=args)

	touch_publisher = TouchPublisher()

	rclpy.spin(touch_publisher)

	touch_publisher.destroy_node()
	rclpy.shutdown()

if __name__ == '__main__':
	main()
