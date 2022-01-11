from agent import Agent
import sys
from threading import Thread


def deploy_agent(agent):
    """Agent must be deployed (send_ready) after they are connected
    otherwise only the first two will be in the game."""
    agent.send_ready()
    agent.wait_start()
    agent.run()  # entry point for the game
    return


agents = []
for a in range(int(sys.argv[1])):
    name = f"agent_{a}"
    agent = Agent(name)
    agents.append(agent)
for agent in agents:
    Thread(target=deploy_agent, args=[agent]).start()
