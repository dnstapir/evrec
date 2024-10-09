import argparse
import asyncio
import json
import logging
import logging.config
from pathlib import Path

import aiomqtt
from jwcrypto.common import JWKeyNotFound
from jwcrypto.jwk import JWK, JWKSet
from jwcrypto.jws import JWS, InvalidJWSSignature
from paho.mqtt.packettypes import PacketTypes
from paho.mqtt.properties import Properties

from . import __verbose_version__
from .settings import Settings
from .validator import MessageValidator

logger = logging.getLogger(__name__)

LOGGING_RECORD_CUSTOM_FORMAT = {
    "time": "asctime",
    # "Created": "created",
    # "RelativeCreated": "relativeCreated",
    "name": "name",
    # "Levelno": "levelno",
    "levelname": "levelname",
    "process": "process",
    "thread": "thread",
    # "threadName": "threadName",
    # "Pathname": "pathname",
    # "Filename": "filename",
    # "Module": "module",
    # "Lineno": "lineno",
    # "FuncName": "funcName",
    "message": "message",
}

LOGGING_CONFIG_JSON = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "json": {
            "class": "evrec.logging.JsonFormatter",
            "format": LOGGING_RECORD_CUSTOM_FORMAT,
        },
    },
    "handlers": {
        "json": {"class": "logging.StreamHandler", "formatter": "json"},
    },
    "root": {"handlers": ["json"], "level": "DEBUG"},
}


TEST_PAYLOAD = '{"payload":"eyJmbGFncyI6MzMxNTIsInFjbGFzcyI6MSwicW5hbWUiOiJpMi1vd3ppcmVzbXZqdmttcnd2YXhjYmNpZWlza2JzbmUuaW5pdC5jZWRleGlzLXJhZGFyLm5ldC4iLCJxdHlwZSI6MSwidGltZXN0YW1wIjoiMjAyNC0wNi0xMVQxNTo1NTowMCswMjowMCIsInR5cGUiOiJuZXdfcW5hbWUiLCJ2ZXJzaW9uIjowfQ","protected":"eyJhbGciOiJFUzI1NiJ9","signature":"JQy6bsdGA-7V1FGGzWDvsMpyeVgwR0U1ZqTGugTalOfrIVYk3UcmFhS6oY6pWsqkyAlKjQ2gNkC-hohAshl5Ow"}'


class EvrecServer:
    def __init__(self, settings: Settings):
        self.logger = logging.getLogger(__name__).getChild(self.__class__.__name__)
        self.settings = settings
        if self.settings.mqtt.topic_write is None:
            self.logger.warning("Not publishing verified messages")
        self.clients_keys = self.get_clients_keys()
        self.message_validator = MessageValidator()

    @classmethod
    def factory(cls):
        logger.info("Starting Event Receiver version %s", __verbose_version__)
        return cls(settings=Settings())

    def get_clients_keys(self) -> JWKSet:
        res = JWKSet()
        for filename in Path(self.settings.clients_database).glob("*.pem"):
            with open(filename, "rb") as fp:
                key = JWK.from_pem(fp.read())
                key.kid = filename.name.removesuffix(".pem")
                self.logger.debug("Adding key kid=%s (%s)", key.kid, key.thumbprint())
                res.add(key)
        return res

    async def run(self):
        while True:
            try:
                async with aiomqtt.Client(
                    hostname=self.settings.mqtt.broker.host,
                    port=self.settings.mqtt.broker.port,
                    username=self.settings.mqtt.broker.username,
                    password=self.settings.mqtt.broker.password,
                ) as client:
                    logging.info("MQTT connected to %s", self.settings.mqtt.broker)
                    await client.subscribe(self.settings.mqtt.topic_read)

                    async for message in client.messages:
                        self.logger.debug("Received message on %s", message.topic)
                        try:
                            jws = JWS()
                            jws.deserialize(message.payload)
                            key = verify_jws_with_keys(jws, self.clients_keys)
                            if self.settings.schema_validation:
                                self.message_validator.validate_message(str(message.topic), jws.objects["payload"])
                            if self.settings.mqtt.topic_write:
                                await self.handle_payload(client, message, jws, key)
                            else:
                                self.logger.debug("Not publishing verified message")
                        except JWKeyNotFound:
                            self.logger.warning("Dropping unverified message on %s", message.topic)
                        except Exception as exc:
                            self.logger.error(
                                "Error parsing message on %s",
                                message.topic,
                                exc_info=exc,
                            )
            except aiomqtt.MqttError:
                logging.error(
                    "MQTT connection lost; Reconnecting in %d seconds...",
                    self.settings.mqtt.reconnect_interval,
                )
                await asyncio.sleep(self.settings.mqtt.reconnect_interval)

    async def handle_payload(
        self,
        client: aiomqtt.Client,
        message: aiomqtt.client.Message,
        jws: JWS,
        key: JWK,
    ) -> None:
        new_topic = f"{self.settings.mqtt.topic_write}/{message.topic}"
        properties = Properties(PacketTypes.PUBLISH)
        properties.UserProperty = [("kid", key.kid), ("thumbprint", key.thumbprint())]
        await client.publish(
            topic=new_topic,
            payload=jws.objects["payload"],
            qos=message.qos,
            retain=message.retain,
            properties=properties,
        )
        self.logger.info("Published verified message from %s on %s", key.kid, new_topic)


def verify_jws_with_keys(jws: JWS, keys: JWKSet) -> JWK:
    """Verify JWS using keys and return key (or raise JWKeyNotFound)"""
    protected_header = json.loads(jws.objects["protected"])
    if kid := protected_header.get("kid"):
        logger.debug("Signature by kid=%s", kid)
    else:
        logger.debug("Signature by unknown key")
    for key in keys.get_keys(kid) or keys:
        try:
            jws.verify(key=key)
            return key
        except InvalidJWSSignature:
            pass
    raise JWKeyNotFound


def main() -> None:
    """Main function"""

    parser = argparse.ArgumentParser(description="Event Receiver")

    parser.add_argument("--debug", action="store_true", help="Enable debugging")
    parser.add_argument("--version", action="store_true", help="Show version")

    args = parser.parse_args()

    if args.version:
        print(f"Event Receiver version {__verbose_version__}")
        return

    logging.config.dictConfig(LOGGING_CONFIG_JSON)

    if args.debug:
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig(level=logging.INFO)

    app = EvrecServer.factory()

    asyncio.run(app.run())


if __name__ == "__main__":
    main()
