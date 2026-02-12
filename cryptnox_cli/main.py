#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Command line interface for Cryptnox Cards
"""
import sys
import traceback
from os import makedirs
from pathlib import Path

import argparse
import lazy_import
from appdirs import user_log_dir

try:
    from __init__ import __version__
    import interactive_cli
    from command import (
        factory,
        options
    )
except ImportError:
    try:
        from . import __version__
        from . import interactive_cli
        from .command import (
            factory,
            options
        )
    except ImportError:
        # When frozen by PyInstaller, use absolute imports
        from cryptnox_cli import __version__
        from cryptnox_cli import interactive_cli
        from cryptnox_cli.command import (
            factory,
            options
        )

cryptnox_sdk_py = lazy_import.lazy_module("cryptnox_sdk_py")
json = lazy_import.lazy_module("json")
re = lazy_import.lazy_module("re")
tabulate = lazy_import.lazy_callable("tabulate.tabulate")
requests = lazy_import.lazy_module("requests")
web3 = lazy_import.lazy_module("web3")

APPLICATION_NAME = "Cryptnox CLI"


def get_parser() -> argparse.ArgumentParser:
    """
    Get the parser that can be used to process user input

    :return: Argument parser to use for processing the user input
    :rtype: argparse.ArgumentParser
    """
    parser = interactive_cli.ErrorParser(description="Cryptnox command line interface.")
    parser.is_main_menu = True

    parser.add_argument("-v", "--version", action="version", version=f"Cryptnox CLI {__version__}")
    parser.add_argument("--verbose", action="store_true", help="Turn on logging")
    parser.add_argument('--port', nargs='?', type=int, default=None,
                        help='Define port to enable remote feature')
    serial_index_parser = parser.add_mutually_exclusive_group()
    serial_index_parser.add_argument("-s", "--serial", type=int,
                                     help="Serial number of the card to be used for the command")

    options.add(parser)

    return parser


def execute(args):
    if args.command:
        result = factory.command(args).execute()
    else:
        print(f'Port: {args.port}')
        result = interactive_cli.InteractiveCli(__version__, args.verbose, args.port).run()

    return result


def _sanitize_error_log(exc_info) -> str:
    """
    Create a sanitized error log that redacts potentially sensitive information.

    :param exc_info: Exception info tuple from sys.exc_info()
    :return: Sanitized error message string
    """
    exc_type, exc_value, exc_tb = exc_info

    # Get basic exception info without local variables
    error_lines = [
        "=" * 70,
        "ERROR REPORT (Sanitized)",
        "=" * 70,
        f"\nException Type: {exc_type.__name__}",
        f"Exception Message: {str(exc_value)}",
        "\nStack Trace (paths only, no variable values):",
        "-" * 70
    ]

    # Add stack trace with file/line info but no local variables
    tb_lines = traceback.format_tb(exc_tb)
    for line in tb_lines:
        # Redact any potential secrets in the stack trace
        # Remove any lines that might contain passwords, keys, mnemonics
        sanitized = re.sub(
            r'(password|passwd|pwd|secret|key|token|mnemonic|seed|pin)["\']?\s*[:=]\s*["\']?[^,\s\)"\']+',
            r'\1=***REDACTED***', line, flags=re.IGNORECASE)
        error_lines.append(sanitized)

    error_lines.extend([
        "=" * 70,
        "\nNOTE: Sensitive data has been redacted from this log.",
        "Local variables and arguments are not included to protect secrets.",
        "=" * 70
    ])

    return "\n".join(error_lines)


def main() -> int:
    """
    Main method to call when the script is executed on the command line

    :return: 0 if the command executed without issues. Other number indicating and issue
    :rtype: int
    """
    parser = get_parser()

    args = parser.parse_args()

    try:
        return execute(args)
    except KeyboardInterrupt:
        return 0
    except Exception:
        print("This is something we haven't foreseen. Please, help us in making the application "
              "better by reporting this issue.")
        traceback.print_exc()
        path = Path(user_log_dir('cryptnox-cli', 'cryptnox'))
        makedirs(path, exist_ok=True)
        error_file = path.joinpath("error.log")
        try:
            # Write sanitized error log instead of full traceback
            with open(error_file, "w", encoding="utf-8") as log:
                sanitized_log = _sanitize_error_log(sys.exc_info())
                log.write(sanitized_log)
        except Exception:
            print("Please, copy this error and send it to us, so that we can make the application "
                  "better.")
        else:
            print(f"Error has been also saved into file {error_file}.")
            print("Note: Sensitive information has been redacted from the log file.")
            print("Please review the file before sharing to ensure no secrets are exposed.")

        input("Press enter to exit application")

        return -1


if __name__ == "__main__":
    sys.exit(main())
