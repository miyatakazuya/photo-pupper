#!/usr/bin/env python3

import cv2
import depthai as dai
import time

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import CompressedImage
from pupper_interfaces.srv import GoPupper

class DepthAIOverlayNode(Node):
    def __init__(self):
        super().__init__('depthai_overlay_node')
        
        # Initialize ROS Publisher (for camera viewing debugging)
        self.publisher_ = self.create_publisher(
            CompressedImage, 
            '/overlay/compressed', 
            10
        )
        
        self.get_logger().info("Initializing DepthAI Pipeline...")
        self.setup_depthai_pipeline()

        # params
        self.publishing = False
        self.turn_threshold = 0.2

        # Service client to send movement commands
        self.cli = self.create_client(GoPupper, 'pup_command')
        while not self.cli.wait_for_service(timeout_sec=1.0):
            self.get_logger().info('Service not available, waiting...')
        
        # Camera callback timer (20Hz)
        timer_period = 1.0 / 20.0
        self.timer = self.create_timer(timer_period, self.timer_callback)
        self.get_logger().info(f"Node spinning. Targeting {1.0/timer_period} FPS.")

    def setup_depthai_pipeline(self):
        """Builds and starts the pipeline, storing hardware queues."""
        fullFrameTracking = False
        useSpatialAssociation = False

        self.pipeline = dai.Pipeline()
        camRgb = self.pipeline.create(dai.node.Camera).build(dai.CameraBoardSocket.CAM_A)
        monoLeft = self.pipeline.create(dai.node.Camera).build(dai.CameraBoardSocket.CAM_B)
        monoRight = self.pipeline.create(dai.node.Camera).build(dai.CameraBoardSocket.CAM_C)

        stereo = self.pipeline.create(dai.node.StereoDepth)
        leftOutput = monoLeft.requestOutput((640, 400))
        rightOutput = monoRight.requestOutput((640, 400))
        leftOutput.link(stereo.left)
        rightOutput.link(stereo.right)

        spatialDetectionNetwork = self.pipeline.create(dai.node.SpatialDetectionNetwork).build(camRgb, stereo, "yolov6-nano")
        self.objectTracker = self.pipeline.create(dai.node.ObjectTracker)

        spatialDetectionNetwork.setConfidenceThreshold(0.6)
        spatialDetectionNetwork.input.setBlocking(False)
        spatialDetectionNetwork.setBoundingBoxScaleFactor(0.5)
        spatialDetectionNetwork.setDepthLowerThreshold(100)
        spatialDetectionNetwork.setDepthUpperThreshold(5000)
        self.labelMap = spatialDetectionNetwork.getClasses()

        self.objectTracker.setDetectionLabelsToTrack([0])
        self.objectTracker.setTrackerType(dai.TrackerType.SHORT_TERM_IMAGELESS)
        self.objectTracker.setTrackerIdAssignmentPolicy(dai.TrackerIdAssignmentPolicy.SMALLEST_ID)
        
        if useSpatialAssociation:
            self.objectTracker.setSpatialAssociation(True)
            self.objectTracker.setSpatialAssociationWeight(0.5)
            self.objectTracker.setSpatialDistanceThreshold(1.5)
            self.objectTracker.setSpatialDepthAwareScale(0.1)

        # Store queues as instance variables so the timer can access them
        self.preview_queue = self.objectTracker.passthroughTrackerFrame.createOutputQueue()
        self.tracklets_queue = self.objectTracker.out.createOutputQueue()

        if fullFrameTracking:
            camRgb.requestFullResolutionOutput().link(self.objectTracker.inputTrackerFrame)
            self.objectTracker.inputTrackerFrame.setBlocking(False)
            self.objectTracker.inputTrackerFrame.setMaxSize(1)
        else:
            spatialDetectionNetwork.passthrough.link(self.objectTracker.inputTrackerFrame)

        spatialDetectionNetwork.passthrough.link(self.objectTracker.inputDetectionFrame)
        spatialDetectionNetwork.out.link(self.objectTracker.inputDetections)

        # Start the pipeline (Assuming your specific DepthAI version uses pipeline.start())
        self.pipeline.start()

    def timer_callback(self):
        """Called by ROS 2 executor at a consistent rate."""
        # Non-blocking pull from hardware. If nothing is there, return immediately.
        imgFrame = self.preview_queue.tryGet()
        track = self.tracklets_queue.tryGet()

        if imgFrame is None or track is None:
            return

        # --- Everything below here is standard frame processing ---
        frame = imgFrame.getCvFrame()
        trackletsData = track.tracklets

        move = "stay"
        for t in trackletsData:
            roi = t.roi.denormalize(frame.shape[1], frame.shape[0])
            x1, y1 = int(roi.topLeft().x), int(roi.topLeft().y)
            x2, y2 = int(roi.bottomRight().x), int(roi.bottomRight().y)

            try:
                label = self.labelMap[t.label]
            except (IndexError, KeyError, TypeError):
                label = t.label
            
            # if a person and not in center, tell to move left or right
            if label == "person":
                center = (x1 + x2) / 2, (y1 + y2) / 2
                
                # Calculate how much of the screen height the person occupies
                person_height = y2 - y1
                frame_height = frame.shape[0]
                height_ratio = person_height / frame_height
                #self.get_logger().info(f"height_ratio: {height_ratio}")
                
                # if person is not within 10% of center, tell to move left or right
                if abs(center[0] - frame.shape[1] / 2) > frame.shape[1] * self.turn_threshold:
                    if center[0] < frame.shape[1] / 2:
                        move = "turn_left"
                    else:
                        move = "turn_right"
                elif height_ratio < 0.25:
                    move = "move_forward"
                elif height_ratio > 0.9:
                    move = "move_backward"
                break
        #self.get_logger().info(move)
        self.send_move_request(move)

        if self.publishing:
            # In-Memory JPEG Compression
            success, encoded_image = cv2.imencode('.jpg', frame, [int(cv2.IMWRITE_JPEG_QUALITY), 90])
            
            if success:
                msg = CompressedImage()
                msg.header.stamp = self.get_clock().now().to_msg()
                msg.header.frame_id = "camera_overlay_frame"
                msg.format = "jpeg"
                msg.data = encoded_image.tobytes()
                
                self.publisher_.publish(msg)

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

def main(args=None):
    rclpy.init(args=args)
    node = DepthAIOverlayNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()
