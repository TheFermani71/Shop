from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from saga_manager import publish_message, consume_message
from database import SessionLocal, init_db
from models import Order, Product

import threading


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
            return

        if status != 'order_created':
            return

        try:
            # Simulate order processing
            print(f"Processing order with id -> {order_id}.")

            order.status = "approved"
            publish_message(PAYMENT_QUEUE, {"order_id": order_id, "status": "order_approved"})

        except Exception as e:
            order.status = "failed"
            publish_message(PAYMENT_QUEUE, {"order_id": order_id, "status": "order_failed"})

        finally:
            print(f"Order with id: {order_id} -> {order.status}!")
            db.commit()


@router.post("/orders")
def create_order(order: OrderRequest):
    with SessionLocal() as db:
        # Fetch the product
        product = db.query(Product).filter(Product.id == order.product_id).first()
        
        if not product:
            raise HTTPException(status_code=404, detail="Product not found!")
        
        # Check if enough quantity is available
        if product.quantity < order.quantity:
            raise HTTPException(status_code=400, detail="Not enough product quantity available!")

        # Decrease the product quantity.
        product.quantity -= order.quantity

        # Create a new order
        new_order = Order(product_id=order.product_id, user_id=order.user_id, quantity=order.quantity, status="created")
        db.add(new_order)
        db.commit()

        db.refresh(new_order)

        # Publish order_created event
        publish_message(ORDER_QUEUE, {"status": "order_created", "order_id": new_order.id})

    return {"message": f"Order with id -> {new_order.id} created. Product quantity updated."}


@router.delete("/orders/{order_id}")
def delete_order(order_id: int):
    with SessionLocal() as db:
        # Fetch the order
        order = db.query(Order).filter(Order.id == order_id).first()
        if not order:
            raise HTTPException(status_code=404, detail="Order not found!")

        # Fetch the associated product
        product = db.query(Product).filter(Product.id == order.product_id).first()

        # Increment the product quantity back
        product.quantity += order.quantity

        # Delete the associated payment if it exists
        publish_message(PAYMENT_QUEUE, {"order_id": order.id, "status": "order_refund"})

        # Marked order as cancelled.
        order.status = 'cancelled'

        # Commit all changes in a single transaction
        db.commit()

    return {"message": f"Order {order_id} deleted, payment refunded, and product quantity restored."}


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
