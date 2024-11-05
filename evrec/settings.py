from typing import Annotated, Tuple, Type

from pydantic import BaseModel, DirectoryPath, Field, UrlConstraints
from pydantic_core import Url
from pydantic_settings import BaseSettings, PydanticBaseSettingsSource, SettingsConfigDict, TomlConfigSettingsSource

from dnstapir.key_cache import KeyCacheSettings

MqttUrl = Annotated[
    Url,
    UrlConstraints(allowed_schemes=["mqtt", "mqtts"], default_port=1883, host_required=True),
]


class MqttSettings(BaseModel):
    broker: MqttUrl = Field(default="mqtt://localhost")
    topic_read: str = Field(default="events/up/#")
    topic_write: str | None = None
    reconnect_interval: int = Field(default=5)


class RedisSettings(BaseModel):
    host: str = Field(description="Redis hostname")
    port: int = Field(description="Redis port", default=6379)


class Settings(BaseSettings):
    mqtt: MqttSettings = Field(default=MqttSettings())
    clients_database: DirectoryPath = Field(default="clients")
    schema_validation: bool = False
    key_cache: KeyCacheSettings | None = None

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
