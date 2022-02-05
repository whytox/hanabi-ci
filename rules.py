from abc import ABC, abstractmethod
from game import Game
from hanabi_model import HanabiState, HanabiAction, Hint, Play, Discard, UnknownCard
from itertools import product
import random
import logging


class Rule(ABC):
    @staticmethod
    @abstractmethod
    def match(hanabi_state: HanabiState) -> HanabiAction:
        raise NotImplementedError


class HintRandomCard(Rule):
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
        hint_value = random.choice(
            hanabi_state.players_list[next_player_turn].hand
        ).value
        return Hint(_from, to, hint_type, hint_value)


class PlayRandomCard(Rule):
    def match(hanabi_state: HanabiState) -> HanabiAction:
        card_index = random.choice(range(hanabi_state.n_cards))
        sender = hanabi_state.me.name
        return Play(sender, card_index)


class DiscardRandomCard(Rule):
    def match(state: HanabiState) -> HanabiAction:
        if state.used_note_tokens == 0:
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
                print(
                    f"{state.my_name}: playable are {playable_cards}\n and \n\t{unknown_card.possible_cards} are all playable.\n"
                )
                return Play(state.my_name, i)


class DiscardUselessCard(Rule):
    def match(state: HanabiState) -> HanabiAction:
        if state.used_note_tokens == 0:
            return None

        future_playable_cards = state.get_future_playable_cards()
        for i, unknown_card in enumerate(state.inference.my_hand):
            # if the possible cards of the card
            # are not in the set of future playable cards
            if not unknown_card.possible_cards & future_playable_cards:
                logging.debug(
                    "discarding an unplayable card: {unknown_card.possible_cars}"
                )
                return Discard(state.my_name, i)
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
            print(f"hintable: by {state.my_name.upper()}:", hintable_cards, sep="\t")
            for card in hintable_cards:
                # TODO: only clue unclued cards
                if card in state.get_clued_cards(player.name):
                    continue
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


class HintUsefulChop(Rule):
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
            chop_card = player.hand[0]
            if chop_card.value == 2:
                Hint(state.my_name, player.name, Hint.HINT_TYPE_COL, chop_card.value)
            elif chop_card.value == 5:
                Hint(state.my_name, player.name, Hint.HINT_TYPE_VAL, chop_card.value)
            elif chop_card in playable_cards:
                Hint(state.my_name, player.name, Hint.HINT_TYPE_COL, chop_card.color)
        return None


class DiscardChop(Rule):
    def match(state: HanabiState) -> HanabiAction:
        if state.used_note_tokens == 0:
            return None

        if state.inference.chop_index is not None:
            return Discard(state.my_name, state.inference.chop_index)
        return None


class PlaySafeImplicitCard(Rule):
    def match(state: HanabiState) -> HanabiAction:
        playable_cards = state.get_valid_playable_cards()
        for card_index, unknown_card in enumerate(state.inference.my_hand):
            print("IMPLICIT:", unknown_card.implicit_possible_cards)
            for (
                hint_sender,
                implicit_cards,
            ) in unknown_card.implicit_possible_cards.items():

                if (
                    not hint_sender in state.inference.not_trusted_players
                    and implicit_cards <= playable_cards
                ) and implicit_cards:
                    print("playing a card supposing it is playable")
                    return Play(state.my_name, card_index)
                else:
                    print(f"implicit cards {implicit_cards} are not {playable_cards}")

        return None


class PlayAlmostSafeCard(Rule):
    PLAY_TRESHOLD = 0.7

    def match(state: HanabiState) -> HanabiAction:
        """Play a card that has a probability of at least PLAY_THRESHOLD
        of being playable."""
        playable_cards = state.get_valid_playable_cards()

        for i, unknown_card in enumerate(state.inference.my_hand):
            # if the set of possible cards is contained in the set
            # valid playable cards => safe play
            p = len(playable_cards & unknown_card.possible_cards) / len(
                unknown_card.possible_cards
            )
            if p > PlayAlmostSafeCard.PLAY_TRESHOLD:
                logging.debug(msg=f"playing a card that is almost safe...")
                return Play(state.my_name, i)
            logging.debug(msg=f"card {i} is not enough safe: {p}")


class PlayLessRiskyCard(Rule):
    def match(state: HanabiState) -> HanabiAction:
        card_risk = list()
        playable_cards = state.get_valid_playable_cards()
        for i, unknown_card in enumerate(state.inference.my_hand):
            risk = len(playable_cards & unknown_card.possible_cards) / len(
                unknown_card.possible_cards
            )
            card_risk.append((i, risk))
        best_card = sorted(card_risk, key=lambda c: c[1])[0][0]
        return Play(state.my_name, best_card)
