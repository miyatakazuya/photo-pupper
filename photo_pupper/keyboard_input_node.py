#!/usr/bin/env python3
"""Keyboard input utility node.

Publishes to 'input_event' using arrow keys and spacebar,
mimicking the gamepad controller when one is not available.

Controls:
    Space       → INPUT_CONFIRM
    Right arrow → INPUT_NEXT
    Left arrow  → INPUT_PREVIOUS
    q / Ctrl+C  → Quit
"""

import sys
import termios
import tty

import rclpy
from rclpy.node import Node
from std_msgs.msg import String

INPUT_CONFIRM = 'INPUT_CONFIRM'
INPUT_NEXT = 'INPUT_NEXT'
INPUT_PREVIOUS = 'INPUT_PREVIOUS'


class KeyboardInputNode(Node):

    def __init__(self):
        super().__init__('keyboard_input_node')
        self.publisher = self.create_publisher(String, 'input_event', 10)
        self.get_logger().info(
            'Keyboard input ready: '
            'Space=confirm, Right=next, Left=previous, q=quit'
        )

    def publish_input(self, event):
        msg = String()
        msg.data = event
        self.publisher.publish(msg)
        self.get_logger().info(f'Published input event: {event}')


def read_key(fd):
    """Read a single keypress, handling escape sequences for arrow keys."""
    ch = sys.stdin.read(1)
    if ch == '\x1b':
        seq = sys.stdin.read(2)
        if seq == '[D':
            return 'LEFT'
        elif seq == '[C':
            return 'RIGHT'
        return None
    return ch


def main(args=None):
    rclpy.init(args=args)
    node = KeyboardInputNode()

    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)

    try:
        tty.setraw(fd)
        print('\r\nKeyboard input active.\r')
        print('  Space = confirm | ← = previous | → = next | q = quit\r')
        print('\r')

        while rclpy.ok():
            key = read_key(fd)

            if key == ' ':
                node.publish_input(INPUT_CONFIRM)
            elif key == 'RIGHT':
                node.publish_input(INPUT_NEXT)
            elif key == 'LEFT':
                node.publish_input(INPUT_PREVIOUS)
            elif key == 'q' or key == '\x03':
                break

            rclpy.spin_once(node, timeout_sec=0)
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
        node.destroy_node()
        rclpy.shutdown()
        print('\nKeyboard input stopped.')


if __name__ == '__main__':
    main()
