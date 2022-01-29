from abc import ABC, abstractmethod
from hanabi_model import HanabiState, HanabiAction
from itertools import product


class Rule(ABC):
    @staticmethod
    @abstractmethod
    def match(hanabi_state: HanabiState) -> HanabiAction:
        raise NotImplementedError


class TestHint(Rule):
    """A rule that just give an hint to an
    already not hinted card of the minimum
    number value.
    (if there is at least an available NoteToken)
    """

    @staticmethod
    @abstractmethod
    def match(hanabi_state: HanabiState) -> HanabiAction:
        players = hanabi_state.players_list
        for p in players[1:]:
            print(p.hand)
            print(p.received_hints)
            print(p.)


class PlaySafeCard(Rule):
    def match(state: HanabiState) -> HanabiAction:
        pass

    def _get_playable_cards(state: HanabiState) -> tuple:
        pass


class DiscardSafeCard(Rule):
    def match(state: HanabiState) -> HanabiAction:
        pass


class HintPlayableCards(Rule):
    def match(state: HanabiState) -> HanabiAction:
        pass


class FinesseCard(Rule):
    def match(state: HanabiState) -> HanabiAction:
        pass


class MustDiscard(Rule):
    def match(state: HanabiState) -> HanabiAction:
        pass


class HintPlayableCard(Rule):
    def match(state: HanabiState) -> HanabiAction:
        pass


class DiscardOldCard(Rule):
    def match(state: HanabiState) -> HanabiAction:
        pass


class HintSafeDiscard(Rule):
    def match(state: HanabiState) -> HanabiAction:
        pass


class PlayImplicitCard(Rule):
    def match(state: HanabiState) -> HanabiAction:
        pass
