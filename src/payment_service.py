from fastapi import FastAPI

from saga_manager import publish_message, consume_message
from database import SessionLocal, init_db
from models import Payment

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

        if not payment:
            payment = Payment(order_id=order_id, status="processing")
            db.add(payment)

        if status == "order_approved":
            print(f"Processing payment with order_id -> {order_id}.")

            try:
                # if order_id % 3 == 0:  # Simulate payment failure for some orders
                #     raise Exception("Payment declined by the bank.")

                payment.status = "success"
                print(f"Processing payment with order_id: {order_id} -> {payment.status}.")

            except Exception as e:
                payment.status = "failed"
                print(f"Processing payment with order_id: {order_id} -> {payment.status}.")
                publish_message(COMPENSATION_QUEUE, {"order_id": order_id, "action": "order_refund"})

        elif status == "order_failed":
            payment.status = "order_failed"
            print(f"Order with id: {order_id} -> failed. No payment required.")

        db.commit()


@router.get("/payments/{order_id}")
def get_payment_status(order_id: int):
    with SessionLocal() as db:
        payment = db.query(Payment).filter(Payment.order_id == order_id).first()

        if not payment:
            return {"order_id": order_id, "status": "Payment not found!"}

        return {"order_id": order_id, "status": payment.status}


'''
def handle_order_event(message):
    if message.get("event") == "order_created":
        order_id = message["order_id"]

        with SessionLocal() as db:
            payment = Payment(order_id=order_id, status="processing")
            db.add(payment)

            try:
                # Simulate payment processing
                if order_id % 2 == 0:
                    raise Exception("Payment failed")

                payment.status = "success"
                publish_message(EVENT_EXCHANGE, {"event": "payment_success", "order_id": order_id})
                db.commit()

            except Exception:
                payment.status = "failed"
                publish_message(EVENT_EXCHANGE, {"event": "RefundEvent", "order_id": order_id})
'''
