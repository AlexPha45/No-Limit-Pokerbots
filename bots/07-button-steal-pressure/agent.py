"""Boston submission: fixed Level 2 policy, selected manually for this artifact."""

import poker_agent_sdk
from core import decide

STRATEGY_MODE = "LEVEL_4"


class Agent(poker_agent_sdk.Agent):
    def act(self, state, memory):
        return decide(state, memory, STRATEGY_MODE)
