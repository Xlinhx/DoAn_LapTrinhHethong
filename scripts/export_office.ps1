param(
    [Parameter(Mandatory=$true)][ValidateSet('Word','PowerPoint')][string]$Kind,
    [Parameter(Mandatory=$true)][string]$InputPath,
    [Parameter(Mandatory=$true)][string]$OutputPath
)
$ErrorActionPreference = 'Stop'
$inputAbsolute = (Resolve-Path -LiteralPath $InputPath).Path
$outputAbsolute = [System.IO.Path]::GetFullPath($OutputPath)
if ($Kind -eq 'Word') {
    $office = New-Object -ComObject Word.Application
    $office.Visible = $false
    $office.DisplayAlerts = 0
    $document = $null
    try {
        $document = $office.Documents.Open($inputAbsolute)
        $document.Repaginate()
        for ($round = 0; $round -lt 2; $round++) {
            foreach ($story in $document.StoryRanges) { $null = $story.Fields.Update() }
            foreach ($toc in $document.TablesOfContents) { $toc.Update() }
            $document.Repaginate()
        }
        $document.Save()
        $document.ExportAsFixedFormat($outputAbsolute, 17)
    } finally {
        if ($null -ne $document) { $document.Close(0) }
        if ($office.Documents.Count -eq 0) { $office.Quit() }
    }
} else {
    $office = New-Object -ComObject PowerPoint.Application
    $document = $null
    try {
        $document = $office.Presentations.Open($inputAbsolute, -1, 0, 0)
        [System.IO.Directory]::CreateDirectory($outputAbsolute) | Out-Null
        $document.Export($outputAbsolute, 'PNG', 1920, 1080)
        $document.SaveCopyAs((Join-Path $outputAbsolute 'Slides.pdf'), 32)
    } finally {
        if ($null -ne $document) { $document.Close() }
        if ($office.Presentations.Count -eq 0) { $office.Quit() }
    }
}
Write-Output "Exported $Kind preview to $outputAbsolute"
