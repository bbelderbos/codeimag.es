web: gunicorn -w 4 -k uvicorn.workers.UvicornWorker tips.main:app
release: alembic upgrade head
