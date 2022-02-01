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
            rl.RandomHint,
            rl.PlayRandomCard,
            # rl.PlayImplicitCard,
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
        self,
        action_response: HanabiAction,
        new_state: GameData.ServerStartGameData,
    ):
        """The action is register inside the agent's state."""
        # first update client's state
        print("TEST2")
        print(new_state)
        super().update_state_with_action(action_response, new_state)
        self.hanabi_state.used_note_tokens = new_state.usedNoteTokens
        self.hanabi_state.used_storm_tokens = new_state.usedStormTokens
        # then update agent's one
        if type(action_response) is Hint:
            # an hint has been sent :^O
            self.hanabi_state.add_hint(action_response)
        elif type(action_response) is Discard:
            # a discard has been performed :^)
            # TODO: add new card drawn into the discard action
            discard = Discard(action_response)
            self.hanabi_state.add_discard(discard)
        elif type(action_response) is Play:
            # a card has been successfully played :^D
            # TODO: add new card drawn into the play action
            self.hanabi_state.add_play(action_response)
        elif type(action_response) is Play:
            # a card has been unsuccessfully played :^@
            bad_play = Play(action_response)
            self.hanabi_state.add_play(action_response)
        else:
            raise ValueError(
                f"Unexpected response received. {action_response}, {action_response.message}"
            )
        return
