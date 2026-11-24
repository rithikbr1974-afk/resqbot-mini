# Renders every docs/diagrams/*.svg to docs/images/*.png (2x) with headless Edge.
$root = Split-Path $PSScriptRoot -Parent
python "$root\docs\diagrams\wiring.py"
Get-ChildItem "$root\docs\diagrams\*.svg" | ForEach-Object {
  $xml = [xml](Get-Content $_.FullName -Raw)
  $w = $xml.svg.width; $h = $xml.svg.height
  $out = Join-Path "$root\docs\images" ($_.BaseName + ".png")
  & "$PSScriptRoot\shot.ps1" ("file:///" + ($_.FullName -replace '\\', '/')) $out $w $h 2
  "$($_.Name) -> $out"
}
