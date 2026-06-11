#!/usr/bin/env python3
# *************************************************
# * Filename: speaker_node.py
# * Student: Kazuya Miyata, kamiyata@ucsd.edu
# *
# * Description: ROS2 node that provides a PlaySound service for audio
# *              playback through a USB speaker using sounddevice.
# *
# * How to use:
# * Usage:
# *     ros2 run photo_pupper speaker_node
# *************************************************
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

        # Declare volume parameter defaulting to 50%
        self.declare_parameter('volume_percent', 50)
        self.volume = self.get_parameter('volume_percent').get_parameter_value().integer_value

        os.system(f"amixer -c 2 sset Master {self.volume}% unmute > /dev/null 2>&1")
        os.system(f"amixer -c 2 sset PCM {self.volume}% unmute > /dev/null 2>&1")
        os.system(f"amixer -c 2 sset Speaker {self.volume}% unmute > /dev/null 2>&1")

        sd.default.device = 1

        # Create the service server
        self.srv = self.create_service(PlaySound, 'play_sound', self.play_sound_callback)
        self.get_logger().info(f"Speaker Node loaded (volume: {self.volume}%)")

    # *************************************************
    # * Name: play_sound_callback(self, request, response)
    # * Purpose: Service callback that plays a WAV file at the configured
    # *          volume when given a valid file path.
    # * @input request, PlaySound.Request with sound_path field.
    # * @input response, PlaySound.Response to populate.
    # * @return response, PlaySound.Response with success and message.
    # *************************************************
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
            # Scale the audio samples digitally to prevent it from being too loud
            volume_factor = self.volume / 100.0
            sd.play(data * volume_factor, fs)
            sd.wait()

            response.success = True
            response.message = f"Successfully played sound: '{target_path}'"
            self.get_logger().info(response.message)

        except Exception as e:
            response.success = False
            response.message = f"An error occurred during playback config: {e}"
            self.get_logger().error(response.message)

        return response

# *************************************************
# * Name: main(args=None)
# * Purpose: Initializes the ROS2 node and spins the speaker service.
# * @input args, command line arguments.
# * @return None.
# *************************************************
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
