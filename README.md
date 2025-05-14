# Parcial A – Procesamiento de Imágenes Asíncrono

Este repo es el MVP para el **Parcial A**, cumple todos los puntos del PDF

## Levantamiento

```bash
docker compose up --build
```

- **RabbitMQ** en `:5672` (management UI en `:15672`)
  
- **Redis** en `:6379`
  
- **API** en `:8000`
  

## Los endpoints:

- **POST** `/upload`
  
  - `multipart/form-data` campo `file`
    
  - Valida que sea imagen, guarda en `/shared/images/<job_id>/original`
    
  - Encola en `resize`, marca `QUEUED` en Redis
    
  - Devuelve `{ "job_id": "<uuid>" }`
    
- **GET** `/status/{job_id}`
  
  - Lee en Redis `job:<job_id>`
    
  - Devuelve `{ status, step?, label?, file? }`
    

## Arquitectura & Stack

- **docker-compose** orquesta todos los contenedores
  
- **Volumes**
  
  - `rabbit_data` → persiste colas de RabbitMQ
    
  - `shared-data` → persiste imágenes y `status.json`
    
- **RabbitMQ**
  
  - **Colas** `resize`, `watermark`, `detect` (durable, prefetch=1, manual ack)
    
  - **Exchange** `processed_images` (fanout) para publish/subscribe de resultados
    
- **Workers** (en `/workers`)
  
  - `resize_worker.py`: thumbnail 1024×1024 → cola `watermark`
    
  - `watermark_worker.py`: pone “© ParcialA” → cola `detect`
    
  - `detect_worker.py`: asigna etiqueta fake → actualiza Redis + publica en `processed_images`
    
  - Todos usan bucle de reintento contra RabbitMQ para no fallar al arrancar
    
- **Redis** guarda el estado de cada job (`QUEUED`, `PROCESSING`, `COMPLETED`, `FAILED`)
  

## Justificaciones

- **Réplicas**
  
  `resize`: 1 réplica (CPU‐bound, rápido),`watermark` & `detect`: escalables (I/O y lógica más pesada)
  
- **Exchange & Bindings**
  
  Colas en modo *work-queue* (round‐robin) para balancear,`processed_images` fanout: cualquiera puede suscribirse a resultados finales
  
- **Errores & Reintentos**
  
  `basic_ack` manual + `prefetch_count=1`: si un worker muere antes de ack, RabbitMQ reencola. No hay backoff extra; el mensaje vuelve a la cola automáticamente
  
- **Persistencia vs Consistencia**
  
  Imágenes y JSON de estado en disco (`shared-data`), sobreviven reinicios, y mensajes durables (`delivery_mode=2`) en RabbitMQ → no se pierden en crash
  

## Flujo

1. Cliente: `POST /upload` → recibe `job_id`
  
2. API: escribe Redis `QUEUED`; encola en `resize`
  
3. `resize_worker` → imagen redimensionada → encola en `watermark`
  
4. `watermark_worker` → marca imagen → encola en `detect`
  
5. `detect_worker` → “detecta” etiqueta → actualiza Redis + publica en `processed_images`
  
6. Cliente: `GET /status/{job_id}` para ver resultado
