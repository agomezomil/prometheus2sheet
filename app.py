import requests
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd
from datetime import datetime

# --- CONFIGURACIÓN ---
PROMETHEUS_URL = "http://prometheus-01-ams01-monitoreo.apps.ocp02-prod.ams.red/"
SHEET_NAME = "Reporte demo"
CREDENTIALS_FILE = 'credentials.json'

# Definimos los 3 SLOs con sus queries
QUERIES_SLO = {
    "SLO Web": """100 * min by (env, tribu) (avg_over_time(probe_success{app="Abacom", name=" Web Abacom Nueva"}[30d]))""",
    "SLO Login": """100 * min by (env, tribu) (avg_over_time(probe_success{app="Abacom", name=~".*Abacom Login|Web Abacom Nueva"}[30d]))""",
    "SLO Cotizar": """100 * min by (env, tribu) (avg_over_time(probe_success{app="Abacom", name=~".*Abacom Login|Web Abacom Nueva| Cotizar Potencial Asociado|Listado Potencial Asociado"}[30d]))""",
    "SLO Afiliar": """avg_over_time((min by (env, tribu) (probe_success{app="Abacom", name=~".*Abacom Login|.*Web Abacom Nueva|.*Listado Potencial Asociado|.*Ficha Guardar.*"}))[30d:1m]) * 100 """
}

def get_slo_data():
    all_rows = []
    timestamp_ejecucion = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    for nombre_slo, query in QUERIES_SLO.items():
        print(f"Consultando {nombre_slo}...")
        try:
            response = requests.get(f"{PROMETHEUS_URL}/api/v1/query", params={'query': query}, timeout=30)
            response.raise_for_status()
            results = response.json()['data']['result']
            
            for item in results:
                row = item['metric'].copy()
                row['tipo_slo'] = nombre_slo
                row['valor'] = round(float(item['value'][1]), 3)
                row['fecha_reporte'] = timestamp_ejecucion
                all_rows.append(row)
        except Exception as e:
            print(f"Error en {nombre_slo}: {e}")
            
    return all_rows

def update_google_sheet(data):
    print("Conectando con Google Sheets...")
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_name(CREDENTIALS_FILE, scope)
    client = gspread.authorize(creds)
    
    spreadsheet = client.open(SHEET_NAME)
    sheet = spreadsheet.get_worksheet(0)
    
    df = pd.DataFrame(data)
    
    # Definimos el orden de las columnas según lo que se ve en tu imagen
    cols = ['fecha_reporte', 'tipo_slo', 'env', 'tribu', 'valor']
    df = df[cols]
    

    # Limpiar la hoja y escribir encabezados + datos
    sheet.clear()
    
    # 3. Preparar los datos (Encabezados + Valores)
    # Convertimos todo a string para evitar errores de formato en la API
    headers = df.columns.values.tolist()
    values = df.values.tolist()
    data_to_upload = [headers] + values
    
    # 4. Actualizar usando la sintaxis más compatible
    sheet.update(range_name='A1', values=data_to_upload)
        
    print(f"✅ ¡Éxito! Se escribieron {len(df)} filas con encabezados.")

if __name__ == "__main__":
    datos = get_slo_data()
    if datos:
        update_google_sheet(datos)