# -*- coding: utf-8 -*-
"""
Module for signing messages with Windows Hello.
"""

import asyncio

from winsdk.windows.security.credentials import (
    KeyCredentialManager,
    KeyCredentialCreationOption,
    KeyCredentialStatus,
    KeyCredential
)
from winsdk.windows.security.cryptography import (
    CryptographicBuffer
)

from .exceptions import (
    CanceledException,
    NotFoundException,
    NotSupportedException,
    UnknownErrorException,
    UserPrefersPasswordException,
    SecurityDeviceLockedException,
    WindowsHelloExceptions
)


def delete(name: str) -> None:
    """
    Delete the key from Windows Hello

    :param str name: name of the slot
    """
    asyncio.run(_delete(name))


def get_public_key(name: str) -> bytearray:
    """
    Get public key from Windows Hello

    :return: public key
    :rtype: bytearray
    """
    return asyncio.run(_public_key(name))


def sign(name: str, message_to_sign: str) -> bytearray:
    """
    Sign given message with Windows Hello

    :param str name: name of the slot
    :param str message_to_sign: message that needs to be signed

    :return: Dictionary with public key and signed message as byte array
    :rtype: bytearray
    """
    return asyncio.run(_sign(name, message_to_sign))


async def _delete(name: str):
    # TODO: Find out how to delete key
    pass


def _error_handle(status):
    if status == KeyCredentialStatus.UNKNOWN_ERROR:
        raise UnknownErrorException("An unknown error occurred.")
    if status == KeyCredentialStatus.NOT_FOUND:
        raise NotFoundException("The credential could not be found.")
    if status == KeyCredentialStatus.USER_CANCELED:
        raise CanceledException("The request was cancelled by the user.")
    if status == KeyCredentialStatus.USER_PREFERS_PASSWORD:
        raise UserPrefersPasswordException("The user prefers to enter a password.")
    if status == KeyCredentialStatus.SECURITY_DEVICE_LOCKED:
        raise SecurityDeviceLockedException("The security device was locked.")

    raise WindowsHelloExceptions('Unknown error occurred')


async def _get_user_credentials(account_id: str) -> KeyCredential:
    key_credential_available = await KeyCredentialManager.is_supported_async()
    if not key_credential_available:
        raise NotSupportedException

    key_result = await KeyCredentialManager.open_async(account_id)

    if key_result.status == KeyCredentialStatus.SUCCESS:
        return key_result.credential

    key_result = await KeyCredentialManager.request_create_async(
        account_id, KeyCredentialCreationOption.FAIL_IF_EXISTS)

    if key_result.status == KeyCredentialStatus.SUCCESS:
        return key_result.credential

    _error_handle(key_result.status)
    return None


async def _public_key(name: str) -> bytearray:
    user_key = await _get_user_credentials(name)
    public_key = CryptographicBuffer.encode_to_hex_string(user_key.retrieve_public_key())

    return bytearray.fromhex(public_key)


async def _sign(name, message_to_sign: str) -> bytearray:
    message = CryptographicBuffer.decode_from_hex_string(message_to_sign)
    user_key = await _get_user_credentials(name)
    sign_result = await user_key.request_sign_async(message)

    if sign_result.status == KeyCredentialStatus.SUCCESS:
        signature = CryptographicBuffer.encode_to_hex_string(sign_result.result)
        return bytearray.fromhex(signature)

    _error_handle(sign_result.status)

    return bytearray()
