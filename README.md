<p align="center">
  <img src="https://github.com/user-attachments/assets/6ce54a27-8fb6-48e6-9d1f-da144f43425a"/>
</p>

<h3 align="center">cryptnox-cli</h3>
<p align="center">CLI for managing Cryptnox smart card wallets</p>

<br/>
<br/>

[![PyPI](https://img.shields.io/pypi/v/cryptnox-cli.svg)](https://pypi.org/project/cryptnox-cli/)
[![Python versions](https://img.shields.io/pypi/pyversions/cryptnox-cli.svg)](https://pypi.org/project/cryptnox-cli/)
[![Documentation status](https://img.shields.io/badge/docs-latest-blue)](https://cryptnox.github.io/cryptnox-cli)
[![License: GPLv3](https://img.shields.io/badge/License-LGPLv3-blue.svg)](https://www.gnu.org/licenses/lgpl-3.0)

`cryptnox-cli` is a command-line interface for managing **Cryptnox Smartcards**, enabling secure seed initialization and cryptographic signing for **Bitcoin** and **Ethereum**.

---

## Supported hardware

- **Cryptnox Smartcards** 💳
- **Standard PC/SC Smartcard Readers**: either USB NFC reader or a USB smartcard reader
  → Readers are also available in the Cryptnox shop.

Get your card and readers here: [shop.cryptnox.com](https://shop.cryptnox.com)

---

## Installation
> 💡 This is only a minimal setup. Additional packages may be required depending on your operating system. See [Installation and Requirements](https://cryptnox.github.io/cryptnox-cli/overview.html#installation-and-requirements).

### From PyPI

```bash
pip install cryptnox-cli
```

### From source

```bash
git clone https://github.com/cryptnox/cryptnox-cli.git
cd cryptnox-cli
pip install .
```
This installs the package and makes the `cryptnox` command available (if your Python installation is in your system `PATH`).

---

## Quick usage examples
> 💡 The examples below are only a subset of available commands. The complete list of commands and detailed usage instructions is described in the [official documentation](https://cryptnox.github.io/cryptnox-cli).
### 1. Dual initialization

1. Factory reset each card:  
   `cryptnox reset` → enter PUK → verify reset.

2. Initialize each card:  
   `cryptnox init` → (optional) set name/email → set **PIN** (4–9 digits) → set or generate **PUK** → verify init.

3. Run dual seed procedure:  
   `cryptnox seed dual` — follow prompts: insert Card A (enter PIN), swap to Card B (enter PIN), swap back as requested.

### 2. Sign and send a Bitcoin transaction

1. Create or obtain a raw unsigned transaction externally.
2. Run the signing & send command:  
   `cryptnox btc send <recipient_address> <amount> [-f <fees>]`

### 3. Change PIN code

1. Run command: `cryptnox change_pin`
2. Enter current PIN → enter new PIN → verify change.  
3. Check with `cryptnox info` using new PIN (BTC & ETH accounts displayed).

### 3. Change PIN code

1. Run command: `cryptnox change_pin`
2. Enter current PIN → enter new PIN → verify change.  
3. Check with `cryptnox info` using new PIN (BTC & ETH accounts displayed).

### 4. Get extended public key (xpub)

1. Run command: `cryptnox get_xpub`
2. Enter **PIN** → enter **PUK**
3. The card returns the **xpub**

---

## Documentation

The full **User & Developer documentation** is available at the [Cryptnox CLI Documentation](https://cryptnox.github.io/cryptnox-cli). It covers installation and setup, usage guides and examples, CLI command reference, and developer notes with API details.

---

## License

This library is available under LGPL-3.0.
For commercial licensing options, contact: info@cryptnox.ch
