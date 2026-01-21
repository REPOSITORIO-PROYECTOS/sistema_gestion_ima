module.exports = {
  apps: [
    {
      // --- BACKEND DE PYTHON ---
      name: "gestion-ima-api",
      script: "bash",
      args: [
        "-c",
        "source venv/bin/activate && " +
        "export PYTHONPATH=/home/sgi_user/proyectos/sistema_gestion_ima:$PYTHONPATH && " +
        "gunicorn -w 4 -k uvicorn.workers.UvicornWorker main:app --bind 127.0.0.1:8000"
      ],
      cwd: "/home/sgi_user/proyectos/sistema_gestion_ima/back/",
      watch: false,
    },
    {
      // --- FRONTEND DE NEXT.JS ---
      name: "gestion-ima-front",
      script: "npm",
      args: "start -- -H 127.0.0.1",
      cwd: "/home/sgi_user/proyectos/sistema_gestion_ima/front/",
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
      cwd: "/home/sgi_user/proyectos/sistema_gestion_ima/boveda_microservicio/",
      watch: false,
    }
  ]
};
