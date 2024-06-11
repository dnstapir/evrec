import argparse
import asyncio
import logging
import logging.config
import os
from pathlib import Path
from typing import Optional

import aiomqtt
from jwcrypto.common import JWKeyNotFound
from jwcrypto.jwk import JWK, JWKSet
from jwcrypto.jws import JWS, InvalidJWSSignature
from paho.mqtt.packettypes import PacketTypes
from paho.mqtt.properties import Properties

from . import __verbose_version__
from .settings import Settings

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
        self.settings = settings
        if self.settings.mqtt_topic_write is None:
            logger.warning("Not publishing verified messages")
        self.clients_keys = self.get_clients_keys()

    @staticmethod
    def create_settings(config_filename: Optional[str]):
        config_filename = config_filename or os.environ.get("EVREC_CONFIG")
        if config_filename:
            logger.info("Reading configuration from %s", config_filename)
            return Settings.from_file(config_filename)
        else:
            return Settings()

    @classmethod
    def factory(cls, config_filename: Optional[str]):
        logger.info("Starting Event Receiver version %s", __verbose_version__)
        return cls(settings=cls.create_settings(config_filename))

    def get_clients_keys(self) -> JWKSet:
        res = JWKSet()
        for filename in Path(self.settings.clients_database).glob("*.pem"):
            with open(filename, "rb") as fp:
                key = JWK.from_pem(fp.read())
                key.kid = filename.name.removesuffix(".pem")
                logger.debug("Adding key kid=%s (%s)", key.kid, key.thumbprint())
                res.add(key)
        return res

    async def run(self):
        async with aiomqtt.Client(self.settings.mqtt_broker) as client:
            await client.subscribe(self.settings.mqtt_topic_read)

            async for message in client.messages:
                try:
                    jws = JWS()
                    jws.deserialize(message.payload)
                    key = verify_jws_with_keys(jws, self.clients_keys)
                    logger.info(
                        "Verified message from %s on %s", key.kid, message.topic
                    )
                    if self.settings.mqtt_topic_write:
                        await self.handle_payload(client, message, jws, key)
                    else:
                        logger.debug("Not publishing verified message")
                except JWKeyNotFound:
                    logger.warning("Dropping unverified message on %s", message.topic)
                except Exception as exc:
                    logger.error(
                        "Error parsing message on %s", message.topic, exc_info=exc
                    )

    async def handle_payload(
        self,
        client: aiomqtt.Client,
        message: aiomqtt.client.Message,
        jws: JWS,
        key: JWK,
    ) -> None:
        new_topic = f"{self.settings.mqtt_topic_write}/{message.topic}"
        properties = Properties(PacketTypes.PUBLISH)
        properties.UserProperty = [("kid", key.kid), ("thumbprint", key.thumbprint())]
        await client.publish(
            topic=new_topic,
            payload=jws.objects["payload"],
            qos=message.qos,
            retain=message.retain,
            properties=properties,
        )
        logger.info("Published verified message from %s on %s", key.kid, new_topic)


def verify_jws_with_keys(jws: JWS, keys: JWKSet) -> JWK:
    """Verify JWS using keys and return key (or raise JWKeyNotFound)"""
    for key in keys:
        try:
            jws.verify(key=key)
            return key
        except InvalidJWSSignature:
            pass
    raise JWKeyNotFound


def main() -> None:
    """Main function"""

    parser = argparse.ArgumentParser(description="Event Receiver")

    parser.add_argument("--config", metavar="filename", help="Configuration file")
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

    app = EvrecServer.factory(args.config)

    asyncio.run(app.run())


if __name__ == "__main__":
    main()
