import json
import os
import requests # Usamos la librería requests, que es más potente
import time

# --- CONFIGURACIÓN ---
# Estos valores se obtendrán de los "Secrets" de GitHub Actions
GIST_ID = os.getenv('GIST_ID')
GH_TOKEN = os.getenv('GH_TOKEN')
OUTPUT_FILENAME = "videos.json" # Nombre del archivo local y en el Gist

def get_category_data(category_key):
    """Obtiene los datos JSON para una clave de categoría específica."""
    url = f"https://b.jw-cdn.org/apis/mediator/v1/categories/S/{category_key}?detailed=1&clientType=www"
    print(f"-> Explorando categoría: {category_key}")
    try:
        response = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'})
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"!! Error al obtener la categoría {category_key}: {e}")
        return None

def format_video(media_item):
    """Convierte un item de la API al formato que necesita nuestra app."""
    try:
        title = media_item['title']
        guid = media_item['naturalKey']
        image_url = media_item['images']['wss']['lg']
        published_date = media_item['firstPublished']
        video_url_720p = next((f.get('progressiveDownloadURL') for f in media_item.get('files', []) if f.get('label') == '720p'), None)
        
        if not video_url_720p:
            return None

        return {"guid": guid, "title": title, "url": video_url_720p, "image": image_url, "published": published_date}
    except (KeyError, TypeError, IndexError):
        return None

def explore_and_extract(category, all_videos, seen_guids):
    """Explora recursivamente las categorías y extrae los vídeos."""
    for item in category.get('media', []):
        guid = item.get('naturalKey')
        if guid and guid not in seen_guids:
            formatted_video = format_video(item)
            if formatted_video:
                all_videos.append(formatted_video)
                seen_guids.add(guid)
    
    for subcategory in category.get('subcategories', []):
        key = subcategory.get('key')
        if key:
            time.sleep(0.1)
            sub_data = get_category_data(key)
            if sub_data and 'category' in sub_data:
                explore_and_extract(sub_data['category'], all_videos, seen_guids)

def update_gist(content):
    """Actualiza el Gist de GitHub con el nuevo contenido JSON."""
    if not GIST_ID or not GH_TOKEN:
        print("Error: GIST_ID o GH_TOKEN no están configurados. No se puede actualizar el Gist.")
        return

    print(f"Preparando para actualizar el Gist: {GIST_ID}")
    url = f"https://api.github.com/gists/{GIST_ID}"
    headers = {
        "Authorization": f"token {GH_TOKEN}",
        "Accept": "application/vnd.github.v3+json"
    }
    payload = {
        "files": {
            OUTPUT_FILENAME: {
                "content": content
            }
        }
    }
    
    response = requests.patch(url, headers=headers, json=payload)
    if response.status_code == 200:
        print("¡Gist actualizado con éxito!")
    else:
        print(f"Error al actualizar el Gist: {response.status_code} - {response.text}")

def main():
    """Función principal que orquesta todo el proceso."""
    print("Iniciando la extracción completa de vídeos...")
    root_data = get_category_data('VideoOnDemand')
    
    if not root_data or 'category' not in root_data:
        print("No se pudo obtener la categoría raíz. Abortando.")
        return

    all_videos = []
    seen_guids = set()
    explore_and_extract(root_data['category'], all_videos, seen_guids)

    print("\n--- Ordenando vídeos ---")
    all_videos.sort(key=lambda x: x['published'], reverse=True)
    print(f"Se han ordenado {len(all_videos)} vídeos únicos por fecha.")

    # Convertimos la lista final a una cadena de texto JSON
    json_content = json.dumps(all_videos, indent=4, ensure_ascii=False)
    
    # Llamamos a la función para actualizar el Gist
    update_gist(json_content)

if __name__ == "__main__":
    main()
