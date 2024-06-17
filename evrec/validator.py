import json
import logging
import os
from pathlib import Path

import jsonschema

SCHEMA_DIR = os.path.dirname(__file__) + "/schema"


class MessageValidator:
    """MQTT Message Validator"""

    VALIDATOR = jsonschema.Draft202012Validator

    def __init__(self) -> None:
        self.logger = logging.getLogger(__name__).getChild(self.__class__.__name__)
        self.schemas: dict[str, jsonschema.Validator] = {}
        for filename in Path(SCHEMA_DIR).glob("*.json"):
            with open(filename) as fp:
                schema = json.load(fp)
            name = filename.name.removesuffix(".json")
            self.schemas[name] = self.VALIDATOR(schema)
            self.logger.debug("Loaded schema %s from %s", name, filename)

    def validate_message(self, topic: str, payload: bytes) -> None:
        """Validate message against schema based on content type"""
        content = json.loads(payload)
        content_type = content["type"]
        if schema := self.schemas.get(content_type):
            schema.validate(content)
            self.logger.debug(
                "Message on %s validated against schema %s", topic, content_type
            )
