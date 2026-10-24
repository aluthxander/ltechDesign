param([switch]$RequirePrerequisites)

# Audit dokumentasi saja: tidak membuktikan perilaku aplikasi atau format native.
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$failures = [System.Collections.Generic.List[string]]::new()
$allowedStatuses = @('not_started', 'in_progress', 'implemented_pending_verification', 'verified', 'blocked', 'not_included')

function Read-ProjectText([string]$relativePath) {
    $absolutePath = Join-Path $projectRoot $relativePath
    if (-not (Test-Path -LiteralPath $absolutePath -PathType Leaf)) {
        throw "Missing audit input: $relativePath"
    }
    return [System.IO.File]::ReadAllText($absolutePath, [System.Text.Encoding]::UTF8)
}

$matrix = Read-ProjectText 'docs/requirements-matrix.md'
$progress = Read-ProjectText 'docs/progress.md'
$prd = Read-ProjectText 'prd.md'
$rows = @{}
foreach ($line in ($matrix -split '\r?\n')) {
    if ($line -notmatch '^\|\s*(FR-|NFR-|AT-|G-|C20\.|DOC-|FILE-|TOK-|STYLE-|IMP-|EXP-|ANALYZE-|UI-|HTTP-|P1-|D-|MCP-)') { continue }
    $cells = @($line.Trim().Trim('|').Split('|') | ForEach-Object { $_.Trim() })
    if ($cells.Count -ne 6) {
        $failures.Add("Expected six columns: $line")
        continue
    }
    $rowId = $cells[0]
    if ($rows.ContainsKey($rowId)) { $failures.Add("Duplicate requirement ID: $rowId") }
    $rows[$rowId] = $cells
    if ($allowedStatuses -notcontains $cells[4]) { $failures.Add("Invalid status for ${rowId}: $($cells[4])") }
    if ($cells[1] -match 'P0' -and $cells[4] -eq 'not_included') { $failures.Add("Mandatory P0 omitted: $rowId") }
    if ($cells[2] -notmatch '^\d{2}[A-D]?$') { $failures.Add("Missing single primary segment owner: $rowId") }
}

$segments = @{}
foreach ($line in ($progress -split '\r?\n')) {
    if ($line -match '^\|\s*(\d{2}[A-D]?)\s*\|') {
        $segmentId = $Matches[1]
        $cells = @($line.Trim().Trim('|').Split('|') | ForEach-Object { $_.Trim() })
        if ($segments.ContainsKey($segmentId)) { $failures.Add("Duplicate roadmap segment: $segmentId") }
        $segments[$segmentId] = $cells[2]
        if ($allowedStatuses -notcontains $cells[2]) { $failures.Add("Invalid segment status: $segmentId") }
        if ($segmentId -match '^(00[A-D]?|01|01A|02|03|04|04A|05|06|06A|07|08|09|10|10A|10B|11|12|13|14|15|16|17|17A|18|18A|18B|18C|19|19A|19B|20|22|23|24|25)$' -and $cells[2] -eq 'not_included') {
            $failures.Add("Mandatory foundation/MVP segment omitted: $segmentId")
        }
    }
}
foreach ($number in 0..42) {
    $segmentId = '{0:D2}' -f $number
    if (-not $segments.ContainsKey($segmentId)) { $failures.Add("Missing roadmap segment: $segmentId") }
}
$checkpointParents = @{
    '00' = @('00A', '00B', '00C', '00D')
    '10' = @('10A', '10B')
    '18' = @('18A', '18B', '18C')
    '19' = @('19A', '19B')
    '31' = @('31A', '31B')
    '32' = @('32A', '32B')
    '33' = @('33A', '33B', '33C')
    '36' = @('36A', '36B')
    '37' = @('37A', '37B', '37C', '37D')
    '38' = @('38A', '38B')
    '39' = @('39A', '39B')
    '40' = @('40A', '40B')
    '42' = @('42A', '42B')
}
foreach ($parentId in $checkpointParents.Keys) {
    foreach ($childId in $checkpointParents[$parentId]) {
        if (-not $segments.ContainsKey($childId)) { $failures.Add("Missing mandatory checkpoint: $childId") }
        if ($segments[$parentId] -eq 'verified' -and $segments[$childId] -ne 'verified') { $failures.Add("Parent $parentId verified before child $childId") }
    }
}
foreach ($cells in $rows.Values) {
    $references = @($cells[2]) + @($cells[3] -split ',\s*')
    foreach ($reference in $references) {
        if (-not $segments.ContainsKey($reference)) { $failures.Add("Unknown segment '$reference' for $($cells[0])") }
    }
}

