#!/usr/bin/env python3
import sounddevice as sd
import soundfile as sf
import time
import os
import subprocess
import rclpy
from rclpy.node import Node

from photo_pupper.srv import PlaySound

class SpeakerNode(Node):
    def __init__(self):
        super().__init__('speaker_node')

        os.system("amixer -c 2 sset Master 80% unmute > /dev/null 2>&1")
        os.system("amixer -c 2 sset PCM 80% unmute > /dev/null 2>&1")
        os.system("amixer -c 2 sset Speaker 80% unmute > /dev/null 2>&1")

        sd.default.device = 1

        # Create the service server
        self.srv = self.create_service(PlaySound, 'play_sound', self.play_sound_callback)
        self.get_logger().info("Speaker Node loaded")

    def play_sound_callback(self, request, response):
        target_path = request.sound_path

        if not os.path.exists(target_path):
            response.success = False
            response.message = f"ERROR: Asset file path not found at direct target: '{target_path}'"
            self.get_logger().error(response.message)
            return response

        try:
            self.get_logger().info(f"Loading sound file: {target_path}")
            data, fs = sf.read(target_path)

            self.get_logger().info(f"Playing sound file: {target_path}")
            sd.play(data, fs)
            sd.wait()

            response.success = True
            response.message = f"Successfully played sound: '{target_path}'"
            self.get_logger().info(response.message)

        except Exception as e:
            response.success = False
            response.message = f"An error occurred during playback config: {e}"
            self.get_logger().error(response.message)

        return response

def main(args=None):
    rclpy.init(args=args)
    node = SpeakerNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()
