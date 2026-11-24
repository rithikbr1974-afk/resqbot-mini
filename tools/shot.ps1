# Screenshot a local page with headless Edge: shot.ps1 <url> <out.png> <width> <height> [scale]
param($Url, $Out, $W, $H, $Scale = 2)
$e = "C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
Start-Process -FilePath $e -Wait -ArgumentList '--headless=new','--disable-gpu','--hide-scrollbars',
  "--force-device-scale-factor=$Scale",'--virtual-time-budget=3000',"--window-size=$W,$H",
  '--user-data-dir=E:\tools\edge-shot',"--screenshot=$Out",$Url
