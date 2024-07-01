from typing import Annotated, Tuple, Type

from pydantic import BaseModel, Field, UrlConstraints
from pydantic_core import Url
from pydantic_settings import (
    BaseSettings,
    PydanticBaseSettingsSource,
    SettingsConfigDict,
    TomlConfigSettingsSource,
)

MqttUrl = Annotated[
    Url,
    UrlConstraints(
        allowed_schemes=["mqtt", "mqtts"], default_port=1883, host_required=True
    ),
]


class MQTT(BaseModel):
    broker: MqttUrl
    username: str | None = None
    password: str | None = None
    topic_read: str
    topic_write: str | None = None
    reconnect_interval: int = Field(default=5)


class Settings(BaseSettings):
    mqtt: MQTT
    clients_database: str
    schema_validation: bool = False

    model_config = SettingsConfigDict(toml_file="evrec.toml")

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: Type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> Tuple[PydanticBaseSettingsSource, ...]:
        return (TomlConfigSettingsSource(settings_cls),)
