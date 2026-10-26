=========
Changelog
=========

Unreleased
----------

Added
^^^^^
- Solana (SOL): ``solana send`` and ``solana config`` commands, and the SOL address and balance in ``info``, signed with the card's Ed25519 key; requires cryptnox-sdk-py 1.0.5 and adds the ``solders`` dependency
- PDF version of the documentation, built together with the HTML pages
- The documentation pages carry Open Graph and Twitter card metadata, and the site publishes a sitemap
- CI checks the licenses of the dependencies the package installs
- CI runs flake8, pylint and the dependency license check on Python 3.14
- Dependabot opens update pull requests for the GitHub Actions every week and for the Python dependencies every month; minor and patch updates come grouped in one pull request per ecosystem, major updates one by one, and a release is proposed once it is seven days old
- ``NOTICES.md`` and the license texts of code from other projects are included in the package; the Windows installer installs them together with the licenses of the bundled Python packages

Changed
^^^^^^^
- Masked PIN, PUK and passphrase input on Linux and macOS is handled by the CLI itself; the ``stdiomask`` dependency is removed
- Ethereum support is loaded only by the commands that use it, so commands such as ``history`` and ``info`` start noticeably faster; the ``lazy-import`` dependency is removed
- Ethereum signatures from the card are completed with the CLI's own secp256k1 code; the ``ecdsa`` dependency is removed
- The unused ``argparse``, ``colander`` and ``pytz`` dependencies are removed; ``eth-account``, ``eth-utils`` and ``hexbytes``, which the Ethereum code imports, are declared directly
- Dependencies with security advisories reported by Dependabot are updated
- The pinned versions of aiohttp, certifi, cryptography and urllib3 are updated to releases with security fixes

Fixed
^^^^^
- Windows: PIN, PUK and BIP39 passphrase entry now accepts the full Unicode range. Earlier versions converted each typed character to the console's code page, so a passphrase containing characters outside ASCII was not the one the user entered. Arrow and function keys are ignored instead of adding characters to the entry, and Ctrl+C cancels the prompt again
- Windows: a BIP39 passphrase entered with version 1.0.4 or 1.0.5 lost at entry every character outside ASCII that the console's code page contains, such as accented letters and umlauts on a European console, so the passphrase that opens such a wallet is the one with those characters removed. Type it that way; this version keeps them. Exceptions:

  - a character the code page does not contain became a question mark or a similar plain character, such as o for ő
  - on a Chinese, Japanese or Korean console, a character could leave one ASCII character behind, such as a backslash
  - pasted into the classic console with right-click, symbols and emoji arrived as nothing; pasted into Windows Terminal, an emoji became two question marks
  - pasted into the classic console with Ctrl+V, nothing arrived, so a passphrase entered and confirmed that way is empty

  With version 1.0.3 and earlier the console behaved the same way, but a character the code page contains was stored as a different character instead of being dropped, so a wallet created that way opens neither with the passphrase as written nor with those characters removed

- Windows: Ctrl+V pastes into the PIN, PUK and passphrase prompts in the classic console, where it used to enter nothing. The first line of the clipboard is pasted, without its line break
- The BIP39 passphrase prompt refuses an empty passphrase once you have chosen to use one, and asks again whether to use one
- Installs on every Python 3.14 release; the version limit admitted 3.14.0 only
- ``requirements.txt`` and ``dev-requirements.txt`` install on Python 3.11 to 3.14: pyscard, pydantic, regex, bitarray, ckzg and cytoolz are updated to releases that build or have wheels for each, and the development requirements include ``sphinx-sitemap`` and the current ``cryptnox-sdk-py``
- The exit status reflects the command's result; it used to be 0 even when a command failed after the card was found
- Findings from CodeQL and Semgrep code scanning are resolved
- Easy mode: the easy-mode PIN is sent to the card again, so ``info`` and other commands that need a verified PIN no longer end without output
- A command that stops because the card has not verified the PIN now says so

`1.0.5 <https://github.com/Cryptnox-Software/cryptnox-cli/compare/ver1.0.4...ver1.0.5>`_
------------------------------------------------------------------------------------------------

Fixed
^^^^^
- Fixed ``ModuleNotFoundError`` for ``manufacturer_certificate`` command in packaged installer (MSIX/MSI) — the module was missing from PyInstaller's ``hiddenimports``, causing all commands to fail at runtime in the frozen executable

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
