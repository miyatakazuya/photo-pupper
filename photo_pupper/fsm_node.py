#!/usr/bin/env python3
# *************************************************
# * Filename: fsm_node.py
# * Student: Kane Li, kal036@ucsd.edu
# * Student: Austin Choi, akc006@ucsd.edu
# * Student: Kazuya Miyata, kamiyata@ucsd.edu
# *
# * Description: Finite state machine node for pupper robot movement
# *              and display update based on user input.
# *
# * How to use:
# * Usage:
# *     ros2 run lab2task5 fsm_node
# *************************************************

import random
from enum import Enum
from pathlib import Path

import rclpy
from ament_index_python.packages import get_package_share_directory
from photo_pupper.srv import PlaySound, PrintImage, ProcessPhoto
from rclpy.node import Node
from std_msgs.msg import String
from std_srvs.srv import Trigger


INPUT_CONFIRM = 'INPUT_CONFIRM'
INPUT_NEXT = 'INPUT_NEXT'
INPUT_PREVIOUS = 'INPUT_PREVIOUS'
MOVEMENT_COMPLETE = 'MOVEMENT_COMPLETE'

WALK_FORWARD = 'walk_forward'
GREETING_NOD = 'greeting_nod'
THINKING_MOTION = 'thinking_motion'
SPEAKING_MOTION = 'speaking_motion'
SUCCESS_DANCE = 'success_dance'
STOP = 'stop'
COUNTDOWN_SECONDS = 1.0
PHOTO_CAPTURE_SECONDS = 1.5
OVERLAY_CONFIRM_SECONDS = 2.5
PRINTING_SCREEN_SECONDS = 4.0
PRINT_COMPLETE_SECONDS = 2.0
ERROR_RESET_SECONDS = 3.0

PLACEHOLDER_CAPTURE_IMAGE = 'happy_man.png'
DEFAULT_PRINT_MEDIA = ''

MOODS = ['happy', 'silly', 'sad', 'serious']
OVERLAYS_BY_MOOD = {
    'happy': ['stars', 'flowers', 'party'],
    'silly': ['comic', 'clouds', 'confetti'],
    'sad': ['sad_cloud', 'rain', 'broken_heart'],
    'serious': ['black_white', 'caution', 'locked_in'],
}
POSE_LINES = {
    'happy': [
        'Try a double bicep flex.',
        'Try making heart hands.',
        'Give me a big smile and thumbs up.',
    ],
    'silly': [
        'Do the dab.',
        'Try funny hand motion on your head',
        'Give me a peace sign!',
    ],
    'sad': [
        'Try a fake crying pose.',
        'Curl up in your chair and hug your legs like you are really sad.',
        'Look down dramatically.',
    ],
    'serious': [
        'Cross your arms like a boss.',
        'Stand strong and pose like superman!',
        'Try a thinker pose.',
    ],
}
MOOD_THINKING_LINES = {
    'happy': "Hmm, you're feeling happy today. Let me think...",
    'silly': "Silly mood? I like it. Let me think...",
    'sad': "Feeling sad today? I'll try to make this one sweet.",
    'serious': 'Serious mood. Let me find something strong.',
}
AUDIO_LINES = {
    'welcome': (
        "Hi! I'm Pupper, your photo booth helper. "
        "I'll help you choose a mood, pick a pose, take your picture, "
        'decorate it, and print it for you.'
    ),
    'ready_prompt': (
        "Before we start, make sure you're okay with me taking your "
        'photo and printing it for this demo. If that sounds good, '
        'choose Yes. If not, choose No.'
    ),
    'sensor_instructions': (
        'Use the left and right buttons to switch options, '
        'and press confirm to choose.'
    ),
    'ready_confirmed': (
        "Alright, sounds like you're ready. "
        "Let's start by choosing a mood for your photo."
    ),
    'mood_instructions': (
        'Pick the mood you want for your photo. '
        'Use the left and right buttons to cycle through the options, '
        'and press confirm to choose.'
    ),
    'camera_ready': (
        'Looking good. Get in view and hold that pose. '
        'Press confirm when you are ready for the countdown.'
    ),
    'countdown_intro': 'Get ready for the countdown!',
    'photo_reaction': 'That was a great shot. You make this look easy.',
    'preview_continue': (
        'Your photo came out great. Press confirm to continue.'
    ),
    'review_prompt': 'Would you like to keep that photo or retake it?',
    'toggle_instructions': (
        'Use the left and right buttons to toggle, and confirm to choose.'
    ),
    'overlay_instructions': (
        'Great choice. Overlay selection comes next. '
        'Use the left and right buttons to choose which overlay theme you want, '
        'and press confirm to choose.'
    ),
    'apply_overlay': 'Applying your chosen decorations now.',
    'final_preview': 'Your final picture came out amazing.',
    'final_prompt': 'What do you think? Keep this final photo or retake it?',
    'printing_start': "Perfect. I'm printing your photo now.",
    'goodbye': (
        'Your photo is ready. Go grab it from the printer beside me. '
        'Thanks for taking pictures with me!'
    ),
}

