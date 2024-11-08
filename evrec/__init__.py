from importlib.metadata import version

__version__ = version("evrec")

try:
    from .buildinfo import __commit__, __timestamp__

    __verbose_version__ = f"{__version__} ({__commit__})"
except ModuleNotFoundError:
    __verbose_version__ = __version__
    __commit__ = None
    __timestamp__ = None
    pass
