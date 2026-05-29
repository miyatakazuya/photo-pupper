#!/usr/bin/env python3

from enum import Enum

import rclpy
from rclpy.node import Node
from std_msgs.msg import String


FRONT_CONFIRM = 'FRONT_CONFIRM'
LEFT_PREV = 'LEFT_PREV'
RIGHT_NEXT = 'RIGHT_NEXT'
MOVEMENT_COMPLETE = 'MOVEMENT_COMPLETE'

WALK_FORWARD = 'walk_forward'
GREETING_NOD = 'greeting_nod'
PLACEHOLDER_AUDIO_SECONDS = 5.0
MOODS = ['happy', 'silly', 'sad', 'serious']


class FSMState(Enum):
    IDLE = 0
    REVEAL = 1
    WELCOME = 2
    READY = 3
    MOOD_SELECTION = 4
    MOOD_CONFIRMATION = 5


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
        self.mood_confirm_yes_selected = True
        self.state_timer = None
        self.enter_idle()

    def touch_callback(self, msg):
        touch_event = msg.data.strip()

        if touch_event == FRONT_CONFIRM:
            self.handle_front_confirm()
        elif touch_event == LEFT_PREV:
            self.handle_selection_change(-1)
        elif touch_event == RIGHT_NEXT:
            self.handle_selection_change(1)

    def movement_callback(self, msg):
        movement_event = msg.data.strip()

        if self.state == FSMState.REVEAL and movement_event == MOVEMENT_COMPLETE:
            self.enter_welcome()

    def handle_front_confirm(self):
        if self.state == FSMState.IDLE:
            self.enter_reveal()
        elif self.state == FSMState.READY:
            self.confirm_ready_selection()
        elif self.state == FSMState.MOOD_SELECTION:
            self.enter_mood_confirmation()
        elif self.state == FSMState.MOOD_CONFIRMATION:
            self.confirm_mood_selection()

    def handle_selection_change(self, direction):
        if self.state == FSMState.READY:
            self.ready_yes_selected = not self.ready_yes_selected
            self.show_ready_screen()
        elif self.state == FSMState.MOOD_SELECTION:
            self.change_mood(direction)
        elif self.state == FSMState.MOOD_CONFIRMATION:
            self.mood_confirm_yes_selected = not self.mood_confirm_yes_selected
            self.show_mood_confirmation_screen()

    def enter_idle(self):
        self.clear_state_timer()
        self.state = FSMState.IDLE
        self.ready_yes_selected = True
        self.selected_mood_index = 0
        self.mood_confirm_yes_selected = True
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
        self.say("Hi! I'm Pupper, your photo booth helper.")
        self.send_movement(GREETING_NOD)
        # Temporary pause until audio or TTS can tell us it finished.
        self.state_timer = self.create_timer(
            PLACEHOLDER_AUDIO_SECONDS,
            self.enter_ready
        )

    def enter_ready(self):
        self.clear_state_timer()
        self.state = FSMState.READY
        self.ready_yes_selected = True
        self.show_ready_screen()
        self.say('Are you ready to take a photo?')

    def confirm_ready_selection(self):
        if self.ready_yes_selected:
            self.say('Ready confirmed. Mood selection comes next.')
            self.enter_mood_selection()
        else:
            self.say('No problem. Resetting.')
            self.enter_idle()

    def enter_mood_selection(self):
        self.clear_state_timer()
        self.state = FSMState.MOOD_SELECTION
        self.selected_mood_index = 0
        self.show_mood_screen()
        self.say('Choose a photo mood. USe the side buttons blah blah')
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
        else:
            self.enter_mood_selection()

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

    def current_mood(self):
        return MOODS[self.selected_mood_index]

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
