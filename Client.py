import logging
import socket
import GameData
from game import Player
from constants import HOST, PORT, DATASIZE
import argparse
from sys import stdout
from game import Game
from colorama import Fore
from collections import Counter

logging.basicConfig(
    format="[%(asctime)s] %(levelname)s: %(message)s",
    datefmt="%H:%M:%S",
    level=logging.INFO,
)

CARD_COLORS = {
    "yellow": Fore.YELLOW,
    "blue": Fore.BLUE,
    "green": Fore.GREEN,
    "red": Fore.RED,
    "white": Fore.WHITE,
}


def card_format(value: str, color: str) -> str:
    num = "?" if value is None else str(value)
    col = color
    if col is not None:
        return " ".join([CARD_COLORS[col], num, Fore.RESET])
    else:
        return num


class Status:
    NOT_CONNECTED = "NOT CONNECTED"
    CONNECTED = "CONNECTED"
    LOBBY = "LOBBY"
    IN_GAME = "IN GAME"


class Action:
    DISCARD = "DISCARD"
    HINT = "HINT"
    PLAY = "PLAY"


################### HANABI STATE ###################
class HanabiState:
    def __init__(self, player: str, state_data: GameData.ServerGameStateData):

        self.player_name = player
        self.current_player = state_data.currentPlayer
        self.players_list = state_data.players
        self.n_cards = 5 if len(self.players_list) <= 3 else 4
        self.hand_info = {
            c: {"color": None, "value": None} for c in range(self.n_cards)
        }
        self.note_tokens = state_data.usedNoteTokens
        self.storm_tokens = state_data.usedStormTokens
        self.table_cards = state_data.tableCards
        self.discard_pile = state_data.discardPile
        self.discard_history = list()
        self.play_history = list()
        self.error_history = list()
        self.hint_history = list()
        self.received_hints = list()
        return

    def add_hint(self, hint_data: GameData.ServerHintData):
        self.hint_history.append(hint_data)
        if hint_data.__delattr__() == self.player_name:
            self.received_hints.append(hint_data)
            for p in hint_data.positions:
                self.hand_info[p][hint_data.type] = hint_data.value
        return

    def add_play(self, play_data: GameData.ServerPlayerMoveOk):
        self.play_history.append(play_data)
        self.current_player = 
        return

    def add_error(self, error_data: GameData.ServerPlayerThunderStrike):
        self.error_history.append(error_data)
        return

    def __str__(self):
        players_hands = "\n".join(
            [self.__player_hand(player) for player in self.players_list]
        )
        note_tokens = f"{self.note_tokens}/8"
        storm_tokens = f"{self.storm_tokens}/3"
        return "\n".join([players_hands, note_tokens, storm_tokens])

    def __player_hand(self, player: Player) -> str:
        """Return a string representation of the player hand"""
        card_str = []
        if player.name == self.player_name:
            for _, info in self.hand_info.items():
                s = card_format(info["value"], info["color"])
                card_str.append(s)
        else:
            for card in player.hand:
                s = card_format(card.value, card.color)
                card_str.append(s)
        return f"{player.name}: {' '.join(card_str)}"

    def is_my_turn(self):
        return self.current_player == self.player_name

    def update_needed(self):
        return False

    def valid_actions_type(self) -> list:
        playable_actions = [Action.DISCARD, Action.PLAY]
        if self.note_tokens < 8:
            playable_actions.append(Action.HINT)
        return playable_actions

    def valid_hints(self, player_name: str, hint_type=None) -> list:
        """Return the valid hints that can be given to player `player_name`
        as a tuple (type, value, n_cards).
        TODO: add remove_known param to filter out already known hints."""
        possible_hints = list()
        player = self.get_player(player_name)
        if hint_type == "color":
            card_info = lambda c: [c.color]
        elif hint_type == "value":
            card_info = lambda c: [c.value]
        else:
            card_info = lambda c: [c.value, c.color]
        for c in player.hand:
            possible_hints += card_info(c)
        return Counter(possible_hints)

    def get_player(self, player_name: str) -> Player:
        for p in self.players_list:
            if p.name == player_name:
                return p
        return None


