from abc import ABC


import GameData
from game import Player, Card
from itertools import product

import logging

from hanabi_view import CARD_COLORS

logging.basicConfig(format="%(message)s", level=logging.DEBUG)


class HanabiAction(ABC):
    def __init__(self):
        pass


class Hint(HanabiAction):
    HINT_TYPE_COL = "color"
    HINT_TYPE_VAL = "value"

    def __init__(self, _from: str, to: str, _type: str, value, positions=None):
        self._from = _from
        self.to = to
        self._type = _type
        self.value = value
        self.positions = positions

    def covers(self, card: Card):
        """Return wheter the given card is covered by the hint or not."""
        if self._type == Hint.HINT_TYPE_COL:
            return card.color == self.value
        else:
            return card.value == self.value

    def __repr__(self) -> str:
        return f"Hint: {self._type} {self.value} in {self.positions}"


class Play(HanabiAction):
    THUNDERSTRIKE = "⚡️"
    GOOD_MOVE = "👍🏻"

    def __init__(
        self, sender: str, card_index: int, real_card=None, card_drawn=None, result=None
    ):
        self.sender = sender
        self.card_index = card_index
        self.real_card = real_card
        self.card_drawn = card_drawn
        self.result = result
        return

    @staticmethod
    def from_thunder_strike(data: GameData.ServerPlayerThunderStrike):
        sender = data.sender
        card_index = data.cardHandIndex
        real_card = data.card
        result = Play.THUNDERSTRIKE
        return Play(sender, card_index, real_card, result)


class Discard(HanabiAction):
    def __init__(
        self,
        sender: str,
        card_index: int,
        card_discarded=None,
        card_drawn=None,
    ):
        self.sender = sender
        self.card_index = card_index
        self.card_discarded = card_discarded
        self.card_drawn = card_drawn
        return

    def __str__(self):
        sender = self.sender
        card_indx = f"Card index: {self.card_index}"
        card_discarded = f"Card discarded: {self.card_discarded.toString()}"
        if type(self.card_drawn) is UnknownCard:
            card_drawn = f"Card drawn: ?"
        elif type(self.card_drawn) is Card:
            card_drawn = f"Card drawn: {self.card_drawn.toString()}"
        return "\n".join([sender, card_indx, card_discarded, card_drawn])


class Inference:
    def __init__(self, n_cards, visible_cards: set):
        self.n_cards = n_cards
        self.my_hand = [UnknownCard(visible_cards) for _ in range(self.n_cards)]
        return

    def add_hint(self, hint: Hint):
        """Update the knowledge about the agent unknown cards.
        Also perform a negative inference, i.e. it registers
        that a certain card has not certain characteristics."""
        for i, c in enumerate(self.my_hand):
            if i in hint.positions:  # the cards is covered by the hint
                c.add_positive_knowledge(hint)
            else:  # the cards is NOT covered by the hint
                c.add_negative_knowledge(hint)
        return


class UnknownCard:
    """Represent the agent unknown card."""

    DECK_DISTR = [(1, 3), (2, 2), (3, 2), (4, 2), (5, 1)]
    RED = "red"
    YELLOW = "yellow"
    GREEN = "green"
    BLUE = "blue"
    WHITE = "white"

    COLORS = [RED, YELLOW, GREEN, BLUE, WHITE]

    def __init__(self, other_player_cards=None, table=None, discard_pile=None):
        self.received_hints = list()
        if other_player_cards is None:
            other_player_cards = set()
        if table is None:
            table = set()
        if discard_pile is None:
            discard_pile = set()
        if other_player_cards is None:
            other_player_cards = set()
        self.possible_cards = (
            UnknownCard.all_possible_cards()
            .difference(other_player_cards)
            .difference(table)
            .difference(discard_pile)
        )
        self.received_hints = list()
        self.not_received_hints = list()

    def add_positive_knowledge(self, hint: Hint):
        """This method register that the card is covered by the hint."""
        # TODO: implement hint reception
        # TODO: remove invalid possible cards after the hint
        # remove cards not corresponding to given hint
        self.received_hints.append(hint)
        not_possible_cards = set()
        for c in self.possible_cards:
            if not hint.covers(c):
                not_possible_cards.add(c)
        # remove the set of non possible cards from the set of possible cards
        self.possible_cards = self.possible_cards.difference(not_possible_cards)
        print(self.possible_cards)
        return

    def add_negative_knowledge(self, hint: Hint):
        """This method register that the card is not covered by the hint."""
        self.not_received_hints.append(hint)
        not_possible_cards = set()
        for c in self.possible_cards:
            if hint.covers(c):
                not_possible_cards.add(c)
        self.possible_cards = self.possible_cards.difference(not_possible_cards)
        print(self.possible_cards)
        return

    @staticmethod
    def all_possible_cards():
        card_set = set()
        card_id = 0
        for num, copies in UnknownCard.DECK_DISTR:
            for _, color in product(range(copies), UnknownCard.COLORS):
                # use server side Card class
                card_set.add(Card(card_id, num, color))
                card_id += 1
        return card_set


