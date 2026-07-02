module.exports = {
  apps: [
    {
      // --- BACKEND DE PYTHON (HTTP only, sin scheduler) ---
      name: "gestion-ima-api",
      script: "bash",
      args: [
        "-c",
        "export PYTHONPATH=/home/dev_taup/proyectos/sistema_gestion_ima:$PYTHONPATH && " +
        "cd /home/dev_taup/proyectos/sistema_gestion_ima/back && " +
        "exec ../back/venv/bin/gunicorn main:app " +
        "-k uvicorn.workers.UvicornWorker " +
        "-w ${GUNICORN_WORKERS:-2} " +
        "-b 127.0.0.1:8011 " +
        "--timeout 120 " +
        "--graceful-timeout 30 " +
        "--access-logfile - " +
        "--error-logfile -"
      ],
      cwd: "/home/dev_taup/proyectos/sistema_gestion_ima/back/",
      env: {
        APP_ENV: "production",
        SQL_ECHO: "false",
        API_ENABLE_SCHEDULER: "false",
        DB_POOL_SIZE: "20",
        DB_MAX_OVERFLOW: "20",
        DB_POOL_TIMEOUT: "30",
        GUNICORN_WORKERS: "2",
      },
      watch: false,
      max_memory_restart: "512M",
    },
    {
      // --- WORKER DE SYNC GOOGLE SHEETS (APScheduler aparte del API) ---
      name: "gestion-ima-sync",
      script: "bash",
      args: [
        "-c",
        "export PYTHONPATH=/home/dev_taup/proyectos/sistema_gestion_ima:$PYTHONPATH && " +
        "/home/dev_taup/proyectos/sistema_gestion_ima/back/venv/bin/python -m back.sync_worker"
      ],
      cwd: "/home/dev_taup/proyectos/sistema_gestion_ima/",
      env: {
        APP_ENV: "production",
        SQL_ECHO: "false",
        DB_POOL_SIZE: "10",
        DB_MAX_OVERFLOW: "10",
      },
      watch: false,
      max_memory_restart: "384M",
    },
    {
      // --- FRONTEND DE NEXT.JS ---
      name: "gestion-ima-front",
      script: "npm",
      args: "start -- -H 127.0.0.1 -p 3016",
      cwd: "/home/dev_taup/proyectos/sistema_gestion_ima/front/",
      interpreter: "node",
      watch: false,
    },
    {
      // --- BOVEDA MICROSERVICIO ---
      name: "boveda-microservicio",
      script: "bash",
      args: [
        "-c",
        "../back/venv/bin/python -m uvicorn boveda_main:app --host 127.0.0.1 --port 8015"
      ],
      cwd: "/home/dev_taup/proyectos/sistema_gestion_ima/boveda_microservicio/",
      watch: false,
    }
  ]
};
