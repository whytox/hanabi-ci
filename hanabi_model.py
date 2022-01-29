from argparse import ArgumentTypeError
import GameData
from game import Player
from collections import Counter
from itertools import product
from hanabi_view import card_format
from collections import Counter


class Card:
    def __init__(self, number, color, id):
        self.number = number
        self.color = color
        self.id = id
        self._str = "".join([str(self.number), self.color, str(self.id)])
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


class Inference:
    """Represent the knowledege of the Hanabi player
    about each cards of its hand and also update it
    based on a set of rules.
    """

    DECK_DISTR = [(1, 3), (2, 2), (3, 2), (4, 2), (5, 1)]
    RED = "RED"
    BLUE = "BLUE"
    GREEN = "GREEN"
    WHITE = "WHITE"
    YELLOW = "YELLOW"
    COLORS = [RED, GREEN, BLUE, WHITE, YELLOW]

    def __init__(self, other_players_hands, discard_pile=None, table=None):
        n_cards = 5 if len(other_players_hands) <= 3 else 4
        print(self.all_possible_cards())

    @staticmethod
    def all_possible_cards():
        card_set = set()
        for num, copies in Inference.DECK_DISTR:
            for _id, color in product(range(copies), Inference.COLORS):
                # print(num, c, col)
                card_set.add(Card(num, color, _id))
        return card_set


class HanabiAction:
    DISCARD = "DISCARD"
    HINT = "HINT"
    PLAY = "PLAY"

    HINT_TYPE_ARG = "HINT_TYPE"
    HINT_VALUE_ARG = "HINT_VALUE"
    HINT_SRC_ARG = "FROM"
    HINT_DEST_ARG = "DEST"
    CARD_INDEX_ARG = "CARD_INDEX"

    def __init__(self, action_type, **kwargs):
        """Valid action_params:
        - hint: hint_type and hint_value
        - discard: card_index
        - play: card_index"""
        self.action_type = action_type
        if action_type == HanabiAction.DISCARD or action_type == HanabiAction.PLAY:
            self.card_index = kwargs[HanabiAction.CARD_INDEX_ARG]
        elif action_type == HanabiAction.HINT:
            self.hint_type = kwargs[HanabiAction.HINT_TYPE_ARG]
            self.hint_value = kwargs[HanabiAction.HINT_VALUE_ARG]
            self.source = kwargs[HanabiAction.HINT_SRC_ARG]
            self.dest = kwargs[HanabiAction.HINT_DEST_ARG]
        else:
            raise ArgumentTypeError("Invalid action type.")
        return


################### HANABI STATE ###################
class HanabiState:
    def __init__(self, player: str, state_data: GameData.ServerGameStateData):

        self.player_name = player
        self.current_player = state_data.currentPlayer
        self.players_list = state_data.players
        self.n_cards = 5 if len(self.players_list) <= 3 else 4
        self.cards_inferences = Inference(self.players_list)

        # <--------------------------------------
        self.note_tokens = state_data.usedNoteTokens
        self.storm_tokens = state_data.usedStormTokens
        self.table_cards = state_data.tableCards
        self.discard_pile = state_data.discardPile
        # self.discard_history = list()
        # self.play_history = list()
        # self.error_history = list()
        # self.hint_history = list()
        # self.received_hints = list()
        return

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
        note_tokens = f"{self.note_tokens}/8"
        storm_tokens = f"{self.storm_tokens}/3"
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

    def update_with_action(
        self, action: HanabiAction, new_state: GameData.ServerGameStateData
    ):
        print(new_state)
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
