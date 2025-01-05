from fastapi import FastAPI

from saga_manager import consume_message, publish_message
from models import Payment, User, Order, Product
from database import SessionLocal, init_db

import threading


router = FastAPI()

PAYMENT_QUEUE = "payment_queue"
ORDER_QUEUE = 'order_queue'


@router.on_event("startup")
def startup_event():
    init_db()
    threading.Thread(target=lambda: consume_message(PAYMENT_QUEUE, process_payment)).start()


def process_payment(message):
    order_id = message["order_id"]
    status = message["status"]

    with SessionLocal() as db:
        payment = db.query(Payment).filter(Payment.order_id == order_id).first()
        order = db.query(Order).filter(Order.id == order_id).first()
        product = db.query(Product).filter(Product.id == order.product_id).first()
        user = db.query(User).filter(User.id == order.user_id).first()

        if not payment:
            payment = Payment(order_id=order_id, status="processing")
            db.add(payment)

        if status == "payment_processing":
            print(f"Processing payment with order_id -> {order_id}.")

            total_payment = product.price * order.quantity

            if user.wallet < total_payment:
                return publish_message(PAYMENT_QUEUE, {"order_id": order_id, "status": "payment_refused"})

            user.wallet -= total_payment
            payment.status = "success"

            print(f"Processing payment with order_id: {order_id} -> {payment.status}.\n"
                  f"User with id -> {user.id}, spent {total_payment}, now he has {user.wallet}.")
            publish_message(ORDER_QUEUE, {"order_id": order_id, "status": "order_approved"})

        elif status == 'payment_refund':
            total_to_refund = product.price * order.quantity

            # Refund the money to the user.
            user.wallet += total_to_refund
            payment.status = "refund"

            print(f"Order with id: {order_id} -> {payment.status}, user refunded.")

        elif status == 'payment_refused':
            payment.status = "refused"
            order.status = "failed"
            print(f"Order with id: {order_id} -> {payment.status}, not enough money.")

        db.commit()


@router.get("/payments/{order_id}")
def get_payment_status(order_id: int):
    with SessionLocal() as db:
        payment = db.query(Payment).filter(Payment.order_id == order_id).first()

        if not payment:
            return {"order_id": order_id, "status": f"Payment not found for the order_id -> {order_id}!"}

        return {"order_id": order_id, "status": payment.status}
