#!/bin/bash

# Script para listar dispositivos USB y Seriales conectados
# Ayuda a identificar en qué puerto está conectada la balanza

echo "=========================================="
echo "    DIAGNÓSTICO DE PUERTOS USB/SERIAL"
echo "=========================================="
echo ""

echo "[1] Listando dispositivos USB conectados (lsusb):"
lsusb
echo ""
echo "------------------------------------------"
echo ""

echo "[2] Listando puertos serie detectados (/dev/tty*):"
# Busca dispositivos ttyUSB o ttyACM que son comunes para balanzas
ls -l /dev/ttyUSB* /dev/ttyACM* 2>/dev/null
if [ $? -ne 0 ]; then
    echo "   -> No se encontraron dispositivos ttyUSB o ttyACM estándar."
else
    echo "   -> Dispositivos encontrados arriba."
fi
echo ""
echo "------------------------------------------"
echo ""

echo "[3] Detalles detallados de dispositivos USB (dmesg | grep usb):"
echo "   (Mostrando las últimas 20 líneas relacionadas con USB)"
dmesg | grep -i usb | tail -n 20
echo ""
echo "------------------------------------------"
echo ""

echo "[4] Grupos del usuario actual (para verificar permisos):"
groups
echo ""
echo "   -> NOTA: El usuario debe estar en el grupo 'dialout' para acceder a puertos serie."
echo "            Si no está, ejecutar: sudo usermod -a -G dialout $USER"
echo ""
echo "=========================================="
echo "Diagnóstico finalizado."
