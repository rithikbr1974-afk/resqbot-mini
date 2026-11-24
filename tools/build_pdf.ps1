# Prints an HTML document to PDF with headless Edge.
#   build_pdf.ps1                      -> docs/proposal/ResQBot_Proposal.html => docs/ResQBot_Proposal.pdf
#   build_pdf.ps1 <in.html> <out.pdf>  -> any page
param($In, $Out)
$root = Split-Path $PSScriptRoot -Parent
if (-not $In) { $In = "$root\docs\proposal\ResQBot_Proposal.html"; $Out = "$root\docs\ResQBot_Proposal.pdf" }
$e = "C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
$src = "file:///" + (Resolve-Path $In).Path.Replace('\', '/')
Start-Process -FilePath $e -Wait -ArgumentList '--headless=new','--disable-gpu','--no-pdf-header-footer',
  '--virtual-time-budget=4000','--user-data-dir=E:\tools\edge-shot',"--print-to-pdf=$Out",$src
Get-Item $Out | Select-Object Name, Length
