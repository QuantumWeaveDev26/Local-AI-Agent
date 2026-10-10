"""Optional Linux real-browser/live-model check. Install Playwright separately to run.

Usage: python tests/browser_workspace.py --base-url http://127.0.0.1:8765
Creates a clearly named validation project and three small real inference jobs.
"""
import argparse
import json
from pathlib import Path

from playwright.sync_api import sync_playwright, expect


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--base-url', required=True)
    parser.add_argument('--screenshot', type=Path)
    args = parser.parse_args()
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(executable_path='/usr/bin/chromium', args=['--no-sandbox'])
        page = browser.new_page(viewport={'width': 1440, 'height': 960})
        failures = []
        page.on('pageerror', lambda error: failures.append(str(error)))
        page.goto(args.base_url)
        expect(page).to_have_title('Local Agent Workspace')
        page.get_by_role('button', name='New project', exact=True).click()
        page.get_by_label('Project name').fill('Browser validation')
        page.get_by_role('button', name='Create project', exact=True).click()
        expect(page.get_by_role('heading', name='Browser validation', exact=True)).to_be_visible()
        page.get_by_label('Agent').select_option('assistant')
        page.get_by_label('Message').fill('Reply with exactly READY. Do not use tools.')
        page.get_by_role('button', name='Send', exact=True).click()
        expect(page.locator('.answer').filter(has_text='READY')).to_have_count(1, timeout=180_000)
        page.reload()
        expect(page.locator('.answer').filter(has_text='READY')).to_have_count(1, timeout=15_000)
        page.get_by_label('Message').fill('What exact word did you reply with in your previous answer? Reply with just that word. Do not use tools.')
        page.get_by_role('button', name='Send', exact=True).click()
        expect(page.locator('.answer').filter(has_text='READY')).to_have_count(2, timeout=180_000)
        page.get_by_label('Upload document').set_input_files({'name': 'notes.txt', 'mimeType': 'text/plain', 'buffer': b'Browser file upload evidence'})
        expect(page.get_by_label('Attach notes.txt')).to_be_visible()
        page.get_by_label('Attach notes.txt').check()
        page.get_by_label('Message').fill('Reply with exactly READY. Do not use tools.')
        page.get_by_role('button', name='Send', exact=True).click()
        page.get_by_role('button', name='Cancel task', exact=True).last.click()
        expect(page.locator('.task-status').filter(has_text='Cancelled')).to_have_count(1, timeout=180_000)
        page.get_by_role('button', name='Inspect task', exact=True).first.click()
        expect(page.get_by_role('heading', name='Task activity')).to_be_visible()
        page.get_by_role('button', name='New conversation', exact=True).click()
        expect(page.locator('.task')).to_have_count(0)
        page.get_by_role('button', name='Conversation 1', exact=True).click()
        expect(page.locator('.task')).to_have_count(3)
        if args.screenshot:
            args.screenshot.parent.mkdir(parents=True, exist_ok=True)
            page.screenshot(path=str(args.screenshot), full_page=True)
        page.set_viewport_size({'width': 390, 'height': 844})
        assert page.evaluate('document.documentElement.scrollWidth <= window.innerWidth')
        assert not failures, failures
        browser.close()
        print(json.dumps({'browser': 'Chromium', 'result': 'passed', 'checks': ['real inference', 'refresh without duplicate', 'context follow-up', 'upload', 'cancel', 'audit', 'session switching', 'mobile width']}))


if __name__ == '__main__':
    main()
