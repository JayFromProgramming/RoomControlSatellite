import asyncio

import aiohttp
from aiohttp import web

from Modules.RoomModule import RoomModule
from loguru import logger as logging
import netifaces


def get_host_names(filter_local=True):
    """
    Gets all the ip addresses that can be bound to
    """
    interfaces = []
    for interface in netifaces.interfaces():
        try:
            if netifaces.AF_INET in netifaces.ifaddresses(interface):
                for link in netifaces.ifaddresses(interface)[netifaces.AF_INET]:
                    if filter_local:
                        if link["addr"] != "" and not link["addr"].startswith("127.") \
                                and not link["addr"].startswith("172."):
                            interfaces.append(link["addr"])
                    else:
                        if link["addr"] != "":
                            interfaces.append(link["addr"])
        except Exception as e:
            logging.debug(f"Error getting interface {interface}: {e}")
            pass
    return interfaces


class LinkHost(RoomModule):
    is_webserver = True
    host_address = "moldy.mug.loafclan.org"

    def __init__(self, room_controller):
        super().__init__(room_controller)
        self.app = web.Application()
        self.app.add_routes([web.post('/downlink', self.downlink),
                             web.get('/uplink', self.uplink)])

        self.room_modules = []
        self.room_objects = []

        self.session = aiohttp.ClientSession()

        self.webserver_address = get_host_names()
        self.webserver_port = 47670

        self.runner = web.AppRunner(self.app)

        asyncio.create_task(self.main())

    async def get_site(self):
        await self.runner.setup()
        site = web.TCPSite(self.runner, self.webserver_address, self.webserver_port)
        return site

    @staticmethod
    def generate_object_payload(room_object):
        return {
            "type": room_object.object_type,
            "data": room_object.get_values(),
            "health": room_object.get_health()
        }

    def generate_payload(self):
        return {
            "name": self.room_controller.name,
            "current_ip": self.webserver_address,
            "objects":
                {obj.object_name: self.generate_object_payload(obj)
                 for obj in self.room_controller.get_all_objects()},
            "auth": self.room_controller.auth
        }

    async def main(self):
        logging.info("Starting uplink loop")
        while True:
            try:
                logging.info("Sending uplink")
                print(self.generate_payload())
                async with self.session.post(f"http://{self.host_address}:47670/uplink",
                                             json=self.generate_payload()) as response:
                    if response.status != 200:
                        logging.warning(f"Failed to send uplink: {response.status}")
                    else:
                        logging.info("Uplink sent")
            except Exception as e:
                logging.error(f"Error sending uplink: {e}")
                logging.exception(e)
            finally:
                await asyncio.sleep(5)

    def fire_event(self, room_object, event_name, *args, **kwargs):
        logging.info(f"Firing event {event_name} for {room_object.object_name}")
        asyncio.create_task(self.send_event(room_object, event_name, *args, **kwargs))

    async def send_event(self, room_object, event_name, *args, **kwargs):
        try:
            async with self.session.post(f"http://{self.host_address}:47670/event",
                                         json={"name": room_object.object_name,
                                               "current_ip": self.webserver_address,
                                               "object": room_object.object_name,
                                               "event": event_name,
                                               "args": args,
                                               "kwargs": kwargs,
                                               "auth": self.room_controller.auth}) as response:
                if response.status != 200:
                    logging.warning(f"Failed to send event: {response.status}")
                else:
                    logging.info("Event sent")
        except Exception as e:
            logging.error(f"Error sending event: {e}")
            logging.exception(e)


    async def downlink(self, request):
        data = await request.json()
        logging.info(f"Received downlink: {data}")
        return web.Response(text="OK")

    async def uplink(self, request):
        logging.info(f"Received uplink")
        return web.Response(text="OK")
