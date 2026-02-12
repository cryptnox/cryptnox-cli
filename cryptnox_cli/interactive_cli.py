# -*- coding: utf-8 -*-
"""
Module for application that behaves as command line interface
"""
import shutil
import socket
import sys
from pathlib import Path
from typing import List

import argparse
import cryptnox_sdk_py

try:
    import config
    import enums
    from command.options import options
    from command.helper import security
    from command.helper.cards import (
        CardManager,
        ExitException,
        TimeoutException
    )
except ImportError:
    from . import config
    from . import enums
    from .command.options import options
    from .command.helper import security
    from .command.helper.cards import (
        CardManager,
        ExitException,
        TimeoutException
    )


def multiline_input(prompt: str = "") -> str:
    """
    Function for handling user input that can span multiple lines.

    :param str prompt: Prompt to show to the user
    :return: User input
    :rtype: str
    """
    line = input(prompt)
    quote_position = list(filter((-1).__ne__, [line.find('"'), line.find("'")]))
    if not quote_position:
        return line

    quote = line[min(quote_position)]
    number_of_quotes = line.count(quote) - line.count(f"\\{quote}")
    result = [line]

    while number_of_quotes % 2:
        line = input()
        number_of_quotes += line.count(quote) - line.count(f"\\{quote}")
        result.append(line)

    return "\n".join(result)


class ErrorParser(argparse.ArgumentParser):
    """
    Parser to override how argparse is showing messages on error.
    """

    is_main_menu = False

    def error(self, message):
        if "the following arguments are required" in message:
            message = self.format_usage()

        args = {'message': message.replace("argument command: ", "")}

        self.exit(2, "%(message)s\n" % args)

    def format_help(self):
        message = super().format_help()

        if not self.is_main_menu:
            return message

        groups = {
            enums.Command.BTC.value: "Blockchain Operations",
            enums.Command.CARD_CONFIGURATION.value: "Card Administration",
            "use": "General",
        }
        lines_out = []
        skip = True
        for line in message.split("\n"):
            if line.strip().startswith("{"):
                skip = False
                continue
            if skip:
                continue
            command = line.strip().split(" ")[0]
            if command in groups:
                lines_out += ["", f"{groups[command]}:", ""]
            lines_out.append(line)

        return "\n".join(lines_out)


class UsageParser(ErrorParser):
    """
    Parser to override how usage is shown to the user
    """
    throw_error = True
    subcommand = []

    def __init__(self, *args, **kwargs):
        kwargs["prefix_chars"] = kwargs.get("prefix_chars") or " -"
        kwargs["add_help"] = False

        super().__init__(*args, **kwargs)
        self.add_argument(" help", action="help", default=argparse.SUPPRESS,
                          help="Show help message")

    def format_help(self):
        message = super().format_help().replace(Path(sys.argv[0]).name, "")
        for subcommand in UsageParser.subcommand:
            message = message.replace(f" {subcommand} ", " ", 1)
        return message

    def format_usage(self) -> str:
        message = super().format_usage()
        message = message.replace(Path(sys.argv[0]).name, "")
        for subcommand in UsageParser.subcommand:
            message = message.replace(f" {subcommand} ", " ", 1)
        return message

    def error(self, message):
        """error(message: string)

        Prints a usage message incorporating the message to stderr and
        exits.

        If you override this in a subclass, it should not return -- it
        should either exit or raise an exception.
        """
        if "the following arguments are required" in message \
                and UsageParser.throw_error:
            raise ValueError
        super().error(message)

    def commands_with_subparser(self, commands: List[str]) -> List:
        """
        Function determining commands to be saved in interactive mode

        :param List[str] commands: List of commands that are being executed
        :return: List of commands to be saved
        :rtype: List[str]
        """
        command_to_save = []
        parser = self

        UsageParser.add_interactive_options(parser)
        for command in commands:
            try:
                parser = parser._subparsers._group_actions[-1].choices[command]
                UsageParser.add_interactive_options(parser)
            except LookupError:
                return []
            except AttributeError:
                break
            if parser._subparsers:
                command_to_save.append(command)
        return command_to_save

    @staticmethod
    def add_interactive_options(parser: argparse.ArgumentParser) -> None:
        """
        Add exit, use and back subparser to selected parser

        :param parser: Parser where subparsers are to be added to
        :return:
        :rtype: None
        """
        if not parser._subparsers._group_actions[-1].choices.get("use"):
            parser._subparsers._actions[-1].add_parser("use",
                                                       help="Change card to be used by default")
        if not parser._subparsers._group_actions[-1].choices.get("back"):
            parser._subparsers._actions[-1].add_parser("back", help="Exit subcommand")
        if not parser._subparsers._group_actions[-1].choices.get("exit"):
            parser._subparsers._actions[-1].add_parser("exit", help="Full application exit")


