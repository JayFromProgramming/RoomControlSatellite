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


class PinWatcherHost(RoomModule):

    def __init__(self, room_controller):
        super().__init__(room_controller)
        self.pin_watchers = []
        self.watcher_configs = json.load(open("Configs/PinWatchers.json"))
        # self.database = room_controller.database

        for watcher in self.watcher_configs:
            self.pin_watchers.append(PinWatcher(watcher["name"], watcher["pin"], watcher["edge"],
                                                watcher["debounce"],
                                                watcher["normallyOpen"]))

        for watcher in self.pin_watchers:
            self.room_controller.attach_object(watcher)


class PinWatcher(RoomObject):
    is_promise = False
    is_sensor_only = True

    def __init__(self, name, pin, edge=None, bouncetime=200, normally_open=True):
        super().__init__(name, "PinWatcher")
        self.online = True
        self.fault = False
        self.fault_message = ""
        self.pin = pin  # Pin number
        self.state = None  # None = Unknown, True = On, False = Off
        self._name = name  # Name of the device

        self._last_rising = 0  # Last time the device was triggered
        self._last_falling = 0  # Last time the device was triggered

        self.edge = None
        self.bouncetime = bouncetime
        self.normal_open = normally_open

        if GPIO is None:
            self.fault = True
            self.fault_message = "RPi.GPIO not found"
            logging.warning(f"PinWatcher ({name}): Not initializing, RPi.GPIO not found")
            return

        super().set_value("triggered", False)
        super().set_value("active_for", 0)
        super().set_value("last_active", 0)

        self.edge = GPIO.RISING if edge else GPIO.BOTH
        try:
            GPIO.setup(self.pin, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
            self.state = GPIO.input(self.pin) if self.normal_open else not GPIO.input(self.pin)
            GPIO.add_event_detect(self.pin, self.edge, callback=self._callback, bouncetime=self.bouncetime)
            logging.debug(f"PinWatcher ({name}): Initialized")
        except Exception as e:
            self.fault = True
            self.fault_message = str(e)
            logging.warning(f"PinWatcher ({name}): Error initializing: {e}")

    def _callback(self, pin):
        self.state = GPIO.input(self.pin) if self.normal_open else not GPIO.input(self.pin)

        if self.state:  # If the device is active
            self._last_rising = time.time()
        else:
            self._last_falling = time.time()

        logging.debug(f"PinWatcher ({self.name()}): Pin {pin} changed state to {self.state}")
        super().emit_event("state_change", self.get_state())
        # Setup new event detect
        GPIO.remove_event_detect(self.pin)
        GPIO.add_event_detect(self.pin, self.edge, callback=self._callback, bouncetime=self.bouncetime)

    @background
    def update_value(self):
        super().set_value("triggered", self.state)
        super().set_value("active_for", 0 if not self.state else time.time() - self._last_rising)
        super().set_value("last_active", self._last_rising)

    def name(self):
        return self._name

    def get_state(self):
        return {
            "triggered": self.state,
            "active_for": 0 if not self.state else time.time() - self._last_rising,
            "last_active": self._last_rising,
        }

    def get_info(self):
        return {
            "name": self.name(),
            "pin": self.pin,
            "edge": self.edge,
            "bouncetime": self.bouncetime
        }

    def get_type(self):
        return "pin_watcher"

    def get_health(self):
        return {
            "online": True,
            "fault": self.fault,
            "reason": self.fault_message
        }
