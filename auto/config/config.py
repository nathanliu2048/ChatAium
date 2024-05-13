"""Configuration class to store the state of bools for different scripts access."""
from __future__ import annotations

from pydantic import Field

from auto.core.configuration.schema import SystemSettings


class Config(SystemSettings, arbitrary_types_allowed=True):
    name: str = "Aium"
    description: str = "Default configuration for the Aium application."
    ########################
    # Application Settings #
    ########################

    debug_mode: bool = False
    authorise_key: str = "y"
    exit_key: str = "n"
    ############
    # Commands #
    ############
    # General
    disabled_command_categories: list[str] = Field(default_factory=list)
    openai_functions: bool = False
