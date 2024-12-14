from pydantic import BaseModel
from fastapi import FastAPI

from saga_manager import publish_message, consume_message
from database import SessionLocal, init_db
from models import Order

import threading


router = FastAPI()

ORDER_QUEUE = "order_queue"
PAYMENT_QUEUE = "payment_queue"


# Pydantic schema
class OrderRequest(BaseModel):
    product_id: int
    quantity: int


def process_order(message):
    order_id = message["order_id"]

    with SessionLocal() as db:
        order = db.query(Order).filter(Order.id == order_id).first()

        if not order:
            return

        try:
            # Simulate order processing
            print(f"Processing order with id -> {order_id}.")

            # if order_id % 2 == 0:  # Simulate failure for even orders
            #     raise Exception("Order validation failed.")

            order.status = "approved"
            publish_message(PAYMENT_QUEUE, {"order_id": order_id, "status": "order_approved"})

        except Exception as e:
            order.status = "failed"
            publish_message(PAYMENT_QUEUE, {"order_id": order_id, "status": "order_failed"})

        finally:
            print(f"Order with id: {order_id} -> {order.status}!")
            db.commit()


'''
def handle_refund_event(message):
    if message.get("event") == "RefundEvent":
        order_id = message["order_id"]

        with SessionLocal() as db:
            order = db.query(Order).filter(Order.order_id == order_id).first()

            if order:
                order.status = "canceled"
                db.commit()
                print(f"Order {order_id} canceled due to refund.")
'''


@router.post("/orders")
def create_order(order: OrderRequest):
    with SessionLocal() as db:
        new_order = Order(product_id=order.product_id, quantity=order.quantity, status="created")
        db.add(new_order)
        db.commit()
        db.refresh(new_order)

        # Publish order_created event
        publish_message(ORDER_QUEUE, {"event": "order_created", "order_id": new_order.id})

    return {"message": f"Order with id -> {new_order.id} created."}


@router.get("/orders")
def list_orders():
    with SessionLocal() as db:
        orders = db.query(Order).all()
        return [
            {
                "id": o.id,
                "product_id": o.product_id,
                "quantity": o.quantity,
                "status": o.status
            } for o in orders
        ]


# Startup: Initialize database and listen for events
@router.on_event("startup")
def startup_event():
    init_db()
    threading.Thread(target=lambda: consume_message(ORDER_QUEUE, process_order)).start()
