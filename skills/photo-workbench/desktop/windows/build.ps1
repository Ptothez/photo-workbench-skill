[CmdletBinding()]
param()
$ErrorActionPreference='Stop'
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
$meta=Get-Content (Join-Path $PSScriptRoot 'dependencies.json') -Encoding UTF8 -Raw | ConvertFrom-Json
if($meta.source -notlike 'https://api.nuget.org/v3-flatcontainer/microsoft.web.webview2/*'){throw 'Unexpected dependency source'}
$sdk=Join-Path $PSScriptRoot ('vendor/webview2-'+$meta.version)
New-Item -ItemType Directory -Path $sdk -Force | Out-Null
$package=Join-Path $sdk 'Microsoft.Web.WebView2.nupkg'
if(-not(Test-Path -LiteralPath $package)){Invoke-WebRequest -Uri $meta.source -OutFile $package -UseBasicParsing -TimeoutSec 120}
if((Get-FileHash -LiteralPath $package -Algorithm SHA256).Hash.ToLowerInvariant() -ne $meta.sha256){throw 'WebView2 package hash mismatch; nothing was executed'}
Add-Type -AssemblyName System.IO.Compression.FileSystem
$archive=[IO.Compression.ZipFile]::OpenRead($package)
try{
    foreach($name in @('lib/net462/Microsoft.Web.WebView2.Core.dll','lib/net462/Microsoft.Web.WebView2.WinForms.dll','runtimes/win-x64/native/WebView2Loader.dll','LICENSE.txt')){
        $entry=$archive.GetEntry($name)
        if(-not $entry){throw "Missing dependency member: $name"}
        $target=Join-Path $sdk ([IO.Path]::GetFileName($name))
        if(-not(Test-Path -LiteralPath $target)){[IO.Compression.ZipFileExtensions]::ExtractToFile($entry,$target)}
    }
}finally{$archive.Dispose()}
$bin=Join-Path $PSScriptRoot 'bin';New-Item -ItemType Directory -Path $bin -Force | Out-Null
foreach($name in @('Microsoft.Web.WebView2.Core.dll','Microsoft.Web.WebView2.WinForms.dll','WebView2Loader.dll')){Copy-Item -LiteralPath (Join-Path $sdk $name) -Destination (Join-Path $bin $name) -Force}
$root=Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$csc=Join-Path $env:WINDIR 'Microsoft.NET/Framework64/v4.0.30319/csc.exe'
$argsList=@('/nologo','/codepage:65001','/target:winexe','/platform:x64',('/out:'+(Join-Path $bin 'PhotographyWorkbench.exe')),('/win32icon:'+(Join-Path $root 'assets/photo-icon.ico')),'/reference:System.dll','/reference:System.Core.dll','/reference:System.Drawing.dll','/reference:System.Windows.Forms.dll',('/reference:'+(Join-Path $bin 'Microsoft.Web.WebView2.Core.dll')),('/reference:'+(Join-Path $bin 'Microsoft.Web.WebView2.WinForms.dll')),(Join-Path $PSScriptRoot 'PhotographyWorkbench.cs'))
& $csc @argsList
if($LASTEXITCODE -ne 0){throw 'Desktop compilation failed'}
Write-Output (Join-Path $bin 'PhotographyWorkbench.exe')