$families = @(@('FR', 33), @('NFR', 5), @('AT', 34))
foreach ($family in $families) {
    $prefix = $family[0]
    $count = [int]$family[1]
    $width = if ($prefix -eq 'AT') { 2 } else { 3 }
    $sourceIds = @([regex]::Matches($prd, "\b$prefix-\d{$width}\b") | ForEach-Object { $_.Value } | Sort-Object -Unique)
    $matrixIds = @($rows.Keys | Where-Object { $_ -match "^$prefix-\d{$width}$" })
    if ($sourceIds.Count -ne $count -or $matrixIds.Count -ne $count) { $failures.Add("Incorrect count for $prefix (PRD $($sourceIds.Count), matrix $($matrixIds.Count), expected $count)") }
    foreach ($requirementId in $sourceIds) {
        if (-not $rows.ContainsKey($requirementId)) { $failures.Add("Unmapped source requirement: $requirementId") }
    }
}

foreach ($number in 1..13) {
    $deliverableId = 'D-{0:D2}' -f $number
    if (-not $rows.ContainsKey($deliverableId)) { $failures.Add("Missing PRD 17 deliverable: $deliverableId") }
}
foreach ($number in 1..9) {
    if (-not @($rows.Keys | Where-Object { $_ -match "^C20\.$number(?:-|$)" }).Count) { $failures.Add("Unmapped PRD section 20.$number") }
}
$requiredSplits = @('TOK-P0', 'STYLE-P0', 'EXP-PDF', 'IMP-NATIVE', 'IMP-RASTER', 'IMP-SVG', 'IMP-PDF', 'EXP-RASTER', 'EXP-CODE', 'EXP-SVG', 'EXP-BATCH', 'ANALYZE-DIAGNOSTIC', 'ANALYZE-ACCESSIBILITY', 'UI-ACCESSIBILITY', 'G-MVP', 'G-FEATURE', 'G-RELEASE', 'DOC-FORMAT', 'HTTP-OPTIONAL')
foreach ($splitId in $requiredSplits) {
    if (-not $rows.ContainsKey($splitId)) { $failures.Add("Missing explicit scope: $splitId") }
}
if ($rows['EXP-PDF'][1] -notmatch 'P0' -or $rows['TOK-P0'][1] -notmatch 'P0') { $failures.Add('Basic multipage PDF and minimum token store must be P0') }
if ($rows['ANALYZE-DIAGNOSTIC'][2] -ne '40B' -or $rows['ANALYZE-ACCESSIBILITY'][2] -ne '37B') { $failures.Add('Incorrect analyze_design/accessibility ownership') }

$registry = ($prd -split '### 7\.3 MCP Tool Registry', 2)[1] -split '### 7\.4 MCP Resources', 2
$requiredTools = [System.Collections.Generic.HashSet[string]]::new()
foreach ($line in ($registry[0] -split '\r?\n')) {
    if ($line -notmatch '^\|') { continue }
    $toolCell = $line.Split('|')[1]
    foreach ($match in [regex]::Matches($toolCell, '`([a-z_]+)`')) { [void]$requiredTools.Add($match.Groups[1].Value) }
}
foreach ($toolName in @('get_job_status', 'cancel_job', 'create_component', 'apply_auto_layout', 'export_html_css', 'analyze_design', 'preview_operations')) { [void]$requiredTools.Add($toolName) }
foreach ($toolName in $requiredTools) {
    if (-not $rows.ContainsKey("MCP-$toolName")) { $failures.Add("Unmapped MCP tool: $toolName") }
}

