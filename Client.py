from abc import ABC, abstractmethod
import logging
import socket
import GameData
from constants import HOST, PORT, DATASIZE
from sys import stdout
from hanabi_model import HanabiAction, Play, Discard, Hint, UnknownCard

logging.basicConfig(
    format="[%(asctime)s] %(levelname)s: %(message)s",
    datefmt="%H:%M:%S",
    level=logging.INFO,
)


class ClientState:
    NOT_CONNECTED = "NOT CONNECTED"
    CONNECTED = "CONNECTED"
    LOBBY = "LOBBY"
    IN_GAME = "IN GAME"
    GAME_OVER = "GAME OVER"


################### CLIENT ###################
class Client(ABC):
    """A class encapsulating some methods to comunicate with the server."""

    def __init__(self, name, host=HOST, port=PORT):
        self.player_name = name
        self.host = host
        self.port = port
        self.socket = None
        self.state = ClientState.NOT_CONNECTED
        self.current_player = None
        # self.player_order = None
        self.__connect()

    def __connect(self):
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.connect((self.host, self.port))
        connection_request = GameData.ClientPlayerAddData(self.player_name)
        self.__send_request(connection_request)
        response = self.__read_response()
        if type(response) is GameData.ServerPlayerConnectionOk:
            self.state = ClientState.CONNECTED
            logging.info(
                f"Connection accepted by the server. Welcome {self.player_name}"
            )
        else:
            raise ConnectionError("There was an error while connecting to the server.")
        return

    def __read_response(self) -> GameData.ServerToClientData:
        """Read the next server response."""
        data = self.socket.recv(DATASIZE)
        response = GameData.GameData.deserialize(data)
        return response

    def __send_request(self, request: GameData.ClientToServerData):
        """Send the specified request to the server."""
        self.socket.send(request.serialize())
        return

    def __send_status(self):
        """Send a status request to the server"""
        request = GameData.ClientGetGameStateRequest(self.player_name)
        self.__send_request(request)
        return

    def send_start(self):
        if self.state != ClientState.CONNECTED:
            raise RuntimeError("You must be connected")

        start_request = GameData.ClientPlayerStartRequest(self.player_name)
        self.__send_request(start_request)
        response = self.__read_response()
        if type(response) is GameData.ServerPlayerStartRequestAccepted:
            self.state = ClientState.LOBBY
            logging.info(
                msg=f"{self.player_name} - Ready: {response.acceptedStartRequests}/{response.connectedPlayers}"
            )
        else:
            raise ConnectionError("Invalid response received on Start request.")
        return

    def wait_start(self):
        if self.state != ClientState.LOBBY:
            raise RuntimeError("You have to be in the lobby")
        # read until it's a ServerStart
        while self.state != ClientState.IN_GAME:
            response = self.__read_response()
            if type(response) is GameData.ServerStartGameData:
                ready_request = GameData.ClientPlayerReadyData(self.player_name)
                self.__send_request(ready_request)
                self.state = ClientState.IN_GAME

                state = self.fetch_state()
                self._init_game_state(state)

                logging.debug(msg="{self.player_name} - ready request sent")
                logging.info(msg=f"{self.player_name} - Game started")
                logging.info(msg=f"{self.player_name}")
            logging.debug(msg=f"response received: {response} of type {type(response)}")
        return True

    @abstractmethod
    def _init_game_state(self, state: GameData.ServerGameStateData):
        self.current_player = state.currentPlayer
        return

    def run(self):
        if self.state != ClientState.IN_GAME:
            return
        s = self.socket
        while self.state == ClientState.IN_GAME:
            if self.current_player == self.player_name:
                action = self.get_action_to_be_played()  # implemented by agent subclass
                action_result, new_state = self.__play_action(action)
            else:
                action_result, new_state = self.fetch_action_result()
            if action_result is not None:  # possbible for game over
                self.update_state_with_action(action_result, new_state)
            stdout.flush()
        return

    @abstractmethod
    def get_action_to_be_played(self):
        """Return the action to be played.
        Implemented by the agent subclass."""
        raise NotImplementedError

    def __play_action(self, action: HanabiAction):
        if type(action) is Play:
            self.__play_card(action)
        elif type(action) is Discard:
            self.__discard_card(action)
        elif type(action) is Hint:
            self.__give_hint(action)
        else:
            raise TypeError(f"Inappropriate action type: {action}")
        # check server response:
        action_result, new_state = self.fetch_action_result()
        return action_result, new_state

    def __discard_card(self, discard: Discard):
        """Send the appropriate request to play the given card."""
        if self.state == ClientState.IN_GAME:
            discard_req = GameData.ClientPlayerDiscardCardRequest(
                self.player_name, discard.card_index
            )
            self.__send_request(discard_req)
        return

    def __play_card(self, play: Play):
        if self.state != ClientState.IN_GAME:
            return
        play_req = GameData.ClientPlayerPlayCardRequest(
            self.player_name, play.card_index
        )
        self.__send_request(play_req)
        return

    def __give_hint(self, hint: Hint):
        if self.state == ClientState.IN_GAME:
            hint_req = GameData.ClientHintData(
                self.player_name, hint.to, hint._type, hint.value
            )
            self.__send_request(hint_req)
        return

    def fetch_action_result(self) -> tuple:
        """Return a tuple (HanabiAction, GameData.ServerGameStateData)
        The first element is the action performed.
        The second element is the new game state after the move has been played.
        # when a player perform an action the server will:
        # - send ServerInvalidAction or ServerInvalidData
        #  if the action/data is not valid, but only to the current user
        # (for all kind of moves)
        # - hint: send ServerHintData
        # - discard: send ServerActionValid
        #   requires a state fetch
        # - play: send either ServerPlayerThunderStrike, ServerPlayerMoveOk
        #   requires a state fetch
        """
        response = self.__read_response()

        if type(response) is GameData.ServerActionInvalid:
            raise ValueError(f"ActionInvalid received: {response.message}")
        elif type(response) is GameData.ServerInvalidDataReceived:
            raise ValueError(f"InvalidData received: {response.data}")
        elif type(response) is GameData.ServerGameOver:
            logging.info("The game is over.")
            self.state = ClientState.GAME_OVER
            return None, None

        logging.debug(response)
        new_state = self.fetch_state()
        played_action = self.build_action_from_server_response(response, new_state)
        return (played_action, new_state)

    def fetch_state(self) -> GameData.ServerGameStateData:
        """Send a ClientGetGameStateRequest and return the
        received ServerGameStateData."""
        if self.state != ClientState.IN_GAME:
            raise RuntimeError("You must be in game")
        self.__send_status()
        response = self.__read_response()
        while not type(response) is GameData.ServerGameStateData:
            response = self.__read_response()
        return response
        # raise ValueError(f"Invalid state received. {response} received.")

    @abstractmethod
    def update_state_with_action(
        self,
        played_action: GameData.ServerToClientData,
        new_state: GameData.ServerGameStateData,
    ):
        """Update current player"""
        self.current_player = new_state.currentPlayer
        return

    def build_action_from_server_response(
        self, data: GameData.ServerToClientData, new_state: GameData.ServerToClientData
    ):
        """Create an Hanabi action from the server response and the new state after the action"""

        if type(data) is GameData.ServerHintData:
            # an hint has been sent :^O
            sender = data.source
            destination = data.destination
            _type = data.type
            value = data.value
            positions = data.positions
            return Hint(sender, destination, _type, value, positions)

        elif type(data) is GameData.ServerActionValid:
            # a discard has been performed :^)
            # include the drawn card in the created Discard action
            sender = data.lastPlayer
            card_index = data.cardHandIndex
            card_discarded = data.card
            card_drawn = self.get_new_sender_card(sender, new_state, card_index)
            return Discard(sender, card_index, card_discarded, card_drawn)

        elif type(data) is GameData.ServerPlayerMoveOk:
            # a card has been successfully played :^D
            sender = data.lastPlayer
            card_index = data.cardHandIndex
            real_card = data.card
            card_drawn = self.get_new_sender_card(sender, new_state, card_index)
            result = Play.GOOD_MOVE
            return Play(sender, card_index, real_card, card_drawn, result)

        elif type(data) is GameData.ServerPlayerThunderStrike:
            # a card has been unsuccessfully played :^@
            sender = data.lastPlayer
            card_index = data.cardHandIndex
            real_card = data.card
            card_drawn = self.get_new_sender_card(sender, new_state, card_index)
            result = Play.THUNDERSTRIKE
            return Play(sender, card_index, real_card, card_drawn, result)
        else:
            raise ValueError("Invalid action response: {data}")

    def get_new_sender_card(
        self, sender: str, new_state: GameData.ServerGameStateData, card_index: int
    ):
        if sender == self.player_name:
            return UnknownCard()
        for p in new_state.players:
            if p.name == sender:
                return p.hand[-1]  # drawn card are appended to the player hand
        raise ValueError("Unable to fetch the new drawn card!!")
