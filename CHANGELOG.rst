=========
Changelog
=========

`1.0.4 <https://github.com/Cryptnox-Software/cryptnox-cli/compare/ver1.0.3...ver1.0.4>`_
------------------------------------------------------------------------------------------------

Added
^^^^^
- Bitcoin (BTC) send transaction support with SegWit/bech32 address support
- Bitcoin testnet4 support for development and testing
- QuickNode integration via Blockbook UTXOs for UTXO fetching, with JSON-RPC for fee estimation and broadcast
- Parallel network queries for faster Bitcoin balance and UTXO lookups
- XRP and BNB address display in card info
- Manufacturer certificate retrieval command
- Power cycle prompt with automatic card reconnection when required
- Double confirmation when changing PIN or PUK to prevent accidental changes
- Ctrl+C cancellation support in PIN/PUK input prompts
- CodeQL, Semgrep, and OSV security scanning workflows in CI/CD

Changed
^^^^^^^
- Updated cryptnox-sdk-py to 1.0.4
- Added Python 3.14 support
- Mainnet set as the default network configuration
- Improved PIN/PUK input UX on Windows (simplified getpass, removed polling loop)
- Improved verify PIN flow: warns instead of blocking when PUK change is attempted with PIN locked
- Card info command now performs network queries in parallel for improved performance
- Updated dependencies to address security vulnerabilities (Dependabot)

Fixed
^^^^^
- Restored Ctrl+C handling in ``getpass`` on all platforms
- Fixed Ctrl+C handling in ``confirm_pin_code`` and ``confirm_puk_code``
- Fixed thread-safety issue by pre-fetching card config before ``ThreadPoolExecutor``
- Fixed CodeQL ``py/incomplete-url-substring-sanitization`` finding in URL validation
- Fixed ``PinBlockedException`` handling and propagation

Removed
^^^^^^^
- Removed AWS backup and seed backup features (``backup.py``, ``seed_backup.py``, ``download_folder.py``)

`1.0.3 <https://github.com/Cryptnox-Software/cryptnox-cli/compare/v1.0.2...v1.0.3>`_
------------------------------------------------------------------------------------------------

Added
^^^^^
- Added Cryptnox logo to documentation
- Added Other/Proprietary License option

Changed
^^^^^^^
- Updated cryptnox-sdk-py to 1.0.2
- Updated other dependencies to latest versions
- Modified documentation UI, colors, and layout
- Updated documentation license information

`1.0.2 <https://github.com/Cryptnox-Software/cryptnox-cli/compare/v1.0.1...v1.0.2>`_
------------------------------------------------------------------------------------------------

Changed
^^^^^^^
- Updated README file with improved documentation
- Modified commercial license details

`1.0.1 <https://github.com/Cryptnox-Software/cryptnox-cli/compare/v2.9.1...ver1.0.1>`_
------------------------------------------------------------------------------------------------

Added
^^^^^
- Package renamed from ``cryptnoxpro`` to ``cryptnox_cli``
  - Install using: ``pip install cryptnox-cli``
- BIP39 passphrase support for seed generation and recovery
- BIP39 passphrase length limitation and validation
- Sphinx documentation framework for comprehensive CLI documentation
- GitHub Actions workflows for automated documentation deployment
- Constants file for centralized configuration management
- Flake8 code quality checks in CI/CD workflow

Changed
^^^^^^^

- Updated README with improved documentation and examples
- Modified documentation configuration and deployment process
- Reconfigured documentation deployment workflow
- Updated setup configuration (setup.cfg) for better package management
- Improved code organization with constants file

Fixed
^^^^^

- Resolved runtime import errors
- Fixed flake8 code style errors throughout the codebase
- Fixed PUK retries persistence issue

Removed
^^^^^^^

- Removed cleos dependency
- Removed Ropsten testnet support (deprecated network)
