import json
import logging
from pathlib import Path
from typing import Any, Optional

from exceptions import ArgumentParamsException
from logger import get_logger

logger: logging.Logger = get_logger("app_logger")


class ParamsParser:
    def __init__(self, params_json_path: str) -> None:
        """
        Initialize the ParamsParser.

        Args:
            params_json_path (str): Path to the params JSON file.
        """
        self.params_json_path: Path = Path(params_json_path)
        self.params: dict[str, Any] = {}

    def parse(self) -> None:
        """
        Parse the params JSON file.
        """
        if not self.params_json_path.is_file():
            raise ArgumentParamsException(f"Params file does not exist: {self.params_json_path.as_posix()}")

        try:
            with open(self.params_json_path, "r", encoding="utf-8") as file:
                json_data: Any = json.load(file)
        except (json.JSONDecodeError, UnicodeDecodeError) as e:
            raise ArgumentParamsException(f"Params file is not valid JSON: {e}")

        if isinstance(json_data, list):
            for item in json_data:
                if isinstance(item, dict):
                    self._parse_dictionary_item(item)
                else:
                    logger.error(f"Not expecting '{type(item)}' under list for params.")
        else:
            logger.error(f"Invalid json data: {type(json_data)}")

    def get(self, name: str) -> Any:
        """
        Get value of a required parameter.

        Args:
            name (str): Name of the parameter.

        Returns:
            Value of the parameter.
        """
        if name not in self.params:
            raise ArgumentParamsException(f"Parameter '{name}' is missing in params file.")
        return self.params[name]

    def _parse_dictionary_item(self, dict_item: dict[Any, Any]) -> None:
        """
        Parse a dictionary item.

        Args:
            dict_item (dict[Any, Any]): Dictionary item to parse.
        """
        item_name: Optional[str] = None
        item_value: Optional[Any] = None
        for key, value in dict_item.items():
            if key == "name":
                item_name = value
            elif key == "value":
                item_value = value
        if item_name is not None and item_value is not None:
            self.params[item_name] = item_value
        else:
            logger.error(f"Invalid param: {dict_item}")
