import json
import time

from loguru import logger as logging

from Modules.Decorators import background
from Modules.RoomModule import RoomModule
from Modules.RoomObject import RoomObject

try:
    import RPi.GPIO as GPIO
    GPIO.setmode(GPIO.BOARD)
except ImportError:
    GPIO = None
    logging.warning("RPi.GPIO not found, GPIO will not be available")


class RelayHost(RoomModule):

    def __init__(self, room_controller):
        logging.info("RelayHost: Initializing")
        super().__init__(room_controller)
        self.relays = []
        self.relay_configs = json.load(open("Configs/Relays.json"))

        for relay in self.relay_configs:
            self.relays.append(Relay(relay["name"], relay["pin"], relay["normallyOpen"], relay["defaultState"]))

        for relay in self.relays:
            self.room_controller.attach_object(relay)


class Relay(RoomObject):

    is_promise = False
    is_sensor_only = True

    def __init__(self, name, pin, normally_open=True, default_state=False):
        super().__init__(name, "Relay")
        logging.info(f"Relay ({name}): Initializing")
        self.online = True
        self.fault = False
        self.fault_message = ""
        self.pin = pin  # Pin number
        self.state = None  # None = Unknown, True = On, False = Off
        self._name = name  # Name of the device

        self.normal_open = normally_open

        if GPIO is None:
            self.fault = True
            self.fault_message = "RPi.GPIO not found"
            logging.warning(f"Relay ({name}): Not initializing, RPi.GPIO not found")
            return

        GPIO.setup(self.pin, GPIO.OUT)
        self.set_state(default_state)
        logging.info(f"Relay ({name}): Initialized with default state {default_state}")

    def set_state(self, state):
        if state:
            GPIO.output(self.pin, GPIO.LOW if self.normal_open else GPIO.HIGH)
        else:
            GPIO.output(self.pin, GPIO.HIGH if self.normal_open else GPIO.LOW)
        self.state = state
        self.emit_event("on_state_update", state)

    def get_state(self):
        return self.state