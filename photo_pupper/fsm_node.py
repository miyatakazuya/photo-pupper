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
SUCCESS_DANCE = 'success_dance'
WELCOME_TALK_SECONDS = 6.0
READY_TALK_SECONDS = 7.0
READY_CONFIRMED_SECONDS = 3.0
POSE_THINKING_SECONDS = 2.0
POSE_SUGGESTION_SECONDS = 8.0
COUNTDOWN_INTRO_SECONDS = 2.0
COUNTDOWN_SECONDS = 1.0
PHOTO_CAPTURE_SECONDS = 1.5
PHOTO_REACTION_SECONDS = 3.0
PHOTO_REVIEW_PROMPT_SECONDS = 3.0
OVERLAY_INTRO_SECONDS = 6.0
OVERLAY_CONFIRM_SECONDS = 2.5
FINAL_PREVIEW_SECONDS = 3.0
FINAL_CONFIRMATION_PROMPT_SECONDS = 3.0
PRINT_INTRO_SECONDS = 3.0
PRINTING_SCREEN_SECONDS = 4.0
PRINT_COMPLETE_SECONDS = 2.0
GOODBYE_TALK_SECONDS = 5.0
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
        self.say(
            "Hi! I'm Pupper, your photo booth helper. "
            "I'll help you choose a mood, pick a pose, take your picture, "
            'decorate it, and print it for you.'
        )
        self.send_movement(GREETING_NOD)
        # Temporary pause until audio or TTS can tell us it finished.
        self.state_timer = self.create_timer(
            WELCOME_TALK_SECONDS,
            self.enter_ready_talk
        )

    def enter_ready_talk(self):
        self.clear_state_timer()
        self.state = FSMState.READY_TALK
        self.show_screen('ready_talking')
        self.say(
            "Before we start, make sure you're okay with me taking your "
            'photo and printing it for this demo. If that sounds good, '
            'choose Yes. If not, choose No.'
        )
        # Temporary pause until audio or TTS can tell us it finished.
        self.state_timer = self.create_timer(
            READY_TALK_SECONDS,
            self.enter_ready
        )

    def enter_ready(self):
        self.clear_state_timer()
        self.state = FSMState.READY
        self.ready_yes_selected = True
        self.show_ready_screen()
        self.say(
            'Use the left and right buttons to switch options, '
            'and press confirm to choose.'
        )

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
        self.say(
            "Alright, sounds like you're ready. "
            "Let's start by choosing a mood for your photo."
        )
        # Temporary pause until audio or TTS can tell us it finished.
        self.state_timer = self.create_timer(
            READY_CONFIRMED_SECONDS,
            self.enter_mood_selection
        )

    def enter_mood_selection(self):
        self.clear_state_timer()
        self.state = FSMState.MOOD_SELECTION
        self.selected_mood_index = 0
        self.show_mood_screen()
        self.say(
            'Pick the mood you want for your photo. '
            'Use the left and right buttons to cycle through the options, '
            'and press confirm to choose.'
        )
        # Later this can be a animated face, blink cycle, and nod gesture.

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
        self.say(MOOD_THINKING_LINES[self.current_mood()])
        # Later this can follow TTS and a thinking gesture.
        self.state_timer = self.create_timer(
            POSE_THINKING_SECONDS,
            self.enter_pose_suggestion
        )

    def enter_pose_suggestion(self):
        self.clear_state_timer()
        self.state = FSMState.POSE_SUGGESTION
        self.selected_pose_index = random.randrange(
            len(POSE_LINES[self.current_mood()])
        )
        self.show_pose_screen()
        self.say(self.current_pose_line())
        self.state_timer = self.create_timer(
            POSE_SUGGESTION_SECONDS,
            self.enter_camera_ready
        )

    def enter_camera_ready(self):
        self.clear_state_timer()
        self.state = FSMState.CAMERA_READY
        self.show_screen('camera_ready')
        # Later this can switch to the DepthAI camera view.
        self.say(
            'Looking good. Get in view and hold that pose. '
            'Press confirm when you are ready for the countdown.'
        )

    def enter_countdown_intro(self):
        self.clear_state_timer()
        self.state = FSMState.COUNTDOWN_INTRO
        self.show_screen('countdown_intro')
        self.say('Get ready for the countdown!')
        self.state_timer = self.create_timer(
            COUNTDOWN_INTRO_SECONDS,
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
        self.show_screen('photo_capture') # screen flash
        # Replace with the DepthAI snapshot path when capture is ready.
        self.play_sound('/usr/share/sounds/alsa/Noise.wav')
        self.captured_photo_path = str(
            self.resource_dir / PLACEHOLDER_CAPTURE_IMAGE
        )
        self.state_timer = self.create_timer(
            PHOTO_CAPTURE_SECONDS,
            self.enter_photo_reaction
        )

    def enter_photo_reaction(self):
        self.clear_state_timer()
        self.state = FSMState.PHOTO_REACTION
        self.show_screen('photo_reaction')
        self.say('That was a great shot. You make this look easy.')
        self.state_timer = self.create_timer(
            PHOTO_REACTION_SECONDS,
            self.enter_photo_preview_ready
        )

    def enter_photo_preview_ready(self):
        self.clear_state_timer()
        self.state = FSMState.PHOTO_PREVIEW_READY
        self.show_screen('photo_preview')
        # Later this should show the real captured photo.
        self.say('Your photo came out great. Press confirm to continue.')

    def enter_photo_review_prompt(self):
        self.clear_state_timer()
        self.state = FSMState.PHOTO_REVIEW_PROMPT
        self.show_screen('photo_preview')
        # Later this should keep showing the real captured photo.
        self.say('Would you like to keep that photo or retake it?')
        self.state_timer = self.create_timer(
            PHOTO_REVIEW_PROMPT_SECONDS,
            self.enter_photo_review_choice
        )

    def enter_photo_review_choice(self):
        self.clear_state_timer()
        self.state = FSMState.PHOTO_REVIEW_CHOICE
        self.keep_photo_selected = True
        self.show_photo_review_screen()
        self.say('Use the left and right buttons to toggle, and confirm to choose.')

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
        self.say(
            'Great choice. Overlay selection comes next. '
            'Use the left and right buttons to choose which overlay theme you want, '
            'and press confirm to choose.'
        )
        # Later this can follow TTS and a speaking gesture.
        self.state_timer = self.create_timer(
            OVERLAY_INTRO_SECONDS,
            self.enter_overlay_selection
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
        self.say('Use the left and right buttons to choose, and confirm to choose.')

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
        self.show_screen('final_preview')
        # Later this should show the real processed photo.
        self.say('Your final picture came out amazing.')
        self.state_timer = self.create_timer(
            FINAL_PREVIEW_SECONDS,
            self.enter_final_confirmation_prompt
        )

    def enter_final_confirmation_prompt(self):
        self.clear_state_timer()
        self.state = FSMState.FINAL_CONFIRMATION_PROMPT
        self.show_screen('final_preview')
        # Later this should keep showing the real processed photo.
        self.say('What do you think? Keep this final photo or retake it?')
        self.state_timer = self.create_timer(
            FINAL_CONFIRMATION_PROMPT_SECONDS,
            self.enter_final_confirmation
        )

    def enter_final_confirmation(self):
        self.clear_state_timer()
        self.state = FSMState.FINAL_CONFIRMATION
        self.final_keep_selected = True
        self.show_final_confirmation_screen()
        self.say('Use the left and right buttons to toggle, and confirm to choose.')

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
        self.say("Perfect. I'm printing your photo now.")
        # Later this can follow TTS and a speaking gesture.
        self.state_timer = self.create_timer(
            PRINT_INTRO_SECONDS,
            self.enter_printing
        )

    def enter_printing(self):
        self.clear_state_timer()
        self.state = FSMState.PRINTING
        self.show_screen('printing')

        if not self.save_image_client.service_is_ready():
            self.enter_error_reset('Sorry, the camera is not ready. Resetting.')
            return

        request = Trigger.Request()
        future = self.save_image_client.call_async(request)
        future.add_done_callback(self.handle_save_image_response)
        self.get_logger().info('Requesting camera_node to save current image...')

    def handle_save_image_response(self, future):
        if self.state != FSMState.PRINTING:
            return

        try:
            response = future.result()
        except Exception as error:
            self.get_logger().error(f'Save image failed: {error}')
            self.enter_error_reset('Sorry, the camera had trouble. Resetting.')
            return

        if not response.success:
            self.get_logger().error(f'Save image failed: {response.message}')
            self.enter_error_reset('Sorry, the camera had trouble. Resetting.')
            return

        self.get_logger().info('Image saved successfully. Now printing...')

        if not self.printer_client.service_is_ready():
            self.enter_error_reset('Sorry, the printer is not ready. Resetting.')
            return

        request = PrintImage.Request()
        request.image_path = self.final_photo_path
        request.media_size = DEFAULT_PRINT_MEDIA

        future_print = self.printer_client.call_async(request)
        future_print.add_done_callback(self.handle_print_response)
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
        self.say(
            'Your photo is ready. Go grab it from the printer beside me. '
            'Thanks for taking pictures with me!'
        )
        # Later this can follow TTS and a speaking gesture.
        self.state_timer = self.create_timer(
            GOODBYE_TALK_SECONDS,
            self.enter_goodbye_dance
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

    def play_sound(self, sound_path):
        if not self.play_sound_client.wait_for_service(timeout_sec=1.0):
            self.get_logger().warn("PlaySound service not available")
            return
        req = PlaySound.Request()
        req.sound_path = sound_path
        self.get_logger().info(f"Calling PlaySound service with: {sound_path}")
        self.play_sound_client.call_async(req)

    def say(self, text):
        self.get_logger().info(f'[Pupper says] {text}')

        phrases_map = {
            "Hi! I'm Pupper, your photo booth helper. I'll help you choose a mood, pick a pose, take your picture, decorate it, and print it for you.": "welcome",
            "Before we start, make sure you're okay with me taking your photo and printing it for this demo. If that sounds good, choose Yes. If not, choose No.": "ready_prompt",
            "Use the left and right buttons to switch options, and press confirm to choose.": "sensor_instructions",
            "Alright, sounds like you're ready. Let's start by choosing a mood for your photo.": "ready_confirmed",
            "Pick the mood you want for your photo. Use the left and right buttons to cycle through the options, and press confirm to choose.": "mood_instructions",
            "Looking good. Get in view and hold that pose. Press confirm when you are ready for the countdown.": "camera_ready",
            "Get ready for the countdown!": "countdown_intro",
            "That was a great shot. You make this look easy.": "photo_reaction",
            "Your photo came out great. Press confirm to continue.": "preview_continue",
            "Would you like to keep that photo or retake it?": "review_prompt",
            "Use the left and right buttons to toggle, and confirm to choose.": "toggle_instructions",
            "Use the left and right buttons to choose, and confirm to choose.": "toggle_instructions",
            "Great choice. Overlay selection comes next. Use the left and right buttons to choose which overlay theme you want, and press confirm to choose.": "overlay_instructions",
            "Applying your chosen decorations now.": "apply_overlay",
            "Your final picture came out amazing.": "final_preview",
            "What do you think? Keep this final photo or retake it?": "final_prompt",
            "Perfect. I'm printing your photo now.": "printing_start",
            "Your photo is ready. Go grab it from the printer beside me. Thanks for taking pictures with me!": "goodbye",
            "Hmm, you're feeling happy today. Let me think...": "think_happy",
            "Silly mood? I like it. Let me think...": "think_silly",
            "Feeling sad today? I'll try to make this one sweet.": "think_sad",
            "Serious mood. Let me find something strong.": "think_serious",
            "Try a double bicep flex.": "pose_happy_1",
            "Try making heart hands.": "pose_happy_2",
            "Give me a big smile and thumbs up.": "pose_happy_3",
            "Do the dab.": "pose_silly_1",
            "Try funny hand motion on your head": "pose_silly_2",
            "Give me a peace sign!": "pose_silly_3",
            "Try a fake crying pose.": "pose_sad_1",
            "Curl up in your chair and hug your legs like you are really sad.": "pose_sad_2",
            "Look down dramatically.": "pose_sad_3",
            "Cross your arms like a boss.": "pose_serious_1",
            "Stand strong and pose like superman!": "pose_serious_2",
            "Try a thinker pose.": "pose_serious_3"
        }

        clean_text = text.strip()
        filename = phrases_map.get(clean_text)
        if filename:
            sound_file = self.audio_dir / f"{filename}.wav"
            self.play_sound(str(sound_file))
        else:
            self.get_logger().info(f"No direct audio file match found for: '{clean_text}'")

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
