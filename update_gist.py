import json
import os
import requests

# --- Configuration ---
API_URL = "https://b.jw-cdn.org/apis/mediator/v1/categories/S/VideoOnDemand?detailed=1&clientType=www"
OUTPUT_FILENAME = "videos.json"

def get_category_data(category_key):
    """Fetches JSON data for a specific category key."""
    url = f"https://b.jw-cdn.org/apis/mediator/v1/categories/S/{category_key}?detailed=1&clientType=www"
    print(f"-> Fetching category: {category_key}")
    try:
        response = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'})
        response.raise_for_status() # Raises an exception for bad status codes
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"!! Error fetching category {category_key}: {e}")
        return None

def format_video(media_item):
    """Converts a media item to our app's format."""
    try:
        title = media_item['title']
        guid = media_item['naturalKey']
        image_url = media_item['images']['wss']['lg']
        published_date = media_item['firstPublished']

        video_url_720p = None
        for file_info in media_item.get('files', []):
            if file_info.get('label') == '720p':
                video_url_720p = file_info.get('progressiveDownloadURL')
                break
        
        if not video_url_720p:
            return None

        return {
            "guid": guid,
            "title": title,
            "url": video_url_720p,
            "image": image_url,
            "published": published_date
        }
    except (KeyError, TypeError, IndexError):
        return None

def explore_and_extract(category, all_videos, seen_guids):
    """Recursively explores categories and extracts videos."""
    # 1. Extract videos from the current category
    for item in category.get('media', []):
        guid = item.get('naturalKey')
        if guid and guid not in seen_guids:
            formatted_video = format_video(item)
            if formatted_video:
                all_videos.append(formatted_video)
                seen_guids.add(guid)
    
    # 2. Explore subcategories
    for subcategory in category.get('subcategories', []):
        key = subcategory.get('key')
        if key:
            sub_data = get_category_data(key)
            if sub_data and 'category' in sub_data:
                explore_and_extract(sub_data['category'], all_videos, seen_guids)

def main():
    """Main script execution."""
    print("Starting full video extraction...")
    root_data = get_category_data('VideoOnDemand')
    
    if not root_data or 'category' not in root_data:
        print("Could not fetch the root category. Aborting.")
        return

    all_videos = []
    seen_guids = set()
    
    explore_and_extract(root_data['category'], all_videos, seen_guids)

    print("\n--- Sorting process ---")
    all_videos.sort(key=lambda x: x['published'], reverse=True)
    print(f"Sorted {len(all_videos)} unique videos by date.")
    
    # Save the file locally for the GitHub Action to pick up
    with open(OUTPUT_FILENAME, 'w', encoding='utf-8') as f:
        json.dump(all_videos, f, indent=4, ensure_ascii=False)
    
    print(f"Success! File '{OUTPUT_FILENAME}' created locally.")

if __name__ == "__main__":
    main()
