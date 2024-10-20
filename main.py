import asyncio
import time

from aiohttp import web, request
from loguru import logger as logging
import os

# Import all modules from the Modules directory
from Modules.RoomModule import RoomModule
from Modules.RoomObject import RoomObject

for module in os.listdir("Modules"):
    if module.endswith(".py") and module != "__init__.py":
        module_name = module.replace(".py", "")
        logging.info(f"Importing {module_name}")
        __import__(f"Modules.{module_name}", fromlist=[module_name])
    if os.path.isdir(f"Modules/{module}"):
        logging.info(f"Importing {module}")
        for module_file in os.listdir(f"Modules/{module}"):
            if module_file.endswith(".py") and module_file != "__init__.py":
                module_name = module_file.replace(".py", "")
                logging.info(f"Importing {module_name} from {module}")
                __import__(f"Modules.{module}.{module_name}", fromlist=[module_name])

class ObjectPointer:

    def __init__(self, initial_ref):
        self.reference = initial_ref

    def __getattr__(self, item):
        # Pass the attribute request to the reference object unless we are trying to update the reference
        if item == "reference":
            return self.reference
        return getattr(self.reference, item)

    def __setattr__(self, key, value):
        if key == "reference":
            super(ObjectPointer, self).__setattr__(key, value)
        else:
            setattr(self.reference, key, value)


class SatelliteController:

    def __init__(self, name="SatelliteController", auth=None):
        # Find all subclasses of RoomModule and create an instance of them
        self.name = name
        self.auth = auth
        self.controllers = []
        self.room_objects = []
        for room_module in RoomModule.__subclasses__():
            logging.info(f"Creating instance of {room_module.__name__}")
            try:
                room_module(self)
            except Exception as e:
                logging.error(f"Error creating instance of {room_module.__name__}: {e}")
                logging.exception(e)

    def _create_promise_object(self, device_name, device_type="promise"):
        # If a room object was looking for another object that hasn't been created yet, it will get a empty RoomObject
        # That will be replaced with the real object when it is created later this allows for circular dependencies
        logging.info(f"Creating promise object {device_name} of type {device_type}")
        pointer = ObjectPointer(RoomObject(device_name, device_type))
        return pointer

    def _create_promise_module(self, module_name):
        logging.info(f"Creating promise module {module_name}")
        return RoomModule(self, module_name)

    def attach_module(self, room_module):
        self.controllers.append(room_module)

    def attach_object(self, device: RoomObject):
        if not issubclass(type(device), RoomObject):
            raise TypeError(f"Device {device} is not a subclass of RoomObject")
        # Check if the device exists as a promise object and replace it with the real object without changing the
        # reference So that any references to the promise object are updated to the real object
        for i, room_object in enumerate(self.room_objects):
            if room_object.object_name == device.object_name:
                logging.info(f"Replacing promise object {room_object.object_name} with real object")
                # Make sure that we copy the callbacks from the promise object to the real object
                device._callbacks = room_object._callbacks
                device._network_hook = room_object._network_hook
                self.room_objects[i].reference = device  # Replace the promise object with the real object
                return
        logging.info(f"Attaching object {device.object_name} to room controller")
        self.room_objects.append(device)

    def get_all_devices(self):
        return self.room_objects

    def get_module(self, module_name):
        for module in self.controllers:
            if module.__class__.__name__ == module_name:
                return module
        return None

    def get_modules(self):
        return self.controllers

    def get_object(self, device_name, create_if_not_found=True):
        for device in self.room_objects:
            if device.object_name == device_name:
                return self.room_objects[self.room_objects.index(device)]  # Return the reference to the object
        if create_if_not_found:
            self.room_objects.append(self._create_promise_object(device_name))
            return self.room_objects[-1]
        return None

    def get_all_objects(self):
        return self.room_objects

    def get_type(self, device_type):
        devices = []
        for device in self.room_objects:
            if device.device_type == device_type:
                devices.append(device)
        return devices


async def main():
    controller = SatelliteController("wopr", "55555")
    await asyncio.sleep(5)
    logging.info("Starting web servers")
    sites = []
    for module in controller.get_modules():
        if hasattr(module, "wait_for_ready"):
            module.wait_for_ready()
        # Collect any aiohttp servers and run use asyncio.gather to run them all at once

        if hasattr(module, "is_webserver") and getattr(module, "get_site", None) is not None:
            logging.info(f"Found web server {module}")
            sites.append(await module.get_site())
    if len(sites) > 0:
        await asyncio.gather(*(site.start() for site in sites))

    logging.info("Web servers started")
    while True:
        await asyncio.sleep(9999)


if __name__ == "__main__":
    asyncio.run(main())
