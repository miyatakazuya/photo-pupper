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
        
        os.system("amixer -c 1 sset Master 100% unmute > /dev/null 2>&1")
        os.system("amixer -c 1 sset PCM 100% unmute > /dev/null 2>&1")
        os.system("amixer -c 1 sset Speaker 100% unmute > /dev/null 2>&1")

        sd.default.device = 1
        
        # Create the service server 
        self.srv = self.create_service(PlaySound, 'play_sound', self.play_sound_callback)
        self.get_logger().info("Speaker Node loaded")

    def play_sound_callback(self, request, response):
        target_path = request.image_path

        if not os.path.exists(target_path):
            response.success = False
            response.message = f"ERROR: Asset file path not found at direct target: '{target_path}'"
            self.get_logger().error(response.message)
            return response

        try:
            print(f"Loading sound file: {target_path}")
            data, fs = sf.read(target_path)
            
            print(f"PLaying sound file: {target_path}")
            sd.play(data, fs)
            sd.wait()  
            # print("Mini Pupper 2 audio playback end.")
            
        except Exception as e:
            print(f"An error occurred during playback config: {e}")
                        
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