$documentFiles = @(Get-ChildItem -LiteralPath (Join-Path $projectRoot 'docs') -Filter '*.md' -Recurse -File)
$scriptBody = [System.IO.File]::ReadAllText($PSCommandPath, [System.Text.Encoding]::UTF8)
if ($scriptBody -match '(?m)[ \t]+\r?$') { $failures.Add('Trailing whitespace: check-segment00.ps1') }
foreach ($documentFile in $documentFiles) {
    $body = [System.IO.File]::ReadAllText($documentFile.FullName, [System.Text.Encoding]::UTF8)
    if ($body -match '(?m)[ \t]+\r?$') { $failures.Add("Trailing whitespace: $($documentFile.Name)") }
    if ($body.Contains([char]0xFFFD)) { $failures.Add("Invalid UTF-8 replacement character: $($documentFile.Name)") }
    foreach ($match in [regex]::Matches($body, '\[[^\]]+\]\(([^)]+)\)')) {
        $linkTarget = $match.Groups[1].Value
        if ($linkTarget -match '^[a-zA-Z][a-zA-Z0-9+.-]*:' -or $linkTarget.StartsWith('#')) { continue }
        $linkTarget = ($linkTarget -split '#', 2)[0]
        $resolvedTarget = [System.IO.Path]::GetFullPath((Join-Path $documentFile.DirectoryName $linkTarget))
        if (-not (Test-Path -LiteralPath $resolvedTarget)) { $failures.Add("Broken local link in $($documentFile.Name): $linkTarget") }
    }
}
if (-not (Test-Path -LiteralPath (Join-Path $projectRoot 'src'))) {
    foreach ($cells in $rows.Values) {
        if ($cells[0] -match '^(FR-|NFR-|AT-|MCP-)' -and $cells[4] -eq 'verified') { $failures.Add("Product requirement verified without application source: $($cells[0])") }
    }
}

$formatSpecPresent = Test-Path -LiteralPath (Join-Path $projectRoot 'docs/ltechdesign-file-format.md') -PathType Leaf
if (-not $formatSpecPresent) {
    if ($segments['00B'] -ne 'blocked' -or $segments['00'] -eq 'verified' -or $rows['DOC-FORMAT'][4] -ne 'blocked') { $failures.Add('Missing format specification must keep 00B and DOC-FORMAT blocked, parent 00 unverified') }
    Write-Output 'BLOCKER B-001: docs/ltechdesign-file-format.md is absent; format conformance is unverified.'
    if ($RequirePrerequisites) { $failures.Add('B-001: normative file-format prerequisite is missing') }
}
elseif ($RequirePrerequisites) {
    $contractAuditPath = Join-Path $PSScriptRoot 'check-file-format-spec.ps1'
    if (-not (Test-Path -LiteralPath $contractAuditPath -PathType Leaf)) {
        $failures.Add('File-format contract/example audit is missing')
    } else {
        & powershell -NoProfile -ExecutionPolicy Bypass -File $contractAuditPath
        if ($LASTEXITCODE -ne 0) { $failures.Add('File-format contract/example audit failed') }
    }
}
Write-Output "Audit scope: $($rows.Count) matrix rows; $($segments.Count) segments/checkpoints; $($requiredTools.Count) MCP tools; $($documentFiles.Count) Markdown files."
if ($failures.Count -gt 0) {
    foreach ($failure in $failures) { Write-Output "FAIL: $failure" }
    exit 1
}
Write-Output 'PASS: documentation coverage, owners, statuses and local links. No application behavior was tested.'
exit 0
