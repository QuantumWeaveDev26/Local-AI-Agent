# Read-only audit. Run on the Dell; never reports environment variable values.
$ErrorActionPreference = 'Stop'
$os = Get-CimInstance Win32_OperatingSystem
$cpu = Get-CimInstance Win32_Processor
$gpu = Get-CimInstance Win32_VideoController
[PSCustomObject]@{
    OS = $os.Caption
    Version = $os.Version
    CPU = ($cpu.Name -join ', ')
    RAMGiB = [math]::Round($os.TotalVisibleMemorySize / 1MB, 2)
    FreeRAMGiB = [math]::Round($os.FreePhysicalMemory / 1MB, 2)
    VirtualizationFirmwareEnabled = ($cpu.VirtualizationFirmwareEnabled -join ', ')
    GPU = ($gpu.Name -join ', ')
    NVIDIA_Driver = ($gpu.DriverVersion -join ', ')
} | Format-List
Get-PSDrive -PSProvider FileSystem | Select-Object Name, @{n='FreeGiB';e={[math]::Round($_.Free/1GB,2)}}
foreach ($tool in @('python','pip','uv','git','ollama','docker','nvidia-smi')) {
    $found = Get-Command $tool -ErrorAction SilentlyContinue
    if ($found) {
        if ($tool -eq 'nvidia-smi') { & $tool --query-gpu=name,driver_version,memory.total,memory.used --format=csv }
        else { & $tool --version }
    } else { Write-Output "$tool : not installed" }
}
