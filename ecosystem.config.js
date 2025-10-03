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
        "gunicorn -w 4 -k uvicorn.workers.UvicornWorker main:app --bind 0.0.0.0:8000"
      ],
      cwd: "/home/sgi_user/proyectos/sistema_gestion_ima/back/",
      watch: false,
    },
    {
      // --- FRONTEND DE NEXT.JS ---
      name: "gestion-ima-front",
      script: "npm",
      args: "start",
      cwd: "/home/sgi_user/proyectos/sistema_gestion_ima/front/",
      interpreter: "node",
      watch: false,
    }
  ]
};
