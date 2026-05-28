#!/usr/bin/env python3

import rclpy
from rclpy.node import Node
from std_msgs.msg import String


WALK_FORWARD = 'walk_forward'
GREETING_NOD = 'greeting_nod'
SUCCESS_DANCE = 'success_dance'
LOOK_MIDDLE = 'look_middle'
STOP = 'stop'

MOVEMENT_COMPLETE = 'MOVEMENT_COMPLETE'

MOTION_DURATIONS = {
    WALK_FORWARD: 3.0,
    GREETING_NOD: 1.5,
    SUCCESS_DANCE: 2.0,
    LOOK_MIDDLE: 0.5,
}


class MovementNode(Node):

    def __init__(self):
        super().__init__('movement_node')
        self.event_publisher = self.create_publisher(
            String,
            'movement_event',
            10
        )
        self.command_subscription = self.create_subscription(
            String,
            'movement_command',
            self.command_callback,
            10
        )
        self.active_motion = None
        self.motion_timer = None

    def command_callback(self, msg):
        command = msg.data.strip()

        if command == STOP:
            self.stop_motion()
            return

        if command not in MOTION_DURATIONS:
            self.get_logger().warn(f'Unknown movement command: {command}')
            return

        self.start_motion(command)

    def start_motion(self, command):
        self.clear_motion_timer()

        self.active_motion = command
        duration = MOTION_DURATIONS[command]

        self.get_logger().info(
            f'temp mock movement command: {command} for {duration:.1f} seconds'
        )
        self.motion_timer = self.create_timer(
            duration,
            self.complete_motion
        )

    def complete_motion(self):
        completed_motion = self.active_motion
        self.clear_motion_timer()
        self.active_motion = None

        self.publish_movement_event(MOVEMENT_COMPLETE)
        self.get_logger().info(f'Movement complete: {completed_motion}')

    def stop_motion(self):
        stopped_motion = self.active_motion
        self.clear_motion_timer()
        self.active_motion = None

        self.publish_movement_event(MOVEMENT_COMPLETE)
        self.get_logger().info(f'Movement stopped: {stopped_motion}')

    def clear_motion_timer(self):
        if self.motion_timer is not None:
            self.motion_timer.cancel()
            self.destroy_timer(self.motion_timer)
            self.motion_timer = None

    def publish_movement_event(self, event):
        msg = String()
        msg.data = event
        self.event_publisher.publish(msg)


def main(args=None):
    rclpy.init(args=args)

    movement_node = MovementNode()

    try:
        rclpy.spin(movement_node)
    finally:
        movement_node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
