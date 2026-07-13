# Subir articulos.xls desde tu PC Windows al servidor
# Ejecutar en PowerShell (en tu PC, no en el servidor):
#
#   scp "$env:USERPROFILE\OneDrive\Documentos\articulos.xls" `
#       dev_taup@164.68.118.75:"/home/dev_taup/proyectos/sistema_gestion_ima/datos /articulos.xls"
#
# O arrastrá el archivo a la carpeta "datos " en Cursor (panel izquierdo).

$origen = "$env:USERPROFILE\OneDrive\Documentos\articulos.xls"
$destino = "dev_taup@164.68.118.75:/home/dev_taup/proyectos/sistema_gestion_ima/datos /articulos.xls"

if (-not (Test-Path $origen)) {
    Write-Error "No encontré: $origen"
    exit 1
}

Write-Host "Subiendo $origen ..."
scp $origen $destino
if ($LASTEXITCODE -eq 0) {
    Write-Host "Listo. Avisale al agente que ya está subido."
}
