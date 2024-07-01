from evrec.server import EvrecServer
from evrec.settings import Settings


def test_server():
    settings = Settings()
    _ = EvrecServer(settings)
