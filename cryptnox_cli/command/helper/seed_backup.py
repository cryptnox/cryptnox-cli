"""
Module for secure seed backup and recovery functionality using
AWS KMS and Secrets Manager services. It handles encryption, storage,
and retrieval of sensitive seed data with proper key management.
"""

import base64
import logging
import secrets

import boto3
from botocore.exceptions import ClientError
from cryptography.fernet import Fernet

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

store_secret_name = ""

bseed = base64.urlsafe_b64encode(secrets.token_bytes(64))

NUM_BYTES_FOR_LEN = 4
ACCESS_KEY = ""
SECRET_KEY = ""
key = ""

session = boto3.Session(
    aws_access_key_id=ACCESS_KEY,
    aws_secret_access_key=SECRET_KEY,
    region_name="us-east-2",
)


def create_data_key(session, cmk_id, key_spec="AES_256"):
    """Generate a data key to use when encrypting and decrypting data

    :param cmk_id: KMS CMK ID or ARN under which to generate and encrypt the
        data key.
    :param key_spec: Length of the data encryption key. Supported values:
        'AES_128': Generate a 128-bit symmetric key
        'AES_256': Generate a 256-bit symmetric key
    :return: Tuple(EncryptedDataKey, PlaintextDataKey) where:
        EncryptedDataKey: Encrypted CiphertextBlob data key as binary string
        PlaintextDataKey: Plaintext base64-encoded data key as binary string
    :return: Tuple(None, None) if error
    """
    # Create data key
    kms_client = session.client("kms")

    try:
        response = kms_client.generate_data_key(KeyId=cmk_id, KeySpec=key_spec)
        """at this stage it returns a dictionary with lots of stuff"""
    except ClientError as e:
        logging.error(e)
        return None, None

    # Return the encrypted and plaintext data key
    """there it returns a tuple with data corresponding to the above keys of the dictionary"""
    return response["CiphertextBlob"], base64.b64encode(response["Plaintext"])


def encrypt_data(data, key):
    # Encrypt the data
    f = Fernet(key)
    data_encrypted = f.encrypt(data)
    """returns a base64.urlsafe_b64encode byte object """
    return data_encrypted


def decrypt_data_key(session, data_key_encrypted):
    """Decrypt an encrypted data key"""

    # Decrypt the data key
    kms_client = session.client("kms")
    response = kms_client.decrypt(CiphertextBlob=data_key_encrypted)

    # Return plaintext base64-encoded binary data key
    return response["Plaintext"]


def decrypt_data(data, key):
    # Decrypt the rest of the file
    f = Fernet(key)
    data_decrypted = f.decrypt(data)

    """returns a base64.urlsafe_b64encode byte object """

    return data_decrypted


def create_secret(session, secret_value, name):
    """
    Creates a new secret. The secret value can only be bytes here.

    :param name: The name of the secret to create.
    :param secret_value: The value of the secret.
    :return: Metadata about the newly created secret.
    """
    client = session.client("secretsmanager")
    try:
        kwargs = {"Name": name}
        kwargs["SecretBinary"] = secret_value
        response = client.create_secret(**kwargs)
        # Security: Only log that a secret was created, not the name which might be sensitive
        logger.info("Created secret successfully.")
    except ClientError:
        # Security: Don't log secret name in exception as it may contain sensitive info
        logger.exception("Couldn't create secret.")
        raise
    else:
        return response


def get_secret(session, store_secret_name):
    secret_name = store_secret_name
    client = session.client("secretsmanager")

    try:
        get_secret_value_response = client.get_secret_value(SecretId=secret_name)
    except ClientError as e:
        if e.response["Error"]["Code"] == "DecryptionFailureException":
            # Secrets Manager can't decrypt the protected secret text using the provided KMS key.
            # Deal with the exception here, and/or rethrow at your discretion.
            raise e
        elif e.response["Error"]["Code"] == "InternalServiceErrorException":
            # An error occurred on the server side.
            # Deal with the exception here, and/or rethrow at your discretion.
            raise e
        elif e.response["Error"]["Code"] == "InvalidParameterException":
            # You provided an invalid value for a parameter.
            # Deal with the exception here, and/or rethrow at your discretion.
            raise e
        elif e.response["Error"]["Code"] == "InvalidRequestException":
            # You provided a parameter value that is not valid for the current state of the resource.
            # Deal with the exception here, and/or rethrow at your discretion.
            raise e
        elif e.response["Error"]["Code"] == "ResourceNotFoundException":
            # We can't find the resource that you asked for.
            # Deal with the exception here, and/or rethrow at your discretion.
            raise e
    else:
        # Decrypts secret using the associated KMS CMK.
        # Depending on whether the secret is a string or binary, one of these
        # fields will be populated.
        decoded_binary_secret = get_secret_value_response["SecretBinary"]
        return decoded_binary_secret


if __name__ == "__main__":
    logger.info("Creating random seed in bytes")

    # CREATING A DATA KEY
    data_key_encrypted, data_key_plaintext = create_data_key(session, key)
    if data_key_encrypted is None:
        logger.error("Failed to create data key")
        raise SystemExit(1)

    logger.info("Data key created successfully")

    # ENCRYPT THE SEED WITH DATA KEY AND DECODE INTO BYTES
    encrypted_data_b64_decoded = base64.urlsafe_b64decode(
        encrypt_data(bseed, data_key_plaintext)
    )

    #  FOR SECRET CONCATENATION, NEEDS LENGTH OF ENCRYPTED KEY STORED INTO FOUR BYTES
    data_key_encrypted_length = len(data_key_encrypted).to_bytes(
        NUM_BYTES_FOR_LEN, byteorder="big"
    )

    # PREPARING SECRET TO STORE = CONCATENATION IN BYTES
    secret_to_store = (
        data_key_encrypted_length + data_key_encrypted + encrypted_data_b64_decoded
    )

    logger.info("Concatenated secret created (%d bytes)", len(secret_to_store))

    # NOW STORING ENCRYPTED SECRET WITH SECRET MANAGER
    create_secret(session, secret_to_store, store_secret_name)

    # RETRIEVING ENCRYPTED SECRET
    retrieved_encrypted_secret = get_secret(session, store_secret_name)

    # RETRIEVING ENCRYPTED KEY LENGTH PLUS "NUM_BYTES_FOR_LEN"
    from_secret_data_key_encrypted_len = (
        int.from_bytes(retrieved_encrypted_secret[:NUM_BYTES_FOR_LEN], byteorder="big")
        + NUM_BYTES_FOR_LEN
    )

    # RETRIEVING ENCRYPTED KEY
    from_secret_data_key_encrypted = retrieved_encrypted_secret[
        NUM_BYTES_FOR_LEN:from_secret_data_key_encrypted_len
    ]

    # DECRYPTING ENCRYPTED KEY
    r_data_key_plaintext = base64.b64encode(
        decrypt_data_key(session, from_secret_data_key_encrypted)
    )

    # RETRIEVING ENCRYPTED DATA
    data_to_decrypt = base64.urlsafe_b64encode(
        retrieved_encrypted_secret[from_secret_data_key_encrypted_len:]
    )

    decrypted_seed = decrypt_data(data_to_decrypt, r_data_key_plaintext)

    logger.info("Seed backup round-trip completed successfully")
