from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from saga_manager import publish_message, consume_message
from database import SessionLocal, init_db
from models import Order, Product

import threading
import random


router = FastAPI()

ORDER_QUEUE = "order_queue"
PAYMENT_QUEUE = "payment_queue"


# Pydantic schema
class OrderRequest(BaseModel):
    product_id: int
    user_id: int
    quantity: int


def process_order(message):
    order_id = message["order_id"]
    status = message['status']

    with SessionLocal() as db:
        order = db.query(Order).filter(Order.id == order_id).first()

        if not order:
            print('Order not found!')
            return

        # Fetch the product.
        product = db.query(Product).filter(Product.id == order.product_id).first()

        if status == 'order_created':
            print(f"Processing order with id -> {order_id}.")

            # If product not present inside the db we call the event "order_failed".
            if not product:
                return publish_message(ORDER_QUEUE, {"order_id": order_id, "status": "order_failed"})

            # Check if enough quantity is available otherwise call the event "order_not_enough".
            if product.quantity < order.quantity:
                return publish_message(ORDER_QUEUE, {"order_id": order_id, "status": "order_not_enough"})

            publish_message(PAYMENT_QUEUE, {"order_id": order_id, "status": "payment_processing"})

        elif status == "order_approved":
            product.quantity -= order.quantity
            order.status = "approved"

        elif status == 'order_failed':
            print('Product not found!')
            order.status = 'failed'

        elif status == 'order_not_enough':
            print('Product quantity not enough!')
            order.status = 'failed'

        elif status == 'order_cancelled':
            # Increment the product quantity back.
            product.quantity += order.quantity

            # Marked order as cancelled.
            order.status = 'cancelled'

            # Delete the associated payment if it exists.
            publish_message(PAYMENT_QUEUE, {"order_id": order.id, "status": "payment_refund"})

        elif status == 'order_retry':
            print('Some error happened, retry in few minutes!')
            order.status = 'error'

        print(f"Order with id: {order_id} -> {order.status}!")
        db.commit()


@router.post("/orders/add")
def create_order(order: OrderRequest):
    with SessionLocal() as db:
        # Create a new order.
        new_order = Order(product_id=order.product_id, user_id=order.user_id, quantity=order.quantity, status="created")

        # try - catch implemented to catch error so we can do the rollback and publish the event -> "order_retry".
        try:
            db.add(new_order)

            # Generate a random number, if modulo 3 equal 0 we throw the exception.
            if random.randint(1, 10) % 3 == 0:
                print(0 / 0)

        except ZeroDivisionError:
            db.rollback()
            publish_message(ORDER_QUEUE, {"order_id": new_order.id, "status": "order_retry"})
            return {"message": f"Order error!"}

        else:
            db.commit()
            db.refresh(new_order)

        # Publish event "order_created" inside the "order_queue".
        publish_message(ORDER_QUEUE, {"order_id": new_order.id, "status": "order_created"})

    return {"message": f"Order with id -> {new_order.id} created."}


@router.delete("/orders/{order_id}")
def delete_order(order_id: int):
    with SessionLocal() as db:
        order = db.query(Order).filter(Order.id == order_id).first()

        if not order:
            raise HTTPException(status_code=404, detail="Order not found!")

        if order.status != 'approved':
            raise HTTPException(status_code=400, detail="You can delete only an 'approved' order!")

        # Delete the associated order and relative payment if exists.
        publish_message(ORDER_QUEUE, {"order_id": order.id, "status": "order_cancelled"})

    return {"message": f"Processing deletion of order with id -> {order_id}."}


@router.get("/orders")
def list_orders():
    with SessionLocal() as db:
        orders = db.query(Order).all()
        return [
            {
                "id": o.id,
                "product_id": o.product_id,
                "user_id": o.user_id,
                "quantity": o.quantity,
                "status": o.status
            } for o in orders
        ]


# Startup: Initialize database and listen for events
@router.on_event("startup")
def startup_event():
    init_db()
    threading.Thread(target=lambda: consume_message(ORDER_QUEUE, process_order)).start()
