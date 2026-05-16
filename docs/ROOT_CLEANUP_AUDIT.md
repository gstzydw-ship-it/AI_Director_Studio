# Root Cleanup Audit

Date: 2026-05-07

## Scope

Added a dry-run audit script for root-level junk candidates:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\tools\audit_root_junk.ps1
```

The script only lists matching root files by name and git state. It does not delete, move, open, or print file contents.

Covered patterns:

- `fix_*.py`
- `scratch_*.py`
- `_tmp*.py`
- `tmp_*.py`
- `_test*.py`
- `test_*.txt`
- `*.log`
- `*.png`
- `*.exe`

## Result Summary

Latest dry-run result:

- `tracked`: 0
- `ignored-untracked`: 187
- `needs-review`: 0

All detected candidates are ignored and untracked, so they are cleanup candidates only after a human confirms they are not needed for local debugging or handoff context.

Representative examples:

- `fix_all_issues.py`
- `scratch_test.py`
- `_tmp_scan_director_graph_exports.py`
- `_test_full_director_pipeline.py`
- `test_output.txt`
- `workflow_debug.log`
- `app_screenshot.png`
- `cloudflared.exe`

No tracked candidate files were reported.
