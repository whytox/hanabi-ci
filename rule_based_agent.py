from client import Client
from hanabi_model import HanabiAction, HanabiState
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
            rl.TestHint,
            rl.PlaySafeCard,
            rl.PlayImplicitCard,
            # rl.GivePlayClue,
            # rl.GiveSaveClue,
            # rl.DiscardChopCard,
        ]
        self.hanabi_state = None

    def get_action_to_be_played(self) -> HanabiAction:
        for rule in self.rules:
            action = rule.match(self.hanabi_state)
            if action is not None:
                return action
        # no matching rule xD
        # go random?
        return

    def _init_game_state(self, state: GameData.ServerStartGameData):
        super()._init_game_state(state)
        print("agent state init")
        if self.hanabi_state is not None:
            return

        self.hanabi_state = HanabiState(self.player_name, state)
        print(self.hanabi_state)
        return

    def update_state_with_action(
        self, action: HanabiAction, new_state: GameData.ServerStartGameData
    ):
        """The action is register inside the agent's state."""
        # first update client's state
        print("TEST2")
        print(new_state)
        super().__update_state_with_action(action, new_state)
        # then update agent's one
        self.hanabi_state.update_with_action(action, new_state)
        # TODO: implement inference
