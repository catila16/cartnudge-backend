web: sh -c "uvicorn main:app --host 0.0.0.0 --port $PORT"
worker: celery -A app.workers.cart_scheduler worker --loglevel=info
