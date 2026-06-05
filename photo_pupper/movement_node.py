#!/usr/bin/env python3

import math

import rclpy
from geometry_msgs.msg import Pose, Twist
from rclpy.node import Node
from std_msgs.msg import String


WALK_FORWARD = "walk_forward"
GREETING_NOD = "greeting_nod"
THINKING_MOTION = "thinking_motion"
SPEAKING_MOTION = "speaking_motion"
SUCCESS_DANCE = "success_dance"
LOOK_MIDDLE = "look_middle"
STOP = "stop"

TURN_LEFT_SMALL = 'turn_left_small'
TURN_RIGHT_SMALL = 'turn_right_small'
STEP_LEFT = 'step_left'
STEP_RIGHT = 'step_right'
STEP_FORWARD = 'step_forward'
STEP_BACKWARD = 'step_backward'
STEP_LEFT_SMALL = 'step_left_small'
STEP_RIGHT_SMALL = 'step_right_small'
STEP_FORWARD_SMALL = 'step_forward_small'
STEP_BACKWARD_SMALL = 'step_backward_small'
STAY = 'stay'

MOVEMENT_COMPLETE = "MOVEMENT_COMPLETE"



MOVEMENT_SEQUENCES = {
    WALK_FORWARD: ['walk_forward_long'],
    'move_forward': [STEP_FORWARD_SMALL],
    'move_backward': [STEP_BACKWARD_SMALL],
    'move_left': [STEP_LEFT_SMALL],
    'move_right': [STEP_RIGHT_SMALL],
    'turn_left': [TURN_LEFT_SMALL],
    'turn_right': [TURN_RIGHT_SMALL],
    'look_up': ['look_up'],
    'look_up_slow': ['look_up_slow'],
    'look_up_fast': ['look_up_fast'],
    'look_down': ['look_down'],
    'look_down_slow': ['look_down_slow'],
    'look_down_fast': ['look_down_fast'],
    'look_left': ['look_left'],
    'look_left_slow': ['look_left_slow'],
    'look_right': ['look_right'],
    'look_right_slow': ['look_right_slow'],
    GREETING_NOD: ['look_up_slow', 'look_down_slow', 'look_up_fast', 'look_down_slow', 'look_up_slow', 'look_down_fast', LOOK_MIDDLE],
    THINKING_MOTION: ['look_up_slow', 'pause_long', 'look_right', 'pause_long', LOOK_MIDDLE],
    SPEAKING_MOTION: ['look_up_slow', 'look_down_slow', 'look_right_slow', LOOK_MIDDLE, 'look_up_fast', 'look_down_slow', LOOK_MIDDLE, 'look_up_fast', 'look_down_slow', 'look_up_slow', 'look_left_fast', 'look_up_slow', LOOK_MIDDLE],
    SUCCESS_DANCE: [
        STEP_LEFT_SMALL,
        STEP_RIGHT_SMALL,
        TURN_LEFT_SMALL,
        TURN_RIGHT_SMALL,
        "look_up",
        LOOK_MIDDLE,
        STEP_LEFT_SMALL,
        STEP_RIGHT_SMALL,
        "look_down",
        LOOK_MIDDLE,
        "pause_medium",
    ],
    LOOK_MIDDLE: [LOOK_MIDDLE],
    TURN_LEFT_SMALL: [TURN_LEFT_SMALL],
    TURN_RIGHT_SMALL: [TURN_RIGHT_SMALL],
    STEP_LEFT_SMALL: [STEP_LEFT_SMALL],
    STEP_LEFT: [STEP_LEFT],
    STEP_RIGHT_SMALL: [STEP_RIGHT_SMALL],
    STEP_RIGHT: [STEP_RIGHT],
    STEP_FORWARD_SMALL: [STEP_FORWARD_SMALL],
    STEP_FORWARD: [STEP_FORWARD],
    STEP_BACKWARD_SMALL: [STEP_BACKWARD_SMALL],
    STEP_BACKWARD: [STEP_BACKWARD],
    STAY: ['pause_medium'],
}


