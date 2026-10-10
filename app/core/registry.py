"""Dynamic configuration storage. No specialist-specific behavior lives here."""
import json
import sqlite3
from app.database import now
from app.core.schemas import Agent, Model, Tool

TYPES = {'models': Model, 'agents': Agent, 'tools': Tool}


class Registry:
    def __init__(self, db):
        self.db = db

    def _add(self, table, record):
        record = TYPES[table].model_validate(record.model_dump())
        with self.db.connect() as c:
            try:
                c.execute(f'INSERT INTO {table}(id,data,created_at,updated_at) VALUES(?,?,?,?)',
                          (record.id, record.model_dump_json(), now(), now()))
            except sqlite3.IntegrityError as e:
                raise ValueError(f'{table} record already exists: {record.id}') from e
        return record

    def _get(self, table, record_id):
        with self.db.connect() as c:
            row = c.execute(f'SELECT data FROM {table} WHERE id=?', (record_id,)).fetchone()
        if row is None:
            raise ValueError(f'unknown {table} record: {record_id}')
        return TYPES[table].model_validate_json(row['data'])

    def _list(self, table, enabled_only=False):
        with self.db.connect() as c:
            records = [TYPES[table].model_validate_json(r['data']) for r in c.execute(f'SELECT data FROM {table} ORDER BY id')]
        return [r for r in records if not enabled_only or r.enabled]

    def add_model(self, model):
        return self._add('models', model)

    def add_tool(self, tool):
        return self._add('tools', tool)

    def add_agent(self, agent):
        self.get_model(agent.model_id)
        if agent.fallback_model_id:
            self.get_model(agent.fallback_model_id)
        for tool_id in agent.tools:
            self.get_tool(tool_id)
        if agent.parent_id:
            self.get_agent(agent.parent_id)
        return self._add('agents', agent)

    def get_model(self, model_id):
        return self._get('models', model_id)

    def get_agent(self, agent_id):
        return self._get('agents', agent_id)

    def get_tool(self, tool_id):
        return self._get('tools', tool_id)

    def list_models(self, enabled_only=False):
        return self._list('models', enabled_only)

    def list_agents(self, enabled_only=False):
        return self._list('agents', enabled_only)

    def list_tools(self, enabled_only=False):
        return self._list('tools', enabled_only)

    def set_enabled(self, table, record_id, enabled):
        if table not in TYPES:
            raise ValueError('unknown registry')
        record = self._get(table, record_id)
        record.enabled = enabled
        with self.db.connect() as c:
            c.execute(f'UPDATE {table} SET data=?,updated_at=? WHERE id=?', (record.model_dump_json(), now(), record_id))

    def update_agent(self, agent_id, **changes):
        data = self.get_agent(agent_id).model_dump()
        data.update(changes)
        candidate = Agent.model_validate(data)
        if candidate.id != agent_id:
            raise ValueError('agent ID cannot be changed')
        self.get_model(candidate.model_id)
        if candidate.fallback_model_id:
            self.get_model(candidate.fallback_model_id)
        if candidate.parent_id:
            self.get_agent(candidate.parent_id)
        for tool_id in candidate.tools:
            self.get_tool(tool_id)
        with self.db.connect() as c:
            c.execute('UPDATE agents SET data=?,updated_at=? WHERE id=?', (candidate.model_dump_json(),now(),agent_id))
        return candidate
