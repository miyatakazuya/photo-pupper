#!/usr/bin/env python3

from pathlib import Path

import rclpy
from ament_index_python.packages import get_package_share_directory
from rclpy.node import Node
from std_msgs.msg import String

try:
    from MangDang.mini_pupper.display import Display
    HAS_DISPLAY = True
except (ModuleNotFoundError, ImportError):
    HAS_DISPLAY = False
    class Display:
        def __init__(self):
            pass
        def show_image(self, path):
            pass


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
    'camera_ready': 'Default_Camera.jpg',
    'countdown_intro': 'Default_Camera.jpg',
    'photo_capture': 'Photo_Capture_Flash.jpg',
    'photo_reaction': 'Happy_Camera.jpg',
    'photo_keep': 'Keep_Selection.jpg',
    'photo_retake': 'Retake_Selection.jpg',
    'overlay_confirm_yes': 'Mood_Yes_Selection.jpg',
    'overlay_confirm_change': 'Mood_Change_Selection.jpg',
    'apply_overlay': PLACEHOLDER_IMAGE,
    'final_preview': PLACEHOLDER_IMAGE,
    'final_keep': 'Keep_Selection.jpg',
    'final_retake': 'Retake_Selection.jpg',
    'printing_talking': 'Default_Camera.jpg',
    'goodbye_talking': 'Default_Camera.jpg',
    'pose_happy_1': 'Happy_Pose_Bicep.jpg',
    'pose_happy_2': 'Happy_Pose_Heart.jpg',
    'pose_happy_3': 'Happy_Pose_ThumbsUp.jpg',
    'pose_silly_1': 'Silly_Pose_Dab.jpg',
    'pose_silly_2': 'Silly_Pose_HandFlare.jpg',
    'pose_silly_3': 'Silly_Pose_Peace.jpg',
    'pose_sad_1': 'Sad_Pose_Cry.jpg',
    'pose_sad_2': 'Sad_Pose_CurlUp.jpg',
    'pose_sad_3': 'Sad_Pose_Droop.jpg',
    'pose_serious_1': 'Serious_Pose_CrossArms.jpg',
    'pose_serious_2': 'Serious_Pose_Superman.jpg',
    'pose_serious_3': 'Serious_Pose_Thinker.jpg',
    'countdown_3': 'Countdown_3.jpg',
    'countdown_2': 'Countdown_2.jpg',
    'countdown_1': 'Countdown_1.jpg',
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
    'done': 'Checkmark_Image.jpg',
    'error': 'XMark_Image.jpg',
}

# Swap these placeholder frames for blink images later.
SCREEN_ANIMATIONS = {
    'welcome_talking': [
        'Default_Camera.jpg',
        'Blink_Camera.jpg',
        'Default_Camera.jpg',
    ],
    'ready_talking': [
        'Default_Camera.jpg',
        'Blink_Camera.jpg',
        'Default_Camera.jpg',
    ],
    'ready_confirmed_talking': [
        'Default_Camera.jpg',
        'Blink_Camera.jpg',
        'Default_Camera.jpg',
    ],
    'pose_thinking': [
        'Default_Camera.jpg',
        'Blink_Camera.jpg',
        'Default_Camera.jpg',
    ],
    'overlay_intro_talking': [
        'Default_Camera.jpg',
        'Blink_Camera.jpg',
        'Default_Camera.jpg',
    ],
    'printing_talking': [
        'Default_Camera.jpg',
        'Blink_Camera.jpg',
        'Default_Camera.jpg',
    ],
    'printing': [
        'Print_Animation_1.jpg',
        'Print_Animation_2.jpg',
        'Print_Animation_3.jpg',
        'Print_Animation_4.jpg',
    ],
    'goodbye_talking': [
        'Default_Camera.jpg',
        'Blink_Camera.jpg',
        'Default_Camera.jpg',
    ],
}

RESOURCE_DIR = Path(get_package_share_directory('photo_pupper')) / 'resource'


class ScreenSubscriber(Node):

    def __init__(self):
        super().__init__('screen_subscriber')
        if not HAS_DISPLAY:
            self.get_logger().info("MangDang display module not found. Using MOCK display.")
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
