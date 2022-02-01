from abc import ABC
from turtle import position
from unittest import result

from numpy import real

import GameData
from game import Game, Player
from itertools import product

import logging

logging.basicConfig(format="%(message)s", level=logging.DEBUG)


class RealCard:
    """Represent a card whose informations are completely known."""

    def __init__(self, number, color, id):
        self.number = number
        self.color = color
        self.id = id
        self._str = ".".join([str(self.number), self.color, str(self.id)])
        # use uniqueness of string representation
        self._hash = hash(self._str)

    def __hash__(self) -> int:
        """We need an hash function to work with
        Sets of cards...
        I hope this work"""
        return self._hash

    def __str__(self):
        return self._str

    def __repr__(self):
        """useful when printing Set of cards"""
        return self._str


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
        self.positions = None

    @staticmethod
    def from_hint_data(data: GameData.ServerHintData):
        _from = data.sender
        to = data.destination
        _type = data.type
        value = data.value
        positions = data.positions
        return Hint(_from, to, _type, value, positions)


class Play(HanabiAction):
    THUNDERSTRIKE = "⚡️"
    GOOD_MOVE = "👍🏻"

    def __init__(self, sender: str, card_index: int, real_card=None, result=None):
        self.sender = sender
        self.card_index = card_index
        self.result = result
        self.real_card = real_card

    @staticmethod
    def from_good_move(data: GameData.ServerPlayerMoveOk):
        sender = data.sender
        card_index = data.cardHandIndex
        real_card = data.card
        result = Play.GOOD_MOVE
        return Play(sender, card_index, real_card, result)

    @staticmethod
    def from_thunderstrike(data: GameData.ServerPlayerThunderStrike):
        sender = data.sender
        card_index = data.cardHandIndex
        real_card = data.card
        result = Play.THUNDERSTRIKE
        return Play(sender, card_index, real_card, result)


class Discard(HanabiAction):
    def __init__(
        self,
        sender: Player,
        card_index: int,
        card_discarded: RealCard,
        card_drawn: RealCard,
    ):
        pass


class Inference:
    def __init__(self, n_cards, visible_cards: set):
        self.n_cards = n_cards
        self.my_hand = [UnknownCard(visible_cards) for _ in range(self.n_cards)]
        pass

    def add_hint(self, hint: Hint):

        pass


class UnknownCard:
    """Represent the agent unknown card."""

    DECK_DISTR = [(1, 3), (2, 2), (3, 2), (4, 2), (5, 1)]
    RED = "RED"
    BLUE = "BLUE"
    GREEN = "GREEN"
    WHITE = "WHITE"
    YELLOW = "YELLOW"
    COLORS = [RED, GREEN, BLUE, WHITE, YELLOW]

    def __init__(self, other_player_cards: set, table=None, discard_pile=None):
        self.received_hints = list()
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

    def add_hint(self, hint: Hint):
        # TODO: implement hint reception
        # TODO: remove invalid possible cards after the hint
        pass

    @staticmethod
    def all_possible_cards():
        card_set = set()
        for num, copies in UnknownCard.DECK_DISTR:
            for _id, color in product(range(copies), UnknownCard.COLORS):
                # print(num, c, col)
                # TODO: does this id work with server implementation?
                # use server implementation in case it doesn't
                card_set.add(RealCard(num, color, _id))
        return card_set


# class HanabiAction:
#     DISCARD = "DISCARD"
#     HINT = "HINT"
#     PLAY = "PLAY"

#     HINT_TYPE_ARG = "HINT_TYPE"
#     HINT_TYPE_VALUE = "VALUE_HINT"
#     HINT_TYPE_COLOR = "COLOR_HINT"
#     HINT_VALUE_ARG = "HINT_VALUE"
#     HINT_SRC_ARG = "SOURCE"
#     HINT_DEST_ARG = "DEST"
#     CARD_INDEX_ARG = "CARD_INDEX"

#     def __init__(self, action_type, **kwargs):
#         """Valid action_params:
#         - hint: hint_type and hint_value
#         - discard: card_index
#         - play: card_index"""
#         self.action_type = action_type
#         if action_type == HanabiAction.DISCARD or action_type == HanabiAction.PLAY:
#             self.card_index = kwargs[HanabiAction.CARD_INDEX_ARG]
#         elif action_type == HanabiAction.HINT:
#             self.hint_type = kwargs[HanabiAction.HINT_TYPE_ARG]
#             self.hint_value = kwargs[HanabiAction.HINT_VALUE_ARG]
#             self.source = kwargs[HanabiAction.HINT_SRC_ARG]
#             self.dest = kwargs[HanabiAction.HINT_DEST_ARG]
#         else:
#             raise ArgumentTypeError("Invalid action type.")
#         return


#    @staticmethod
#    def new_hint(_from:Player, to: Player, _type: str, value):
#        """Return a new HanabiAction of type HINT"""
#        return HanabiAction(HanabiAction.HINT, HanabiAction.HINT_SRC_ARG=_from,
#        )

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
        print(f"I am {self.me.name}")
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
        # TODO: check if agent is included in player list and is effectively the firs
        visible_cards = (
            set([c for p in self.players_list[1:] for c in p.hand])
            .union(set(self.discard_pile))
            .union(set(self.table_cards))
        )
        logging.debug(f"{visible_cards}")

    # @staticmethod
    # def from_server_data(player_name, state: GameData.ServerGameStateData):
    #     current_player = state.currentPlayer
    #     players = state.players
    #     used_storm_tokens = state.usedStormTokens
    #     used_note_tokens = state.usedNoteTokens
    #     table_cards = state.tableCards
    #     discard_pile = state.discardPile
    #     return

    def __str__(self):
        # players_hands = "\n".join(
        #    [self.__player_hand(player) for player in self.players_list]
        # )
        note_tokens = f"{self.used_note_tokens}/8"
        storm_tokens = f"{self.used_storm_tokens}/3"
        return "\n".join([str(self.players_list), note_tokens, storm_tokens])

    # def valid_actions_type(self) -> list:
    #     playable_actions = [Action.DISCARD, Action.PLAY]
    #     if self.note_tokens < 8:
    #         playable_actions.append(Action.HINT)
    #     return playable_actions

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

    def get_player(self, player_name: str) -> Player:
        for p in self.players_list:
            if p.name == player_name:
                return p
        return None

    def add_hint(self, hint: Hint):
        if hint.to == self.me.name:
            self.inference.add_hint(hint)
        else:
            # TODO: add hint to hint list
            pass

    def add_play(self, play: Play):
        pass

    def get_next_player_hand(self):
        for p in self.players_list:
            pass

    # def
    # def add_hint(self, hint_data: GameData.ServerHintData):
    #     self.hint_history.append(hint_data)
    #     if hint_data.__delattr__() == self.player_name:
    #         self.received_hints.append(hint_data)
    #         for p in hint_data.positions:
    #             self.hand_info[p][hint_data.type] = hint_data.value
    #     return

    # def add_play(self, play_data: GameData.ServerPlayerMoveOk):
    #     self.play_history.append(play_data)
    #     # self.current_player =
    #     return

    # def add_error(self, error_data: GameData.ServerPlayerThunderStrike):
    #     self.error_history.append(error_data)
    #     return
