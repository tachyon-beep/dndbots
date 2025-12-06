"""Built-in output plugins."""

from dndbots.output.plugins.console import ConsolePlugin
from dndbots.output.plugins.jsonlog import JsonLogPlugin
from dndbots.output.plugins.callback import CallbackPlugin

__all__ = ["ConsolePlugin", "JsonLogPlugin", "CallbackPlugin"]
