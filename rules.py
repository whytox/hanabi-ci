from abc import ABC, abstractmethod
from game import Game
from hanabi_model import HanabiState, HanabiAction, Hint, Play, Discard, UnknownCard
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
        sender = hanabi_state.me.name
        return Discard(sender, card_index)


class DiscardRandomCard(Rule):
    def match(state: HanabiState) -> HanabiAction:
        if state.used_note_tokens == 8:
            return None
        card_index = random.choice(range(state.n_cards))
        sender = state.me
        return Discard(sender, card_index)


class PlaySafeCard(Rule):
    def match(state: HanabiState) -> HanabiAction:
        playable_cards = state.get_valid_playable_cards()
        for i, unknown_card in enumerate(state.inference.my_hand):
            # if the set of possible cards is contained in the set
            # valid playable cards => safe play
            if unknown_card.possible_cards <= playable_cards:
                return Play(state.my_name, i)


class DiscardSafeCard(Rule):
    def match(state: HanabiState) -> HanabiAction:
        pass


class HintPlayableCard(Rule):
    def match(state: HanabiState) -> HanabiAction:
        if state.used_note_tokens == 8:
            return None

        playable_cards = state.get_valid_playable_cards()
        # order the player starting from the one following me
        players = (
            state.players_list[state.my_turn + 1 :]
            + state.players_list[: state.my_turn]
        )

        for player in players:
            player_cards = set(player.hand)
            # if there are some playable cards in player's hand...
            hintable_cards = player_cards & playable_cards
            print(state.my_name.upper(), hintable_cards, sep="\t")
            for card in hintable_cards:
                # TODO: only clue unclued cards
                same_color_cards = UnknownCard.possible_cards_with_color(card.color)
                same_value_cards = UnknownCard.possible_cards_with_number(card.value)
                # and the player doesn't have other non-hintable
                # cards with the same color...
                if not (player_cards - hintable_cards) & same_color_cards:
                    return Hint(
                        state.my_name, player.name, Hint.HINT_TYPE_COL, card.color
                    )
                # or if the player doesn't have other non-hintable
                # cards with the same number...
                if not (player_cards - hintable_cards) & same_value_cards:
                    return Hint(
                        state.my_name, player.name, Hint.HINT_TYPE_VAL, card.value
                    )
        return None


class FinesseCard(Rule):
    def match(state: HanabiState) -> HanabiAction:
        pass


class MustDiscard(Rule):
    def match(state: HanabiState) -> HanabiAction:
        pass
