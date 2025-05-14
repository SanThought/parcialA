import os
import json
import time
import pika
from PIL import Image

# reintento RabbitMQ
params = pika.URLParameters(os.getenv("RABBIT_URL"))
while True:
    try:
        conn = pika.BlockingConnection(params)
        break
    except pika.exceptions.AMQPConnectionError:
        print("resize_worker: esperando RabbitMQ...")
        time.sleep(2)

ch = conn.channel()
ch.queue_declare(queue="resize", durable=True)
ch.basic_qos(prefetch_count=1)

def callback(ch, method, props, body):
    payload = json.loads(body)
    job_id = payload["job_id"]
    src = payload["path"]

    # resize
    img = Image.open(src)
    img.thumbnail((1024, 1024))
    out = os.path.join(os.path.dirname(src), "resized.jpg")
    img.save(out, "JPEG")

    # Publicar siguiente paso
    next_msg = {"job_id": job_id, "path": out}
    ch.basic_publish(
        exchange="",
        routing_key="watermark",
        body=json.dumps(next_msg).encode(),
        properties=pika.BasicProperties(delivery_mode=2)
    )
    ch.basic_ack(method.delivery_tag)

ch.basic_consume(queue="resize", on_message_callback=callback)
ch.start_consuming()

