#!/usr/bin/env python3
"""Lock Repo project revisions without replacing original manifest remotes."""
import argparse
import re
import xml.etree.ElementTree as ET


def projects(path):
    root = ET.parse(path).getroot()
    result = {}
    for p in root.findall('project'):
        name = p.get('name')
        project_path = p.get('path', name)
        if not name or not project_path or project_path in result:
            raise ValueError(f'invalid or duplicate project path: {project_path!r}')
        result[project_path] = p
    return result


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('locked')
    p.add_argument('current')
    p.add_argument('--overlay')
    a = p.parse_args()
    locked, current = projects(a.locked), projects(a.current)
    if len(locked) != 1267 or locked.keys() != current.keys():
        raise ValueError('project path set differs from the 1,267-project lock')
    overlay = ET.Element('manifest')
    for path, project in sorted(locked.items()):
        name, rev = project.get('name'), project.get('revision', '')
        actual = current[path]
        if actual.get('name') != name or not re.fullmatch('[0-9a-f]{40}', rev):
            raise ValueError(f'project name or locked full revision invalid: {path}')
        if a.overlay:
            ET.SubElement(overlay, 'extend-project', name=name, path=path, revision=rev)
        elif actual.get('revision') != rev:
            raise ValueError(f'checked-out commit differs from lock: {path}')
    if a.overlay:
        ET.indent(overlay)
        ET.ElementTree(overlay).write(a.overlay, encoding='utf-8', xml_declaration=True)
    print(f'PASS: {len(locked)} project paths and pinned revisions ' + ('prepared' if a.overlay else 'verified'))


if __name__ == '__main__':
    main()
