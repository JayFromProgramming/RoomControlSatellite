import asyncio

from aiohttp import web, request
from loguru import logger as logging
import os

# Import all modules from the Modules directory
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


async def main():

    # Using to test satellite interface on the main controller
    json = {
        "name": "wopr",
        "current_ip": "wopr.eggs.loafclan.org",
        "objects": {
            "room_temp": {
                "type": "EnvironmentSensor",
                "data": {
                    "name": "room_temp",
                    "current_value": 72,
                    "unit": "F"
                },
                "health": {
                    "online": True,
                    "fault": False,
                    "reason": ""
                }
            },
            "room_humid": {
                "type": "EnvironmentSensor",
                "data": {
                    "name": "room_humid",
                    "current_value": 40,
                    "unit": "%"
                },
                "health": {
                    "online": True,
                    "fault": False,
                    "reason": ""
                }
            },
            "motion": {
                "type": "MotionSensor",
                "data": {
                    "current_value": False
                },
                "health": {
                    "online": True,
                    "fault": False,
                    "reason": ""
                }
            }
        },
        "auth": "55555"
    }
    while True:
        async with request("POST", "http://moldy.mug.loafclan.org:47670/uplink", json=json) as resp:
            logging.info(f"Response: {await resp.text()}")
        await asyncio.sleep(5)


if __name__ == "__main__":
    asyncio.run(main())
