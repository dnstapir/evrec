from evrec.server import EvrecServer
from evrec.settings import Settings


def test_server():
    settings = Settings(
        clients_database="clients",
        mqtt_broker=None,
        mqtt_topic_read="read",
        mqtt_topic_write="write",
    )
    _ = EvrecServer(settings)
