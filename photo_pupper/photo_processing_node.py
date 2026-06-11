#!/usr/bin/env python3
# *************************************************
# * Filename: photo_processing_node.py
# * Student: Kazuya Miyata, kamiyata@ucsd.edu
# *
# * Description: ROS2 node that provides a ProcessPhoto service for
# *              applying overlay frames to captured images using PIL.
# *
# * How to use:
# * Usage:
# *     ros2 run photo_pupper photo_processing_node
# *************************************************
import os
import tempfile
import rclpy
from rclpy.node import Node
from PIL import Image
from ament_index_python.packages import get_package_share_directory

from photo_pupper.srv import ProcessPhoto


OVERLAY_FILES = {
    ProcessPhoto.Request.OVERLAY_FLOWERS: 'Overlay_Flowers.png',
    ProcessPhoto.Request.OVERLAY_STARS: 'Overlay_Stars.png',
    ProcessPhoto.Request.OVERLAY_PARTY: 'Overlay_Party.png',
    ProcessPhoto.Request.OVERLAY_COMIC: 'Overlay_Comic.png',
    ProcessPhoto.Request.OVERLAY_CLOUDS: 'Overlay_Clouds.png',
    ProcessPhoto.Request.OVERLAY_CONFETTI: 'Overlay_Confetti.png',
    ProcessPhoto.Request.OVERLAY_SAD_CLOUD: 'Overlay_Sad_Cloud.png',
    ProcessPhoto.Request.OVERLAY_RAIN: 'Overlay_Rain.png',
    ProcessPhoto.Request.OVERLAY_BROKEN_HEART: 'Overlay_Broken_Heart.png',
    ProcessPhoto.Request.OVERLAY_BLACK_WHITE: 'Overlay_Black_White.png',
    ProcessPhoto.Request.OVERLAY_CAUTION: 'Overlay_Caution.png',
    ProcessPhoto.Request.OVERLAY_LOCKED_IN: 'Overlay_Locked_In.png',
}


# *************************************************
# * Name: crop_to_aspect(image, target_aspect)
# * Purpose: Center-crops an image to match a target aspect ratio.
# * @input image, PIL Image to crop.
# * @input target_aspect, float target width/height ratio.
# * @return PIL Image, cropped to the target aspect ratio.
# *************************************************
def crop_to_aspect(image, target_aspect):
    width, height = image.size
    current_aspect = width / height

    if current_aspect > target_aspect:
        crop_width = int(height * target_aspect)
        left = (width - crop_width) // 2
        return image.crop((left, 0, left + crop_width, height))

    crop_height = int(width / target_aspect)
    top = (height - crop_height) // 2
    return image.crop((0, top, width, top + crop_height))


class PhotoProcessingNode(Node):
    def __init__(self):
        super().__init__('photo_processing_node')
        
        # Create service server
        self.srv = self.create_service(ProcessPhoto, 'process_photo', self.process_photo_callback)
        self.get_logger().info("Photo Processing Node initialized")

    # *************************************************
    # * Name: process_photo_callback(self, request, response)
    # * Purpose: Service callback that loads an image, applies the
    # *          requested overlay, and saves the result as JPEG.
    # * @input request, ProcessPhoto.Request with input_path, overlay_type, output_path.
    # * @input response, ProcessPhoto.Response to populate.
    # * @return response, ProcessPhoto.Response with success, message, processed_path.
    # *************************************************
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
            if overlay_type == ProcessPhoto.Request.OVERLAY_NONE:
                self.get_logger().info("No overlay selected. Output will match input.")
                final_img = raw_img
            elif overlay_type in OVERLAY_FILES:
                pkg_share = get_package_share_directory('photo_pupper')
                overlay_path = os.path.join(
                    pkg_share,
                    'resource',
                    OVERLAY_FILES[overlay_type]
                )

                if not os.path.exists(overlay_path):
                    response.success = False
                    response.message = f"ERROR: Overlay image not found: '{overlay_path}'"
                    self.get_logger().error(response.message)
                    return response

                self.get_logger().info(
                    f"Loading overlay frame from: '{overlay_path}'"
                )
                overlay_img = Image.open(overlay_path).convert("RGBA")
                raw_img = crop_to_aspect(
                    raw_img,
                    overlay_img.width / overlay_img.height
                )
                overlay_img = overlay_img.resize(raw_img.size, Image.LANCZOS)
                final_img = Image.alpha_composite(raw_img, overlay_img)
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

# *************************************************
# * Name: main(args=None)
# * Purpose: Initializes the ROS2 node and spins the photo processor.
# * @input args, command line arguments.
# * @return None.
# *************************************************
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