################### HANABI STATE ###################
class HanabiState:
    def __init__(self, player: str, state_data: GameData.ServerGameStateData):

        self.current_player = state_data.currentPlayer
        self.players_list = state_data.players
        logging.debug(f"Players names: {[p.name for p in self.players_list]}")
        self.used_note_tokens = state_data.usedNoteTokens
        self.used_storm_tokens = state_data.usedStormTokens
        self.table_cards = state_data.tableCards
        self.discard_pile = state_data.discardPile

        self.n_cards = 5 if len(self.players_list) <= 3 else 4
        self.my_name = player

        for t, p in enumerate(self.players_list):
            if p.name == self.my_name:
                self.my_turn = t
                self.me = p

        visible_cards = self.get_visible_cards()
        self.inference = Inference(self.n_cards, visible_cards)
        # self.hint_history =
        # <--------------------------------------

        # self.discard_history = list()
        # self.play_history = list()
        # self.error_history = list()
        # self.hint_history = list()
        # self.received_hints = list()
        return

    def get_my_turn(self):
        if self.my_turn is None:
            for t, player in enumerate(self.players_list):
                if player.name == self.my_name:
                    self.my_turn == t
        return self.my_turn

    def get_visible_cards(self) -> set:
        """Return the set of RealCard which is currently in the hands
        of the ohter players."""
        visible_cards = (
            set([c for p in self.players_list[1:] for c in p.hand])
            .union(set(self.discard_pile))
            .union(set(self.table_cards))
        )
        logging.debug(f"{visible_cards}")
        return visible_cards

    def update_state(self, new_state: GameData.ServerGameStateData):
        self.used_note_tokens = new_state.usedNoteTokens
        self.used_storm_tokens = new_state.usedStormTokens
        self.players_list = new_state.players
        self.table_cards = new_state.tableCards
        self.discard_pile = new_state.discardPile
        return

    def get_player(self, player_name: str) -> Player:
        for p in self.players_list:
            if p.name == player_name:
                return p
        return None

    def on_hint(self, hint: Hint):
        if hint.to == self.me.name:
            print(f"{self.me.name} received an hint from {hint._from}")
            self.inference.add_hint(hint)
        else:
            # TODO: add hint to hint list
            print(f"{hint._from} sent an hint to {hint.to}")
        return

    def on_play(self, play: Play):
        logging.debug(f"card drawn: {play.card_drawn}")
        # TODO: self.inference.add_visible_card(play.card_drawn)
        pass

    def on_discard(self, discard: Discard):
        # TODO: update state on discard's result
        pass

    def __str__(self):
        note_tokens = f"{self.used_note_tokens}/8"
        storm_tokens = f"{self.used_storm_tokens}/3"
        return "\n".join([str(self.players_list), note_tokens, storm_tokens])

    # def valid_hints(self, player_name: str, hint_type=None) -> list:
    #     """Return the valid hints that can be given to player `player_name`
    #     as a tuple (type, value, n_cards).
    #     TODO: add remove_known param to filter out already known hints."""
    #     hints_for_player = list()
    #     player = self.get_player(player_name)
    #     for i, c in enumerate(player.hand):
    #         card_info = [c.value, c.color]  # no card index??
    #         hints_for_player.extend(card_info)
    #     if hint_type == "color":
    #         hint_filt = lambda info: type(info) == str  # card color hint
    #     elif hint_type == "value":
    #         hint_filt = lambda info: type(info) == int  # card value hint
    #     else:
    #         return Counter(hints_for_player)
    #     hints_for_player = filter(hint_filt, hints_for_player)
    #     return Counter(hints_for_player)
