# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

import os
import sys

sys.path.insert(0, os.path.abspath(".."))

project = 'cryptnox-cli'
copyright = '2025, Cryptnox'
author = 'Cryptnox'
release = '1.0.2'

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.autosummary",
    "sphinx.ext.napoleon",
    "sphinx.ext.viewcode",
]

# Disable autosummary generation to prevent hangs
autosummary_generate = False

templates_path = ['_templates']
exclude_patterns = ['_build', 'Thumbs.db', '.DS_Store']

# autodoc_mock_imports - Sphinx will create mock imports for these modules
# This is safer than manual sys.modules mocking and prevents hangs
autodoc_mock_imports = [
    # Cryptnox SDK (PyPI package: cryptnox-sdk-py)
    'cryptnox_sdk_py',
    # Input/Output
    'stdiomask',
    'tabulate',
    # AWS
    'boto3',
    'botocore',
    'botocore.exceptions',
    'botocore.client',
    'botocore.config',
    # Web3 and Ethereum
    'web3',
    'web3.eth',
    'web3.contract',
    'web3.middleware',
    'eth_account',
    'eth_account._utils',
    'eth_account._utils.legacy_transactions',
    'eth_account.transactions',
    'eth_account.account',
    'eth_account.datastructures',
    'eth_utils',
    'eth_utils.curried',
    'eth_typing',
    'eth_keys',
    'eth_rlp',
    'eth_abi',
    'eth_hash',
    'hexbytes',
    'ecdsa',
    'rlp',
    # Validation
    'pydantic',
    'pydantic_core',
    # Smart card
    'pyscard',
    'smartcard',
    'smartcard.CardConnection',
    'smartcard.System',
    'smartcard.Exceptions',
    'smartcard.CardType',
    'smartcard.CardRequest',
    'smartcard.util',
    'smartcard.scard',
    # Utilities
    'cytoolz',
    'toolz',
    'winsdk',
    'base58',
]

# Autodoc configuration
autodoc_default_options = {
    'members': True,
    'member-order': 'bysource',
    'special-members': '__init__',
    'undoc-members': True,
    'exclude-members': '__weakref__'
}

# Set autodoc to not fail on import errors
autoclass_content = 'both'

# Handle ambiguous cross-references
nitpicky = False
nitpick_ignore = [
    ('py:class', 'Command'),
    ('py:class', 'Cards'),
]

# Suppress specific warnings
suppress_warnings = [
    'ref.python',
]

# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme = "sphinx_rtd_theme"
html_static_path = ['_static']

# Logo configuration
html_logo = "_static/cryptnox-logo.png"

# Custom CSS and JS
html_css_files = [
    'custom.css',
]

html_js_files = [
    'custom.js',
]

# Theme options
html_theme_options = {
    'analytics_id': '',  # Provided by Google Analytics
    'logo_only': False,
    'prev_next_buttons_location': 'bottom',
    'style_external_links': False,
    'vcs_pageview_mode': '',
    'style_nav_header_background': '#101f2e9',
    # Toc options
    'collapse_navigation': True,
    'sticky_navigation': True,
    'navigation_depth': 4,
    'includehidden': True,
    'titles_only': False
}
