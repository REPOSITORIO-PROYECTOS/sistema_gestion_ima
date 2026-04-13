module.exports = {
  apps: [
    {
      // --- BACKEND DE PYTHON ---
      name: "gestion-ima-api",
      script: "bash",
      args: [
        "-c",
        "export PYTHONPATH=/home/dev_taup/proyectos/sistema_gestion_ima:$PYTHONPATH && " +
        "/home/dev_taup/proyectos/sistema_gestion_ima/back/venv/bin/python -m uvicorn main:app --host 127.0.0.1 --port 8011"
      ],
      cwd: "/home/dev_taup/proyectos/sistema_gestion_ima/back/",
      watch: false,
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
