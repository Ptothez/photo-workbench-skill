[CmdletBinding()]
param()
$root=Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$profile=Get-Content (Join-Path $root 'profile.json') -Encoding UTF8 -Raw | ConvertFrom-Json
$name=$profile.workbench_name
if(-not $name){$name=([string][char]0x6444+[char]0x5F71+[char]0x5DE5+[char]0x4F5C+[char]0x53F0)}
foreach($char in [IO.Path]::GetInvalidFileNameChars()){$name=$name.Replace([string]$char,'_')}
$sha=[Security.Cryptography.SHA256]::Create();try{$id='Photography.Workbench.'+([BitConverter]::ToString($sha.ComputeHash([Text.Encoding]::UTF8.GetBytes([IO.Path]::GetFullPath($root).ToUpperInvariant())))).Replace('-','').Substring(0,16)}finally{$sha.Dispose()}
$ErrorActionPreference='Stop'
$exe=(Resolve-Path (Join-Path $PSScriptRoot 'bin/PhotographyWorkbench.exe')).Path
$desktop=Join-Path ([Environment]::GetFolderPath('Desktop')) ($name+'.lnk')
$shell=New-Object -ComObject WScript.Shell
$link=$shell.CreateShortcut($desktop)
if($link.TargetPath -and $link.TargetPath -ne $exe){throw 'An existing shortcut belongs to a different workbench. Choose another workbench_name.'}
$link.TargetPath=$exe;$link.Arguments='';$link.IconLocation="$exe,0";$link.WorkingDirectory=Split-Path -Parent $exe;$link.Save()
Add-Type -TypeDefinition @'
using System;
using System.Runtime.InteropServices;
using System.Runtime.InteropServices.ComTypes;
[ComImport,Guid("00021401-0000-0000-C000-000000000046")]class PhotoShellLink{}
[StructLayout(LayoutKind.Sequential)]struct PhotoPropertyKey{public Guid fmtid;public uint pid;}
[StructLayout(LayoutKind.Explicit)]struct PhotoPropVariant{[FieldOffset(0)]public ushort vt;[FieldOffset(8)]public IntPtr value;}
[ComImport,Guid("886D8EEB-8CF2-4446-8D02-CDBA1DBDCF99"),InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]interface PhotoPropertyStore{
 void GetCount(out uint count);void GetAt(uint index,out PhotoPropertyKey key);void GetValue(ref PhotoPropertyKey key,out PhotoPropVariant value);void SetValue(ref PhotoPropertyKey key,ref PhotoPropVariant value);void Commit();
}
public class PhotoShortcutIdentity{
 public static void Set(string file,string id){object link=new PhotoShellLink();try{var persist=(IPersistFile)link;persist.Load(file,2);var store=(PhotoPropertyStore)link;var key=new PhotoPropertyKey{fmtid=new Guid("9F4C2855-9F79-4B39-A8D0-E1D42DE1D5F3"),pid=5};var value=new PhotoPropVariant{vt=31,value=Marshal.StringToCoTaskMemUni(id)};try{store.SetValue(ref key,ref value);store.Commit();persist.Save(file,true);}finally{Marshal.FreeCoTaskMem(value.value);}}finally{Marshal.FinalReleaseComObject(link);}}
}
'@
[PhotoShortcutIdentity]::Set($desktop,$id)
$pinned=Join-Path $env:APPDATA 'Microsoft/Internet Explorer/Quick Launch/User Pinned/TaskBar'
Get-ChildItem -LiteralPath $pinned -Filter '*.lnk' | ForEach-Object {
    $item=$shell.CreateShortcut($_.FullName)
    if($item.TargetPath -eq $exe){[PhotoShortcutIdentity]::Set($_.FullName,$id);Write-Output "Matched pinned application: $($_.Name)"}
}
Write-Output 'Desktop and matching pinned shortcuts use the same workbench identity.'
