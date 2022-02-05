import logging
from client import Client
from hanabi_model import HanabiAction, HanabiState, Hint, Discard, Play
import rules as rl
import GameData


class RuleBasedAgent(Client):
    """A Client enriched with a state which tracks
    user's actions and make inferences.

    On the same state the agent performs the rule
    match to get the action to play."""

    SIGN = "_asd"

    def __init__(self, name):
        super().__init__(name + RuleBasedAgent.SIGN)
        self.rules = [
            rl.PlaySafeCard,
            rl.PlayAlmostSafeCard,
            rl.HintPlayableCard,
            rl.DiscardUselessCard,
            rl.HintUsefulChop,
            rl.HintMostUncluedCards,
            rl.HintMostCards,
            rl.HintUselessCard,
            rl.DiscardLessUsefulCard,
            rl.DiscardChop,
            rl.HintRandomCard,
            rl.DiscardRandomCard,
            rl.PlayLessRiskyCard,
        ]
        self.hanabi_state = None

    def get_action_to_be_played(self) -> HanabiAction:
        for rule in self.rules:
            print(rule)
            action = rule.match(self.hanabi_state)
            if action is not None:
                return action
        return

    def _init_game_state(self, state: GameData.ServerStartGameData):
        super()._init_game_state(state)
        if self.hanabi_state is not None:
            return

        self.hanabi_state = HanabiState(self.player_name, state)
        print(self.hanabi_state)
        return

    def update_state_with_action(
        self,
        action_response: HanabiAction,
        new_state: GameData.ServerGameStateData,
    ):
        """The action is register inside the agent's state."""

        super().update_state_with_action(action_response, new_state)

        self.hanabi_state.update_state(new_state)
        logging.debug(f"{action_response}")
        if type(action_response) is Hint:
            # an hint has been sent :^O
            self.hanabi_state.on_hint(action_response)
        elif type(action_response) is Discard:
            # a discard has been performed :^)
            self.hanabi_state.on_discard(action_response)
        elif type(action_response) is Play:
            # a card has been successfully played :^D
            self.hanabi_state.on_play(action_response)
        else:
            raise ValueError(
                f"Unexpected response received. {action_response}, {action_response.message}"
            )
        return
