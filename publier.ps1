# Publie une nouvelle version de TamagoChat (mise à jour automatique de tous les chats).
#   .\publier.ps1          -> version suivante (ex : 1.0.0 -> 1.0.1)
#   .\publier.ps1 1.2.0    -> version précise
param([string]$Version)
$py = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"
if ($Version) { & $py (Join-Path $PSScriptRoot "publier.py") $Version }
else { & $py (Join-Path $PSScriptRoot "publier.py") }
