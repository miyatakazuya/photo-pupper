#!/usr/bin/env python3
# *************************************************
# * Filename: gamepad_node.py
# * Student: Austin Choi, akc006@ucsd.edu
# *
# * Description: ROS2 node that reads gamepad button presses from the
# *              Joy topic and publishes input events for the FSM.
# *
# * How to use:
# * Usage:
# *     ros2 run photo_pupper gamepad_node
# *************************************************

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Joy
from std_msgs.msg import String


INPUT_CONFIRM = 'INPUT_CONFIRM'
INPUT_NEXT = 'INPUT_NEXT'
INPUT_PREVIOUS = 'INPUT_PREVIOUS'


class GamepadInputNode(Node):

    def __init__(self):
        super().__init__('gamepad_input_node')

        self.declare_parameter('joy_topic', 'joy')
        self.declare_parameter('input_topic', 'input_event')
        self.declare_parameter('confirm_button_index', 2)
        self.declare_parameter('next_button_index', 5)
        self.declare_parameter('previous_button_index', 4)

        joy_topic = (
            self.get_parameter('joy_topic')
            .get_parameter_value()
            .string_value
        )
        input_topic = (
            self.get_parameter('input_topic')
            .get_parameter_value()
            .string_value
        )
        self.confirm_button_index = (
            self.get_parameter('confirm_button_index')
            .get_parameter_value()
            .integer_value
        )
        self.next_button_index = (
            self.get_parameter('next_button_index')
            .get_parameter_value()
            .integer_value
        )
        self.previous_button_index = (
            self.get_parameter('previous_button_index')
            .get_parameter_value()
            .integer_value
        )

        self.publisher = self.create_publisher(String, input_topic, 10)
        self.subscription = self.create_subscription(
            Joy,
            joy_topic,
            self.joy_callback,
            10
        )
        self.previous_buttons = []

        self.get_logger().info(
            'Gamepad input ready: '
            f'confirm={self.confirm_button_index}, '
            f'next={self.next_button_index}, '
            f'previous={self.previous_button_index}'
        )

    # *************************************************
    # * Name: joy_callback(self, msg)
    # * Purpose: Detects rising-edge button presses from the gamepad
    # *          and publishes the corresponding input event.
    # * @input msg, Joy message with current button states.
    # * @return None.
    # *************************************************
    def joy_callback(self, msg):
        if self.was_pressed(msg.buttons, self.confirm_button_index):
            self.publish_input(INPUT_CONFIRM)
        elif self.was_pressed(msg.buttons, self.next_button_index):
            self.publish_input(INPUT_NEXT)
        elif self.was_pressed(msg.buttons, self.previous_button_index):
            self.publish_input(INPUT_PREVIOUS)

        self.previous_buttons = list(msg.buttons)

    # *************************************************
    # * Name: was_pressed(self, buttons, index)
    # * Purpose: Checks if a button at the given index was just pressed
    # *          (rising edge) by comparing current and previous states.
    # * @input buttons, list of current button states.
    # * @input index, integer index of the button to check.
    # * @return bool, True if the button was just pressed.
    # *************************************************
    def was_pressed(self, buttons, index):
        if index < 0 or index >= len(buttons):
            return False

        was_down = (
            index < len(self.previous_buttons)
            and self.previous_buttons[index] == 1
        )

        return buttons[index] == 1 and not was_down

    # *************************************************
    # * Name: publish_input(self, event)
    # * Purpose: Publishes an input event string to the input_event topic.
    # * @input event, string input event to publish.
    # * @return None.
    # *************************************************
    def publish_input(self, event):
        msg = String()
        msg.data = event
        self.publisher.publish(msg)
        self.get_logger().info(f'Published input event: {event}')


# *************************************************
# * Name: main(args=None)
# * Purpose: Initializes the ROS2 node and spins the gamepad listener.
# * @input args, command line arguments.
# * @return None.
# *************************************************
def main(args=None):
    rclpy.init(args=args)

    gamepad_input_node = GamepadInputNode()

    try:
        rclpy.spin(gamepad_input_node)
    finally:
        gamepad_input_node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
