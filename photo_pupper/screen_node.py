#!/usr/bin/env python3

from pathlib import Path

import rclpy
from MangDang.mini_pupper.display import Display
from rclpy.node import Node
from std_msgs.msg import String


PLACEHOLDER_IMAGE = 'placeholder.jpg'

# Maps screen commands from the only the FSM to theimage files
SCREEN_IMAGES = {
    'idle': PLACEHOLDER_IMAGE,
    'reveal': PLACEHOLDER_IMAGE,
    'welcome': PLACEHOLDER_IMAGE,
    'ready': PLACEHOLDER_IMAGE,
    'mood_happy': PLACEHOLDER_IMAGE,
    'mood_silly': PLACEHOLDER_IMAGE,
    'mood_sad': PLACEHOLDER_IMAGE,
    'mood_serious': PLACEHOLDER_IMAGE,
    'mood_confirm': PLACEHOLDER_IMAGE,
    'pose_happy_1': PLACEHOLDER_IMAGE,
    'pose_happy_2': PLACEHOLDER_IMAGE,
    'pose_happy_3': PLACEHOLDER_IMAGE,
    'pose_silly_1': PLACEHOLDER_IMAGE,
    'pose_silly_2': PLACEHOLDER_IMAGE,
    'pose_silly_3': PLACEHOLDER_IMAGE,
    'pose_sad_1': PLACEHOLDER_IMAGE,
    'pose_sad_2': PLACEHOLDER_IMAGE,
    'pose_sad_3': PLACEHOLDER_IMAGE,
    'pose_serious_1': PLACEHOLDER_IMAGE,
    'pose_serious_2': PLACEHOLDER_IMAGE,
    'pose_serious_3': PLACEHOLDER_IMAGE,
    'countdown_3': PLACEHOLDER_IMAGE,
    'countdown_2': PLACEHOLDER_IMAGE,
    'countdown_1': PLACEHOLDER_IMAGE,
    'photo_preview': PLACEHOLDER_IMAGE,
    'overlay_stars': PLACEHOLDER_IMAGE,
    'overlay_flowers': PLACEHOLDER_IMAGE,
    'overlay_party': PLACEHOLDER_IMAGE,
    'overlay_comic': PLACEHOLDER_IMAGE,
    'overlay_clouds': PLACEHOLDER_IMAGE,
    'overlay_confetti': PLACEHOLDER_IMAGE,
    'overlay_sad_cloud': PLACEHOLDER_IMAGE,
    'overlay_rain': PLACEHOLDER_IMAGE,
    'overlay_broken_heart': PLACEHOLDER_IMAGE,
    'overlay_black_white': PLACEHOLDER_IMAGE,
    'overlay_caution': PLACEHOLDER_IMAGE,
    'overlay_locked_in': PLACEHOLDER_IMAGE,
    'final_confirmation': PLACEHOLDER_IMAGE,
    'printing': PLACEHOLDER_IMAGE,
    'done': PLACEHOLDER_IMAGE,
    'error': PLACEHOLDER_IMAGE,
}

RESOURCE_DIR = Path(__file__).resolve().parents[1] / 'resource'


class ScreenSubscriber(Node):

    def __init__(self):
        super().__init__('screen_subscriber')
        self.display = Display()
        self.subscription = self.create_subscription(
            String,
            'screen_command',
            self.screen_callback,
            10
        )
        self.show_screen('idle')

    def screen_callback(self, msg):
        self.show_screen(msg.data.strip())

    def show_screen(self, screen_name):
        image_name = SCREEN_IMAGES.get(screen_name, SCREEN_IMAGES['error'])
        image_path = RESOURCE_DIR / image_name

        self.display.show_image(str(image_path))
        self.get_logger().info(f'Showing screen: {screen_name}')


def main(args=None):
    rclpy.init(args=args)

    screen_subscriber = ScreenSubscriber()

    try:
        rclpy.spin(screen_subscriber)
    finally:
        screen_subscriber.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
