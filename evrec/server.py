import argparse
import asyncio
import json
import logging

import aiomqtt
from jwcrypto.common import JWKeyNotFound
from jwcrypto.jwk import JWK, JWKSet
from jwcrypto.jws import JWS, InvalidJWSSignature
from paho.mqtt.packettypes import PacketTypes
from paho.mqtt.properties import Properties

from dnstapir.key_cache import key_cache_from_settings
from dnstapir.key_resolver import key_resolver_from_client_database
from dnstapir.logging import setup_logging

from . import __verbose_version__
from .keys import EvrecJWKSet
from .settings import Settings
from .validator import MessageValidator

logger = logging.getLogger(__name__)


class EvrecServer:
    def __init__(self, settings: Settings):
        self.logger = logging.getLogger(__name__).getChild(self.__class__.__name__)
        self.settings = settings
        if self.settings.mqtt.topic_write is None:
            self.logger.warning("Not publishing verified messages")
        key_cache = key_cache_from_settings(self.settings.key_cache) if self.settings.key_cache else None
        key_resolver = key_resolver_from_client_database(
            client_database=self.settings.clients_database, key_cache=key_cache
        )
        self.clients_keyset = EvrecJWKSet(key_resolver=key_resolver)
        self.message_validator = MessageValidator()

    @classmethod
    def factory(cls):
        logger.info("Starting Event Receiver version %s", __verbose_version__)
        return cls(settings=Settings())

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
                            key = verify_jws_with_keys(jws, self.clients_keyset)
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
        for key in keys.get_keys(kid):
            try:
                jws.verify(key=key)
                if not hasattr(key, "kid"):
                    key.kid = kid
                return key
            except InvalidJWSSignature:
                pass
    else:
        logger.debug("Signature without kid")
    raise JWKeyNotFound


def main() -> None:
    """Main function"""

    parser = argparse.ArgumentParser(description="Event Receiver")

    parser.add_argument("--log-json", action="store_true", help="Enable JSON logging")
    parser.add_argument("--debug", action="store_true", help="Enable debugging")
    parser.add_argument("--version", action="store_true", help="Show version")

    args = parser.parse_args()

    if args.version:
        print(f"Event Receiver version {__verbose_version__}")
        return

    setup_logging(json_logs=args.log_json, log_level="DEBUG" if args.debug else "INFO")

    app = EvrecServer.factory()

    asyncio.run(app.run())


if __name__ == "__main__":
    main()
