from traceback import format_exc
from colorama import Fore

CARD_COLORS = {
    "yellow": Fore.YELLOW,
    "blue": Fore.BLUE,
    "green": Fore.GREEN,
    "red": Fore.RED,
    "white": Fore.WHITE,
}


def player_hand(self, name, hand) -> str:
    """Return a string representation of the player hand"""
    print(hand)


def card_format(value: str, color: str) -> str:
    num = "?" if value is None else str(value)
    col = color
    if col is not None:
        return " ".join([CARD_COLORS[col], num, Fore.RESET])
    else:
        return num
