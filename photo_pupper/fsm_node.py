#!/usr/bin/env python3

import random
from enum import Enum

import rclpy
from rclpy.node import Node
from std_msgs.msg import String


FRONT_CONFIRM = 'FRONT_CONFIRM'
LEFT_CYCLE = 'LEFT_CYCLE'
MOVEMENT_COMPLETE = 'MOVEMENT_COMPLETE'

WALK_FORWARD = 'walk_forward'
GREETING_NOD = 'greeting_nod'
SUCCESS_DANCE = 'success_dance'
WELCOME_TALK_SECONDS = 6.0
READY_TALK_SECONDS = 7.0
READY_CONFIRMED_SECONDS = 3.0
POSE_THINKING_SECONDS = 2.0
POSE_SUGGESTION_SECONDS = 5.0
COUNTDOWN_INTRO_SECONDS = 2.0
COUNTDOWN_SECONDS = 1.0
PHOTO_CAPTURE_SECONDS = 1.5
PHOTO_REACTION_SECONDS = 3.0
PHOTO_REVIEW_PROMPT_SECONDS = 3.0
OVERLAY_INTRO_SECONDS = 6.0
OVERLAY_CONFIRM_SECONDS = 2.5
APPLY_OVERLAY_SECONDS = 1.0
FINAL_PREVIEW_SECONDS = 3.0
FINAL_CONFIRMATION_PROMPT_SECONDS = 3.0
PRINT_INTRO_SECONDS = 3.0
MOCK_PRINT_SECONDS = 4.0
PRINT_COMPLETE_SECONDS = 2.0
GOODBYE_TALK_SECONDS = 5.0

MOODS = ['happy', 'silly', 'sad', 'serious']
OVERLAYS_BY_MOOD = {
    'happy': ['stars', 'flowers', 'party'],
    'silly': ['comic', 'clouds', 'confetti'],
    'sad': ['sad_cloud', 'rain', 'broken_heart'],
    'serious': ['black_white', 'caution', 'locked_in'],
}
POSE_LINES = {
    'happy': [
        'Give me a big smile and thumbs up.',
        'Try making heart hands.',
        'Try a double bicep flex.',
    ],
    'silly': [
        'Give me a peace sign!',
        'Try funny hand motion on your head',
        'Do the dab.',
    ],
    'sad': [
        'Try a fake crying pose.',
        'Look down dramatically.',
        'Curl up in your chair and hug your legs like you are really sad.',
    ],
    'serious': [
        'Cross your arms like a boss.',
        'Try a thinker pose.',
        'Stand strong and pose like superman!',
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
        self.touch_subscription = self.create_subscription(
            String,
            'touch',
            self.touch_callback,
            10
        )
        self.movement_subscription = self.create_subscription(
            String,
            'movement_event',
            self.movement_callback,
            10
        )

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
        self.state_timer = None
        self.enter_idle()

    def touch_callback(self, msg):
        touch_event = msg.data.strip()

        if touch_event == FRONT_CONFIRM:
            self.handle_front_confirm()
        elif touch_event == LEFT_CYCLE:
            self.handle_selection_change()

    def movement_callback(self, msg):
        movement_event = msg.data.strip()

        if self.state == FSMState.REVEAL and movement_event == MOVEMENT_COMPLETE:
            self.enter_welcome()
        elif (
            self.state == FSMState.GOODBYE_DANCE
            and movement_event == MOVEMENT_COMPLETE
        ):
            self.enter_idle()

    def handle_front_confirm(self):
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

    def handle_selection_change(self):
        if self.state == FSMState.READY:
            self.ready_yes_selected = not self.ready_yes_selected
            self.show_ready_screen()
        elif self.state == FSMState.MOOD_SELECTION:
            self.change_mood()
        elif self.state == FSMState.MOOD_CONFIRMATION:
            self.mood_confirm_yes_selected = not self.mood_confirm_yes_selected
            self.show_mood_confirmation_screen()
        elif self.state == FSMState.PHOTO_REVIEW_CHOICE:
            self.keep_photo_selected = not self.keep_photo_selected
            self.show_photo_review_screen()
        elif self.state == FSMState.OVERLAY_SELECTION:
            self.change_overlay()
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
            'Use my left sensor to switch options, '
            'and press my front sensor to confirm.'
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
            'Use my left sensor to cycle through the options, '
            'and press my front sensor to confirm.'
        )
        # Later this can be a animated face, blink cycle, and nod gesture.

    def change_mood(self):
        self.selected_mood_index = (
            self.selected_mood_index + 1
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
            'Press my front sensor when you are ready for the countdown.'
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
        # Later this triggers the camera, flash screen, and shutter sound.
        self.get_logger().info('[Snapshot sound placeholder]')
        self.captured_photo_path = 'mock_captured_photo'
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
        self.say('Your photo came out great. Press my front sensor to continue.')

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
        self.say('Use my left sensor to toggle, and front to confirm.')

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
            'Use my left sensor to choose which overlay theme you want, '
            'and press my front sensor to confirm.'
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

    def change_overlay(self):
        self.selected_overlay_index = (
            self.selected_overlay_index + 1
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
        self.say('Use my left sensor to choose, and front to confirm.')

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
        # Later this calls the photo processing service and stores its output path.
        self.final_photo_path = 'mock_final_photo'
        self.state_timer = self.create_timer(
            APPLY_OVERLAY_SECONDS,
            self.enter_final_preview
        )

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
        self.say('Use my left sensor to toggle, and front to confirm.')

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
        # Later this will call the PrintImage service from printer_node.py.
        self.get_logger().info(f'Mock printing image: {self.final_photo_path}')
        self.state_timer = self.create_timer(
            MOCK_PRINT_SECONDS,
            self.enter_print_complete
        )

    def enter_print_complete(self):
        self.clear_state_timer()
        self.state = FSMState.PRINT_COMPLETE
        self.show_screen('done')
        self.get_logger().info('[Print complete sound placeholder]')
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

    def say(self, text):
        # Replace this logger with TTS/audio later.
        self.get_logger().info(f'[Pupper says] {text}')

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
