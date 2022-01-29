from rule_based_agent import RuleBasedAgent
import sys
from threading import Thread


def deploy_agent(agent):
    """Agent must be deployed (send_ready) after they are connected
    otherwise only the first two will be in the game."""
    # TODO: change agent interface for entering the game
    agent.send_start()
    agent.wait_start()
    agent.run()  # entry point for the game
    return


agents = []
for a in range(int(sys.argv[1])):
    name = f"agent_{a}"
    agent = RuleBasedAgent(name)
    agents.append(agent)
for agent in agents:
    Thread(target=deploy_agent, args=[agent]).start()
