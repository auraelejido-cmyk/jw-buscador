import json
import urllib.request
import time

NOMBRE_ARCHIVO_SALIDA = "videos.json"

def formatear_video_para_app(media_item):
    """Convierte un item de la API al formato que necesita nuestra app."""
    try:
        titulo = media_item['title']
        guid = media_item['naturalKey']
        imagen_url = media_item['images']['wss']['lg']
        fecha_publicacion = media_item['firstPublished']
        video_url_720p = None
        for archivo in media_item.get('files', []):
            if archivo.get('label') == '720p':
                video_url_720p = archivo.get('progressiveDownloadURL')
                break
        if not video_url_720p:
            return None
        return {
            "guid": guid,
            "title": titulo,
            "url": video_url_720p,
            "image": imagen_url,
            "published": fecha_publicacion
        }
    except (KeyError, TypeError, IndexError):
        return None

def obtener_datos_categoria(key_categoria):
    """Obtiene los datos JSON para una clave de categoría específica."""
    url = f"https://b.jw-cdn.org/apis/mediator/v1/categories/S/{key_categoria}?detailed=1&clientType=www"
    print(f"-> Obteniendo datos de: {key_categoria}")
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req) as response:
            return json.load(response)
    except Exception as e:
        print(f"!! Error al obtener la categoría {key_categoria}: {e}")
        return None

def explorar_y_extraer_videos(categoria_actual, videos_encontrados, ids_vistos):
    """Función recursiva: extrae vídeos y explora subcategorías DENTRO de una categoría principal."""
    for item in categoria_actual.get('media', []):
        guid = item.get('naturalKey')
        if guid not in ids_vistos:
            video_formateado = formatear_video_para_app(item)
            if video_formateado:
                videos_encontrados.append(video_formateado)
                ids_vistos.add(guid)
    
    for subcategoria_info in categoria_actual.get('subcategories', []):
        key_subcategoria = subcategoria_info.get('key')
        if key_subcategoria:
            time.sleep(0.1) 
            datos_subcategoria = obtener_datos_categoria(key_subcategoria)
            if datos_subcategoria and 'category' in datos_subcategoria:
                explorar_y_extraer_videos(datos_subcategoria['category'], videos_encontrados, ids_vistos)

def main():
    """Función principal del script."""
    print("Iniciando la extracción completa de vídeos por categorías...")
    datos_raiz = obtener_datos_categoria('VideoOnDemand')
    
    if not datos_raiz or 'category' not in datos_raiz:
        print("No se pudo obtener la categoría raíz. Abortando.")
        return

    datos_finales_por_categoria = {}
    
    # 1. Recorremos las categorías principales (Películas, Familia, etc.)
    for categoria_principal in datos_raiz['category'].get('subcategories', []):
        nombre_categoria = categoria_principal.get('name')
        key_categoria = categoria_principal.get('key')

        if not all([nombre_categoria, key_categoria]):
            continue

        print(f"\n--- Procesando categoría principal: {nombre_categoria} ---")
        
        videos_de_esta_categoria = []
        ids_vistos_en_esta_categoria = set()
        
        # Obtenemos los datos detallados de esta categoría principal
        datos_categoria_detallados = obtener_datos_categoria(key_categoria)
        if datos_categoria_detallados and 'category' in datos_categoria_detallados:
            # 2. Empezamos la exploración recursiva DESDE esta categoría
            explorar_y_extraer_videos(datos_categoria_detallados['category'], videos_de_esta_categoria, ids_vistos_en_esta_categoria)

        # 3. Ordenamos los vídeos de esta categoría por fecha
        videos_de_esta_categoria.sort(key=lambda video: video['published'], reverse=True)
        
        # 4. Añadimos la categoría y sus vídeos al resultado final
        if videos_de_esta_categoria:
            datos_finales_por_categoria[nombre_categoria] = videos_de_esta_categoria
            print(f"--- {nombre_categoria} finalizada. Se encontraron {len(videos_de_esta_categoria)} vídeos. ---")

    print("\n--- Proceso finalizado ---")
    
    with open(NOMBRE_ARCHIVO_SALIDA, 'w', encoding='utf-8') as f:
        json.dump(datos_finales_por_categoria, f, indent=4, ensure_ascii=False)
    
    print(f"¡Éxito! Archivo '{NOMBRE_ARCHIVO_SALIDA}' creado con la estructura de categorías.")

if __name__ == "__main__":
    main()
