Command Line Interface
======================

The ``cryptnox`` command provides a comprehensive CLI for managing Cryptnox cards and performing cryptocurrency operations.

Installation
------------

After installing the cryptnox-cli package, the ``cryptnox`` command becomes available in your system:

.. code-block:: bash

   pip install cryptnox-cli

Basic Usage
-----------

.. code-block:: bash

   cryptnox [OPTIONS] COMMAND [ARGS]...

Global Options
--------------

.. option:: -v, --version

   Show the version and exit.

.. option:: --verbose

   Turn on logging for detailed output.

.. option:: -s, --serial SERIAL

   Serial number of the card to be used for the command.

.. option:: --port PORT

   Define port to enable remote feature.

Commands Overview
-----------------

Card Management Commands
~~~~~~~~~~~~~~~~~~~~~~~~

list
^^^^

List all connected Cryptnox cards.

.. code-block:: bash

   cryptnox list

init
^^^^

Initialize a Cryptnox card with owner information and PIN/PUK codes.

.. code-block:: bash

   cryptnox init [OPTIONS]

Options:
  - ``-e, --easy_mode``: Initialize card in easy mode (sets PIN and PUK to all zeros)

reset
^^^^^

Reset the card to factory defaults.

.. code-block:: bash

   cryptnox reset

**Warning:** This will erase all data on the card.

info
^^^^

Display default accounts information for the card.

.. code-block:: bash

   cryptnox info

Shows:
  - Card serial number and type
  - Ethereum and Bitcoin addresses
  - Public keys
  - Derivation information

cert
^^^^

Retrieve and display the manufacturer certificate from the card in a human-readable format.

.. code-block:: bash

   cryptnox cert

**Features:**
  - Retrieves the full manufacturer certificate from the card
  - Displays certificate details (Issuer, Subject, Validity, Public Key, Signature)
  - Human-readable format similar to ``openssl x509 -text``

Seed Management Commands
~~~~~~~~~~~~~~~~~~~~~~~~

seed chip
^^^^^^^^^

Generate new root key directly in the card's secure chip.

.. code-block:: bash

   cryptnox seed chip

**Note:** The seed never leaves the card and cannot be backed up.

seed dual
^^^^^^^^^

Generate the same seed on two cards for redundancy.

.. code-block:: bash

   cryptnox seed dual

**Requirements:** Two initialized Cryptnox cards

**Process:**
  1. Generate seed on first card
  2. Swap cards
  3. Load same seed on second card
  4. Results in two cards with identical keys

seed recover
^^^^^^^^^^^^

Recover a wallet from an existing BIP39 mnemonic phrase (12 or 24 words).

.. code-block:: bash

   cryptnox seed recover

**Input Required:**
  - Existing BIP39 mnemonic (12 or 24 words)
  - Optional: BIP39 passphrase (13th/25th word)

**Use Cases:**
  - Restoring existing wallet
  - Migrating wallet from another device
  - Recovering from backup mnemonic

**Important:** If the original wallet used a BIP39 passphrase, you **must** provide the same passphrase during recovery.

seed upload
^^^^^^^^^^^

Generate new random seed, upload to card, and display BIP39 mnemonic for backup.

.. code-block:: bash

   cryptnox seed upload

**Features:**
  - Generates new 32-byte random seed using card's hardware RNG
  - Converts to BIP39 mnemonic (12 or 24 words)
  - Optional: Add BIP39 passphrase (13th/25th word) for extra security
  - Displays mnemonic for manual backup

**Output:** The generated mnemonic phrase (save it securely!)

**Important:** If you use a BIP39 passphrase, you **must** remember it. It cannot be recovered.

Security Commands
~~~~~~~~~~~~~~~~~

change_pin
^^^^^^^^^^

Change the PIN code of the card.

.. code-block:: bash

   cryptnox change_pin

**Requirements:** Current PIN code

change_puk
^^^^^^^^^^

Change the PUK (PIN Unblocking Key) code of the card.

.. code-block:: bash

   cryptnox change_puk

**Requirements:** Current PUK code

unlock_pin
^^^^^^^^^^

Unlock a card with blocked PIN using the PUK code and set a new PIN.

.. code-block:: bash

   cryptnox unlock_pin

**Requirements:** PUK code

**Note:** PIN becomes blocked after multiple failed attempts.

Card Configuration
~~~~~~~~~~~~~~~~~~

card_conf
^^^^^^^^^

Show or modify card configuration settings.

.. code-block:: bash

   cryptnox card_conf [KEY] [VALUE]

