from GameData import GameData
from client import Client, Action, HanabiState
from constants import HOST, PORT
import random


# class HanabiKnowledge(HanabiState):
#     def __init__(self, player: str, state_data: GameData.ServerGameStateData):
#         super().__init__(player, state_data)
#         self.__possible_cards = list()
#         self.__init_inference()

#     def __init_inference():
#         pass


class Agent(Client):
    def __init__(self, name: str, host=HOST, port=PORT) -> None:
        super().__init__(name, host, port)

    def play(self):
        action_type = random.choice(self.game_state.valid_actions_type())
        action = self.random_action(action_type)
        self.play_action(action)
        return

    def random_action(self, action_type):
        if action_type == Action.DISCARD:
            return self.__random_discard()
        if action_type == Action.HINT:
            return self.__random_hint()
        if action_type == Action.PLAY:
            return self.__random_play()
        raise ValueError("Invali action type")

    def __random_discard(self):
        action = {}
        action["type"] = Action.DISCARD
        action["card"] = random.choice(range(self.game_state.n_cards))
        return action

    def __random_play(self):
        action = {}
        action["type"] = Action.PLAY
        action["card"] = random.choice(range(self.game_state.n_cards))
        return action

    def __random_hint(self):
        action = {}
        action["type"] = Action.HINT
        player_names = [p.name for p in self.game_state.players_list]
        destination = random.choice(player_names)
        hint_type = random.choice(["color", "value"])
        possible_hint_value = self.game_state.valid_hints(destination, hint_type)
        print(possible_hint_value)
        hint_value = random.choice(
            list(possible_hint_value.keys())
        )  # valid_hints returns also the nuber of cards
        print(hint_type, hint_value)
        action["destination"] = destination
        action["hint_type"] = hint_type
        action["hint_value"] = hint_value
        return action
