"""Boston submission: change STRATEGY_MODE only when building a new artifact."""

import poker_agent_sdk
from core import decide

STRATEGY_MODE = "LEVEL_1"


class Agent(poker_agent_sdk.Agent):
    def act(self, state, memory):
        return decide(state, memory, STRATEGY_MODE)
