import aiohttp
import asyncio
import os
from bs4 import BeautifulSoup
import time  # Import time module

desktop = os.path.join(os.path.join(os.environ['USERPROFILE']), 'Desktop')
downloadDirectory = os.path.join(desktop, "NHentai Backups")

CPU_Core_Count = os.cpu_count()
WORKER_COUNT = 8 * CPU_Core_Count

# Retry count for failed downloads
retries = 3

# Async function to download an image
semaphore = asyncio.Semaphore(10)  # Limit concurrent downloads to 10
async def download_image(session, image_url, folder):
    async with semaphore:  # Ensure only 10 downloads are running concurrently
        if not os.path.exists(folder):
            os.makedirs(folder, exist_ok=True)
        
        image_name = image_url.split('/')[-1]
        image_path = os.path.join(folder, image_name)

        for attempt in range(retries):
            try:
                async with session.get(image_url, timeout=15) as response:
                    if response.status == 200:
                        with open(image_path, 'wb') as img_file:
                            img_file.write(await response.read())
                        return 1  # Return 1 to indicate success
                    else:
                        print(f"Failed to download image from {image_url}. Status code: {response.status}")
            except asyncio.TimeoutError:
                print(f"Timeout on attempt {attempt + 1} for {image_url}")
        return 0  # Return 0 if all attempts failed


# Async function to scrape the gallery page and get image URLs
async def get_gallery_image_url(session, url):
    async with session.get(url) as response:
        if response.status == 200:
            soup = BeautifulSoup(await response.text(), 'html.parser')
            image_tag = soup.select_one('#image-container img')

            if image_tag:
                image_url = image_tag.get('data-src') or image_tag.get('src')
                if not image_url.startswith('http'):
                    image_url = 'https:' + image_url
                return image_url
        return None

# Main function to download the full gallery
async def download_full_gallery(galleryID, downloadDir):
    print(f"Starting download of NHentai gallery {galleryID}")
    correctedGalleryID = str("0" * (6 - len(str(galleryID)))) + str(galleryID)
    baseGalleryURL = 'https://nhentai.net/g/' + correctedGalleryID + '/'
    
    galleryIndex = 1
    downloadPath = os.path.join(downloadDir, str(galleryID))
    
    image_urls = []
    
    async with aiohttp.ClientSession() as session:
        while True:
            page_url = baseGalleryURL + str(galleryIndex)
            image_url = await get_gallery_image_url(session, page_url)
            if image_url:
                # Check if file already exists before adding to download list
                image_name = image_url.split('/')[-1]
                image_path = os.path.join(downloadPath, image_name)
                
                if not os.path.exists(image_path):
                    image_urls.append(image_url)
                else:
                    print(f"File already exists: {image_name}, skipping.")
                
                galleryIndex += 1
            else:
                break
        
        # Count number of successfully downloaded pages
        download_count = 0
        tasks = [download_image(session, image_url, downloadPath) for image_url in image_urls]
        results = await asyncio.gather(*tasks)
        download_count += sum(results)  # Sum the successful downloads
    print(f"Finished download of NHentai gallery {galleryID}. Total images downloaded: {download_count}")
    return download_count  # Return the count of pages/images downloaded

# Wrapper to run the async function in an event loop
def start_gallery_download(galleryID, downloadDir):
    return asyncio.run(download_full_gallery(galleryID, downloadDir))

# Start tracking the time
start_time = time.time()

# Count total pages downloaded across all galleries
total_pages_downloaded = 0

for i in range(529190, 529194):
    downloaded_pages = start_gallery_download(i, downloadDirectory)
    total_pages_downloaded += downloaded_pages
    print()

# Calculate the total time taken
end_time = time.time()
total_time = end_time - start_time

# Print the results
print(f"Total time taken:       {total_time:.2f} seconds")
print(f"Total pages downloaded: {total_pages_downloaded}")

timePerPage = total_time / total_pages_downloaded
print(f"Time taken per page:     {timePerPage:.2f}")
