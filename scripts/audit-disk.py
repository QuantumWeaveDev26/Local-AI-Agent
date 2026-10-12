"""Read-only metadata scan. Python 3.11+, no packages or admin rights required.

Reports logical file sizes, not exact allocated NTFS space. Links/cloud
placeholders are skipped. Never opens file contents or performs cleanup.
"""
import argparse
from collections import defaultdict
import heapq
import json
import os
from pathlib import Path
import shutil
import stat
import sys
import time

INTERESTING = {'node_modules', '.venv', 'venv', '.cache', '.ollama', '.git',
               'docker', 'wsl', 'huggingface', 'npm-cache', 'pip', 'uv',
               'downloads', 'temp', '__pycache__'}


def skip_metadata(info):
    # Windows reparse points, offline files, recall-on-open/data-access files.
    return bool(getattr(info, 'st_file_attributes', 0) & (0x400 | 0x1000 | 0x40000 | 0x400000))


def scan(root, top=20, progress=None):
    root = Path(root).absolute()
    try:
        info = root.stat(follow_symlinks=False)
    except OSError as error:
        raise ValueError('scan root must be an accessible directory') from error
    if not stat.S_ISDIR(info.st_mode) or skip_metadata(info):
        raise ValueError('scan root must be a real accessible directory, not a link')
    if not 1 <= top <= 100:
        raise ValueError('top must be between 1 and 100')

    report = {'root': str(root), 'accessible_file_bytes': 0, 'file_count': 0,
              'directory_count': 0, 'skipped_links_or_placeholders': 0,
              'skipped_duplicate_hardlinks': 0, 'access_errors': 0,
              'skipped_examples': [], 'size_basis': 'Logical accessible file sizes; not allocated disk usage'}
    usage = shutil.disk_usage(root)
    report['disk'] = {'total_bytes': usage.total, 'used_bytes': usage.used, 'free_bytes': usage.free}
    largest_files, largest_folders, interesting, roots = [], [], [], []
    extensions = defaultdict(lambda: [0, 0])
    hardlinks = set()
    last_progress = time.monotonic()

    def relative(path):
        return path.relative_to(root).as_posix()

    def skip(path, reason):
        if len(report['skipped_examples']) < 20:
            report['skipped_examples'].append({'path': relative(path), 'reason': reason})

    def keep(heap, size, path):
        item = (size, relative(path))
        if len(heap) < top:
            heapq.heappush(heap, item)
        elif item > heap[0]:
            heapq.heapreplace(heap, item)

    def frame(path, depth):
        iterator = os.scandir(path)
        report['directory_count'] += 1
        return {'path': path, 'depth': depth, 'iterator': iterator, 'bytes': 0}

    try:
        stack = [frame(root, 0)]
    except OSError as error:
        raise ValueError('scan root must be an accessible directory') from error
    try:
        while stack:
            current = stack[-1]
            try:
                entry = next(current['iterator'])
            except (StopIteration, OSError) as error:
                if isinstance(error, OSError):
                    report['access_errors'] += 1
                    skip(current['path'], 'directory enumeration failed')
                current['iterator'].close()
                stack.pop()
                path, size, depth = current['path'], current['bytes'], current['depth']
                if depth:
                    if depth == 1:
                        roots.append((size, relative(path)))
                    if depth <= 5:
                        keep(largest_folders, size, path)
                    if path.name.lower() in INTERESTING:
                        keep(interesting, size, path)
                    stack[-1]['bytes'] += size
                else:
                    report['accessible_file_bytes'] = size
                continue
            path = Path(entry.path)
            try:
                metadata = entry.stat(follow_symlinks=False)
                if stat.S_ISLNK(metadata.st_mode) or skip_metadata(metadata):
                    report['skipped_links_or_placeholders'] += 1
                    skip(path, 'link, reparse point or cloud placeholder')
                    continue
                if stat.S_ISDIR(metadata.st_mode):
                    stack.append(frame(path, current['depth'] + 1))
                elif stat.S_ISREG(metadata.st_mode):
                    # Windows DirEntry.stat zeros identity fields; os.stat supplies
                    # them. Do this only after rejecting links/cloud placeholders.
                    identity_info = os.stat(path, follow_symlinks=False) if not metadata.st_ino else metadata
                    if identity_info.st_nlink > 1 and identity_info.st_ino:
                        identity = (identity_info.st_dev, identity_info.st_ino)
                        if identity in hardlinks:
                            report['skipped_duplicate_hardlinks'] += 1
                            continue
                        hardlinks.add(identity)
                    size = metadata.st_size
                    current['bytes'] += size
                    report['file_count'] += 1
                    ext = path.suffix.lower() or '(no extension)'
                    extensions[ext][0] += size
                    extensions[ext][1] += 1
                    keep(largest_files, size, path)
            except OSError:
                report['access_errors'] += 1
                skip(path, 'metadata inaccessible or entry changed during scan')
            if progress and time.monotonic() - last_progress >= 5:
                progress(f"Scanned {report['file_count']:,} files; current folder: {current['path']}")
                last_progress = time.monotonic()
    finally:
        for current in stack:
            current['iterator'].close()

    def rows(items):
        return [{'path': path, 'bytes': size} for size, path in sorted(items, reverse=True)]
    report['root_folders'] = rows(sorted(roots, reverse=True)[:top])
    report['largest_folders'] = rows(largest_folders)
    report['largest_files'] = rows(largest_files)
    report['development_and_cache_folders'] = rows(interesting)
    report['file_types'] = [{'extension': ext, 'bytes': values[0], 'files': values[1]}
                            for ext, values in sorted(extensions.items(), key=lambda pair: pair[1][0], reverse=True)[:top]]
    return report


def display(report):
    def gib(value):
        return value / 2**30
    disk = report['disk']
    print(f"Drive: {gib(disk['used_bytes']):.2f} GiB used, {gib(disk['free_bytes']):.2f} GiB free")
    print(f"Accessible scan: {report['file_count']:,} files, {gib(report['accessible_file_bytes']):.2f} GiB logical size")
    for title, key in [('Root folders', 'root_folders'), ('Largest folders (inclusive sizes; do not add rows)', 'largest_folders'),
                       ('Development/cache folders (inspect before cleanup)', 'development_and_cache_folders'), ('Largest files', 'largest_files')]:
        print('\n' + title)
        for item in report[key]:
            path = item['path'].replace('\n', '\\n').replace('\r', '\\r')
            print(f"{gib(item['bytes']):9.2f} GiB  {path}")
    print(f"\nSkipped {report['skipped_links_or_placeholders']} links/placeholders, {report['skipped_duplicate_hardlinks']} duplicate hardlinks; {report['access_errors']} access errors.")
    print('Totals can differ from drive usage: protected files, cloud placeholders, compression, sparse files and filesystem metadata.')
    print('Read-only audit complete; no files were deleted.')


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--top', type=int, default=20)
    parser.add_argument('--output', type=Path, help='Save a new JSON report; never overwrite an existing file')
    args = parser.parse_args(argv)
    try:
        if args.output and args.output.exists():
            raise ValueError('report already exists; choose a new output filename')
        report = scan(args.root, args.top, progress=lambda message: print(message, file=sys.stderr, flush=True))
        display(report)
        if args.output:
            with args.output.open('x', encoding='utf-8') as file:
                json.dump(report, file, ensure_ascii=False, indent=2)
            print(f'Report saved: {args.output}')
        return 0
    except (OSError, ValueError) as error:
        print(str(error), file=sys.stderr)
        return 1


if __name__ == '__main__':
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(errors='replace')
        sys.stderr.reconfigure(errors='replace')
    raise SystemExit(main())
