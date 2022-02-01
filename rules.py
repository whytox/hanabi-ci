from abc import ABC, abstractmethod
from hanabi_model import HanabiState, HanabiAction, Hint, Play, Discard
from itertools import product
import random


class Rule(ABC):
    @staticmethod
    @abstractmethod
    def match(hanabi_state: HanabiState) -> HanabiAction:
        raise NotImplementedError


class RandomHint(Rule):
    """A rule that just give an hint to an
    already not hinted card of the minimum
    number value.
    (if there is at least an available NoteToken)
    """

    @staticmethod
    def match(hanabi_state: HanabiState) -> HanabiAction:
        if hanabi_state.used_note_tokens == 8:
            return None
        _from = hanabi_state.me.name

        hint_type = Hint.HINT_TYPE_VAL
        next_player_turn = (hanabi_state.my_turn + 1) % len(hanabi_state.players_list)
        to = hanabi_state.players_list[next_player_turn].name  # to next player
        print(to)
        print(hanabi_state.players_list[next_player_turn].hand)
        hint_value = random.choice(
            hanabi_state.players_list[next_player_turn].hand
        ).value
        print(f"hint  for {to} from {_from}")
        return Hint(_from, to, hint_type, hint_value)


class PlayRandomCard(Rule):
    def match(hanabi_state: HanabiState) -> HanabiAction:
        card_index = random.choice(range(hanabi_state.n_cards))
        sender = hanabi_state.me.name
        return Play(sender, card_index)


class DiscardRandomCard(Rule):
    def match(hanabi_state: HanabiState) -> HanabiAction:
        card_index = random.choice(range(hanabi_state.n_cards))
        sender = hanabi_state.me
        return Discard(sender, card_index)


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
