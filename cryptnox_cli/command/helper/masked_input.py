# -*- coding: utf-8 -*-
"""
Masked entry of PINs, PUKs and passphrases: one mask character is echoed per
character entered, on Windows consoles and POSIX terminals alike.
"""
import codecs
import os
import sys

# UTF-16 surrogate ranges. A character outside the Basic Multilingual Plane,
# an emoji for instance, reaches a Windows console as two of these halves.
_HIGH_SURROGATE = range(0xD800, 0xDC00)
_LOW_SURROGATE = range(0xDC00, 0xE000)


def _masked_input(read_char, prompt, mask):
    """
    Read a secret, echoing one mask character per character entered.

    :param read_char: Callable returning the next UTF-16 code unit as a
                      one-character string, an empty string for a key that
                      carries no character, such as an arrow or function key,
                      or raising EOFError when the input ends.
    :param str prompt: Text to show before the entry
    :param str mask: Character to echo for each character entered

    :return: The entered text
    :rtype: str

    An astral character arrives as a surrogate pair and is joined back into one
    entry, so it echoes one mask character and one backspace removes all of it.
    Only ASCII control characters are left out. Separators and format
    characters, such as the ideographic space a Japanese keyboard produces, are
    part of a passphrase and change the wallet it derives.
    """
    entered = []
    pending = ''
    sys.stdout.write(prompt)
    sys.stdout.flush()
    while True:
        char = read_char()
        if not char:
            continue
        if ord(char) in _HIGH_SURROGATE:
            pending = char
            continue
        if pending:
            if ord(char) in _LOW_SURROGATE:
                # Rebuild the character the pair stands for. Joining the halves
                # as text would leave two unusable ones that cannot be encoded.
                char = chr(0x10000 + (ord(pending) - 0xD800) * 0x400
                           + (ord(char) - 0xDC00))
            pending = ''
        elif ord(char) in _LOW_SURROGATE:
            continue  # Half of a character without its partner, not text

        if char in ('\r', '\n'):  # Enter
            return ''.join(entered)
        if char == '\x03':  # Ctrl+C
            raise KeyboardInterrupt
        if char in ('\b', '\x7f'):  # Backspace/Del
            if entered:
                sys.stdout.write('\b \b')
                sys.stdout.flush()
                entered.pop()
        elif ord(char) > 31:
            entered.append(char)
            sys.stdout.write(mask)
            sys.stdout.flush()


def _console_reader(handle, kernel32):
    """
    Build a read_char callable over a Windows console input handle.

    Keys are taken from ReadConsoleInputW rather than msvcrt, because the
    console records say whether a key produced a character. Through msvcrt an
    arrow key is announced by a lead byte that cannot be told apart from a
    typed 'a with grave accent', which would either swallow the next character
    or add the arrow's scan code to the secret.
    """
    import ctypes
    from ctypes import wintypes

    class CharUnion(ctypes.Union):
        """Character of a key event, as text or as a byte."""
        _fields_ = [("UnicodeChar", ctypes.c_wchar), ("AsciiChar", ctypes.c_char)]

    class KeyEvent(ctypes.Structure):
        """KEY_EVENT_RECORD of the Windows console API."""
        _fields_ = [("bKeyDown", wintypes.BOOL), ("wRepeatCount", wintypes.WORD),
                    ("wVirtualKeyCode", wintypes.WORD), ("wVirtualScanCode", wintypes.WORD),
                    ("uChar", CharUnion), ("dwControlKeyState", wintypes.DWORD)]

    class EventUnion(ctypes.Union):
        """Event of an input record. Only key events are read."""
        _fields_ = [("KeyEvent", KeyEvent), ("padding", ctypes.c_byte * 16)]

    class InputRecord(ctypes.Structure):
        """INPUT_RECORD of the Windows console API."""
        _fields_ = [("EventType", wintypes.WORD), ("Event", EventUnion)]

    key_event = 0x0001
    vk_menu = 0x12  # Alt
    record = InputRecord()
    read = wintypes.DWORD()
    buffered = []

    def read_char():
        while not buffered:
            if not kernel32.ReadConsoleInputW(handle, ctypes.byref(record), 1,
                                              ctypes.byref(read)) or not read.value:
                raise EOFError
            if record.EventType != key_event:
                continue
            # A key delivers its character on both key-down and key-up, so only
            # key-down is taken. The exception is Alt: a character composed with
            # Alt and the numeric keypad arrives on the Alt key-up alone, and the
            # classic console's paste delivers each half of a character outside
            # the Basic Multilingual Plane, an emoji for instance, the same way.
            if (not record.Event.KeyEvent.bKeyDown
                    and record.Event.KeyEvent.wVirtualKeyCode != vk_menu):
                continue
            char = record.Event.KeyEvent.uChar.UnicodeChar
            if char == '\x00':
                continue  # A key that produces no character, such as an arrow
            buffered.extend([char] * max(1, record.Event.KeyEvent.wRepeatCount))
        return buffered.pop(0)

    return read_char


