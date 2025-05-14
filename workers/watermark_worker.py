import os
import json
import time
import pika
from PIL import Image, ImageDraw, ImageFont

# Bucle RabbitMQ
params = pika.URLParameters(os.getenv("RABBIT_URL"))
while True:
    try:
        conn = pika.BlockingConnection(params)
        break
    except pika.exceptions.AMQPConnectionError:
        print("watermark_worker: esperando RabbitMQ...")
        time.sleep(2)

ch = conn.channel()
ch.queue_declare(queue="watermark", durable=True)
ch.basic_qos(prefetch_count=1)

FONT_PATH = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"

def callback(ch, method, props, body):
    payload = json.loads(body)
    job_id = payload["job_id"]
    img_path = payload["path"]

    # watermark
    img = Image.open(img_path).convert("RGBA")
    txt = Image.new("RGBA", img.size, (255, 255, 255, 0))
    d = ImageDraw.Draw(txt)
    fnt = ImageFont.truetype(FONT_PATH, 36)
    d.text((10, img.size[1] - 50), "© ParcialA", font=fnt, fill=(255,255,255,128))
    watermarked = Image.alpha_composite(img, txt)
    out = os.path.join(os.path.dirname(img_path), "watermarked.png")
    watermarked.convert("RGB").save(out, "PNG")

    # siguiente paso
    next_msg = {"job_id": job_id, "path": out}
    ch.basic_publish(
        exchange="",
        routing_key="detect",
        body=json.dumps(next_msg).encode(),
        properties=pika.BasicProperties(delivery_mode=2)
    )
    ch.basic_ack(method.delivery_tag)

ch.basic_consume(queue="watermark", on_message_callback=callback)
ch.start_consuming()

