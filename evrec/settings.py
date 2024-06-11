import tomllib

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    clients_database: str
    mqtt_broker: str | None
    mqtt_topic_read: str
    mqtt_topic_write: str

    @classmethod
    def from_file(cls, filename: str):
        with open(filename, "rb") as fp:
            data = tomllib.load(fp)

        return cls(
            clients_database=data.get("CLIENTS_DATABASE", "clients"),
            mqtt_broker=data.get("MQTT_BROKER"),
            mqtt_topic_read=data.get("MQTT_TOPIC_READ", "events/up/#"),
            mqtt_topic_write=data.get("MQTT_TOPIC_WRITE", "verified"),
        )