################### CLIENT ###################
class Client:
    def __init__(self, name, host=HOST, port=PORT):
        self.playerName = name
        self.host = host
        self.port = port
        self.socket = None
        self.status = Status.NOT_CONNECTED
        self.game_state = None
        self.must_update_state = True
        self.running = False
        self.__init_connection()

    def __init_connection(self):
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.connect((self.host, self.port))
        connection_request = GameData.ClientPlayerAddData(self.playerName)
        self.socket.send(connection_request.serialize())
        data = self.socket.recv(DATASIZE)
        data = GameData.GameData.deserialize(data)
        if type(data) is GameData.ServerPlayerConnectionOk:
            self.status = Status.CONNECTED
            logging.info(
                f"Connection accepted by the server. Welcome {self.playerName}"
            )
        else:
            raise ConnectionError("There was an error while connecting to the server.")
        return

    def send_ready(self):
        if self.status != Status.CONNECTED:
            print("You must be connected")
            return

        ready_request = GameData.ClientPlayerStartRequest(self.playerName)
        self.socket.send(ready_request.serialize())
        data = self.socket.recv(DATASIZE)
        data = GameData.GameData.deserialize(data)
        if type(data) is GameData.ServerPlayerStartRequestAccepted:
            self.status = Status.LOBBY
            logging.info(
                msg=f"{self.playerName} - Ready: {data.acceptedStartRequests}/{data.connectedPlayers}"
            )
        return

    def wait_start(self):
        if self.status != Status.LOBBY:
            print("You have to be in the lobby")
            return
        # read until it's a ServerStart
        while self.status != Status.IN_GAME:
            data = self.socket.recv(DATASIZE)
            data = GameData.GameData.deserialize(data)
            if type(data) is GameData.ServerStartGameData:
                confirm = GameData.ClientPlayerReadyData(self.playerName)
                self.socket.send(confirm.serialize())
                logging.debug(msg="{self.playerName} - ready request sent")
                self.status = Status.IN_GAME
                logging.info(msg=f"{self.playerName} - Game started")
                self.__init_game_state()
                logging.info(msg=f"{self.playerName} - State:\n{self.game_state}")
            logging.debug(msg=f"response received: {data} of type {type(data)}")
        return True

    def __init_game_state(self):
        logging.info(f"{self.playerName} - sending status request")
        if self.game_state is None:
            state_data = self.fetch_state()
            self.game_state = HanabiState(self.playerName, state_data)
        else:
            logging.error(msg="Games state is already initialized.")
        return

    def run(self):
        if self.status != Status.IN_GAME:
            return
        s = self.socket
        self.running = True
        logging.info(self.game_state)
        while self.running:
            if self.game_state.is_my_turn():
                self.play()
            if self.game_state.update_needed():
                self.update_state()
            data = s.recv(DATASIZE)
            if not data:
                continue
            data = GameData.GameData.deserialize(data)
            if type(data) is GameData.ServerGameStateData:
                dataOk = True
                print("Current player: " + data.currentPlayer)
                print("Player hands: ")
                for p in data.players:
                    print(p.toClientString())
                print("Table cards: ")
                for pos in data.tableCards:
                    print(pos + ": [ ")
                    for c in data.tableCards[pos]:
                        print(c.toClientString() + " ")
                    print("]")
                print("Discard pile: ")
                for c in data.discardPile:
                    print("\t" + c.toClientString())
                print("Note tokens used: " + str(data.usedNoteTokens) + "/8")
                print("Storm tokens used: " + str(data.usedStormTokens) + "/3")
            if type(data) is GameData.ServerActionInvalid:
                dataOk = True
                print("Invalid action performed. Reason:")
                print(data.message)
            if type(data) is GameData.ServerActionValid:
                dataOk = True
                print("Action valid!")
                print("Current player: " + data.player)
            if type(data) is GameData.ServerPlayerMoveOk:
                dataOk = True
                print("Nice move!")
                print("Current player: " + data.player)
            if type(data) is GameData.ServerPlayerThunderStrike:
                dataOk = True
                print("OH NO! The Gods are unhappy with you!")
            if type(data) is GameData.ServerHintData:
                dataOk = True
                print("Hint type: " + data.type)
                print(
                    "Player "
                    + data.destination
                    + " cards with value "
                    + str(data.value)
                    + " are:"
                )
                for i in data.positions:
                    print("\t" + str(i))
            if type(data) is GameData.ServerInvalidDataReceived:
                dataOk = True
                print(data.data)
            if type(data) is GameData.ServerGameOver:
                dataOk = True
                logging.info(msg=data.message)
                logging.info(msg=data.score)
                logging.info(msg=data.scoreMessage)
                stdout.flush()
                run = False
            if not dataOk:
                logging.error(
                    mesg="Unknown or unimplemented data type: " + str(type(data))
                )
            # print("[" + self.playerName + " - " + self.status + "]: ", end="")
            stdout.flush()
        return

    def fetch_state(self) -> GameData.ServerGameStateData:
        if self.status != Status.IN_GAME:
            print("You must be in game")
            return
        state_request = GameData.ClientGetGameStateRequest(self.playerName)
        self.socket.send(state_request.serialize())
        data = self.socket.recv(DATASIZE)
        data = GameData.GameData.deserialize(data)
        if type(data) is GameData.ServerGameStateData:
            return data
        return None

    # def __update_state(self, data: GameData.ServerGameStateData):
    #     raise NotImplementedError("abstract method")

    def play_action(self, action: dict):
        if action["type"] == Action.DISCARD:
            card = action["card"]
            self.__discard_card(card)
        elif action["type"] == Action.PLAY:
            card = action["card"]
            self.__play_card(card)
        elif action["type"] == Action.HINT:
            destination = action["destination"]
            hint_type = action["hint_type"]
            hint_value = action["hint_value"]
            self.__give_hint(destination, hint_type, hint_value)
        else:
            raise ValueError("Invalid action specified")
        return

    def __discard_card(self, card: int):
        if self.status == Status.IN_GAME:
            discard_req = GameData.ClientPlayerDiscardCardRequest(self.playerName, card)
            self.socket.send(discard_req.serialize())
        return

    def __play_card(self, card: int):
        if self.status != Status.IN_GAME:
            return
        play_req = GameData.ClientPlayerPlayCardRequest(self.playerName, card)
        self.socket.send(play_req.serialize())

        # verify answer
        s = self.socket
        data = s.recv(DATASIZE)
        data = GameData.GameData.deserialize(data)
        if type(data) is GameData.ServerPlayerMoveOk:
            logging.info(
                f"{self.playerName} - correctly played card {card}: {data.card}"
            )
            self.game_state.add_play(data)
            return True
        if type(data) is GameData.ServerPlayerThunderStrike:
            self.game_state.add_error(data)
            return True
        if type(data) is GameData.ServerActionInvalid:
            logging.error(msg=f"{data.message}")
            return False
        return False

    def __give_hint(self, destination: str, hint_type: str, hint_value: str):
        if self.status == Status.IN_GAME:
            hint_req = GameData.ClientHintData(
                self.playerName, destination, hint_type, hint_value
            )
            self.socket.send(hint_req.serialize())
        return


clientParser = argparse.ArgumentParser()

clientParser.add_argument(
    "name", type=str, help="The name used by the player", default="s289902"
)
clientParser.add_argument("--host", type=str, default=HOST)
clientParser.add_argument("--port", type=int, default=PORT)

# computerParser = argparse.ArgumentParser(parents=[clientParser])
# computerParser.add_argument("-n", type=int, help="Number of #computer players to create")
