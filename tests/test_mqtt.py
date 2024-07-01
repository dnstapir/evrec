from evrec.server import EvrecServer
from evrec.settings import MQTT, Settings


def test_server():
    settings = Settings(
        clients_database="clients", mqtt=MQTT(topic_read="read", topic_write="write")
    )
    _ = EvrecServer(settings)