class InteractiveCli:
    """
    Application running a command line interface.

    :param str version: Version of the application the interface should return
    :param bool debug: Print out debug information in regard to the communication to the card
    :param bool remote: Determines whether the application should use remote feature
                        or look for local readers
    """

    class ExitException(Exception):
        """
        Exception to handle when the user requests to exit the application.
        """

    def __init__(self, version: str, debug: bool = False, port: int = None):
        self.version = version
        self.debug: bool = debug
        self.port: int = port

        self._reconnect = False
        self._card_info = None
        self._cards = CardManager()

        self.subcommand = []
        self.parser = None

    def run(self) -> int:
        print("Loading cards...")
        client = self._client()

        try:
            self._cards.refresh(self.port and client is not None)
            self._card_info = list(self._cards.values())[0].info
        except IndexError:
            pass

        self._cards.print_card_list(show_warnings=True, print_with_one_card=True)
        print("\n\nType help for list of commands.\n\n")
        print("\n\nWith any input that is requested from you, to exit the current command type: exit \n\n")

        while True:
            try:
                self._process_command()
            except InteractiveCli.ExitException:
                self._close_client(client)
                break

        return 0

    def _client(self):
        if not self.port:
            return None

        print(f"Found port {self.port} defined, searching remotely.")
        try:
            client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            client.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            server = socket.gethostbyname(socket.gethostname() + ".local")
            client.connect((server, self.port))
        except Exception as error:
            client = None
            print(f'Remote card connection not found: {error}')
        else:
            config.REMOTE_CONNECTIONS.append(client)

        return client

    def _close_client(self, client):
        if not self.port or not client:
            return

        message = '!Close'.encode('utf-8')
        msg_length = len(message)
        send_length = str(msg_length).encode('utf-8')
        send_length += b' ' * (64 - len(send_length))

        try:
            client.send(send_length)
            client.send(message)
            client.close()
        except Exception as e:
            print(f'Probably no socket to close: {e}')

    def is_valid_subcommand(self, new_subcommand: List[str],
                            execute: List[str]) -> bool:
        """
        Check is command eligible for saving.

        :param List[str] new_subcommand: Command to be saved
        :param List[str] execute: Commands that are executed
        :return: True if command can be permanent, else otherwise
        :rtype: bool
        """
        return len(self.subcommand) < len(new_subcommand) and execute == new_subcommand

    def _process_command(self):
        to_always_run = ["list"]
        command_to_execute = multiline_input(self._prompt)
        execute = command_to_execute.strip().split()

        for command in execute:
            if command in ["version", "help"]:
                execute[execute.index(command)] = f" {command}"

        if self.subcommand:
            try:
                if execute[0] not in ["use", "exit", "back"]:
                    execute[0:0] = self.subcommand
            except LookupError:
                pass
        else:
            self._prepare_parser()

        try:
            args = self.parser.parse_args(execute)
        except SystemExit:
            pass
        except ValueError:
            new_subcommand = self.parser.commands_with_subparser(execute)
            if self.is_valid_subcommand(new_subcommand, execute):
                self.subcommand = new_subcommand
                UsageParser.subcommand = self.subcommand
            else:
                UsageParser.throw_error = False
                try:
                    self.parser.parse_args(execute)
                except SystemExit:
                    pass
                UsageParser.throw_error = True
        else:
            self._process(args, to_always_run)

    def _process(self, args, to_always_run: List = None) -> None:
        to_always_run = [] or to_always_run
        if args.command == "exit":
            raise InteractiveCli.ExitException

        if args.command == "use":
            self._use(args.serial_index)

        elif args.command == "back" and self.subcommand:
            self.subcommand.pop(-1)
        elif args.command:
            if self._card_info and args.command in to_always_run:
                if self._card_info["serial_number"] not in self._cards:
                    self._card_info = None
            self._run_command(args, to_always_run)

    def _use(self, serial_index):
        self._card_info = None

        try:
            if serial_index is None:
                self._card_info = self._cards.select_card().info
            else:
                self._card_info = self._cards[serial_index - 1].info
        except (cryptnox_sdk_py.exceptions.CryptnoxException, ExitException, TimeoutException) as error:
            print(error)
            return

        if self._card_info:
            print(f"Changing card to: {self._card_info['serial_number']}\n")
        else:
            print("Can't change card")

    @property
    def _prompt(self) -> str:
        large_screen = shutil.get_terminal_size((80, 20)).columns > 100
        easy_mode = ""
        if security.is_easy_mode(self._card_info):
            easy_mode = " - easy mode" if large_screen else "e"
        help_text = "serial number: " if large_screen else "sn:"
        try:
            serial = f" ({help_text}{self._card_info['serial_number']}{easy_mode})" \
                if self._card_info else ""
        except TypeError:
            serial = ""

        card = "cryptnox_cli" if large_screen else "cryptnox"

        try:
            commands = [f"{subcommand} > " for subcommand in self.subcommand]
        except TypeError:
            commands = []
        string_to_return = card + serial + " > " + "".join(commands)
        return string_to_return

    def _run_command(self, args: argparse.Namespace, to_always_run: List = None) -> None:
        try:
            from command import factory
        except ImportError:
            from .command import factory

        to_always_run = [] or to_always_run
        always_run = args.command in to_always_run

        if not self._card_info and not always_run:
            try:
                self._cards.refresh(self.port is not None)
                self._card_info = list(self._cards.values())[0].info
            except IndexError:
                print("No cards found.\n")
                return

        command = factory.command(args, self._cards)

        execute_result = command.execute(
            self._card_info["serial_number"] if self._card_info else None)
        if execute_result == -1:
            return

        try:
            self._card_info = self._cards[command.serial_number].info
        except KeyError:
            pass
        except (cryptnox_sdk_py.exceptions.CryptnoxException, ExitException, TimeoutException) as error:
            print(error)

        print("\n")

    def _prepare_parser(self) -> None:
        self.parser = UsageParser(description="Cryptnox command line interface")
        self.parser.is_main_menu = True
        self.parser.add_argument(" version", action="version",
                                 version=f"Cryptnox CLI {self.version}",
                                 help="Show program's version number")

        options.add(self.parser, True)
