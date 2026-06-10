#!/usr/bin/env python3

import cv2
import depthai as dai
import os
from pathlib import Path

import rclpy
from ament_index_python.packages import get_package_share_directory
from photo_pupper.srv import SaveImage
from rclpy.node import Node
from sensor_msgs.msg import CompressedImage
from std_msgs.msg import String
from std_srvs.srv import SetBool
from movement_node import (
    TURN_LEFT_SMALL,
    TURN_RIGHT_SMALL,
    STEP_FORWARD_SMALL,
    STEP_BACKWARD_SMALL,
)


REFRAMING_COMPLETE = "REFRAMING_COMPLETE"


class CameraNode(Node):
    def __init__(self):
        super().__init__("camera_node")

        # Initialize ROS Publisher (for camera viewing debugging)
        self.publisher_ = self.create_publisher(
            CompressedImage, "/camera/compressed", 10
        )

        self.get_logger().info("Initializing DepthAI Pipeline...")
        self.setup_depthai_pipeline()

        # Declare parameters
        self.declare_parameter("publishing", False)
        self.declare_parameter("turn_threshold", 0.1)
        self.declare_parameter("hz", 2.0)
        self.declare_parameter("centered_frames_required", 3)

        # Get parameter values
        self.publishing = (
            self.get_parameter("publishing").get_parameter_value().bool_value
        )
        self.turn_threshold = (
            self.get_parameter("turn_threshold")
            .get_parameter_value()
            .double_value
        )
        self.hz = (
            self.get_parameter("hz").get_parameter_value().double_value
        )
        self.centered_frames_required = (
            self.get_parameter("centered_frames_required")
            .get_parameter_value()
            .integer_value
        )

        # camera captured frames
        self.latest_frame = None

        # Publisher to send movement commands to movement_node
        self.movement_publisher = self.create_publisher(
            String, "movement_command", 10
        )
        self.reframing_event_publisher = self.create_publisher(
            String, "reframing_event", 10
        )

        # tracking enabled flag
        self.tracking_enabled = True
        self.centered_frames = 0
        self.color = (0, 255, 0)  # Green bounding box (BGR)

        # Service server to enable/disable user tracking
        self.toggle_tracking_srv = self.create_service(
            SetBool, "toggle_tracking", self.toggle_tracking_callback
        )

        # Service server to save current camera image
        self.save_image_srv = self.create_service(
            SaveImage, "save_image", self.save_image_callback
        )

        # Camera callback timer (20Hz)
        timer_period = 1.0 / self.hz
        self.timer = self.create_timer(timer_period, self.timer_callback)
        self.get_logger().info(f"Node spinning. Targeting {1.0 / timer_period} FPS.")

    def setup_depthai_pipeline(self):
        """Builds and starts the pipeline, storing hardware queues."""
        fullFrameTracking = False
        useSpatialAssociation = False

        self.pipeline = dai.Pipeline()
        camRgb = self.pipeline.create(dai.node.Camera).build(
            dai.CameraBoardSocket.CAM_A
        )
        monoLeft = self.pipeline.create(dai.node.Camera).build(
            dai.CameraBoardSocket.CAM_B
        )
        monoRight = self.pipeline.create(dai.node.Camera).build(
            dai.CameraBoardSocket.CAM_C
        )

        stereo = self.pipeline.create(dai.node.StereoDepth)
        leftOutput = monoLeft.requestOutput((640, 400))
        rightOutput = monoRight.requestOutput((640, 400))
        leftOutput.link(stereo.left)
        rightOutput.link(stereo.right)

        spatialDetectionNetwork = self.pipeline.create(
            dai.node.SpatialDetectionNetwork
        ).build(camRgb, stereo, "yolov6-nano")
        self.objectTracker = self.pipeline.create(dai.node.ObjectTracker)

        spatialDetectionNetwork.setConfidenceThreshold(0.6)
        spatialDetectionNetwork.input.setBlocking(False)
        spatialDetectionNetwork.setBoundingBoxScaleFactor(0.5)
        spatialDetectionNetwork.setDepthLowerThreshold(100)
        spatialDetectionNetwork.setDepthUpperThreshold(5000)
        self.labelMap = spatialDetectionNetwork.getClasses()

        self.objectTracker.setDetectionLabelsToTrack([0])
        self.objectTracker.setTrackerType(dai.TrackerType.SHORT_TERM_IMAGELESS)
        self.objectTracker.setTrackerIdAssignmentPolicy(
            dai.TrackerIdAssignmentPolicy.SMALLEST_ID
        )

        if useSpatialAssociation:
            self.objectTracker.setSpatialAssociation(True)
            self.objectTracker.setSpatialAssociationWeight(0.5)
            self.objectTracker.setSpatialDistanceThreshold(1.5)
            self.objectTracker.setSpatialDepthAwareScale(0.1)

        # Store queues as instance variables so the timer can access them
        self.preview_queue = (
            self.objectTracker.passthroughTrackerFrame.createOutputQueue()
        )
        self.tracklets_queue = self.objectTracker.out.createOutputQueue()

        if fullFrameTracking:
            camRgb.requestFullResolutionOutput().link(
                self.objectTracker.inputTrackerFrame
            )
            self.objectTracker.inputTrackerFrame.setBlocking(False)
            self.objectTracker.inputTrackerFrame.setMaxSize(1)
        else:
            spatialDetectionNetwork.passthrough.link(
                self.objectTracker.inputTrackerFrame
            )

        spatialDetectionNetwork.passthrough.link(
            self.objectTracker.inputDetectionFrame
        )
        spatialDetectionNetwork.out.link(self.objectTracker.inputDetections)

        # Start the pipeline (Assuming your specific DepthAI version uses pipeline.start())
        self.pipeline.start()

    def timer_callback(self):
        # Non-blocking pull from hardware. If nothing is there, return immediately.
        imgFrame = self.preview_queue.tryGet()
        track = self.tracklets_queue.tryGet()

        if imgFrame is None or track is None:
            return

        # --- Everything below here is standard frame processing ---
        frame = imgFrame.getCvFrame()
        self.latest_frame = frame
        if self.tracking_enabled:
            trackletsData = track.tracklets

            move = None
            person_centered = False
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

                    cv2.putText(frame, str(label), (x1 + 10, y1 + 20), cv2.FONT_HERSHEY_TRIPLEX, 0.5, 255)
                    cv2.putText(frame, f"ID: {[t.id]}", (x1 + 10, y1 + 35), cv2.FONT_HERSHEY_TRIPLEX, 0.5, 255)
                    cv2.putText(frame, t.status.name, (x1 + 10, y1 + 50), cv2.FONT_HERSHEY_TRIPLEX, 0.5, 255)
                    cv2.rectangle(frame, (x1, y1), (x2, y2), self.color, 1)

                    cv2.putText(frame, f"X: {int(t.spatialCoordinates.x)} mm", (x1 + 10, y1 + 65), cv2.FONT_HERSHEY_TRIPLEX, 0.5, 255)
                    cv2.putText(frame, f"Y: {int(t.spatialCoordinates.y)} mm", (x1 + 10, y1 + 80), cv2.FONT_HERSHEY_TRIPLEX, 0.5, 255)
                    cv2.putText(frame, f"Z: {int(t.spatialCoordinates.z)} mm", (x1 + 10, y1 + 95), cv2.FONT_HERSHEY_TRIPLEX, 0.5, 255)

                    # Calculate how much of the screen height the person occupies
                    person_height = y2 - y1
                    frame_height = frame.shape[0]
                    height_ratio = person_height / frame_height

                    # if person is not within 10% of center, tell to move left or right
                    if (
                        abs(center[0] - frame.shape[1] / 2)
                        > frame.shape[1] * self.turn_threshold
                    ):
                        if center[0] < frame.shape[1] / 2:
                            move = TURN_LEFT_SMALL
                        else:
                            move = TURN_RIGHT_SMALL
                    elif height_ratio < 0.25:
                        move = STEP_FORWARD_SMALL
                    elif height_ratio > 0.9:
                        move = STEP_BACKWARD_SMALL
                    else:
                        person_centered = True
                    break

            if person_centered:
                self.centered_frames += 1
                if self.centered_frames >= self.centered_frames_required:
                    self.complete_reframing()
            else:
                self.centered_frames = 0
                if move is not None:
                    self.send_move_request(move)

        if self.publishing:
            # In-Memory JPEG Compression
            success, encoded_image = cv2.imencode(
                ".jpg", frame, [int(cv2.IMWRITE_JPEG_QUALITY), 90]
            )

            if success:
                msg = CompressedImage()
                msg.header.stamp = self.get_clock().now().to_msg()
                msg.header.frame_id = "camera_frame"
                msg.format = "jpeg"
                msg.data = encoded_image.tobytes()

                self.publisher_.publish(msg)

    def send_move_request(self, move_command):
        msg = String()
        msg.data = move_command
        self.movement_publisher.publish(msg)

    def complete_reframing(self):
        self.tracking_enabled = False
        self.centered_frames = 0

        msg = String()
        msg.data = REFRAMING_COMPLETE
        self.reframing_event_publisher.publish(msg)
        self.get_logger().info("Reframing complete")

    def save_image_callback(self, request, response):
        if self.latest_frame is None:
            response.success = False
            response.message = "Error: No camera frame captured yet."
            return response

        # Resolve the save path using request.filename and self.save_path
        filename = request.filename if request.filename else "camera_image.jpg"
        save_path = str(
            Path(get_package_share_directory('photo_pupper'))
            / 'resource'
            / filename
        )
        try:
            os.makedirs(os.path.dirname(save_path), exist_ok=True)
            resized_frame = cv2.resize(self.latest_frame, (320, 240))
            cv2.imwrite(save_path, resized_frame)
            response.success = True
            response.message = f"Successfully saved current camera image to {save_path}"
            self.get_logger().info(response.message)
        except Exception as e:
            response.success = False
            response.message = f"Failed to save image: {str(e)}"
            self.get_logger().error(response.message)
        return response

    def toggle_tracking_callback(self, request, response):
        self.tracking_enabled = request.data
        self.centered_frames = 0
        response.success = True
        tracking_state = 'enabled' if self.tracking_enabled else 'disabled'
        response.message = f"Tracking {tracking_state}."
        self.get_logger().info(response.message)
        return response


def main(args=None):
    rclpy.init(args=args)
    node = CameraNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