for mood, line in MOOD_THINKING_LINES.items():
    AUDIO_LINES[f'think_{mood}'] = line

for mood, lines in POSE_LINES.items():
    for pose_index, line in enumerate(lines, start=1):
        AUDIO_LINES[f'pose_{mood}_{pose_index}'] = line


class FSMState(Enum):
    IDLE = 0
    REVEAL = 1
    WELCOME = 2
    READY_TALK = 3
    READY = 4
    READY_CONFIRMED_TALK = 5
    MOOD_SELECTION = 6
    MOOD_CONFIRMATION = 7
    POSE_THINKING = 8
    POSE_SUGGESTION = 9
    CAMERA_READY = 10
    COUNTDOWN_INTRO = 11
    COUNTDOWN = 12
    PHOTO_CAPTURE = 13
    PHOTO_REACTION = 14
    PHOTO_PREVIEW_READY = 15
    PHOTO_REVIEW_PROMPT = 16
    PHOTO_REVIEW_CHOICE = 17
    OVERLAY_INTRO = 18
    OVERLAY_SELECTION = 19
    OVERLAY_CONFIRM_TALK = 20
    OVERLAY_CONFIRM_CHOICE = 21
    APPLY_OVERLAY = 22
    FINAL_PREVIEW = 23
    FINAL_CONFIRMATION_PROMPT = 24
    FINAL_CONFIRMATION = 25
    PRINT_INTRO_TALK = 26
    PRINTING = 27
    PRINT_COMPLETE = 28
    GOODBYE_TALK = 29
    GOODBYE_DANCE = 30
    ERROR_RESET = 31


