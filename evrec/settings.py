import tomllib

from pydantic_settings import BaseSettings

DEFAULT_MQTT_RECONNECT_INTERVAL = 5


class Settings(BaseSettings):
    clients_database: str
    mqtt_broker: str | None
    mqtt_topic_read: str
    mqtt_topic_write: str | None
    mqtt_reconnect_interval: int = DEFAULT_MQTT_RECONNECT_INTERVAL
    schema_validation: bool = False

    @classmethod
    def from_file(cls, filename: str):
        with open(filename, "rb") as fp:
            data = tomllib.load(fp)

        return cls(
            clients_database=data.get("CLIENTS_DATABASE", "clients"),
            mqtt_broker=data.get("MQTT_BROKER"),
            mqtt_topic_read=data.get("MQTT_TOPIC_READ", "events/up/#"),
            mqtt_topic_write=data.get("MQTT_TOPIC_WRITE"),
            mqtt_reconnect_interval=data.get(
                "MQTT_RECONNECT_INTERVAL", DEFAULT_MQTT_RECONNECT_INTERVAL
            ),
            schema_validation=data.get("SCHEMA_VALIDATION", False),
        )
