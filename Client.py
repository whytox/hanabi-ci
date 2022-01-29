from abc import ABC, abstractmethod
import logging
import socket
from urllib import response
import GameData
from constants import HOST, PORT, DATASIZE
import argparse
from sys import stdout
from hanabi_model import HanabiAction, HanabiState

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
        if self.__response_of_type(response, GameData.ServerPlayerConnectionOk):
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

    def __response_of_type(
        self, response: GameData.ServerToClientData, response_class
    ) -> bool:
        """Return True if the given response is of the specified type.
        Probably useless..."""
        if type(response) is response_class:
            return True
        return False

    def __send_request(self, request: GameData.ClientToServerData):
        """Send the specified request to the server."""
        self.socket.send(request.serialize())
        print("request sent")
        return

    # def __send_ready(self):
    #     """Send a ready request to the server."""
    #     request = GameData.ClientPlayerReadyData(self.player_name)
    #     self.__send_request(request)
    #     return

    # def __send_start(self):
    #     """Send a start request to the server."""
    #     request = GameData.ClientPlayerStartRequest(self.player_name)
    #     self.__send_request(request)
    #     return

    def __send_status(self):
        """Send a status request to the server"""
        request = GameData.ClientGetGameStateRequest(self.player_name)
        self.__send_request(request)
        return

    def __send_action(self, action):
        pass

    # TODO: refactor to `ready``
    def send_start(self):
        if self.state != ClientState.CONNECTED:
            print("You must be connected")
            return

        start_request = GameData.ClientPlayerStartRequest(self.player_name)
        self.__send_request(start_request)
        response = self.__read_response()
        if self.__response_of_type(response, GameData.ServerPlayerStartRequestAccepted):
            self.state = ClientState.LOBBY
            logging.info(
                msg=f"{self.player_name} - Ready: {response.acceptedStartRequests}/{response.connectedPlayers}"
            )
        else:
            raise ConnectionError("Invalid response received on Start request.")
        return

    # TODO: refactor to `start`
    # TODO: make this code more readable
    def wait_start(self):
        if self.state != ClientState.LOBBY:
            print("You have to be in the lobby")
            return
        # read until it's a ServerStart
        while self.state != ClientState.IN_GAME:
            response = self.__read_response()
            if self.__response_of_type(response, GameData.ServerStartGameData):
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

    # TODO: must be updated to be passed to the Agent
    # that it creates an HanabiState
    # HanabiState.from_game_data(Server)
    @abstractmethod
    def _init_game_state(self, state: GameData.ServerGameStateData):
        print("client state init")
        self.current_player = state.currentPlayer
        # self.player_order = state.players
        return

    def run(self):
        if self.state != ClientState.IN_GAME:
            return
        s = self.socket
        while self.state == ClientState.IN_GAME:
            print(self.current_player)
            if self.current_player == self.player_name:
                action = self.get_action_to_be_played()  # implemented by agent subclass
                self.__play_action(action)
            else:
                action, new_state = self.fetch_action_result()
                print("TEST1")
                self.update_state_with_action(action, new_state)
            # TODO: check for game over
            stdout.flush()
        return

    @abstractmethod
    def get_action_to_be_played(self):
        """Return the action to be played.
        Implemented by the agent subclass."""
        raise NotImplementedError

    def __play_action(self, action: HanabiAction):
        if action.action_type == HanabiAction.PLAY:
            return self.__play_card(action.card_index)
        elif action.action_type == HanabiAction.DISCARD:
            return self.__discard_card(action.card_index)
        elif action.action_type == HanabiAction.HINT:
            return self.__give_hint(action.dest, action.hint_type, action.hint_value)
        raise TypeError("Inappropriate action type.")

    def __discard_card(self, card: int):
        """Send the appropriate request to play the given card."""
        if self.state == ClientState.IN_GAME:
            discard_req = GameData.ClientPlayerDiscardCardRequest(self.playerName, card)
            self.__send_request(discard_req)
        return

    def __play_card(self, card: int):
        if self.state != ClientState.IN_GAME:
            return
        play_req = GameData.ClientPlayerPlayCardRequest(self.playerName, card)
        self.__send_request(play_req)

        # verify answer
        response = self.__read_response()
        if self.__response_of_type(response, GameData.ServerPlayerMoveOk):
            logging.info(
                f"{self.playerName} - correctly played card {card}: {response.card}"
            )
            self.game_state.add_play(response)
            return True
        elif self.__response_of_type(response, GameData.ServerPlayerThunderStrike):
            self.game_state.add_error(response)
            return True
        elif self.__response_of_type(response, GameData.ServerActionInvalid):
            return False
        return False

    def __give_hint(self, destination: str, hint_type: str, hint_value: str):
        if self.state == ClientState.IN_GAME:
            hint_req = GameData.ClientHintData(
                self.playerName, destination, hint_type, hint_value
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
        if self.__response_of_type(response, GameData.ServerHintData):
            # an hint has been sent :^O
            action = HanabiAction.from_hint_data(response)
        elif self.__response_of_type(response, GameData.ServerActionValid):
            # a discard has been performed :^)
            action = HanabiAction.from_action_valid(response)
        elif self.__response_of_type(response, GameData.ServerPlayerMoveOk):
            # a card has been successfully played :^D
            action = HanabiAction.from_good_move(response)
            pass
        elif self.__response_of_type(response, GameData.ServerPlayerThunderStrike):
            # a card has been unsuccessfully played :^@
            action = HanabiAction.from_thunder_strike(response)
        else:
            raise ValueError("Unexpected response received.")
        new_state = self.fetch_state()
        return (action, new_state)

    def fetch_state(self) -> GameData.ServerGameStateData:
        """Send a ClientGetGameStateRequest and return the
        received ServerGameStateData."""
        if self.state != ClientState.IN_GAME:
            print("You must be in game")
            return
        self.__send_status()
        response = self.__read_response()
        if self.__response_of_type(response, GameData.ServerGameStateData):
            return response
        raise ValueError("Invalid state received.")

    @abstractmethod
    def update_state_with_action(
        self, action: HanabiAction, new_state: GameData.ServerGameStateData
    ):
        """Update current player"""
        self.current_player = new_state.currentPlayer
        return


clientParser = argparse.ArgumentParser()

clientParser.add_argument(
    "name", type=str, help="The name used by the player", default="s289902"
)
clientParser.add_argument("--host", type=str, default=HOST)
clientParser.add_argument("--port", type=int, default=PORT)

# computerParser = argparse.ArgumentParser(parents=[clientParser])
# computerParser.add_argument("-n", type=int, help="Number of #computer players to create")
