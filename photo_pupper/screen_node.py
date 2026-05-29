#!/usr/bin/env python3

from pathlib import Path

import rclpy
from MangDang.mini_pupper.display import Display
from rclpy.node import Node
from std_msgs.msg import String


PLACEHOLDER_IMAGE = 'placeholder.jpg'
ANIMATION_PERIOD = 0.4

SCREEN_IMAGES = {
    'idle': 'Default_Camera.jpg',
    'reveal': 'Happy_Camera.jpg',
    'welcome': 'Default_Camera.jpg',
    'ready': 'Default_Camera.jpg',
    'ready_yes': 'Yes_Selection.jpg',
    'ready_no': 'No_Selection.jpg',
    'mood_happy': 'Happy_Selection.jpg',
    'mood_silly': 'Silly_Selection.jpg',
    'mood_sad': 'Sad_Selection.jpg',
    'mood_serious': 'Serious_Selection.jpg',
    'mood_confirm': PLACEHOLDER_IMAGE,
    'mood_confirm_yes': 'Mood_Yes_Selection.jpg',
    'mood_confirm_change': 'Mood_Change_Selection.jpg',
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

# Swap these placeholder frames for blink images later.
SCREEN_ANIMATIONS = {
    'welcome_talking': [
        'Default_Camera.jpg',
        'Blink_Camera.jpg',
        'Default_Camera.jpg',
    ],
}

RESOURCE_DIR = Path(__file__).resolve().parents[1] / 'resource'


class ScreenSubscriber(Node):

    def __init__(self):
        super().__init__('screen_subscriber')
        self.display = Display()
        self.animation_timer = None
        self.animation_frames = []
        self.animation_index = 0
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
        if screen_name in SCREEN_ANIMATIONS:
            self.start_animation(screen_name)
            return

        self.stop_animation()
        image_name = SCREEN_IMAGES.get(screen_name, SCREEN_IMAGES['error'])
        self.show_image(image_name)
        self.get_logger().info(f'Showing screen: {screen_name}')

    def start_animation(self, screen_name):
        self.stop_animation()
        self.animation_frames = SCREEN_ANIMATIONS[screen_name]
        self.animation_index = 0
        self.show_next_animation_frame()
        self.animation_timer = self.create_timer(
            ANIMATION_PERIOD,
            self.show_next_animation_frame
        )
        self.get_logger().info(f'Playing screen animation: {screen_name}')

    def show_next_animation_frame(self):
        image_name = self.animation_frames[self.animation_index]
        self.show_image(image_name)
        self.animation_index = (
            self.animation_index + 1
        ) % len(self.animation_frames)

    def stop_animation(self):
        if self.animation_timer is not None:
            self.animation_timer.cancel()
            self.destroy_timer(self.animation_timer)
            self.animation_timer = None

    def show_image(self, image_name):
        image_path = RESOURCE_DIR / image_name
        self.display.show_image(str(image_path))


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
