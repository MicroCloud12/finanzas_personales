# finanzas/tasks.py
import os
import json
from io import BytesIO
from decimal import Decimal
from datetime import datetime
from celery import shared_task
from django.conf import settings
from django.contrib.auth.models import User
from allauth.socialaccount.models import SocialApp
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from PIL import Image
import google.generativeai as genai
from .models import registro_transacciones


def get_folder_id(drive_service, folder_name: str, parent_folder_id: str = 'root'):
    try:
        query = f"name='{folder_name}' and '{parent_folder_id}' in parents and mimeType='application/vnd.google-apps.folder' and trashed=false"
        response = drive_service.files().list(q=query, spaces='drive', fields='files(id, name)').execute()
        files = response.get('files', [])
        return files[0]['id'] if files else None
    except HttpError as error:
        print(f"Ocurrió un error al buscar la carpeta '{folder_name}': {error}")
        return None

def move_file_to_processed(drive_service, file_id, original_folder_id):
    processed_folder_id = get_folder_id(drive_service, 'Procesados', parent_folder_id=original_folder_id)
    if not processed_folder_id:
        print("Creando carpeta 'Procesados'...")
        file_metadata = {
            'name': 'Procesados',
            'mimeType': 'application/vnd.google-apps.folder',
            'parents': [original_folder_id]
        }
        processed_folder = drive_service.files().create(body=file_metadata, fields='id').execute()
        processed_folder_id = processed_folder.get('id')
    try:
        file = drive_service.files().get(fileId=file_id, fields='parents').execute()
        previous_parents = ",".join(file.get('parents'))
        drive_service.files().update(
            fileId=file_id,
            addParents=processed_folder_id,
            removeParents=previous_parents,
            fields='id, parents'
        ).execute()
        print(f"Archivo {file_id} movido a la carpeta 'Procesados'.")
    except HttpError as error:
        print(f"Ocurrió un error al mover el archivo: {error}")


@shared_task
def procesar_tickets_drive(user_id, auth_token, refresh_token):
    print(f"--- Iniciando procesamiento de tickets para el usuario ID: {user_id} ---")
    try:
        app = SocialApp.objects.get(provider='google')
        usuario = User.objects.get(id=user_id)

        creds = Credentials(
            token=auth_token,
            refresh_token=refresh_token,
            token_uri='https://oauth2.googleapis.com/token',
            client_id=app.client_id,
            client_secret=app.secret
        )
        drive_service = build('drive', 'v3', credentials=creds)
        print("Conexión con Google Drive API exitosa.")

        genai.configure(api_key=settings.GEMINI_API_KEY)
        model = genai.GenerativeModel("models/gemini-1.5-flash")

        folder_to_check = "Tickets de Compra" 
        folder_id = get_folder_id(drive_service, folder_to_check)
        
        if not folder_id:
            print(f"El usuario no tiene una carpeta llamada '{folder_to_check}'. Finalizando tarea.")
            return

        query = f"'{folder_id}' in parents and (mimeType='image/jpeg' or mimeType='image/png') and trashed=false"
        results = drive_service.files().list(q=query, fields="nextPageToken, files(id, name)").execute()
        items = results.get('files', [])

        if not items:
            print("No se encontraron nuevos tickets para procesar.")
            return "No hay archivos nuevos."

        print(f"Se encontraron {len(items)} tickets. Procesando...")
        for item in items:
            print(f"\nProcesando archivo: {item['name']} (ID: {item['id']})")
            file_id = item['id']

            request = drive_service.files().get_media(fileId=file_id)
            file_content = BytesIO(request.execute())
            image = Image.open(file_content)

            prompt = """
            Caso 1: Analiza la imagen de este ticket de compra. Extrae la siguiente información y devuélvela ESTRICTAMENTE en formato JSON, sin texto adicional antes o después del JSON:
                - "fecha": La fecha en formato YYYY-MM-DD.
                - "establecimiento": El nombre de la tienda.
                - "total": El monto total como un número (float).
            Caso 2: Analiza la imagen de este comprobante de transferencia. Extrae la siguiente información y devuélvela ESTRICTAMENTE en formato JSON:
                - "fecha": La fecha en formato YYYY-MM-DD.
                - "descripcion": El concepto de la transferencia.
                - "total": El monto como un número (float).
            """
            
            response = model.generate_content([prompt, image])
            cleaned_response = response.text.strip().replace("```json", "").replace("```", "").strip()
            
            try:
                data = json.loads(cleaned_response)
                
                fecha_obj = datetime.strptime(data.get("fecha"), "%Y-%m-%d").date()

                registro_transacciones.objects.create(
                    propietario=usuario,
                    fecha=fecha_obj,
                    descripcion=data.get("descripcion", data.get("establecimiento", "Sin descripción")),
                    categoria="Compra",
                    monto=Decimal(data.get("total", 0.0)),
                    tipo='GASTO',
                    cuenta_origen="Ticket de Drive",
                    cuenta_destino="N/A"
                )
                print(f"¡Éxito! Ticket '{item['name']}' guardado en la base de datos.")

                move_file_to_processed(drive_service, file_id, folder_id)

            except (json.JSONDecodeError, KeyError, ValueError) as e:
                print(f"Error al procesar o guardar datos del ticket '{item['name']}': {e}")
                print(f"Respuesta de Gemini que causó el error: {cleaned_response}")

    except Exception as e:
        print(f"Ocurrió un error inesperado en la tarea Celery: {type(e).__name__} - {e}")

    return f"Procesamiento finalizado para el usuario {user_id}."