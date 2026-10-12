# `just comfy`: start the project's own ComfyUI portable install in the foreground (Ctrl+C stops it).
#
# Only this install, only on 127.0.0.1, with the output and models folders `just render` and
# `just models` expect, and without workflow metadata in the saved PNGs. Paths come from the
# STILLSTIFT_COMFY_* variables (see .env.example), with the D:\Stillstift defaults.
$ErrorActionPreference = 'Stop'

function Get-Setting([string] $name, [string] $default) {
    $value = [Environment]::GetEnvironmentVariable($name)
    if ([string]::IsNullOrWhiteSpace($value)) { return $default }
    return $value
}

$home_ = Get-Setting 'STILLSTIFT_COMFY_HOME' 'D:\Stillstift\ComfyUI'
$url = [Uri] (Get-Setting 'STILLSTIFT_COMFY_URL' 'http://127.0.0.1:8189')
$output = Get-Setting 'STILLSTIFT_COMFY_OUTPUT' 'D:\Stillstift\outputs'
$models = Get-Setting 'STILLSTIFT_COMFY_MODELS' (Join-Path $home_ 'ComfyUI\models')

# The render step talks to STILLSTIFT_COMFY_URL; anything but loopback would expose the install.
if ($url.Host -ne '127.0.0.1') {
    throw "STILLSTIFT_COMFY_URL must point at 127.0.0.1, not $($url.Host)"
}
$python = Join-Path $home_ 'python_embeded\python.exe'
$main = Join-Path $home_ 'ComfyUI\main.py'
foreach ($path in $python, $main) {
    if (-not (Test-Path -LiteralPath $path -PathType Leaf)) {
        throw "no ComfyUI portable install at $home_ (missing $path)"
    }
}
if (-not (Test-Path -LiteralPath $models -PathType Container)) {
    throw "no models folder at $models"
}
# Whatever already listens on the port is someone else's; leave it alone rather than compete.
if (Get-NetTCPConnection -LocalPort $url.Port -State Listen -ErrorAction SilentlyContinue) {
    throw "port $($url.Port) is in use already; not starting a second server on it"
}
New-Item -ItemType Directory -Force -Path $output | Out-Null

& $python -s $main `
    --windows-standalone-build `
    --listen 127.0.0.1 `
    --port $url.Port `
    --output-directory $output `
    --models-directory $models `
    --disable-metadata `
    --disable-auto-launch
exit $LASTEXITCODE