**Available Settings:**

- ``pinless``: Enable/disable PIN-less path
- ``pin``: Enable/disable PIN authentication

**Values:** ``yes`` or ``no``

**Examples:**

.. code-block:: bash

   # Show current configuration
   cryptnox card_conf

   # Enable PIN-less path
   cryptnox card_conf pinless yes

   # Disable PIN-less path
   cryptnox card_conf pinless no

Bitcoin Commands
~~~~~~~~~~~~~~~~

btc send
^^^^^^^^

Send Bitcoin to an address.

.. code-block:: bash

   cryptnox btc send ADDRESS AMOUNT [OPTIONS]

**Arguments:**
  - ``ADDRESS``: Bitcoin address (P2PKH, P2SH, or Bech32)
  - ``AMOUNT``: Amount in BTC

**Options:**
  - ``-n, --network {mainnet,testnet}``: Network to use
  - ``-f, --fees SATOSHIS``: Transaction fees in satoshis per byte

**Example:**

.. code-block:: bash

   cryptnox btc send 1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa 0.001 -n mainnet -f 10

btc config
^^^^^^^^^^

View or modify Bitcoin configuration.

.. code-block:: bash

   cryptnox btc config [KEY] [VALUE]

**Settings:**
  - ``network``: mainnet or testnet
  - ``derivation``: Key derivation method

Ethereum Commands
~~~~~~~~~~~~~~~~~

eth send
^^^^^^^^

Send Ether (ETH) to an address.

.. code-block:: bash

   cryptnox eth send ADDRESS AMOUNT [OPTIONS]

**Arguments:**
  - ``ADDRESS``: Ethereum address (0x...)
  - ``AMOUNT``: Amount in ETH

**Options:**
  - ``-n, --network {mainnet,sepolia,goerli}``: Network to use
  - ``--price GWEI``: Gas price in Gwei
  - ``--limit GAS``: Gas limit

**Example:**

.. code-block:: bash

   cryptnox eth send 0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb 0.1 -n mainnet --price 20

eth config
^^^^^^^^^^

View or modify Ethereum configuration.

.. code-block:: bash

   cryptnox eth config [KEY] [VALUE]

**Settings:**
  - ``network``: mainnet, sepolia, or other networks
  - ``derivation``: Key derivation method
  - ``api_key``: Etherscan/Infura API key
  - ``endpoint``: RPC endpoint

ERC Token Commands
~~~~~~~~~~~~~~~~~~

eth erc20 init
^^^^^^^^^^^^^^

Initialize ERC-20 token contract for transactions.

.. code-block:: bash

   cryptnox eth erc20 init CONTRACT_ADDRESS [OPTIONS]

eth erc20 info
^^^^^^^^^^^^^^

Display information about configured ERC-20 tokens.

.. code-block:: bash

   cryptnox eth erc20 info

eth erc20 send
^^^^^^^^^^^^^^

Send ERC-20 tokens.

.. code-block:: bash

   cryptnox eth erc20 send TOKEN_ADDRESS RECIPIENT_ADDRESS AMOUNT [OPTIONS]

transfer
^^^^^^^^

Transfer ERC-20 or ERC-721 tokens.

.. code-block:: bash

   cryptnox transfer ADDRESS AMOUNT [OPTIONS]

**Options:**
  - ``--price GWEI``: Gas price
  - ``--limit GAS``: Gas limit

Configuration Commands
~~~~~~~~~~~~~~~~~~~~~~

config
^^^^^^

List or modify blockchain configurations.

.. code-block:: bash

   cryptnox config [SECTION] [KEY] [VALUE]

**Examples:**

.. code-block:: bash

   # Show all configuration
   cryptnox config

   # Show Ethereum configuration
   cryptnox config eth

   # Set Ethereum network
   cryptnox config eth network mainnet

   # Set Bitcoin derivation
   cryptnox config btc derivation DERIVE

History and Information
~~~~~~~~~~~~~~~~~~~~~~~

history
^^^^^^^

List performed signatures and transactions.

.. code-block:: bash

   cryptnox history [PAGE]

**Arguments:**
  - ``PAGE``: Page number to display (default: 1)

**Note:** Shows up to 148 entries, 25 per page.

Advanced Commands
~~~~~~~~~~~~~~~~~

get_xpub
^^^^^^^^

Get extended public key (xpub) for hierarchical deterministic wallets.

.. code-block:: bash

   cryptnox get_xpub [OPTIONS]

**Options:**
  - Derivation path
  - Key type

get_clearpubkey
^^^^^^^^^^^^^^^

