# -*- coding: utf-8 -*-
"""
Module for defining validators
"""
import re
from abc import ABC, abstractmethod
from typing import Any


class ValidationError(Exception):
    """
    Exception for indicating that validation criteria are not met
    """


class Validator(ABC):
    """
    Validator class defining setters and getters
    """

    def __init__(self, valid_values: str = None):
        self.valid_values = valid_values
        self.name = None

    def __set_name__(self, owner, name):
        self.name = f"_{name}"

    def __get__(self, instance, instance_type=None):
        return getattr(instance, self.name)

    def __set__(self, instance, value):
        value = self.validate(value)
        setattr(instance, self.name, value)

    @abstractmethod
    def validate(self, value):
        """

        :param value: Evaluated value
        :return: None
        :raise ValidationError: Validation criteria not satisfied
        """


class AnyValidator(Validator):
    def validate(self, value):
        return value


class IntValidator(Validator):
    """
       Class for validating if value is integer
       """

    def __init__(self, max_value: int = None, min_value: int = None):
        self.max_value = max_value
        self.min_value = min_value
        super().__init__(None)

    def validate(self, value) -> int:
        if not is_int(value):
            raise ValidationError("Number must be integer")
        if self.min_value and self.max_value \
                and self.min_value > int(value) > self.max_value:
            raise ValidationError(f"Number must be integer larger than: "
                                  f"{self.min_value} and smaller "
                                  f"than {self.max_value}")
        return int(float(value))


class EnumValidator(Validator):
    """
    Class for validating if value is part of the enum
    """

    def __init__(self, current_enum):
        super().__init__("\n".join(value.name for value in current_enum))
        self.current_enum = current_enum

    def validate(self, value) -> None:
        value = value.upper()
        try:
            self.current_enum[value]
        except LookupError as error:
            raise ValidationError("Invalid value") from error
        return value


class UrlValidator(Validator):
    """
    Class for validating URLs
    """

    def validate(self, value: str) -> str:
        regex = re.compile(
            r'^(?:http|ftp)s?://'  # http:// or https://
            r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+(?:[A-Z]{2,6}\.?'
            r'|[A-Z0-9-]{2,}\.?)|'  # domain...
            r'localhost|'  # localhost...
            r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # ...or ip
            r'(?::\d+)?'  # optional port
            r'(?:/?|[/?]\S+)$', re.IGNORECASE)
        if re.match(regex, value) is None:
            raise ValidationError("Invalid value for the URL")
        return value


def is_int(value: Any) -> bool:
    value = str(value)
    if value[0] in ('-', '+'):
        return value[1:].isdigit()
    else:
        return value.isdigit()