def _getpass_windows(prompt, mask):
    """
    Masked input for a Windows console.

    Line editing, echo and Ctrl+C handling are switched off for the duration,
    so every keypress is delivered as it is typed and Ctrl+C reaches the loop
    as a character. The console mode is restored afterwards. When standard
    input is not a console there is nothing to mask and the line is read as is.
    """
    import ctypes

    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    # A HANDLE is pointer sized; left untyped, ctypes would cut it to 32 bits
    kernel32.GetStdHandle.restype = ctypes.c_void_p
    std_input_handle = -10
    handle = ctypes.c_void_p(kernel32.GetStdHandle(std_input_handle))
    mode = ctypes.c_ulong()
    if not kernel32.GetConsoleMode(handle, ctypes.byref(mode)):
        return input(prompt)

    # ENABLE_PROCESSED_INPUT | ENABLE_LINE_INPUT | ENABLE_ECHO_INPUT
    # | ENABLE_WINDOW_INPUT | ENABLE_VIRTUAL_TERMINAL_INPUT
    line_editing_and_echo = 0x0001 | 0x0002 | 0x0004 | 0x0008 | 0x0200
    try:
        kernel32.SetConsoleMode(handle, mode.value & ~line_editing_and_echo)
        return _masked_input(_console_reader(handle, kernel32), prompt, mask)
    finally:
        kernel32.SetConsoleMode(handle, mode.value)
        sys.stdout.write('\n')
        sys.stdout.flush()


def _getpass_posix(prompt, mask):
    """
    Masked input for POSIX terminals.
    The terminal is switched to cbreak mode: keys arrive one at a time without
    echo, while Ctrl+C still raises KeyboardInterrupt. Bytes are decoded
    incrementally, so a multi-byte UTF-8 character counts as one entry.
    When stdin is not a terminal there is nothing to mask and the line is read as is.
    """
    import termios
    import tty

    try:
        fd = sys.stdin.fileno()
        old_settings = termios.tcgetattr(fd)
    except (AttributeError, ValueError, termios.error):
        return input(prompt)

    decoder = codecs.getincrementaldecoder(sys.stdin.encoding or 'utf-8')(errors='ignore')
    entered = []
    sys.stdout.write(prompt)
    sys.stdout.flush()
    try:
        tty.setcbreak(fd)
        while True:
            data = os.read(fd, 1)
            if not data:
                raise EOFError
            char = decoder.decode(data)
            if not char:  # Incomplete multi-byte character
                continue
            if char in ('\n', '\r'):  # Enter
                return ''.join(entered)
            if char in ('\b', '\x7f'):  # Backspace/Del
                if entered:
                    sys.stdout.write('\b \b')
                    sys.stdout.flush()
                    entered.pop()
            elif ord(char) > 31:
                # Only ASCII control characters are left out. Separators and format
                # characters (ideographic space, no-break space, zero width joiner)
                # are part of a passphrase and change the wallet it derives.
                entered.append(char)
                sys.stdout.write(mask)
                sys.stdout.flush()
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
        sys.stdout.write('\n')
        sys.stdout.flush()


def getpass(prompt='Password: ', mask='*'):
    """
    Cross-platform getpass that raises KeyboardInterrupt on Ctrl+C.
    """
    if sys.platform == 'win32':
        return _getpass_windows(prompt, mask)

    return _getpass_posix(prompt, mask)
