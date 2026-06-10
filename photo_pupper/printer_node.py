#!/usr/bin/env python3
# *************************************************
# * Filename: printer_node.py
# * Student: Kazuya Miyata, kamiyata@ucsd.edu
# *
# * Description: ROS2 node that provides a PrintImage service for
# *              printing images via CUPS to a thermal printer.
# *
# * How to use:
# * Usage:
# *     ros2 run photo_pupper printer_node
# *************************************************
import os
import subprocess
import rclpy
from rclpy.node import Node

from photo_pupper.srv import PrintImage

class PrinterNode(Node):
    def __init__(self):
        super().__init__('printer_node')
        
        self.declare_parameter('printer_name', 'Phomemo_T02')
        self.declare_parameter('default_media', 'w50h60')
        
        self.printer_name = self.get_parameter('printer_name').get_parameter_value().string_value
        self.default_media = self.get_parameter('default_media').get_parameter_value().string_value
        
        # Create the service server 
        self.srv = self.create_service(PrintImage, 'print_image', self.print_image_callback)
        self.check_printer()

    # *************************************************
    # * Name: check_printer(self)
    # * Purpose: Verifies that the configured printer is connected
    # *          and available via CUPS.
    # * @input None.
    # * @return None.
    # *************************************************
    def check_printer(self):
        try:
            result = subprocess.run(
                ['lpstat', '-p', self.printer_name],
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
            )
            if result.returncode == 0:
                self.get_logger().info(
                    f'Printer connected: {self.printer_name}'
                )
            else:
                self.get_logger().warn(
                    f'Printer not found: {self.printer_name}. '
                    f'Print jobs will fail until it is connected.'
                )
        except FileNotFoundError:
            self.get_logger().warn(
                'CUPS (lpstat) not installed. Printing will not work.'
            )

    # *************************************************
    # * Name: print_image_callback(self, request, response)
    # * Purpose: Service callback that sends an image to the printer
    # *          via the CUPS lp command.
    # * @input request, PrintImage.Request with image_path and media_size.
    # * @input response, PrintImage.Response to populate.
    # * @return response, PrintImage.Response with success and message.
    # *************************************************
    def print_image_callback(self, request, response):
        target_path = request.image_path
        target_media = request.media_size if request.media_size else self.default_media

        if not os.path.exists(target_path):
            response.success = False
            response.message = f"ERROR: Asset file path not found at direct target: '{target_path}'"
            self.get_logger().error(response.message)
            return response

        try:
            self.get_logger().info(f"Invoking CUPS on host for asset path: {target_path}")
            
            cmd = ['lp', '-d', self.printer_name, '-o', f'media={target_media}', target_path]
            result = subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            
            response.success = True
            response.message = f"Queued to system spooler: {result.stdout.strip()}"
            self.get_logger().info(response.message)
            
        except subprocess.CalledProcessError as e:
            response.success = False
            response.message = f"CUPS subsystem processing failure: {e.stderr.strip()}"
            self.get_logger().error(response.message)
            
        return response

# *************************************************
# * Name: main(args=None)
# * Purpose: Initializes the ROS2 node and spins the printer service.
# * @input args, command line arguments.
# * @return None.
# *************************************************
def main(args=None):
    rclpy.init(args=args)
    node = PrinterNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()