Get clear (uncompressed) public key from the card.

.. code-block:: bash

   cryptnox get_clearpubkey [OPTIONS]

decrypt
^^^^^^^

Decrypt data using the card's private key.

.. code-block:: bash

   cryptnox decrypt [OPTIONS]

User Key Management
~~~~~~~~~~~~~~~~~~~

user_key list
^^^^^^^^^^^^^

List all configured user keys for authentication.

.. code-block:: bash

   cryptnox user_key list

user_key add
^^^^^^^^^^^^

Add a new user key for authentication (PIV card, Windows Hello).

.. code-block:: bash

   cryptnox user_key add TYPE [DESCRIPTION]

**Available Types:**
  - ``piv``: PIV-compatible smart card
  - ``hello``: Windows Hello (biometric)

**Example:**

.. code-block:: bash

   cryptnox user_key add piv "My PIV Key"

user_key delete
^^^^^^^^^^^^^^^

Delete a user key.

.. code-block:: bash

   cryptnox user_key delete TYPE

Server Mode
~~~~~~~~~~~

server
^^^^^^

Start a server or establish connection to a remote server.

.. code-block:: bash

   cryptnox server [OPTIONS]

**Options:**
  - ``--port PORT``: Server port (default: 5050)
  - ``--host HOST``: Server host (default: 0.0.0.0)

**Use Case:** Remote card access over network

Interactive Mode
----------------

Launch interactive CLI mode:

.. code-block:: bash

   cryptnox

In interactive mode, you can:
  - Execute commands without repeating ``cryptnox``
  - Use ``use`` command to switch between multiple cards
  - Use ``exit`` to quit

**Example Session:**

.. code-block:: text

   $ cryptnox
   Cryptnox CLI 1.0.3
   
   > list
   [Shows available cards]
   
   > info
   [Shows card information]
   
   > exit

BIP39 Passphrase Support
-------------------------

The ``seed recover`` and ``seed upload`` commands support BIP39 passphrases (also known as the 13th/25th word).

What is a BIP39 Passphrase?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

A BIP39 passphrase is an optional additional word that enhances security:
  - Acts as a "second factor" for your seed
  - Creates a completely different wallet from the same mnemonic
  - Must be remembered separately (not stored with the mnemonic)
  - Cannot be recovered if forgotten

Using BIP39 Passphrase
~~~~~~~~~~~~~~~~~~~~~~~

**During seed upload (new wallet):**

.. code-block:: bash

   cryptnox seed upload

The command will prompt:

.. code-block:: text

   Do you want to use a BIP39 passphrase? [y/N]

If you choose ``yes``:
  - Enter your desired passphrase
  - Confirm the passphrase
  - **Remember it!** You'll need it for recovery

**During seed recover (existing wallet):**

.. code-block:: bash

   cryptnox seed recover

If your wallet was created with a passphrase, you **must** provide the same passphrase when recovering.

**Important Notes:**
  - ⚠️ If you forget your passphrase, your funds are **permanently lost**
  - ✅ Same mnemonic + different passphrase = completely different wallet
  - ✅ Passphrase can be any UTF-8 string (including spaces and special characters)

Exit Codes
----------

The CLI returns the following exit codes:

- ``0``: Success
- ``-1``: Error occurred
- ``-2``: Card error or card not found

Error Handling
--------------

When errors occur:
  - Detailed error messages are displayed
  - Errors are logged to: ``~/.local/share/cryptnox-cli/error.log`` (Linux/macOS) or ``%LOCALAPPDATA%\\cryptnox\\cryptnox-cli\\error.log`` (Windows)
  - You can report errors to help improve the application

Examples
--------

**Initialize a new card:**

.. code-block:: bash

   cryptnox init

**Generate and upload a seed:**

.. code-block:: bash

   cryptnox seed upload

**Recover from existing mnemonic:**

.. code-block:: bash

   cryptnox seed recover

**Send Bitcoin:**

.. code-block:: bash

   cryptnox btc send 1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa 0.001 -n testnet

**Send Ethereum:**

.. code-block:: bash

   cryptnox eth send 0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb 0.1 -n mainnet

**View card info:**

.. code-block:: bash

   cryptnox info

**Change PIN:**

.. code-block:: bash

   cryptnox change_pin

See Also
--------

- :doc:`overview` - Overview of Cryptnox CLI
- :mod:`cryptnox_cli.command.seed` - Seed command implementation details
- :doc:`cryptnox_cli.command` - All command implementations
- :doc:`modules` - Complete API Reference

