$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.IO.Compression.FileSystem
$root = Split-Path $PSScriptRoot -Parent
$sources = @()
foreach ($version in @(8,9)) {
    $name = "Положение_о_внутреннем_аудите_редакция_${version}_обезличено.docx"
    $path = Join-Path "$env:USERPROFILE/Downloads" $name
    $zip = [IO.Compression.ZipFile]::OpenRead($path)
    try {
        $reader = [IO.StreamReader]::new($zip.GetEntry('word/document.xml').Open())
        try { [xml]$xml = $reader.ReadToEnd() } finally { $reader.Dispose() }
        $ns = [Xml.XmlNamespaceManager]::new($xml.NameTable)
        $ns.AddNamespace('w','http://schemas.openxmlformats.org/wordprocessingml/2006/main')
        $paragraphs = @($xml.SelectNodes('//w:body//w:p',$ns) | ForEach-Object {
            ($_.SelectNodes('.//w:t',$ns) | ForEach-Object { $_.InnerText }) -join ''
        })
        $start = -1
        $end = -1
        for ($i=0; $i -lt $paragraphs.Count; $i++) {
            if ($paragraphs[$i] -match '^3\.4\.') { $start=$i }
            if ($start -ge 0 -and $paragraphs[$i] -match '^3\.5\.') { $end=$i; break }
        }
        if ($start -lt 0 -or $end -lt 0) { throw "Section 3.4 missing: $name" }
        $sources += [ordered]@{ version=$version; name=$name; section='3.4'; sha256=(Get-FileHash $path -Algorithm SHA256).Hash; paragraphs=$paragraphs[$start..($end-1)]; file="sources/$name" }
        New-Item -ItemType Directory -Force (Join-Path $root 'sources') | Out-Null
        Copy-Item -LiteralPath $path -Destination (Join-Path $root "sources/$name")
    } finally { $zip.Dispose() }
}
$json = ConvertTo-Json -InputObject $sources -Depth 6
[IO.File]::WriteAllText((Join-Path $root 'sources.js'), "window.DOCUMENT_SOURCES = $json;", [Text.UTF8Encoding]::new($false))
Write-Output 'Verified section 3.4 extracted from both DOCX files; originals and SHA256 retained.'
