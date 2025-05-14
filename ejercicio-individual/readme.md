

![Screenshot from 2025-05-13 20-22-43](https://github.com/user-attachments/assets/84bce331-2505-4318-add4-03fe04407aba)


Ejercicio 18 – Feature Flags con un exchange fanout

Para este punto 18 creamos un **exchange** llamado `flags.fanout` de tipo **fanout**, que no utiliza *routing keys*; en su lugar envía cada mensaje a **todas** las colas enlazadas. Ligamos `flags.fanout` a las tres colas receptoras: `service_A`, `service_B` y `service_C`. Al publicar un mensaje (por ejemplo `{"flag":"featureX","enabled":true}`) en `flags.fanout`, éste se duplica y aparece en las tres colas simultáneamente. En la topología se observa el exchange naranja apuntando a cada cola azul, y en el *Message Log* de cada consumidor amarillo se ve claramente cómo cada uno recibe la misma carga útil.
