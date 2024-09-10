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


# Async function to handle concurrent gathering of image URLs
async def gather_image_urls(session, baseGalleryURL, start_index):
    image_urls = []
    galleryIndex = start_index
    while True:
        page_url = baseGalleryURL + str(galleryIndex)
        image_url = await get_gallery_image_url(session, page_url)
        if image_url:
            image_urls.append(image_url)
            galleryIndex += 1
        else:
            break  # Stop gathering if no more valid image URLs are found
    return image_urls


# Main function to download the full gallery
async def download_full_gallery(galleryID, downloadDir):
    print(f"Starting download of NHentai gallery {galleryID}")
    correctedGalleryID = str("0" * (6 - len(str(galleryID)))) + str(galleryID)
    baseGalleryURL = 'https://nhentai.net/g/' + correctedGalleryID + '/'
    
    downloadPath = os.path.join(downloadDir, str(galleryID))
    
    async with aiohttp.ClientSession() as session:
        # Gather URLs concurrently
        image_urls = await gather_image_urls(session, baseGalleryURL, 1)
        
        # Check if file already exists before adding to download list
        filtered_image_urls = []
        for image_url in image_urls:
            if image_url:
                image_name = image_url.split('/')[-1]
                image_path = os.path.join(downloadPath, image_name)

                if not os.path.exists(image_path):
                    filtered_image_urls.append(image_url)
                else:
                    print(f"File already exists: {image_name}, skipping.")
        
        # Count number of successfully downloaded pages
        download_count = 0
        tasks = [download_image(session, image_url, downloadPath) for image_url in filtered_image_urls]
        results = await asyncio.gather(*tasks)
        download_count += sum(results)  # Sum the successful downloads
    
    print(f"Finished download of NHentai gallery {galleryID}. Total images downloaded: {download_count}")
    return download_count  # Return the count of pages/images downloaded


# Wrapper to run all gallery downloads in one event loop
async def download_multiple_galleries(start_id, end_id, downloadDir):
    total_pages_downloaded = 0
    for i in range(start_id, end_id + 1):
        downloaded_pages = await download_full_gallery(i, downloadDir)
        total_pages_downloaded += downloaded_pages
        print()
    return total_pages_downloaded


# Start tracking the time
start_time = time.time()

# Run the event loop for all galleries
total_pages_downloaded = asyncio.run(download_multiple_galleries(529190, 529199, downloadDirectory))

# Calculate the total time taken
end_time = time.time()
total_time = end_time - start_time

# Print the results
print(f"Total time taken:       {total_time:.2f} seconds")
print(f"Total pages downloaded: {total_pages_downloaded}")

if total_pages_downloaded > 0:
    timePerPage = total_time / total_pages_downloaded
    print(f"Time taken per page:     {timePerPage:.2f} seconds")
    cTTDE_Seconds = 16619421*timePerPage
    cTTDE_Days = cTTDE_Seconds / 86400
    print(f"Calculated time to download all of NHentai is {cTTDE_Days} days")
