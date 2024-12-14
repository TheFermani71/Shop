cd src;

uvicorn product_service:router --reload --port=8000 &
uvicorn order_service:router --reload --port=8001 &
uvicorn payment_service:router --reload --port=8002 &
wait;
