=========
Changelog
=========

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
