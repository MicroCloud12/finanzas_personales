# finanzas/tasks.py

from celery import shared_task

@shared_task
def procesar_tickets_drive(user_id):
    """
    Esta es la tarea que se ejecutará en segundo plano.
    Por ahora, solo imprimirá un mensaje en la consola de Celery
    para confirmar que se está ejecutando.
    """
    print(f"¡Éxito! La tarea de procesamiento de Drive se ha iniciado para el usuario con ID: {user_id}")

    # Aquí es donde, en el futuro, irá toda la lógica para:
    # 1. Conectar con la API de Google Drive.
    # 2. Listar y descargar las imágenes de los tickets.
    # 3. Enviar las imágenes a la API de Gemini.
    # 4. Recibir el JSON y guardarlo en la base de datos.

    return f"Tarea completada para el usuario {user_id}"