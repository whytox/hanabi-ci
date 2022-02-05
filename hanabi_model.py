from abc import ABC
from dis import dis
from typing_extensions import Self
import GameData
from game import Player, Card
from itertools import product
from collections import Counter
import logging

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

    def __str__(self) -> str:
        _str = f"{self.sender} plays cards at index {self.card_index}"
        if self.real_card is not None:
            _str += f" which is {self.real_card}"
        if self.card_drawn is not None:
            _str += f" and drawn {self.card_drawn}"
        if self.result is not None:
            _str += f"\nResult: {self.result}"
        return _str

    def __repr__(self) -> str:
        return self.__str__()


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
    def __init__(
        self,
        state,
        n_cards,
        other_players_card: set,
        playable_cards: set(),
    ):
        self.state = state
        self.n_cards = n_cards
        self.visible_cards = other_players_card
        self.my_hand = [UnknownCard(self.visible_cards) for _ in range(self.n_cards)]
        self.not_trusted_players = set()
        self.chop_index = 0
        self.playable_cards = playable_cards
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

        # update the chop after adding the hint to the cards
        if self.chop_index in hint.positions:
            cards_clues = list(map(lambda c: c.is_hinted(), self.my_hand))
            if False in cards_clues:  # if there are unclued cards
                self.chop_index = cards_clues.index(False)  # the first unclued
            else:
                self.chop_index = None  # no discardable card
        return

    def wrong_play(self, play: Play):
        # I'am here cause I played a bad card
        for card_index, hint_sender in self.implicit_playable:
            # was it an implicit playable?
            if play.card_index == card_index:
                # then put the sender in the list of untrusted player
                self.not_trusted_players.add(hint_sender)
        return

    # def check_hint_trust(self, hint: Hint, real_card, playable_cards):
    #     """Check if the hint is given in accordance to the conventions."""
    #     if not real_card in playable_cards and not :
    #         self.not_trusted_players.add(hint._from)
    #     return

    def add_new_unknown_card(self, hanabi_action: HanabiAction):
        """Create a new unknown card after a previous one has
        been played or discarded."""
        card_index = hanabi_action.card_index
        # the new card is placed at the end of the player hand
        # so: remove the played card and append an unknown card at the end
        self.my_hand = self.my_hand[:card_index] + self.my_hand[card_index + 1 :]
        if type(hanabi_action) is Discard:
            self.add_visible_card(hanabi_action.card_discarded)
        elif type(hanabi_action) is Play:
            self.add_visible_card(hanabi_action.real_card)
        self.my_hand.append(UnknownCard(self.visible_cards))
        return

    def add_visible_card(self, card: Card):
        """Add a new visible card to the set of visible cards."""
        self.visible_cards.add(card)
        for u in self.my_hand:
            u.remove_possible(card)
        return


class UnknownCard:
    """Represent the agent unknown card."""

    DECK_DISTR = {1: 3, 2: 2, 3: 2, 4: 2, 5: 1}
    RED = "red"
    YELLOW = "yellow"
    GREEN = "green"
    BLUE = "blue"
    WHITE = "white"

    COLORS = [RED, YELLOW, GREEN, BLUE, WHITE]

    def __init__(self, not_possible_cards=None):
        if not_possible_cards is None:
            not_possible_cards = set()

        self.possible_cards = UnknownCard.all_possible_cards().difference(
            not_possible_cards
        )
        if not self.possible_cards:
            raise ValueError(f"Empty possible cards, but {not_possible_cards} given")
        self.received_hints = list()
        self.not_received_hints = list()
        self.implicit_possible_cards = dict()  # sender: possible_implicit

    # TODO: merge the two following methods in a single one
    def add_positive_knowledge(self, hint: Hint):
        """This method register that the card is covered by the hint."""
        # remove cards not corresponding to given hint
        self.received_hints.append(hint)
        not_possible_cards = set()
        for c in self.possible_cards:
            if not hint.covers(c):
                not_possible_cards.add(c)
        # remove the set of non possible cards from the set of possible cards
        self.possible_cards = self.possible_cards.difference(not_possible_cards)
        return

    def add_negative_knowledge(self, hint: Hint):
        """This method register that the card is not covered by the hint."""
        self.not_received_hints.append(hint)
        not_possible_cards = set()
        for c in self.possible_cards:
            if hint.covers(c):
                not_possible_cards.add(c)
        self.possible_cards = self.possible_cards.difference(not_possible_cards)
        return

    def remove_possible(self, card: Card):
        if card in self.possible_cards:
            self.possible_cards.remove(card)
        return

    def is_hinted(self):
        """Return True if at least an  hint has been received."""
        return bool(self.received_hints)

    @staticmethod
    def all_possible_cards():
        card_set = set()
        card_id = 0
        for num, copies in UnknownCard.DECK_DISTR.items():
            for _, color in product(range(copies), UnknownCard.COLORS):
                # use server side Card class
                card_set.add(Card(card_id, num, color))
                card_id += 1
        return card_set

    NUM_BASE_IDS = {1: 0, 2: 15, 3: 25, 4: 35, 5: 45}

    @staticmethod
    def possible_cards_with_number(number: int):
        cards = set()
        id = UnknownCard.NUM_BASE_IDS[number]
        for _, color in product(
            range(UnknownCard.DECK_DISTR[number]), UnknownCard.COLORS
        ):
            cards.add(Card(id, number, color))
            id += 1
        return cards

    COLOR_BASE_IDS = {RED: 0, YELLOW: 1, GREEN: 2, BLUE: 3, WHITE: 4}

    @staticmethod
    def possible_cards_with_color(color: str):
        cards = set()
        id = UnknownCard.COLOR_BASE_IDS[color]
        for number in range(1, 6):
            for _ in range(UnknownCard.DECK_DISTR[number]):
                cards.add(Card(id, number, color))
                id += 5
        return cards

    @staticmethod
    def possible_cards_with_info(number: int, color: str):
        color_set = UnknownCard.possible_cards_with_color(color)
        number_set = UnknownCard.possible_cards_with_number(number)
        return number_set & color_set

    def __str__(self):
        return "?" if len(self.possible_cards) == 50 else str(self.possible_cards)

    def __repr__(self) -> str:
        return self.__str__()