class PupperFSM(Node):

    def __init__(self):
        super().__init__('pupper_fsm')

        self.screen_publisher = self.create_publisher(
            String,
            'screen_command',
            10
        )
        self.movement_publisher = self.create_publisher(
            String,
            'movement_command',
            10
        )
        self.input_subscription = self.create_subscription(
            String,
            'input_event',
            self.input_callback,
            10
        )
        self.movement_subscription = self.create_subscription(
            String,
            'movement_event',
            self.movement_callback,
            10
        )
        self.photo_processing_client = self.create_client(
            ProcessPhoto,
            'process_photo'
        )
        self.printer_client = self.create_client(
            PrintImage,
            'print_image'
        )
        self.save_image_client = self.create_client(
            Trigger,
            'save_image'
        )

        self.play_sound_client = self.create_client(PlaySound, 'play_sound')
        self.audio_dir = Path(get_package_share_directory('photo_pupper')) / 'resource' / 'audio'

        self.state = FSMState.IDLE
        self.ready_yes_selected = True
        self.selected_mood_index = 0
        self.selected_pose_index = 0
        self.mood_confirm_yes_selected = True
        self.countdown_number = 3
        self.keep_photo_selected = True
        self.selected_overlay_index = 0
        self.overlay_confirm_yes_selected = True
        self.final_keep_selected = True
        self.captured_photo_path = None
        self.final_photo_path = '/home/ubuntu/ros2_ws/camera_image.jpg'
        self.resource_dir = (
            Path(get_package_share_directory('photo_pupper')) / 'resource'
        )
        self.state_timer = None
        self.enter_idle()

    def input_callback(self, msg):
        input_event = msg.data.strip()

        if input_event == INPUT_CONFIRM:
            self.handle_confirm()
        elif input_event == INPUT_NEXT:
            self.handle_selection_change(1)
        elif input_event == INPUT_PREVIOUS:
            self.handle_selection_change(-1)

    def movement_callback(self, msg):
        movement_event = msg.data.strip()

        if self.state == FSMState.REVEAL and movement_event == MOVEMENT_COMPLETE:
            self.enter_welcome()
        elif (
            self.state == FSMState.GOODBYE_DANCE
            and movement_event == MOVEMENT_COMPLETE
        ):
            self.enter_idle()

    def handle_confirm(self):
        if self.state == FSMState.IDLE:
            self.enter_reveal()
        elif self.state == FSMState.READY:
            self.confirm_ready_selection()
        elif self.state == FSMState.MOOD_SELECTION:
            self.enter_mood_confirmation()
        elif self.state == FSMState.MOOD_CONFIRMATION:
            self.confirm_mood_selection()
        elif self.state == FSMState.CAMERA_READY:
            self.enter_countdown_intro()
        elif self.state == FSMState.PHOTO_PREVIEW_READY:
            self.enter_photo_review_prompt()
        elif self.state == FSMState.PHOTO_REVIEW_CHOICE:
            self.confirm_photo_review_choice()
        elif self.state == FSMState.OVERLAY_SELECTION:
            self.enter_overlay_confirm_talk()
        elif self.state == FSMState.OVERLAY_CONFIRM_CHOICE:
            self.confirm_overlay_choice()
        elif self.state == FSMState.FINAL_CONFIRMATION:
            self.confirm_final_choice()

    def handle_selection_change(self, direction):
        if self.state == FSMState.READY:
            self.ready_yes_selected = not self.ready_yes_selected
            self.show_ready_screen()
        elif self.state == FSMState.MOOD_SELECTION:
            self.change_mood(direction)
        elif self.state == FSMState.MOOD_CONFIRMATION:
            self.mood_confirm_yes_selected = not self.mood_confirm_yes_selected
            self.show_mood_confirmation_screen()
        elif self.state == FSMState.PHOTO_REVIEW_CHOICE:
            self.keep_photo_selected = not self.keep_photo_selected
            self.show_photo_review_screen()
        elif self.state == FSMState.OVERLAY_SELECTION:
            self.change_overlay(direction)
        elif self.state == FSMState.OVERLAY_CONFIRM_CHOICE:
            self.overlay_confirm_yes_selected = (
                not self.overlay_confirm_yes_selected
            )
            self.show_overlay_confirmation_screen()
        elif self.state == FSMState.FINAL_CONFIRMATION:
            self.final_keep_selected = not self.final_keep_selected
            self.show_final_confirmation_screen()

    def enter_idle(self):
        self.clear_state_timer()
        self.state = FSMState.IDLE
        self.ready_yes_selected = True
        self.selected_mood_index = 0
        self.selected_pose_index = 0
        self.mood_confirm_yes_selected = True
        self.countdown_number = 3
        self.keep_photo_selected = True
        self.selected_overlay_index = 0
        self.overlay_confirm_yes_selected = True
        self.final_keep_selected = True
        self.captured_photo_path = None
        self.final_photo_path = None
        self.show_screen('idle')

    def enter_reveal(self):
        self.clear_state_timer()
        self.state = FSMState.REVEAL
        self.show_screen('reveal')
        self.send_movement(WALK_FORWARD)

    def enter_welcome(self):
        self.clear_state_timer()
        self.state = FSMState.WELCOME
        self.show_screen('welcome_talking')
        self.say_clip(
            'welcome',
            self.enter_ready_talk,
            GREETING_NOD
        )

    def enter_ready_talk(self):
        self.clear_state_timer()
        self.state = FSMState.READY_TALK
        self.show_screen('ready_talking')
        self.say_clip(
            'ready_prompt',
            self.enter_ready,
            SPEAKING_MOTION
        )

    def enter_ready(self):
        self.clear_state_timer()
        self.state = FSMState.READY
        self.ready_yes_selected = True
        self.show_ready_screen()
        self.say_clip('sensor_instructions')

    def confirm_ready_selection(self):
        if self.ready_yes_selected:
            self.enter_ready_confirmed_talk()
        else:
            self.say('No problem. Resetting.')
            self.enter_idle()

    def enter_ready_confirmed_talk(self):
        self.clear_state_timer()
        self.state = FSMState.READY_CONFIRMED_TALK
        self.show_screen('ready_confirmed_talking')
        self.say_clip(
            'ready_confirmed',
            self.enter_mood_selection,
            SPEAKING_MOTION
        )

    def enter_mood_selection(self):
        self.clear_state_timer()
        self.state = FSMState.MOOD_SELECTION
        self.selected_mood_index = 0
        self.show_mood_screen()
        self.say_clip(
            'mood_instructions',
            None,
            SPEAKING_MOTION
        )

    def change_mood(self, direction):
        self.selected_mood_index = (
            self.selected_mood_index + direction
        ) % len(MOODS)
        self.show_mood_screen()

    def enter_mood_confirmation(self):
        self.state = FSMState.MOOD_CONFIRMATION
        self.mood_confirm_yes_selected = True
        self.show_mood_confirmation_screen()
        self.say(f'You chose {self.current_mood()}. Is that right?')

    def confirm_mood_selection(self):
        if self.mood_confirm_yes_selected:
            self.say('Mood confirmed. Pose suggestion comes next.')
            self.enter_pose_thinking()
        else:
            self.enter_mood_selection()

    def enter_pose_thinking(self):
        self.clear_state_timer()
        self.state = FSMState.POSE_THINKING
        self.show_screen('pose_thinking')
        self.say_clip(
            f'think_{self.current_mood()}',
            self.enter_pose_suggestion,
            THINKING_MOTION
        )

    def enter_pose_suggestion(self):
        self.clear_state_timer()
        self.state = FSMState.POSE_SUGGESTION
        self.selected_pose_index = random.randrange(
            len(POSE_LINES[self.current_mood()])
        )
        self.show_pose_screen()
        self.say_clip(
            f'pose_{self.current_mood()}_{self.selected_pose_index + 1}',
            self.enter_camera_ready,
            SPEAKING_MOTION
        )

    def enter_camera_ready(self):
        self.clear_state_timer()
        self.state = FSMState.CAMERA_READY
        # reframing
        self.show_screen('camera_ready')
        # Later this can switch to the DepthAI camera view.
        self.say_clip('camera_ready')

    def enter_countdown_intro(self):
        self.clear_state_timer()
        self.state = FSMState.COUNTDOWN_INTRO
        self.show_screen('countdown_intro')
        self.say_clip(
            'countdown_intro',
            self.enter_countdown
        )

    def enter_countdown(self):
        self.clear_state_timer()
        self.state = FSMState.COUNTDOWN
        self.countdown_number = 3
        self.show_screen('camera_ready')
        # Later this can overlay numbers on the DepthAI camera view.
        self.show_countdown_step()

    def show_countdown_step(self):
        self.say(str(self.countdown_number))
        self.show_screen(f'countdown_{self.countdown_number}')
        self.state_timer = self.create_timer(
            COUNTDOWN_SECONDS,
            self.advance_countdown
        )

    def advance_countdown(self):
        self.clear_state_timer()
        self.countdown_number -= 1

        if self.countdown_number > 0:
            self.show_countdown_step()
        else:
            self.enter_photo_capture()

    def enter_photo_capture(self):
        self.clear_state_timer()
        self.state = FSMState.PHOTO_CAPTURE
        self.show_screen('photo_capture')  # screen flash
        self.play_sound('/usr/share/sounds/alsa/Noise.wav')

        if not self.save_image_client.service_is_ready():
            self.get_logger().warn('save_image service not ready, using placeholder')
            self.captured_photo_path = str(
                self.resource_dir / PLACEHOLDER_CAPTURE_IMAGE
            )
            self.state_timer = self.create_timer(
                PHOTO_CAPTURE_SECONDS,
                self.enter_photo_reaction
            )
            return

        future = self.save_image_client.call_async(Trigger.Request())
        future.add_done_callback(self.handle_capture_response)
        self.get_logger().info('Requesting camera to save image...')

    def handle_capture_response(self, future):
        if self.state != FSMState.PHOTO_CAPTURE:
            return

        try:
            response = future.result()
        except Exception as error:
            self.get_logger().error(f'Camera capture failed: {error}')
            self.captured_photo_path = str(
                self.resource_dir / PLACEHOLDER_CAPTURE_IMAGE
            )
            self.enter_photo_reaction()
            return

        if not response.success:
            self.get_logger().error(f'Camera capture failed: {response.message}')
            self.captured_photo_path = str(
                self.resource_dir / PLACEHOLDER_CAPTURE_IMAGE
            )
            self.enter_photo_reaction()
            return

        self.captured_photo_path = '/home/ubuntu/ros2_ws/camera_image.jpg'
        self.get_logger().info(
            f'Camera image saved to: {self.captured_photo_path}'
        )
        self.enter_photo_reaction()

    def enter_photo_reaction(self):
        self.clear_state_timer()
        self.state = FSMState.PHOTO_REACTION
        self.show_screen('photo_reaction')
        self.say_clip(
            'photo_reaction',
            self.enter_photo_preview_ready,
            SPEAKING_MOTION
        )

    def enter_photo_preview_ready(self):
        self.clear_state_timer()
        self.state = FSMState.PHOTO_PREVIEW_READY
        self.show_screen(self.captured_photo_path or 'photo_preview')
        self.say_clip('preview_continue')

    def enter_photo_review_prompt(self):
        self.clear_state_timer()
        self.state = FSMState.PHOTO_REVIEW_PROMPT
        self.show_screen(self.captured_photo_path or 'photo_preview')
        self.say_clip(
            'review_prompt',
            self.enter_photo_review_choice,
            SPEAKING_MOTION
        )

    def enter_photo_review_choice(self):
        self.clear_state_timer()
        self.state = FSMState.PHOTO_REVIEW_CHOICE
        self.keep_photo_selected = True
        self.show_photo_review_screen()
        self.say_clip('toggle_instructions')

    def confirm_photo_review_choice(self):
        if self.keep_photo_selected:
            self.enter_overlay_intro()
        else:
            self.say("No problem, let's try again.")
            self.enter_camera_ready()

    def enter_overlay_intro(self):
        self.clear_state_timer()
        self.state = FSMState.OVERLAY_INTRO
        self.show_screen('overlay_intro_talking')
        self.say_clip(
            'overlay_instructions',
            self.enter_overlay_selection,
            SPEAKING_MOTION
        )

    def enter_overlay_selection(self):
        self.clear_state_timer()
        self.state = FSMState.OVERLAY_SELECTION
        self.selected_overlay_index = 0
        self.show_overlay_screen()

    def change_overlay(self, direction):
        self.selected_overlay_index = (
            self.selected_overlay_index + direction
        ) % len(OVERLAYS_BY_MOOD[self.current_mood()])
        self.show_overlay_screen()

    def enter_overlay_confirm_talk(self):
        self.clear_state_timer()
        self.state = FSMState.OVERLAY_CONFIRM_TALK
        self.show_overlay_screen()
        self.say(f'You chose {self.current_overlay_label()}. Is that right?')
        self.state_timer = self.create_timer(
            OVERLAY_CONFIRM_SECONDS,
            self.enter_overlay_confirmation
        )

    def enter_overlay_confirmation(self):
        self.clear_state_timer()
        self.state = FSMState.OVERLAY_CONFIRM_CHOICE
        self.overlay_confirm_yes_selected = True
        self.show_overlay_confirmation_screen()
        self.say_clip('toggle_instructions')

    def confirm_overlay_choice(self):
        if self.overlay_confirm_yes_selected:
            self.enter_apply_overlay()
        else:
            self.say("No problem, let's choose again.")
            self.enter_overlay_selection()

    def enter_apply_overlay(self):
        self.clear_state_timer()
        self.state = FSMState.APPLY_OVERLAY
        self.show_screen('apply_overlay')
        self.say_clip('apply_overlay')

        if not self.photo_processing_client.service_is_ready():
            self.enter_error_reset('Sorry, photo processing is not ready. Resetting.')
            return

        request = ProcessPhoto.Request()
        request.input_path = self.captured_photo_path
        request.overlay_type = self.current_overlay_type()
        request.output_path = ''

        future = self.photo_processing_client.call_async(request)
        future.add_done_callback(self.handle_process_photo_response)
        self.get_logger().info(
            f'Processing photo with overlay: {self.current_overlay()}'
        )

    def handle_process_photo_response(self, future):
        if self.state != FSMState.APPLY_OVERLAY:
            return

        try:
            response = future.result()
        except Exception as error:
            self.get_logger().error(f'Photo processing failed: {error}')
            self.enter_error_reset('Sorry, the photo overlay had trouble. Resetting.')
            return

        if not response.success:
            self.get_logger().error(f'Photo processing failed: {response.message}')
            self.enter_error_reset('Sorry, the photo overlay had trouble. Resetting.')
            return

        self.final_photo_path = response.processed_path
        self.get_logger().info(f'Processed photo path: {self.final_photo_path}')
        self.enter_final_preview()

    def enter_final_preview(self):
        self.clear_state_timer()
        self.state = FSMState.FINAL_PREVIEW
        self.show_screen(self.final_photo_path or 'final_preview')
        self.say_clip(
            'final_preview',
            self.enter_final_confirmation_prompt,
            SPEAKING_MOTION
        )

    def enter_final_confirmation_prompt(self):
        self.clear_state_timer()
        self.state = FSMState.FINAL_CONFIRMATION_PROMPT
        self.show_screen(self.final_photo_path or 'final_preview')
        self.say_clip(
            'final_prompt',
            self.enter_final_confirmation,
            SPEAKING_MOTION
        )

    def enter_final_confirmation(self):
        self.clear_state_timer()
        self.state = FSMState.FINAL_CONFIRMATION
        self.final_keep_selected = True
        self.show_final_confirmation_screen()
        self.say_clip('toggle_instructions')

    def confirm_final_choice(self):
        if self.final_keep_selected:
            self.enter_print_intro_talk()
        else:
            self.say("No problem, let's try the photo again.")
            self.enter_camera_ready()

    def enter_print_intro_talk(self):
        self.clear_state_timer()
        self.state = FSMState.PRINT_INTRO_TALK
        self.show_screen('printing_talking')
        self.say_clip(
            'printing_start',
            self.enter_printing,
            SPEAKING_MOTION
        )

    def enter_printing(self):
        self.clear_state_timer()
        self.state = FSMState.PRINTING
        self.show_screen('printing')

        if self.final_photo_path is None:
            self.enter_error_reset('No processed photo to print.')
            return

        if not self.printer_client.service_is_ready():
            self.enter_error_reset('Sorry, the printer is not ready. Resetting.')
            return

        request = PrintImage.Request()
        request.image_path = self.final_photo_path
        request.media_size = DEFAULT_PRINT_MEDIA

        future = self.printer_client.call_async(request)
        future.add_done_callback(self.handle_print_response)
        self.get_logger().info(f'Printing image: {self.final_photo_path}')

    def handle_print_response(self, future):
        if self.state != FSMState.PRINTING:
            return

        try:
            response = future.result()
        except Exception as error:
            self.get_logger().error(f'Print failed: {error}')
            self.enter_error_reset('Sorry, the printer had trouble. Resetting.')
            return

        if not response.success:
            self.get_logger().error(f'Print failed: {response.message}')
            self.enter_error_reset('Sorry, the printer had trouble. Resetting.')
            return

        self.get_logger().info(response.message)
        self.state_timer = self.create_timer(
            PRINTING_SCREEN_SECONDS,
            self.enter_print_complete
        )

    def enter_print_complete(self):
        self.clear_state_timer()
        self.state = FSMState.PRINT_COMPLETE
        self.show_screen('done')
        self.play_sound('/usr/share/sounds/speech-dispatcher/dummy-message.wav')
        self.state_timer = self.create_timer(
            PRINT_COMPLETE_SECONDS,
            self.enter_goodbye_talk
        )

    def enter_goodbye_talk(self):
        self.clear_state_timer()
        self.state = FSMState.GOODBYE_TALK
        self.show_screen('goodbye_talking')
        self.say_clip(
            'goodbye',
            self.enter_goodbye_dance,
            SPEAKING_MOTION
        )

    def enter_goodbye_dance(self):
        self.clear_state_timer()
        self.state = FSMState.GOODBYE_DANCE
        self.show_screen('done')
        self.send_movement(SUCCESS_DANCE)

    def enter_error_reset(self, message):
        self.clear_state_timer()
        self.state = FSMState.ERROR_RESET
        self.show_screen('error')
        self.say(message)
        self.state_timer = self.create_timer(
            ERROR_RESET_SECONDS,
            self.enter_idle
        )

    def show_ready_screen(self):
        if self.ready_yes_selected:
            self.show_screen('ready_yes')
        else:
            self.show_screen('ready_no')

    def show_mood_screen(self):
        self.show_screen(f'mood_{self.current_mood()}')

    def show_mood_confirmation_screen(self):
        if self.mood_confirm_yes_selected:
            self.show_screen('mood_confirm_yes')
        else:
            self.show_screen('mood_confirm_change')

    def show_pose_screen(self):
        self.show_screen(
            f'pose_{self.current_mood()}_{self.selected_pose_index + 1}'
        )

    def show_photo_review_screen(self):
        if self.keep_photo_selected:
            self.show_screen('photo_keep')
        else:
            self.show_screen('photo_retake')

    def show_overlay_screen(self):
        self.show_screen(f'overlay_{self.current_overlay()}')

    def show_overlay_confirmation_screen(self):
        if self.overlay_confirm_yes_selected:
            self.show_screen('overlay_confirm_yes')
        else:
            self.show_screen('overlay_confirm_change')

    def show_final_confirmation_screen(self):
        if self.final_keep_selected:
            self.show_screen('final_keep')
        else:
            self.show_screen('final_retake')

    def current_mood(self):
        return MOODS[self.selected_mood_index]

    def current_pose_line(self):
        return POSE_LINES[self.current_mood()][self.selected_pose_index]

    def current_overlay(self):
        return OVERLAYS_BY_MOOD[self.current_mood()][self.selected_overlay_index]

    def current_overlay_label(self):
        return self.current_overlay().replace('_', ' ').title()

    def current_overlay_type(self):
        # Replace this when ProcessPhoto.srv has one enum per overlay.
        return ProcessPhoto.Request.OVERLAY_FLOWERS

    def show_screen(self, screen_name):
        msg = String()
        msg.data = screen_name
        self.screen_publisher.publish(msg)
        self.get_logger().info(f'Screen command: {screen_name}')

    def send_movement(self, movement_command):
        msg = String()
        msg.data = movement_command
        self.movement_publisher.publish(msg)
        self.get_logger().info(f'Movement command: {movement_command}')

    def play_sound(self, sound_path, next_callback=None,
                   movement_command=None, expected_state=None):
        if not self.play_sound_client.wait_for_service(timeout_sec=1.0):
            self.get_logger().warn('PlaySound service not available')
            return False

        req = PlaySound.Request()
        req.sound_path = sound_path

        self.get_logger().info(f'Calling PlaySound service with: {sound_path}')
        future = self.play_sound_client.call_async(req)

        if next_callback is not None or movement_command is not None:
            future.add_done_callback(
                lambda done_future: self.handle_sound_response(
                    done_future,
                    expected_state,
                    next_callback,
                    movement_command
                )
            )

        return True

    def say(self, text):
        # Replace this with TTS when the speech node is ready.
        self.get_logger().info(f'[Pupper says] {text}')

    def say_clip(self, clip_name, next_callback=None, movement_command=None):
        self.say(AUDIO_LINES.get(clip_name, clip_name))

        if movement_command is not None:
            self.send_movement(movement_command)

        expected_state = self.state
        sound_file = self.audio_dir / f'{clip_name}.wav'
        sound_started = self.play_sound(
            str(sound_file),
            next_callback,
            movement_command,
            expected_state
        )

        if sound_started:
            return

        if movement_command is not None:
            self.send_movement(STOP)

        if next_callback is not None:
            next_callback()

    def handle_sound_response(self, future, expected_state,
                              next_callback, movement_command):
        if self.state != expected_state:
            return

        try:
            response = future.result()
        except Exception as error:
            self.get_logger().warn(f'PlaySound failed: {error}')
        else:
            if not response.success:
                self.get_logger().warn(response.message)

        if movement_command is not None:
            self.send_movement(STOP)

        if next_callback is not None:
            next_callback()

    def clear_state_timer(self):
        if self.state_timer is not None:
            self.state_timer.cancel()
            self.destroy_timer(self.state_timer)
            self.state_timer = None


def main(args=None):
    rclpy.init(args=args)

    fsm = PupperFSM()

    try:
        rclpy.spin(fsm)
    finally:
        fsm.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
