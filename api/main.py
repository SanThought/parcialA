import os, uuid, json, time
from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import JSONResponse
import pika, redis

app = FastAPI()

# Configuración
RABBIT_URL = os.getenv("RABBIT_URL", "amqp://guest:guest@rabbitmq:5672/")
REDIS_HOST = os.getenv("REDIS_HOST", "redis")
IMAGE_DIR = os.getenv("IMAGE_DIR", "/shared/images")

# Crear conexión a RabbitMQ con reintento
params = pika.URLParameters(RABBIT_URL)
while True:
    try:
        rabbit_conn = pika.BlockingConnection(params)
        break
    except pika.exceptions.AMQPConnectionError:
        print("Esperando RabbitMQ...")
        time.sleep(2)

channel = rabbit_conn.channel()
channel.queue_declare(queue="resize", durable=True)
channel.queue_declare(queue="watermark", durable=True)
channel.queue_declare(queue="detect", durable=True)
channel.exchange_declare(exchange="processed_images", exchange_type="fanout", durable=True)

# Redis
redis_client = redis.Redis(host=REDIS_HOST, port=6379, decode_responses=True)

@app.post("/upload")
async def upload_image(file: UploadFile = File(...)):
    if file.content_type.split("/")[0] != "image":
        raise HTTPException(400, "Solo se aceptan archivos de imagen")

    job_id = str(uuid.uuid4())
    job_dir = os.path.join(IMAGE_DIR, job_id)
    os.makedirs(job_dir, exist_ok=True)
    orig_path = os.path.join(job_dir, "original")

    with open(orig_path, "wb") as f:
        f.write(await file.read())

    task = {"job_id": job_id, "path": orig_path}
    channel.basic_publish(
        exchange="",
        routing_key="resize",
        body=json.dumps(task).encode(),
        properties=pika.BasicProperties(delivery_mode=2)
    )

    redis_client.hset(f"job:{job_id}", mapping={"status": "QUEUED", "step": "resize"})
    return {"job_id": job_id}

@app.get("/status/{job_id}")
def get_status(job_id: str):
    data = redis_client.hgetall(f"job:{job_id}")
    if not data:
        raise HTTPException(404, "job_id no encontrado")
    return JSONResponse(data)
