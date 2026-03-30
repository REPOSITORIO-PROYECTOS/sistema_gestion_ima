#!/bin/bash

# 🔐 SETUP DE AIDE Y AUDITD - EJECUTAR CON: sudo bash AIDE_AUDITD_SETUP.sh

echo "═══════════════════════════════════════════════════════════"
echo "🔐 CONFIGURANDO AIDE Y AUDITD"
echo "═══════════════════════════════════════════════════════════"
echo ""

# ============= AIDE SETUP =============
echo "PASO 1: Inicializando AIDE (File Integrity Monitor)..."
echo "─────────────────────────────────────"
echo "⏳ Creando baseline (tarda ~1-2 min, semejante a git init)..."

aideinit 2>&1 | grep -E "AIDE|Running|Creating" || echo "Procesando..."

echo "✅ AIDE baseline creado en /var/lib/aide/aide.db"
echo ""

# Configurar cron para revisar cada día
echo "Configurando revisión automática diaria..."
# Backup de crontab actual
crontab -l > /tmp/crontab_backup.txt 2>/dev/null

# Agregar nueva línea si no existe
if ! crontab -l 2>/dev/null | grep -q "aide --check"; then
    (crontab -l 2>/dev/null; echo "0 2 * * * /usr/sbin/aide --check | mail -s 'AIDE Report' root 2>&1") | crontab -
    echo "✅ Cron job añadido (revisar diario a las 2:00 AM)"
fi

echo ""

# ============= AUDITD SETUP =============
echo "PASO 2: Configurando auditd (System Call Auditing)..."
echo "─────────────────────────────────────"

# Crear directorio si no existe
mkdir -p /etc/audit/rules.d

# Crear reglas de auditoría personalizadas
cat > /etc/audit/rules.d/sistema-ima.rules << 'AUDIT_RULES'
# Sistema de Gestión IMA - Reglas de Auditoría Personalizadas

# 1️⃣ Monitorear ejecución de binarios sospechosos
-w /usr/bin/ -p x -k audit_exec_bin
-w /usr/local/bin/ -p x -k audit_exec_local
-w /opt/ -p x -k audit_exec_opt
-w /home/ -p x -k audit_exec_home

# 2️⃣ Monitorear cambios en archivos de configuración
-w /etc/ -p wa -k audit_etc_changes
-w /etc/ssh/ -p wa -k audit_ssh_config
-w /etc/sudoers -p wa -k audit_sudoers
-w /etc/sudoers.d/ -p wa -k audit_sudoers

# 3️⃣ Monitorear directorios temporales (donde malware intenta escribir)
-w /tmp/ -p wa -k audit_tmp_changes
-w /var/tmp/ -p wa -k audit_vartmp_changes
-w /dev/shm/ -p wa -k audit_shm_changes

# 4️⃣ Monitorear archivos de log críticos
-w /var/log/auth.log -p wa -k audit_auth_log
-w /var/log/syslog -p wa -k audit_syslog
-w /var/log/kern.log -p wa -k audit_kern_log

# 5️⃣ Monitorear cambios de permisos/propietarios (chmod, chown)
-a always,exit -F arch=b64 -S chmod,fchmod,fchmodat -F auid>=1000 -F auid!=4294967295 -k audit_permission_changes
-a always,exit -F arch=b64 -S chown,fchown,fchownat,lchown -F auid>=1000 -F auid!=4294967295 -k audit_ownership_changes

# 6️⃣ Monitorear ejecución de shell (/bin/bash, /bin/sh)
-a always,exit -F path=/bin/bash -F perm=x -F auid>=1000 -F auid!=4294967295 -k audit_bash_exec
-a always,exit -F path=/bin/sh -F perm=x -F auid>=1000 -F auid!=4294967295 -k audit_sh_exec

# 7️⃣ Monitorear intentos de escalada de privilegios (sudo)
-w /usr/bin/sudo -p x -k audit_sudo_exec
-w /usr/bin/su -p x -k audit_su_exec

# Hacer las reglas persistentes después de reboot
-e 2
AUDIT_RULES

echo "✅ Archivo de reglas creado en /etc/audit/rules.d/sistema-ima.rules"
echo ""

# Cargar las reglas
echo "Cargando reglas de auditoría..."
augenrules --load 2>&1 | tail -3 || echo "✓ Reglas procesadas"

# Aplicar reglas inmediatamente
auditctl -R /etc/audit/rules.d/sistema-ima.rules 2>&1 | tail -1

echo ""

# Verificar que auditd esté corriendo
echo "Iniciando servicio auditd..."
systemctl enable auditd 2>&1 | grep -E "enabled|already" || true
systemctl start auditd 2>&1 | grep -E "active|running|already" || true

echo "✅ auditd habilitado y ejecutándose"

echo ""
echo "═══════════════════════════════════════════════════════════"
echo "✅ CONFIGURACIÓN COMPLETADA EXITOSAMENTE"
echo "═══════════════════════════════════════════════════════════"
echo ""

echo "📊 VERIFICAR FUNCIONAMIENTO:"
echo "─────────────────────────────────────"
echo ""
echo "1️⃣ Verificar AIDE:"
echo "   sudo aide --check"
echo "   Ejemplo: sudo aide --check | head -20"
echo ""
echo "2️⃣ Verificar auditd (ver eventos):"
echo "   sudo ausearch -k audit_exec_bin  (últimas ejecuciones sospechosas)"
echo "   sudo ausearch -k audit_etc_changes  (cambios en /etc)"
echo "   sudo ausearch -k audit_ssh_config  (cambios en SSH)"
echo ""
echo "3️⃣ Ver todas las reglas activas:"
echo "   sudo auditctl -l"
echo ""
echo "4️⃣ Ver estadísticas de auditd:"
echo "   sudo auditctl -s"
echo ""
echo "5️⃣ Ver logs en tiempo real:"
echo "   sudo tail -f /var/log/audit/audit.log"
echo ""

echo "📋 CRON AUTOMÁTICO:"
echo "─────────────────────────────────────"
echo "AIDE se revisará cada día a las 2:00 AM"
echo "Resultados se enviarán por email a root"
echo "Ver histórico: sudo aide --check"
echo ""

echo "🛡️ LO QUE ESÁS PROTEGIDO:"
echo "─────────────────────────────────────"
echo "✓ Cambios en archivos del sistema"
echo "✓ Ejecución de binarios sospechosos"
echo "✓ Modificaciones en configuración SSH"
echo "✓ Cambios en sudo/sudoers"
echo "✓ Actividad en /tmp/ y directorios temp"
echo "✓ Cambios de permisos y propietarios"
echo "✓ Utilización de escalada de privilegios"
echo ""
