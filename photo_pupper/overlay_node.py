#!/usr/bin/env python3

import cv2
import depthai as dai
import time

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import CompressedImage

class DepthAIOverlayNode(Node):
    def __init__(self):
        super().__init__('depthai_overlay_node')
        
        # 1. Initialize ROS Publisher
        self.publisher_ = self.create_publisher(
            CompressedImage, 
            '/overlay/compressed', 
            10
        )
        
        self.get_logger().info("Initializing DepthAI Pipeline...")
        self.setup_depthai_pipeline()
        
        # FPS Tracking vars
        self.color = (255, 255, 255)
        
        # 2. The ROS 2 Timer (Targeting ~20 FPS for consistency and low CPU usage)
        timer_period = 1.0 / 20.0  # 0.05 seconds
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
        
        for t in trackletsData:
            roi = t.roi.denormalize(frame.shape[1], frame.shape[0])
            x1, y1 = int(roi.topLeft().x), int(roi.topLeft().y)
            x2, y2 = int(roi.bottomRight().x), int(roi.bottomRight().y)

            try:
                label = self.labelMap[t.label]
            except:
                label = t.label

            if label == 'person':
                label == 'IDK MAN'

            cv2.putText(frame, str(label), (x1 + 10, y1 + 20), cv2.FONT_HERSHEY_TRIPLEX, 0.5, 255)
            cv2.putText(frame, f"ID: {[t.id]}", (x1 + 10, y1 + 35), cv2.FONT_HERSHEY_TRIPLEX, 0.5, 255)
            cv2.putText(frame, t.status.name, (x1 + 10, y1 + 50), cv2.FONT_HERSHEY_TRIPLEX, 0.5, 255)
            cv2.rectangle(frame, (x1, y1), (x2, y2), self.color, 1)

            cv2.putText(frame, f"X: {int(t.spatialCoordinates.x)} mm", (x1 + 10, y1 + 65), cv2.FONT_HERSHEY_TRIPLEX, 0.5, 255)
            cv2.putText(frame, f"Y: {int(t.spatialCoordinates.y)} mm", (x1 + 10, y1 + 80), cv2.FONT_HERSHEY_TRIPLEX, 0.5, 255)
            cv2.putText(frame, f"Z: {int(t.spatialCoordinates.z)} mm", (x1 + 10, y1 + 95), cv2.FONT_HERSHEY_TRIPLEX, 0.5, 255)
            
            if t.velocity is not None and t.speed is not None:
                cv2.putText(frame, f"Speed: {t.speed:.2f} m/s", (x1 + 10, y1 + 155), cv2.FONT_HERSHEY_TRIPLEX, 0.5, 255)

        # In-Memory JPEG Compression
        success, encoded_image = cv2.imencode('.jpg', frame, [int(cv2.IMWRITE_JPEG_QUALITY), 90])
        
        if success:
            msg = CompressedImage()
            msg.header.stamp = self.get_clock().now().to_msg()
            msg.header.frame_id = "camera_overlay_frame"
            msg.format = "jpeg"
            msg.data = encoded_image.tobytes()
            
            self.publisher_.publish(msg)

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
