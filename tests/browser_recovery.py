"""Optional Linux Chromium regressions against real HTTP/SQLite, with no inference calls.

Run with the same external Playwright installation as browser_workspace.py.
"""
import threading
import sys

from playwright.sync_api import sync_playwright, expect

from app.agents.defaults import seed
from app.core.registry import Registry
from app.database import Database
from app.services.sessions import SessionStore
from app.web.server import create_server
from tempfile import TemporaryDirectory
from pathlib import Path


def main():
    with TemporaryDirectory() as directory:
        registry = Registry(Database(Path(directory) / 'data.sqlite'))
        seed(registry)
        store = SessionStore(registry.db, Path(directory) / 'workspace')
        alpha, beta = store.create_project('Alpha'), store.create_project('Beta')
        store.create_session(alpha['id'], 'Alpha conversation')
        store.create_session(beta['id'], 'Beta conversation')
        server = create_server(store, registry, 0)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(executable_path='/usr/bin/chromium', args=['--no-sandbox'])
                page = browser.new_page()
                page.goto(f'http://127.0.0.1:{server.server_port}')
                expect(page.get_by_role('heading', name='Alpha', exact=True)).to_be_visible()
                case = sys.argv[1] if len(sys.argv) > 1 else 'all'
                # A definitive 400 must leave an editable message, not endless retry.
                if case in ('all', 'rejected'):
                    registry.set_enabled('agents', 'assistant', False)
                    page.get_by_label('Message').fill('Please help')
                    page.get_by_role('button', name='Send', exact=True).click()
                    expect(page.get_by_role('alert')).to_contain_text('disabled')
                    expect(page.get_by_label('Message')).to_be_enabled()
                    assert page.get_by_label('Message').input_value() == 'Please help'
                    registry.set_enabled('agents', 'assistant', True)
                # Lose an accepted reply. Polling must reconcile the persisted key.
                if case in ('all', 'lost'):
                    page.get_by_label('Message').fill('Please help')
                    dropped = []
                    def drop_reply(route):
                        if route.request.method == 'POST' and not dropped:
                            dropped.append(route.fetch().json()['id'])
                            route.abort()
                        else:
                            route.continue_()
                    page.route('**/api/sessions/*/tasks', drop_reply)
                    page.get_by_role('button', name='Send', exact=True).click()
                    expect(page.locator('.task')).to_have_count(1)
                    expect(page.get_by_label('Message')).to_be_enabled(timeout=10_000)
                    expect(page.get_by_role('button', name='Send', exact=True)).to_be_enabled()
                    assert len(store.history(store.sessions(alpha['id'])[0]['id'])) == 1
                    page.unroute('**/api/sessions/*/tasks')
                # Delay Alpha while Beta wins; late Alpha must not replace B's state.
                if case in ('all', 'race'):
                    page.get_by_role('button', name='Beta', exact=True).click()
                    expect(page.get_by_role('heading', name='Beta', exact=True)).to_be_visible()
                    delayed = []
                    def delay_alpha(route):
                        if route.request.method == 'GET':
                            delayed.append(route)
                        else:
                            route.continue_()
                    page.route(f'**/api/projects/{alpha["id"]}/sessions', delay_alpha)
                    page.get_by_role('button', name='Alpha', exact=True).click()
                    page.get_by_role('button', name='Beta', exact=True).click()
                    expect(page.get_by_role('heading', name='Beta', exact=True)).to_be_visible()
                    assert delayed
                    delayed[0].continue_()
                    page.wait_for_timeout(300)
                    page.get_by_role('button', name='New conversation', exact=True).click()
                    expect(page.get_by_role('button', name='Conversation 2', exact=True)).to_be_visible()
                    expect(page.get_by_role('button', name='Alpha conversation', exact=True)).to_have_count(0)
                    expect(page.get_by_role('button', name='Beta conversation', exact=True)).to_be_visible()
                browser.close()
                print('Browser recovery: rejected submission, lost reply and project race passed')
        finally:
            server.shutdown(); server.server_close(); thread.join()


if __name__ == '__main__':
    main()
