# *************************************************
# * Filename: fsm_node.py
# * Student: Kane Li, kal036@ucsd.edu
# * Student: Austin Choi, akc006@ucsd.edu
# * Student: Kazuya Miyata, kamiyata@ucsd.edu
# *
# * Description: Finite state machine node for pupper robot movement 
# *              and display update based on touch sensor input.
# *
# * How to use:
# * Usage:
# *     ros2 run lab2task5 fsm_node
# *************************************************
import rclpy
from rclpy.node import Node
from std_msgs.msg import String # Added missing import
from enum import Enum
from pupper_interfaces.srv import GoPupper

from MangDang.mini_pupper.display import Display, BehaviorState
import time
from resizeimage import resizeimage  # library for image resizing
from PIL import Image, ImageDraw, ImageFont # library for image manip.
MAX_WIDTH = 320

# TODO: Refactor these states
class FSMState(Enum):
    IDLE = 0
    RIGHT = 1
    LEFT = 2
    FORWARD = 3

class touchState(Enum):
    FRONT = 0
    LEFT = 1
    RIGHT = 2
    NONE = 3

class pupper_fsm(Node):
    def __init__(self):
        # Initializing node
        super().__init__('pupper_fsm')
        
        # Service client
        self.cli = self.create_client(GoPupper, 'pup_command')
        while not self.cli.wait_for_service(timeout_sec=1.0):
            self.get_logger().info('Service not available, waiting...')

        # Subscribing to touch detection
        self.subscription = self.create_subscription(String, 'touch', self.touch_callback, 10)
        
        # Internal state variables
        self.touch = touchState.NONE
        self.state = FSMState.IDLE

        # Initialize Control Loop for FSM (10Hz)
        self.timer = self.create_timer(0.1, self.fsm_loop)

        # TODO: These should be in their respective nodes
        # self.disp = Display()

        # self.imgFrontFile = "/home/ubuntu/ros2_ws/src/lab2task5/resource/Forward_Image.jpg"
        # self.imgLeftFile = "/home/ubuntu/ros2_ws/src/lab2task5/resource/Right_Image.jpg"
        # self.imgRightFile = "/home/ubuntu/ros2_ws/src/lab2task5/resource/Left_Image.jpg"
        # self.imgNoneFile = "/home/ubuntu/ros2_ws/src/lab2task5/resource/Idle_Image.jpg"

    # *************************************************
    # * Name: touch_callback(self, data)
    # * Purpose: Callback function that updates the current touch state 
    # *          from the touch topic string data.
    # * @input data, a std_msgs/String containing the touch sensor status.
    # * @return None.
    # *************************************************
    def touch_callback(self, data):
        msg = data.data.upper() 
        if 'FRONT' in msg :
            self.touch = touchState.FRONT
        elif 'LEFT' in msg:
            self.touch = touchState.LEFT
        elif 'RIGHT' in msg:
            self.touch = touchState.RIGHT
        else:
            self.touch = touchState.NONE

    # *************************************************
    # * Name: send_move_request(self, move_command)
    # * Purpose: Sends an asynchronous request to the pup_command service 
    # *          with the desired move action.
    # * @input move_command, a string indicating movement direction.
    # * @return None.
    # *************************************************
    def send_move_request(self, move_command):
        req = GoPupper.Request()
        req.command = move_command
        self.cli.call_async(req)

    # *************************************************
    # * Name: pupper_display(self, image)
    # * Purpose: Updates the robot's display with a given image.
    # * @input image, a string path to the image file to show.
    # * @return None.
    # *************************************************
    def pupper_display(self, image):
        self.disp.show_image(image)

    # *************************************************
    # * Name: fsm_loop(self)
    # * Purpose: The main control loop that determines robot movement 
    # *          state from the current touch status, and updates display/movement.
    # * @input None.
    # * @return None.
    # *************************************************
    def fsm_loop(self):
        self.get_logger().info(f"Current State: {self.state.name} | Touch: {self.touch.name}")

        # 1. Update State based on Touch Sensor
        if self.touch == touchState.FRONT:
            self.state = FSMState.FORWARD
        elif self.touch == touchState.RIGHT:
            self.state = FSMState.RIGHT
        elif self.touch == touchState.LEFT:
            self.state = FSMState.LEFT
        else:
            self.state = FSMState.IDLE

        # 2. Execute Action based on State
        if self.state == FSMState.IDLE:
            self.send_move_request("stop")
            self.pupper_display(self.imgNoneFile)
        
        elif self.state == FSMState.FORWARD:
            self.send_move_request("move_forward")
            self.pupper_display(self.imgFrontFile)
            
        elif self.state == FSMState.LEFT:
            self.send_move_request("move_left")
            self.pupper_display(self.imgLeftFile)

        elif self.state == FSMState.RIGHT:
            self.send_move_request("move_right")
            self.pupper_display(self.imgRightFile)

# *************************************************
# * Name: main(args=None)
# * Purpose: Initializes the ROS2 node and spins the finite state machine.
# * @input args, command line arguments.
# * @return None.
# *************************************************
def main(args=None):
    rclpy.init(args=args)
    controller_obj = pupper_fsm()

    try:
        rclpy.spin(controller_obj)
    except KeyboardInterrupt:
        pass
    finally:
        controller_obj.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()
