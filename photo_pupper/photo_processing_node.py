#!/usr/bin/env python3
import os
import tempfile
import rclpy
from rclpy.node import Node
from PIL import Image
from ament_index_python.packages import get_package_share_directory

from photo_pupper.srv import ProcessPhoto

class PhotoProcessingNode(Node):
    def __init__(self):
        super().__init__('photo_processing_node')
        
        # Create service server
        self.srv = self.create_service(ProcessPhoto, 'process_photo', self.process_photo_callback)
        self.get_logger().info("Photo Processing Node initialized")

    def process_photo_callback(self, request, response):
        input_path = request.input_path
        overlay_type = request.overlay_type
        output_path = request.output_path

        self.get_logger().info(f"Received processing request: input_path='{input_path}', overlay_type={overlay_type}")

        # Validate input path
        if not os.path.exists(input_path):
            response.success = False
            response.message = f"ERROR: Input image path not found: '{input_path}'"
            self.get_logger().error(response.message)
            return response

        try:
            # 1. Load the raw camera photo
            raw_img = Image.open(input_path).convert("RGBA")
            
            # 2. Select and load the overlay if any
            if overlay_type == ProcessPhoto.Request.OVERLAY_FLOWERS:
                pkg_share = get_package_share_directory('photo_pupper')
                overlay_path = os.path.join(pkg_share, 'resource', 'OverlayTemplate.png')
                
                if not os.path.exists(overlay_path):
                    overlay_path = '/home/kmiyata/dev/cse190/photo-pupper/resource/OverlayTemplate.png'
                
                if not os.path.exists(overlay_path):
                    response.success = False
                    response.message = f"ERROR: OverlayTemplate.png not found: '{overlay_path}'"
                    self.get_logger().error(response.message)
                    return response
                
                self.get_logger().info(f"Loading overlay frame from: '{overlay_path}'")
                overlay_img = Image.open(overlay_path).convert("RGBA")
                
                # Resize the overlay to match raw photo dimensions
                overlay_img = overlay_img.resize(raw_img.size, Image.LANCZOS)
                
                # Composite overlay on top of raw photo 
                final_img = Image.alpha_composite(raw_img, overlay_img)
            elif overlay_type == ProcessPhoto.Request.OVERLAY_NONE:
                self.get_logger().info("No overlay selected. Output will match input.")
                final_img = raw_img
            else:
                response.success = False
                response.message = f"ERROR: Unsupported overlay type: {overlay_type}"
                self.get_logger().error(response.message)
                return response

            # 3. Determine the output path if empty
            if not output_path:
                temp_dir = tempfile.gettempdir()
                output_path = os.path.join(temp_dir, f"processed_photo_{overlay_type}.jpg")
            
            # Ensure the output directory exists
            out_dir = os.path.dirname(output_path)
            if out_dir:
                os.makedirs(out_dir, exist_ok=True)

            # 4. Convert to RGB and save as JPEG
            final_img.convert("RGB").save(output_path, "JPEG")
            
            response.success = True
            response.message = f"Successfully processed image and saved to: '{output_path}'"
            response.processed_path = output_path
            self.get_logger().info(response.message)

        except Exception as e:
            response.success = False
            response.message = f"ERROR: Image processing exception occurred: {str(e)}"
            self.get_logger().error(response.message)

        return response

def main(args=None):
    rclpy.init(args=args)
    node = PhotoProcessingNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()