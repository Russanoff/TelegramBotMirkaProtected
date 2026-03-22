import yookassa
from yookassa import Refund
from yookassa import Configuration, Payment
import uuid
from config import SHOP_ID, SECRET_KEY


yookassa.Configuration.account_id = SHOP_ID
yookassa.Configuration.secret_key = SECRET_KEY


def create_pay(amount, user_id, msg_id, days):
    idempotence_key = str(uuid.uuid4())
    payment = Payment.create({
        "amount": {
            "value": amount,
            "currency": "RUB"
        },
        "confirmation": {
            "type": "redirect",
            "return_url": "https://t.me/mirkaprotecbot"
        },
        "capture": True,
        "metadata": {
            "user_id": user_id,
            "msg_id": msg_id,
            "term":days
        },
        "description": "Оплата доступа к платным услугам и товарам."
    }, idempotence_key)

    return payment.confirmation.confirmation_url, payment.id


