# -*- coding: utf-8 -*-
# SPDX-FileCopyrightText: 2021-2026 Cryptnox SA
# SPDX-License-Identifier: LGPL-3.0-only OR LicenseRef-Commercial

"""
Module for endpoints that can be used for working with the Ethereum network
"""
import abc
from typing import List

from .. import validators

try:
    import enums
except ImportError:
    from ... import enums


class EndpointValidator(validators.Validator):
    """
    Validator to validate endpoints for the Ethereum network
    """
    def __init__(self, valid_values: str = None):
        valid_values = valid_values or "\n".join(cls.name for cls in Endpoint.__subclasses__())
        super().__init__(valid_values)

    def validate(self, value):
        if value not in [cls.name for cls in Endpoint.__subclasses__()]:
            raise validators.ValidationError("Invalid value")

        return value


class Endpoint(metaclass=abc.ABCMeta):
    """
    Abstract base class for interface for endpoint implementations
    """
    def __init__(self, network: enums.EthNetwork, api_key: str = ""):
        super().__init__()

        self.network = network
        self._api_key: str = api_key

    @staticmethod
    @property
    @abc.abstractmethod
    def available_networks() -> List[enums.EthNetwork]:
        """
        :return: Ethereum networks handled by the endpoint implementation
        :rtype: List[enums.EthNetwork]
        """

    @property
    @abc.abstractmethod
    def domain(self) -> str:
        """
        :return: Domain that is used by the endpoint implementation
        :rtype: str
        """

    @staticmethod
    @property
    @abc.abstractmethod
    def name() -> str:
        """
        :return: Name of the endpoint implementation
        :rtype: str
        """

    @property
    @abc.abstractmethod
    def provider(self) -> str:
        """
        :return: Full URL that can be used as Web3 provider
        :rtype: str
        """


class InfuraEndpoint(Endpoint):
    """
    Implementation of the Infura endpoint
    """
    name = "infura"

    available_networks = [x.name for x in enums.EthNetwork]

    def __init__(self, network: enums.EthNetwork, api_key: str = ""):
        super().__init__(network, api_key)
        if not self._api_key:
            raise ValueError("\nTo use the Ethereum network. Go to https://infura.io. Register "
                             "and get an API key. Set the API key with: eth config api_key")

    @property
    def domain(self) -> str:
        return f"{self.network.name.lower()}.infura.io/v3"

    @property
    def provider(self) -> str:
        return f"https://{self.domain}/{self._api_key}"


class CryptnoxEndpoint(Endpoint):
    """
    Implementation of the Cryptnox endpoint
    """
    name = "cryptnox"

    _NETWORK_MAPPING = {
        enums.EthNetwork.MAINNET: "ethereum",
        enums.EthNetwork.SEPOLIA: "sepolia",
    }

    available_networks = [x.name for x in _NETWORK_MAPPING.keys()]

    @property
    def domain(self) -> str:
        network_name = self._NETWORK_MAPPING.get(self.network, self.network.name.lower())
        return f"{network_name}.nodes.cryptnox.tech"

    @property
    def provider(self) -> str:
        return f"https://{self.domain}"


class PublicNodeEndpoint(Endpoint):
    """
    Implementation of the PublicNode public RPC endpoint (free, no API key required)
    """
    name = "publicnode"

    _NETWORK_MAPPING = {
        enums.EthNetwork.MAINNET: "ethereum",
        enums.EthNetwork.SEPOLIA: "ethereum-sepolia",
    }

    available_networks = [x.name for x in _NETWORK_MAPPING.keys()]

    @property
    def domain(self) -> str:
        network_name = self._NETWORK_MAPPING.get(self.network, self.network.name.lower())
        return f"{network_name}.publicnode.com"

    @property
    def provider(self) -> str:
        return f"https://{self.domain}"


class DirectEndpoint:
    def __init__(self, url: str, network: enums.EthNetwork):
        self.network = network
        self.url = url

    @property
    def provider(self) -> str:
        return self.url


def factory(endpoint: str, network: enums.EthNetwork, api_key: str = "") -> Endpoint:
    """
    Factory method for Endpoint instances

    :param endpoint: Name of the endpoint to use
    :type: str
    :param network: Ethereum network to use
    :type: enums.EthNetwork
    :param api_key: API key to use on the endpoint
    :type: str

    :return: Return an Endpoint instance that can be used to get the urls
    :rtype: Endpoint

    :raises ValueError: In case endpoint with endpoint name wasn't found
    """
    if isinstance(network, str):
        network = enums.EthNetwork[network.upper()]

    for cls in Endpoint.__subclasses__():
        try:
            if cls.name == endpoint:
                return cls(network, api_key)
        except KeyError:
            continue

    raise ValueError("Endpoint not valid")