def quaternion_from_euler(roll, pitch, yaw):
    cr = math.cos(roll * 0.5)
    sr = math.sin(roll * 0.5)
    cp = math.cos(pitch * 0.5)
    sp = math.sin(pitch * 0.5)
    cy = math.cos(yaw * 0.5)
    sy = math.sin(yaw * 0.5)

    w = cr * cp * cy + sr * sp * sy
    x = sr * cp * cy - cr * sp * sy
    y = cr * sp * cy + sr * cp * sy
    z = cr * cp * sy - sr * sp * cy

    return x, y, z, w


class MovementNode(Node):
    def __init__(self):
        super().__init__("movement_node")
        # False keeps movement mocked and log only; true publishes real cmd_vel/body pose.
        self.declare_parameter('real_movement', True)
        self.real_movement = (
            self.get_parameter("real_movement").get_parameter_value().bool_value
        )
        self.declare_parameter('enable_logging', True)
        self.enable_logging = (
            self.get_parameter("enable_logging").get_parameter_value().bool_value
        )
        if not self.enable_logging:
            from rclpy.logging import LoggingSeverity
            self.get_logger().set_level(LoggingSeverity.WARN)

        self.declare_parameter('linear_speed', 0.05)
        self.linear_speed = (
            self.get_parameter("linear_speed").get_parameter_value().double_value
        )
        self.declare_parameter('side_speed', 0.04)
        self.side_speed = (
            self.get_parameter("side_speed").get_parameter_value().double_value
        )
        self.declare_parameter('turn_speed', 0.25)
        self.turn_speed = (
            self.get_parameter("turn_speed").get_parameter_value().double_value
        )
        self.declare_parameter('step_seconds', 0.4)
        self.step_seconds = (
            self.get_parameter("step_seconds").get_parameter_value().double_value
        )
        self.declare_parameter('pose_seconds', 0.4)
        self.pose_seconds = (
            self.get_parameter("pose_seconds").get_parameter_value().double_value
        )

        self.primitive_moves = {
            "walk_forward_long": {
                "kind": "velocity",
                "duration": 3.0,
                "linear_x": self.linear_speed,
                "linear_y": 0.0,
                "angular_z": 0.0,
            },
            STEP_FORWARD_SMALL: {
                "kind": "velocity",
                "duration": self.step_seconds,
                "linear_x": self.linear_speed,
                "linear_y": 0.0,
                "angular_z": 0.0,
            },
            STEP_BACKWARD_SMALL: {
                "kind": "velocity",
                "duration": self.step_seconds,
                "linear_x": -self.linear_speed,
                "linear_y": 0.0,
                "angular_z": 0.0,
            },
            STEP_LEFT_SMALL: {
                "kind": "velocity",
                "duration": self.step_seconds,
                "linear_x": 0.0,
                "linear_y": self.side_speed,
                "angular_z": 0.0,
            },
            STEP_RIGHT_SMALL: {
                "kind": "velocity",
                "duration": self.step_seconds,
                "linear_x": 0.0,
                "linear_y": -self.side_speed,
                "angular_z": 0.0,
            },
            TURN_LEFT_SMALL: {
                "kind": "velocity",
                "duration": self.step_seconds,
                "linear_x": 0.0,
                "linear_y": 0.0,
                "angular_z": self.turn_speed,
            },
            TURN_RIGHT_SMALL: {
                "kind": "velocity",
                "duration": self.step_seconds,
                "linear_x": 0.0,
                "linear_y": 0.0,
                "angular_z": -self.turn_speed,
            },
            STEP_FORWARD: {
                'kind': 'velocity',
                'duration': self.step_seconds,
                'linear_x': 0.15,
                'linear_y': 0.0,
                'angular_z': 0.0,
            },
            STEP_BACKWARD: {
                'kind': 'velocity',
                'duration': self.step_seconds,
                'linear_x': -0.15,
                'linear_y': 0.0,
                'angular_z': 0.0,
            },
            STEP_LEFT: {
                'kind': 'velocity',
                'duration': self.step_seconds,
                'linear_x': 0.0,
                'linear_y': 0.12,
                'angular_z': 0.0,
            },
            STEP_RIGHT: {
                'kind': 'velocity',
                'duration': self.step_seconds,
                'linear_x': 0.0,
                'linear_y': -0.12,
                'angular_z': 0.0,
            },
            'look_up': {
                'kind': 'pose',
                'duration': self.pose_seconds,
                'roll': 0.0,
                'pitch': -0.2,
                'yaw': 0.0,
            },
            'look_up_fast': {
                'kind': 'pose',
                'duration': 0.8,
                'roll': 0.0,
                'pitch': -0.3,
                'yaw': 0.0,
            },
            'look_up_slow': {
                'kind': 'pose',
                'duration': 1.2,
                'roll': 0.0,
                'pitch': -0.2,
                'yaw': 0.0,
            },
            'look_down': {
                'kind': 'pose',
                'duration': self.pose_seconds,
                'roll': 0.0,
                'pitch': 0.2,
                'yaw': 0.0,
            },
            'look_down_fast': {
                'kind': 'pose',
                'duration': 1.2,
                'roll': 0.0,
                'pitch': 0.3,
                'yaw': 0.0,
            },
            'look_down_slow': {
                'kind': 'pose',
                'duration': 0.8,
                'roll': 0.0,
                'pitch': 0.2,
                'yaw': 0.0,
            },
            'look_left': {
                'kind': 'pose',
                'duration': self.pose_seconds,
                'roll': 0.0,
                'pitch': 0.0,
                'yaw': 0.2,
            },
            'look_left_slow': {
                'kind': 'pose',
                'duration': 0.8,
                'roll': 0.0,
                'pitch': 0.0,
                'yaw': 0.2,
            },
            'look_right': {
                'kind': 'pose',
                'duration': self.pose_seconds,
                'roll': 0.0,
                'pitch': 0.0,
                'yaw': -0.2,
            },
            'look_right_slow': {
                'kind': 'pose',
                'duration': 0.8,
                'roll': 0.0,
                'pitch': 0.0,
                'yaw': -0.2,
            },
            LOOK_MIDDLE: {
                "kind": "pose",
                "duration": self.pose_seconds,
                "roll": 0.0,
                "pitch": 0.0,
                "yaw": 0.0,
            },
            "pause_short": {
                "kind": "pause",
                "duration": 0.2,
            },
            "pause_medium": {
                "kind": "pause",
                "duration": 0.6,
            },
            'pause_long': {
                'kind': 'pause',
                'duration': 1.5,
            },
        }

        self.event_publisher = self.create_publisher(String, "movement_event", 10)
        self.velocity_publisher = self.create_publisher(Twist, "cmd_vel", 10)
        self.pose_publisher = self.create_publisher(Pose, "reference_body_pose", 10)
        self.command_subscription = self.create_subscription(
            String, "movement_command", self.command_callback, 10
        )
        self.active_command = None
        self.active_sequence = []
        self.sequence_index = 0
        self.active_primitive = None
        self.motion_timer = None
        self.get_logger().info(f"real_movement={self.real_movement}")

    def command_callback(self, msg):
        command, duration_override = self.parse_command(msg.data.strip())

        if command == STOP:
            self.stop_motion()
            return

        sequence = self.build_sequence(command, duration_override)

        if sequence is None:
            self.get_logger().warn(f"Unknown movement command: {command}")
            return

        self.start_sequence(command, sequence)

    def parse_command(self, raw_command):
        if ":" not in raw_command:
            return raw_command, None

        command, duration_text = raw_command.split(":", 1)

        try:
            duration = float(duration_text)
        except ValueError:
            self.get_logger().warn(f"Invalid movement duration: {raw_command}")
            return command, None

        if duration <= 0.0:
            self.get_logger().warn(f"Invalid movement duration: {raw_command}")
            return command, None

        return command, duration

    def build_sequence(self, command, duration_override):
        if command not in MOVEMENT_SEQUENCES:
            return None

        primitive_names = MOVEMENT_SEQUENCES[command]
        sequence = []

        for primitive_name in primitive_names:
            primitive = dict(self.primitive_moves[primitive_name])
            primitive["name"] = primitive_name
            sequence.append(primitive)

        if duration_override is not None:
            if len(sequence) == 1:
                sequence[0]["duration"] = duration_override
            else:
                self.get_logger().warn(
                    f"Duration override ignored for sequence: {command}"
                )

        return sequence

    def start_sequence(self, command, sequence):
        if (
            self.active_primitive is not None
            and self.active_primitive["kind"] == "velocity"
        ):
            self.stop_velocity()

        self.clear_motion_timer()

        self.active_command = command
        self.active_sequence = sequence
        self.sequence_index = 0
        self.active_primitive = None

        self.get_logger().info(f"Starting movement command: {command}")
        self.run_next_primitive()

    def run_next_primitive(self):
        if self.sequence_index >= len(self.active_sequence):
            self.complete_motion()
            return

        primitive = self.active_sequence[self.sequence_index]
        self.active_primitive = primitive
        self.execute_primitive(primitive)

        self.motion_timer = self.create_timer(
            primitive["duration"], self.finish_primitive
        )

    def execute_primitive(self, primitive):
        name = primitive["name"]
        duration = primitive["duration"]

        if primitive["kind"] == "velocity":
            if self.real_movement:
                self.publish_velocity_move(primitive)
                self.get_logger().info(
                    "Publishing velocity move: "
                    f"{name}, x={primitive['linear_x']:.2f}, "
                    f"y={primitive['linear_y']:.2f}, "
                    f"az={primitive['angular_z']:.2f}, "
                    f"{duration:.1f}s"
                )
            else:
                self.get_logger().info(
                    "Mock velocity move: "
                    f"{name}, x={primitive['linear_x']:.2f}, "
                    f"y={primitive['linear_y']:.2f}, "
                    f"az={primitive['angular_z']:.2f}, "
                    f"{duration:.1f}s"
                )
        elif primitive["kind"] == "pose":
            if self.real_movement:
                self.publish_body_pose(primitive)
                self.get_logger().info(
                    "Publishing body pose: "
                    f"{name}, roll={primitive['roll']:.2f}, "
                    f"pitch={primitive['pitch']:.2f}, "
                    f"yaw={primitive['yaw']:.2f}, "
                    f"{duration:.1f}s"
                )
            else:
                self.get_logger().info(
                    "Mock body pose: "
                    f"{name}, roll={primitive['roll']:.2f}, "
                    f"pitch={primitive['pitch']:.2f}, "
                    f"yaw={primitive['yaw']:.2f}, "
                    f"{duration:.1f}s"
                )
        elif primitive["kind"] == "pause":
            self.get_logger().info(f"Mock pause: {name}, {duration:.1f}s")

    def finish_primitive(self):
        self.clear_motion_timer()

        if (
            self.active_primitive is not None
            and self.active_primitive["kind"] == "velocity"
        ):
            self.stop_velocity()

        self.sequence_index += 1
        self.run_next_primitive()

    def complete_motion(self):
        completed_command = self.active_command
        self.clear_motion_timer()
        self.active_command = None
        self.active_sequence = []
        self.sequence_index = 0
        self.active_primitive = None

        self.publish_movement_event(MOVEMENT_COMPLETE)
        self.get_logger().info(f"Movement complete: {completed_command}")

    def stop_motion(self):
        stopped_command = self.active_command
        self.clear_motion_timer()
        self.active_command = None
        self.active_sequence = []
        self.sequence_index = 0
        self.active_primitive = None

        self.stop_velocity()
        self.publish_movement_event(MOVEMENT_COMPLETE)
        self.get_logger().info(f"Movement stopped: {stopped_command}")

    def clear_motion_timer(self):
        if self.motion_timer is not None:
            self.motion_timer.cancel()
            self.destroy_timer(self.motion_timer)
            self.motion_timer = None

    def publish_movement_event(self, event):
        msg = String()
        msg.data = event
        self.event_publisher.publish(msg)

    def publish_velocity_move(self, primitive):
        twist = Twist()
        twist.linear.x = primitive["linear_x"]
        twist.linear.y = primitive["linear_y"]
        twist.angular.z = primitive["angular_z"]
        self.velocity_publisher.publish(twist)

    def stop_velocity(self):
        if self.real_movement:
            self.velocity_publisher.publish(Twist())
            self.get_logger().info("Published velocity stop")
        else:
            self.get_logger().info("Mock velocity stop")

    def publish_body_pose(self, primitive):
        pose = Pose()
        x, y, z, w = quaternion_from_euler(
            primitive["roll"], primitive["pitch"], primitive["yaw"]
        )
        pose.orientation.x = x
        pose.orientation.y = y
        pose.orientation.z = z
        pose.orientation.w = w
        self.pose_publisher.publish(pose)


def main(args=None):
    rclpy.init(args=args)

    movement_node = MovementNode()

    try:
        rclpy.spin(movement_node)
    finally:
        movement_node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
