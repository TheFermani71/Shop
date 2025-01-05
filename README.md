# Shop
Shop is a project developed for the Parallel and Distributed Programming exam. It consists of a set of APIs implemented with the fastapi lib in Python and follows the SAGA design pattern.

## Requirements
For running the project you just have to copy and paste the following command line.

```bash
# Check if "fastapi" is downloaded in your virtual environment or inside your global environment.
pip3 install fastapi pika sqlalchemy uvicorn pydantic;

# Run docker with rabbitmq with the following commands.
docker run rabbitmq;
docker run rabbitmq:management;
docker run -d --name rabbitmq -p 5672:5672 -p 15672:15672 rabbitmq:management;


# Run in development mode, now you have 3 microservices up: 
# - product   -> "http://127.0.0.1:8000/docs" to see all the products APIs.
# - order     -> "http://127.0.0.1:8001/docs" to see all the orders APIs.
# - payment   -> "http://127.0.0.1:8002/docs" to see all the payments APIs.
chmod +x run.sh;
./run.sh;

# Otherwise you can run three different command for each terminal or all in one.
uvicorn product_service:router --reload --port=8000 &
uvicorn order_service:router --reload --port=8001 &
uvicorn payment_service:router --reload --port=8002 & wait;
```
