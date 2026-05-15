#!/usr/bin/env python3
"""
Batch create and close TFS daily tasks for a date range.
Skips weekends automatically.

Usage (from hermes terminal):
  py -3 <this_script.py>

Modify the config section below before running.
"""
import json
import subprocess
import os
from datetime import datetime, timedelta

# ── Config ──────────────────────────────────────────────────────────────
PAT_FILE = r'C:\Users\89286\AppData\Local\hermes\tfs_pat.txt'
PARENT_ID = 1523040  # User Story to attach tasks to
PROJECT = 'XiNanArea-New'
AREA = rf'{PROJECT}\四川省区团队'
HOURS = 8

# Date range (inclusive, local time UTC+8)
START_DATE = '2026-05-01'  # YYYY-MM-DD
END_DATE   = '2026-05-15'

# Existing task dates to skip (YYYY-MM-DD set)
EXISTING_DATES = set()  # fill if you know some days already have tasks

# Iteration mapping: {date_str: iteration_path}
# Auto-detect via API if left empty (recommended)
ITERATION_MAP = {}
# Manual override example:
# ITERATION_MAP = {
#     '2026-05-01': rf'{PROJECT}\迭代 2026-4-4',
#     '2026-05-06': rf'{PROJECT}\迭代2026-5-1',
# }
# ── End Config ──────────────────────────────────────────────────────────

def get_pat():
    return open(PAT_FILE).read().strip()

def get_iteration_for_date(date_str, pat):
    """Query TFS API to find which iteration covers the given date."""
    import urllib.request, base64
    cred = base64.b64encode((':' + pat).encode()).decode()

    req = urllib.request.Request(
        f'http://dev.tellhowsoft.com/DefaultCollection/{PROJECT}/_apis/wit/classificationnodes/iterations?$depth=2&api-version=2.0',
        headers={'Authorization': 'Basic ' + cred}
    )
    resp = urllib.request.urlopen(req)
    data = json.loads(resp.read())

    target = datetime.strptime(date_str, '%Y-%m-%d').date()
    for child in data.get('children', []):
        attrs = child.get('attributes', {})
        start_str = attrs.get('startDate', '')
        end_str = attrs.get('finishDate', '')
        if start_str and end_str:
            start = datetime.strptime(start_str[:10], '%Y-%m-%d').date()
            end = datetime.strptime(end_str[:10], '%Y-%m-%d').date()
            if start <= target <= end:
                name = child['name']
                return rf'{PROJECT}\{name}'
    return None

def create_task(date_str, iteration, title, desc, pat):
    desc_html = f'<div>1、今日完成开发情况（{desc}）<br>2、BUG修复情况（无）<br>3、需求沟通情况（无）<br>4、其他（无）</div>'
    patch_data = [
        {'op': 'add', 'path': '/fields/System.Title', 'value': title},
        {'op': 'add', 'path': '/fields/System.AssignedTo', 'value': 'TELLHOW\\yangtao'},
        {'op': 'add', 'path': '/fields/System.AreaPath', 'value': AREA},
        {'op': 'add', 'path': '/fields/System.IterationPath', 'value': iteration},
        {'op': 'add', 'path': '/fields/Microsoft.VSTS.Scheduling.OriginalEstimate', 'value': HOURS},
        {'op': 'add', 'path': '/fields/Microsoft.VSTS.Scheduling.RemainingWork', 'value': HOURS},
        {'op': 'add', 'path': '/fields/Microsoft.VSTS.Scheduling.StartDate', 'value': f'{date_str}T00:30:00Z'},
        {'op': 'add', 'path': '/fields/Microsoft.VSTS.Scheduling.FinishDate', 'value': f'{date_str}T09:30:00Z'},
        {'op': 'add', 'path': '/fields/Microsoft.VSTS.Common.Activity', 'value': '开发'},
        {'op': 'add', 'path': '/fields/System.Description', 'value': desc_html},
        {'op': 'add', 'path': '/relations/-', 'value': {
            'rel': 'System.LinkTypes.Hierarchy-Reverse',
            'url': f'http://dev.tellhowsoft.com/DefaultCollection/_apis/wit/workItems/{PARENT_ID}'
        }}
    ]
    fname = f'tfs_create_{date_str}.json'
    with open(fname, 'w', encoding='utf-8') as f:
        json.dump(patch_data, f, ensure_ascii=False)

    result = subprocess.run(
        ['curl', '-s', '-u', f':{pat}', '-X', 'POST',
         '-H', 'Content-Type: application/json-patch+json',
         '-d', f'@{fname}',
         f'http://dev.tellhowsoft.com/DefaultCollection/{PROJECT}/_apis/wit/workitems/$%E4%BB%BB%E5%8A%A1?api-version=2.0'],
        capture_output=True, text=True
    )
    r = json.loads(result.stdout)
    return r.get('id')

