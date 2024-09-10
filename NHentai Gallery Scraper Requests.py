import requests
from bs4 import BeautifulSoup
import os
from concurrent.futures import ThreadPoolExecutor

desktop = os.path.join(os.path.join(os.environ['USERPROFILE']), 'Desktop')
downloadDirectory = os.path.join(desktop,"NHentai Backups")

CPU_Core_Count = os.cpu_count()
WORKER_COUNT = 4*CPU_Core_Count

# Function to download an image
def download_image(image_url, folder):
    # Create a folder if it doesn't exist
    if not os.path.exists(folder):
        os.makedirs(folder, exist_ok=True)
    
    # Extract the image name from the URL
    image_name = image_url.split('/')[-1]
    image_path = os.path.join(folder, image_name)

    # Download the image
    response = requests.get(image_url)
    if response.status_code == 200:
        with open(image_path, 'wb') as img_file:
            img_file.write(response.content)
        print(f"Downloaded: {image_name}")
    else:
        print(f"Failed to download image from {image_url}. Status code: {response.status_code}")

# Function to scrape and download the image from the nhentai gallery page
def get_gallery_image_url(url):
    # Fetch the HTML content
    response = requests.get(url)
    
    if response.status_code == 200:
        soup = BeautifulSoup(response.content, 'html.parser')

        # Try using more flexible CSS selector that includes 'img' inside '#image-container'
        image_tag = soup.select_one('#image-container img')

        if image_tag:
            # Check if the image is lazy-loaded (e.g., in 'data-src' or 'src')
            image_url = image_tag.get('data-src') or image_tag.get('src')

            # Prepend the protocol if missing (nhentai often uses 'https')
            if not image_url.startswith('http'):
                image_url = 'https:' + image_url

            print(f"Image URL found: {image_url}")
            return image_url
        else:
            print("Image not found on the page.")
    else:
        print(f"Failed to load the page. Status code: {response.status_code}")
    return None

def download_full_gallery(galleryID, downloadDir):
    correctedGalleryID = str("0" * (6 - len(str(galleryID)))) + str(galleryID)
    baseGalleryURL = 'https://nhentai.net/g/' + correctedGalleryID + '/'
    print(baseGalleryURL)
    
    galleryIndex = 1
    downloadPath = os.path.join(downloadDir, str(galleryID))
    print(downloadPath)
    
    image_urls = []
    
    while True:
        page_url = baseGalleryURL + str(galleryIndex)
        image_url = get_gallery_image_url(page_url)
        if image_url:
            image_urls.append((image_url, downloadPath))
            galleryIndex += 1
        else:
            break
    
    # Download images in parallel using ThreadPoolExecutor
    with ThreadPoolExecutor(max_workers=WORKER_COUNT) as executor:
        executor.map(lambda url_folder: download_image(*url_folder), image_urls)

    return

def cloneEVERYTHING(downloadDir):
    for i in range(0,999999):
        download_full_gallery(529194, downloadDir)





download_full_gallery(529194, downloadDirectory)