################### HANABI STATE ###################
class HanabiState:
    def __init__(self, player: str, state_data: GameData.ServerGameStateData):

        self.current_player = state_data.currentPlayer
        self.players_list = state_data.players
        self.used_note_tokens = state_data.usedNoteTokens
        self.used_storm_tokens = state_data.usedStormTokens
        self.table_cards = state_data.tableCards
        self.discard_pile = set(state_data.discardPile)

        # the first index is the player (in turn order)
        self.other_players_hints = {player.name: set() for player in self.players_list}
        # tracks the info received by clued players' cards
        # dict: Cards: (number, color)
        self.cards_known_infos = dict()

        self.n_cards = 5 if len(self.players_list) <= 3 else 4
        self.my_name = player

        for t, p in enumerate(self.players_list):
            if p.name == self.my_name:
                self.my_turn = t
                self.me = p

        visible_cards = self.get_visible_cards()
        self.inference = Inference(
            self, self.n_cards, visible_cards, self.get_valid_playable_cards()
        )

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
        self.discard_pile = set(new_state.discardPile)
        self.inference.playable_cards = self.get_valid_playable_cards()
        return

    def get_player(self, player_name: str) -> Player:
        for p in self.players_list:
            if p.name == player_name:
                return p
        return None

    def on_hint(self, hint: Hint):
        if hint.to == self.me.name:
            logging.debug(f"{self.me.name} received an hint from {hint._from}")
            self.inference.add_hint(hint)
        else:
            logging.debug(f"{hint._from} sent an hint to {hint.to}")
            receiver_hand = self.get_player(hint.to).hand
            for p in hint.positions:
                try:
                    self.other_players_hints[hint.to].add(receiver_hand[p])
                except IndexError:
                    pass  # that hurts
        return

    def on_play(self, play: Play):
        logging.debug(f"card drawn: {play.card_drawn}")

        if play.sender == self.my_name:
            self.inference.add_new_unknown_card(play)
        else:
            if play.real_card in self.other_players_hints[play.sender]:
                self.other_players_hints[play.sender].remove(play.real_card)
            self.inference.add_visible_card(play.card_drawn)
        return

    def on_discard(self, discard: Discard):
        if discard.sender == self.my_name:
            self.inference.add_new_unknown_card(discard)
        else:
            if discard.card_discarded in self.other_players_hints[discard.sender]:
                self.other_players_hints[discard.sender].remove(discard.card_discarded)
            self.inference.add_visible_card(discard.card_drawn)
        return

    def get_valid_playable_cards(self):
        """Return the set of all possible playable cards."""
        playable_cards = set()
        for pile_color, cards_list in self.table_cards.items():
            top_number = len(cards_list)
            if top_number == 5:
                continue  # no playable cards in this pile
            playable_cards |= (
                UnknownCard.possible_cards_with_info(top_number + 1, pile_color)
                - self.discard_pile
            )
        return playable_cards

    def get_future_playable_cards(self):
        """Return the set of cards missing to complete the game."""
        future_playable_cards = self.get_valid_playable_cards()
        for pile_color, cards_list in self.table_cards.items():
            top_number = len(cards_list)
            if top_number == 5:
                continue
            # add the cards from current playable to 5 (included)
            for required_number in range(top_number + 1, 6):
                required_cards = UnknownCard.possible_cards_with_info(
                    required_number, pile_color
                )
                # if required cards have been discarded...
                if required_cards <= self.discard_pile:
                    # the folliwing ones are not playable anymore
                    # Ex: red 2 on top but all red 3s have been discarded
                    #  => red 4s and 5s are not playable neither
                    break
                # otherwise include only cards that are not in the discard pile
                future_playable_cards |= (
                    UnknownCard.possible_cards_with_info(required_number, pile_color)
                    - self.discard_pile
                )
        return future_playable_cards

    def __str__(self):
        note_tokens = f"{self.used_note_tokens}/8"
        storm_tokens = f"{self.used_storm_tokens}/3"
        player_data = [f"{p.name}: {p.hand}" for p in self.players_list]
        return "\n".join([*player_data, note_tokens, storm_tokens])

    def get_valid_hints(
        self, player_name: str, hint_type=None, remove_clued=False
    ) -> list:
        """Return the valid hints that can be given to player `player_name`
        as a tuple (value, n_cards).
        If the value is numeric => number hint
        else if string => color hint"""
        hints_for_player = list()
        player = self.get_player(player_name)
        for i, c in enumerate(player.hand):
            if remove_clued and c in self.other_players_hints[player_name]:
                continue
            card_info = [c.value, c.color]  # no card index??
            hints_for_player.extend(card_info)
        if hint_type == "color":
            hint_filt = lambda info: type(info) == str  # card color hint
        elif hint_type == "value":
            hint_filt = lambda info: type(info) == int  # card value hint
        else:
            return Counter(hints_for_player)
        hints_for_player = filter(hint_filt, hints_for_player)
        return Counter(hints_for_player)

    def get_clued_cards(self, player: str) -> set:
        return self.other_players_hints[player]

    def get_relative_player_order(self) -> list:
        return self.players_list[self.my_turn + 1 :] + self.players_list[: self.my_turn]
