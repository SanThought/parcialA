import os
import json
import time
import pika
import random

# revisar img dir
IMAGE_DIR = os.getenv("IMAGE_DIR", "/shared/images")
os.makedirs(IMAGE_DIR, exist_ok=True) 

# reintento RabbitMQ
params = pika.URLParameters(os.getenv("RABBIT_URL"))
while True:
    try:
        conn = pika.BlockingConnection(params)
        break
    except pika.exceptions.AMQPConnectionError:
        print("detect_worker: esperando RabbitMQ...")
        time.sleep(2)

ch = conn.channel()
ch.queue_declare(queue="detect", durable=True)
ch.exchange_declare(exchange="processed_images", exchange_type="fanout", durable=True)
ch.basic_qos(prefetch_count=1)

# revisar status.json
IMAGE_DIR = os.getenv("IMAGE_DIR")
STATUS_FILE = os.path.join(IMAGE_DIR, "status.json")
if not os.path.exists(STATUS_FILE):
    with open(STATUS_FILE, "w") as f:
        json.dump({}, f)

LABELS = ["safe", "adult", "violence", "other"]

def update(job_id, new_status, meta):
    with open(STATUS_FILE, "r+") as f:
        d = json.load(f)
        d[job_id] = {"status": new_status, **meta}
        f.seek(0)
        json.dump(d, f)
        f.truncate()

def callback(ch, method, props, body):
    payload = json.loads(body)
    job_id = payload["job_id"]
    img_path = payload["path"]

    # Detección simulada
    label = random.choice(LABELS)
    meta = {"step": "done", "label": label, "file": img_path}
    update(job_id, "COMPLETED", meta)

    # evento fanout
    ch.basic_publish(
        exchange="processed_images",
        routing_key="",
        body=json.dumps({"job_id": job_id, **meta}).encode(),
        properties=pika.BasicProperties(delivery_mode=2)
    )
    ch.basic_ack(method.delivery_tag)

ch.basic_consume(queue="detect", on_message_callback=callback)
ch.start_consuming()