def close_task(date_str, task_id, pat):
    patch_data = [
        {'op': 'replace', 'path': '/fields/System.State', 'value': '已关闭'},
        {'op': 'replace', 'path': '/fields/Microsoft.VSTS.Scheduling.OriginalEstimate', 'value': HOURS},
        {'op': 'replace', 'path': '/fields/Microsoft.VSTS.Scheduling.CompletedWork', 'value': HOURS},
        {'op': 'replace', 'path': '/fields/Microsoft.VSTS.Scheduling.TargetDate', 'value': f'{date_str}T09:30:00Z'}
    ]
    fname = f'tfs_close_{date_str}.json'
    with open(fname, 'w', encoding='utf-8') as f:
        json.dump(patch_data, f, ensure_ascii=False)

    result = subprocess.run(
        ['curl', '-s', '-u', f':{pat}', '-X', 'PATCH',
         '-H', 'Content-Type: application/json-patch+json',
         '-d', f'@{fname}',
         f'http://dev.tellhowsoft.com/DefaultCollection/_apis/wit/workitems/{task_id}?api-version=2.0'],
        capture_output=True, text=True
    )
    r = json.loads(result.stdout)
    return r.get('fields', {}).get('System.State')

def main():
    pat = get_pat()
    start = datetime.strptime(START_DATE, '%Y-%m-%d').date()
    end = datetime.strptime(END_DATE, '%Y-%m-%d').date()

    # Collect weekdays
    dates = []
    d = start
    while d <= end:
        if d.weekday() < 5:  # Mon=0 .. Fri=4
            dates.append(d)
        d += timedelta(days=1)

    # Filter out existing
    dates = [d for d in dates if d.strftime('%Y-%m-%d') not in EXISTING_DATES]

    print(f'Will create {len(dates)} tasks: {[d.strftime("%Y-%m-%d") for d in dates]}')

    # Resolve iterations
    for d in dates:
        ds = d.strftime('%Y-%m-%d')
        if ds not in ITERATION_MAP:
            it = get_iteration_for_date(ds, pat)
            if it:
                ITERATION_MAP[ds] = it
            else:
                print(f'WARNING: No iteration found for {ds}, skipping')
        print(f'{ds} -> {ITERATION_MAP.get(ds, "UNKNOWN")}')

    # Create all tasks
    created = []
    for d in dates:
        ds = d.strftime('%Y-%m-%d')
        iteration = ITERATION_MAP.get(ds)
        if not iteration:
            continue
        title = 'app接口迁移开发'
        desc = '完成app接口迁移开发'
        task_id = create_task(ds, iteration, title, desc, pat)
        if task_id:
            print(f'Created {ds}: ID={task_id}')
            created.append((ds, task_id))
        else:
            print(f'FAIL {ds}')

    # Close all tasks
    for ds, task_id in created:
        state = close_task(ds, task_id, pat)
        print(f'{ds} ID={task_id} -> {state}')

    print(f'\nDone! Created and closed {len(created)} tasks under parent {PARENT_ID}')

if __name__ == '__main__':
    main()
