param(
    [ValidateSet('Install','Poll','Configure','Verify','Probe')][string]$Mode,
    [Parameter(Mandatory=$true)][string]$GuestPassword
)
$ErrorActionPreference = 'Stop'
$vmrun = 'F:\Vmware\vmrun.exe'
$vmx = 'E:\ubtuntu12\Ubuntu 64-bit.vmx'
$auth = @('-gu','qyunt','-gp',$GuestPassword)
function Invoke-VM([string[]]$VmArgs) {
    & $vmrun @auth @VmArgs
    if ($LASTEXITCODE -ne 0) { throw "VMware operation failed: $($VmArgs[0])" }
}
if ($Mode -eq 'Poll') {
    Invoke-VM @('copyFileFromGuestToHost',$vmx,'/tmp/codex-ros-progress.log',(Join-Path $PSScriptRoot 'ros-progress.log'))
    Get-Content -LiteralPath (Join-Path $PSScriptRoot 'ros-progress.log') -Tail 12
    foreach ($stage in @('INSTALL','CONFIGURE','VERIFY')) {
        if (Select-String -LiteralPath (Join-Path $PSScriptRoot 'ros-progress.log') -Pattern "${stage}_EXIT=0" -Quiet) {
            Copy-Item -LiteralPath (Join-Path $PSScriptRoot 'ros-progress.log') -Destination (Join-Path $PSScriptRoot ('ros-' + $stage.ToLowerInvariant() + '.log'))
        }
    }
    exit
}
$scriptName = 'ros-' + $Mode.ToLowerInvariant() + '.sh'
$scriptPath = Join-Path $PSScriptRoot $scriptName
if (!(Test-Path -LiteralPath $scriptPath)) { throw "Missing task script: $scriptName" }
Invoke-VM @('copyFileFromHostToGuest',$vmx,$scriptPath,('/tmp/codex-' + $scriptName))
if ($Mode -eq 'Install') {
    $quotedPassword = "'" + $GuestPassword.Replace("'", "'\''") + "'"
    $guestCommand = "printf '%s\n' $quotedPassword | sudo -S -p '' /bin/bash /tmp/codex-$scriptName > /tmp/codex-ros-progress.log 2>&1"
} else {
    $guestCommand = "/bin/bash /tmp/codex-$scriptName > /tmp/codex-ros-progress.log 2>&1"
}
Invoke-VM @('runScriptInGuest',$vmx,'-noWait','/bin/bash',$guestCommand)
Write-Output "Started ROS stage: $Mode"
