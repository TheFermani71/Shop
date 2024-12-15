from fastapi import FastAPI

from saga_manager import publish_message, consume_message
from models import Payment, User, Order, Product
from database import SessionLocal, init_db

import threading


router = FastAPI()

PAYMENT_QUEUE = "payment_queue"
COMPENSATION_QUEUE = "compensation_queue"


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

        if status == "order_approved":
            print(f"Processing payment with order_id -> {order_id}.")

            try:
                total_payment = product.price * order.quantity

                if user.wallet < total_payment:
                    raise Exception("Not enough money in the user wallet!")

                # Decrease the money quantity.
                user.wallet -= total_payment

                payment.status = "success"
                print(f"Processing payment with order_id: {order_id} -> {payment.status}.\n"
                      f"User with id -> {user.id}, spent {total_payment}, now he has {user.wallet}.")

            except Exception as e:
                payment.status = "failed"
                print(f"Payment with order_id: {order_id} -> {payment.status}.")
                # publish_message(COMPENSATION_QUEUE, {"order_id": order_id, "status": "order_failed"})

        elif status == "order_failed":
            payment.status = "failed"
            print(f"Order with id: {order_id} -> {payment.status}. No payment required.")

        elif status == 'order_refund':
            total_to_refund = product.price * order.quantity

            # Refund the money.
            user.wallet += total_to_refund

            payment.status = "refund"
            print(f"Order with id: {order_id} -> {payment.status}, user refunded.")

        db.commit()


@router.get("/payments/{order_id}")
def get_payment_status(order_id: int):
    with SessionLocal() as db:
        payment = db.query(Payment).filter(Payment.order_id == order_id).first()

        if not payment:
            return {"order_id": order_id, "status": "Payment not found!"}

        return {"order_id": order_id, "status": payment.status}
