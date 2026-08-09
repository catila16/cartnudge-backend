web: python main.py
worker: celery -A app.workers.cart_scheduler worker --loglevel=info --pool=solo --concurrency=1 --max-tasks-per-child=20
