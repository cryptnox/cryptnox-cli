Cryptnox CLI Overview
=====================

``cryptnox-cli`` is a command-line interface for managing **Cryptnox Smart cards**, enabling secure seed initialization and cryptographic signing for **Bitcoin** and **Ethereum**.

Supported Hardware
------------------

- **Cryptnox Smart cards** 💳
- **Standard PC/SC Smart card Readers**: either USB NFC reader or a USB smart card reader

Get your card and readers here: `shop.cryptnox.com <https://shop.cryptnox.com>`_

Installation
------------

.. note::
   This is only a minimal setup. Additional packages may be required depending on your operating system.

From PyPI
~~~~~~~~~

.. code-block:: bash

   pip install cryptnox-cli

From source
~~~~~~~~~~~

.. code-block:: bash

   git clone https://github.com/cryptnox/cryptnox-cli.git
   cd cryptnox-cli
   pip install .

This installs the package and makes the ``cryptnox`` command available (if your Python installation is in your system ``PATH``).

Quick Usage Examples
--------------------

.. note::
   The examples below are only a subset of available commands. The complete list of commands and detailed usage instructions is described in the :doc:`cli` section.

1. Dual initialization
~~~~~~~~~~~~~~~~~~~~~~~

1. Factory reset each card:
   
   ``cryptnox reset`` → enter PUK → verify reset.

2. Initialize each card:
   
   ``cryptnox init`` → (optional) set name/email → set **PIN** (4–9 digits) → set or generate **PUK** → verify init.

3. Run dual seed procedure:
   
   ``cryptnox seed dual`` — follow prompts: insert Card A (enter PIN), swap to Card B (enter PIN), swap back as requested.

2. Sign and send a Bitcoin transaction
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

1. Create or obtain a raw unsigned transaction externally.
2. Run the signing & send command:
   
   ``cryptnox btc send <recipient_address> <amount> [-f <fees>]``

3. Change PIN code
~~~~~~~~~~~~~~~~~~

1. Run command: ``cryptnox change_pin``
2. Enter current PIN → enter new PIN → verify change.
3. Check with ``cryptnox info`` using new PIN (BTC & ETH accounts displayed).

4. Get extended public key (xpub)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

1. Run command: ``cryptnox get_xpub``
2. Enter **PIN** → enter **PUK**
3. The card returns the **xpub**

License
-------

cryptnox-cli is dual-licensed:

- **LGPL-3.0** for open-source projects and proprietary projects that comply with LGPL requirements
- **Commercial license** for projects that require a proprietary license without LGPL obligations (see COMMERCIAL.md for details)

For commercial inquiries, contact: contact@cryptnox.com
