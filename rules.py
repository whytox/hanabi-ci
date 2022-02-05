from abc import ABC, abstractmethod
from logging.config import valid_ident
from os import remove
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
            if chop_card.value == 2:  # twos are generally considered useful
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


class PlayAlmostSafeCard(Rule):
    PLAY_TRESHOLD = 0.6

    def match(state: HanabiState) -> HanabiAction:
        """Play a card that has a probability of at least PLAY_THRESHOLD
        of being playable."""
        if state.used_storm_tokens > 1:
            return None
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
        print(card_risk)
        best_card = max(card_risk, key=lambda c: c[1])[0]
        return Play(state.my_name, best_card)


class HintMostUncluedCards(Rule):
    def match(state: HanabiState) -> HanabiAction:
        if state.used_note_tokens == 8:
            return None

        state.get_relative_player_order()
        best_hint = None
        max_cards_addressed = 0
        for player in state.players_list:
            valid_hints = state.get_valid_hints(player.name, remove_clued=True)
            #       most common element is the frirst----v  v---- second element of most common element
            if not valid_hints:
                continue
            most_common_info = valid_hints.most_common(1)[0]  # so ugly I know
            num_cards_addressed = most_common_info[1]
            if num_cards_addressed > max_cards_addressed:
                hint_type = (
                    Hint.HINT_TYPE_COL
                    if type(most_common_info[0]) is str
                    else Hint.HINT_TYPE_VAL
                )
                hint_value = most_common_info[0]
                best_hint = Hint(state.my_name, player.name, hint_type, hint_value)
                max_cards_addressed = num_cards_addressed
        if best_hint is not None:
            logging.debug(
                f"Best hint addresses {max_cards_addressed} of {best_hint.to}"
            )
        return best_hint


class HintMostCards(Rule):  # so ugly I know
    def match(state: HanabiState) -> HanabiAction:
        if state.used_note_tokens == 8:
            return None

        state.get_relative_player_order()
        best_hint = None
        max_cards_addressed = 0
        for player in state.players_list:
            valid_hints = state.get_valid_hints(player.name, remove_clued=False)
            #       most common element is the frirst----v  v---- second element of most common element
            if not valid_hints:
                continue
            most_common_info = valid_hints.most_common(1)[0]
            num_cards_addressed = most_common_info[1]
            if num_cards_addressed > max_cards_addressed:
                hint_type = (
                    Hint.HINT_TYPE_COL
                    if type(most_common_info[0]) is str
                    else Hint.HINT_TYPE_VAL
                )
                hint_value = most_common_info[0]
                best_hint = Hint(state.my_name, player.name, hint_type, hint_value)
                max_cards_addressed = num_cards_addressed
        if best_hint is not None:
            logging.debug(
                f"Best hint addresses {max_cards_addressed} of {best_hint.to}"
            )
        return best_hint


class HintUselessCard(Rule):
    def match(state: HanabiState) -> HanabiAction:
        if state.used_note_tokens == 8:
            return None

        still_useful_card = state.get_future_playable_cards()
        for player in state.get_relative_player_order():
            for card in player.hand:
                if (
                    not card in still_useful_card
                    and not card in state.other_players_hints[player.name]
                ):
                    return Hint(
                        state.my_name, player.name, Hint.HINT_TYPE_COL, card.color
                    )
        return None


class DiscardLessUsefulCard(Rule):
    def match(state: HanabiState) -> Discard:
        if state.used_note_tokens == 0:
            return None

        future_useful_cards = state.get_future_playable_cards()
        cards_usefulness = list()
        for i, unknown_card in enumerate(state.inference.my_hand):
            usefulness = len(unknown_card.possible_cards & future_useful_cards) / len(
                unknown_card.possible_cards
            )
            cards_usefulness.append((i, usefulness))

        most_useless_card_index = min(cards_usefulness, key=lambda c: c[1])[0]
        useleness = min(cards_usefulness, key=lambda c: c[1])[1]
        logging.debug(
            f"most useless card is {most_useless_card_index} with uselesness of {useleness}"
        )
        return Discard(state.my_name, most_useless_card_index)
