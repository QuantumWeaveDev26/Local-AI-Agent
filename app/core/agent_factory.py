"""Resolve agent configuration and enabled capabilities for each task."""
from dataclasses import dataclass
from app.core.schemas import Agent, Model, Tool


@dataclass
class RuntimeAgent:
    config: Agent
    model: Model
    tools: list[Tool]


class AgentFactory:
    def __init__(self, registry):
        self.registry = registry

    def load(self, agent_id):
        agent = self.registry.get_agent(agent_id)
        if not agent.enabled:
            raise ValueError(f'agent {agent.id} is disabled')
        model = self.registry.get_model(agent.model_id)
        if not model.enabled:
            raise ValueError(f'model {model.id} is disabled')
        tools = [self.registry.get_tool(t) for t in agent.tools]
        if any(not t.enabled for t in tools):
            raise ValueError('an assigned tool is disabled')
        return RuntimeAgent(agent,model,tools)
