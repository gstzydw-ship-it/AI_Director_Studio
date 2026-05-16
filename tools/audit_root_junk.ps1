[CmdletBinding()]
param(
    [string]$Root = ""
)

$ErrorActionPreference = "Stop"

$patterns = @(
    "fix_*.py",
    "scratch_*.py",
    "_tmp*.py",
    "tmp_*.py",
    "_test*.py",
    "test_*.txt",
    "*.log",
    "*.png",
    "*.exe"
)

function Test-GitTracked {
    param(
        [string]$RepoRoot,
        [string]$RelativePath
    )

    $output = & git -C $RepoRoot ls-files -- $RelativePath
    if ($LASTEXITCODE -ne 0) {
        throw "git ls-files failed for $RelativePath"
    }

    return $output -contains $RelativePath
}

function Test-GitIgnored {
    param(
        [string]$RepoRoot,
        [string]$RelativePath
    )

    & git -C $RepoRoot check-ignore -q -- $RelativePath
    return $LASTEXITCODE -eq 0
}

function Get-MatchedPattern {
    param([string]$FileName)

    foreach ($pattern in $patterns) {
        if ($FileName -like $pattern) {
            return $pattern
        }
    }

    return $null
}

if ([string]::IsNullOrWhiteSpace($Root)) {
    $Root = Join-Path $PSScriptRoot ".."
}

$resolvedRoot = (Resolve-Path $Root).Path

& git -C $resolvedRoot rev-parse --show-toplevel *> $null
if ($LASTEXITCODE -ne 0) {
    throw "Root is not inside a git repository: $resolvedRoot"
}

$results = [ordered]@{
    tracked = New-Object System.Collections.Generic.List[object]
    "ignored-untracked" = New-Object System.Collections.Generic.List[object]
    "needs-review" = New-Object System.Collections.Generic.List[object]
}

Get-ChildItem -LiteralPath $resolvedRoot -Force -File |
    Sort-Object Name |
    ForEach-Object {
        $matchedPattern = Get-MatchedPattern -FileName $_.Name
        if ($null -eq $matchedPattern) {
            return
        }

        $entry = [pscustomobject]@{
            path = $_.Name
            pattern = $matchedPattern
        }

        if (Test-GitTracked -RepoRoot $resolvedRoot -RelativePath $_.Name) {
            $results.tracked.Add($entry) | Out-Null
            return
        }

        if (Test-GitIgnored -RepoRoot $resolvedRoot -RelativePath $_.Name) {
            $results["ignored-untracked"].Add($entry) | Out-Null
            return
        }

        $results["needs-review"].Add($entry) | Out-Null
    }

Write-Output "Root junk audit (dry-run)"
Write-Output "Root: $resolvedRoot"
Write-Output "Patterns: $($patterns -join ', ')"
Write-Output "Action: list only; no files are deleted, moved, or opened."
Write-Output ""

foreach ($category in @("tracked", "ignored-untracked", "needs-review")) {
    $items = $results[$category]
    Write-Output "$category ($($items.Count))"

    if ($items.Count -eq 0) {
        Write-Output "  (none)"
        Write-Output ""
        continue
    }

    foreach ($item in $items) {
        Write-Output "  - $($item.path) [$($item.pattern)]"
    }

    Write-Output ""
}

Write-Output "Summary: tracked=$($results.tracked.Count); ignored-untracked=$($results["ignored-untracked"].Count); needs-review=$($results["needs-review"].Count)"
