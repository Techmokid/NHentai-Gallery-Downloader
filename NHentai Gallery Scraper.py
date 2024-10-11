import aiohttp
import asyncio
import os
from bs4 import BeautifulSoup
import time
import zipfile
import shutil

desktop = os.path.join(os.path.join(os.environ['USERPROFILE']), 'Desktop')
downloadDirectory = os.path.join(desktop, "NHentai Backups")

CPU_Core_Count = os.cpu_count()
WORKER_COUNT = 8 * CPU_Core_Count

# Retry count for failed downloads
retries = 10
rate_limit_retries = 5  # Number of times to retry on rate limit
rate_limit_wait = 10  # Fixed wait time for rate limit in seconds

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
                    elif response.status == 429:
                        print(f"Rate limit exceeded for {image_url}. Waiting {rate_limit_wait} seconds before retrying...")
                        await asyncio.sleep(rate_limit_wait)  # Wait before retrying
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

def zip_folder(folder_path):
    zip_file_path = f"{folder_path}.zip"
    with zipfile.ZipFile(zip_file_path, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        for foldername, subfolders, filenames in os.walk(folder_path):
            for filename in filenames:
                file_path = os.path.join(foldername, filename)
                # Add file to the zip file, keeping the directory structure
                zip_file.write(file_path, os.path.relpath(file_path, folder_path))
    #print(f"Zipped folder: {zip_file_path}")

# Main function to download the full gallery
async def download_full_gallery(galleryID, downloadDir, englishOnly):
    print(f"Checking NHentai gallery {galleryID}")
    correctedGalleryID = str(galleryID)
    baseGalleryURL = 'https://nhentai.net/g/' + correctedGalleryID + '/'

    if englishOnly and not await checkEnglish(baseGalleryURL):
        return 0
    
    downloadPath = os.path.join(downloadDir, str(galleryID))
    if os.path.exists(downloadPath + ".zip"):
        print(f"Gallery ID {galleryID} - Already zipped")
        print()
        return 0
    
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
                    print(f"Gallery ID {galleryID} - File already exists: {image_name}, skipping.")
        
        # Count number of successfully downloaded pages
        download_count = 0
        tasks = [download_image(session, image_url, downloadPath) for image_url in filtered_image_urls]
        results = await asyncio.gather(*tasks)
        download_count += sum(results)  # Sum the successful downloads
    
    print(f"Gallery ID {galleryID} - Zipping up gallery...")
    #zip_folder(downloadPath)
    #if os.path.exists(downloadPath):
    #    shutil.rmtree(downloadPath)
    
    print(f"Gallery ID {galleryID} - Finished download of NHentai gallery {galleryID}. Total images downloaded: {download_count}")
    print()
    return download_count  # Return the count of pages/images downloaded


# Wrapper to run all gallery downloads in one event loop
async def download_multiple_galleries(start_id, end_id, downloadDir, englishOnly=True):
    total_pages_downloaded = 0
    for i in range(start_id, end_id + 1):
        downloaded_pages = await download_full_gallery(i, downloadDir, englishOnly)
        total_pages_downloaded += downloaded_pages
    return total_pages_downloaded

async def fetch(url):
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            return await response.text()

async def checkEnglish(url):
    try:
        # Fetch the content of the webpage
        html_content = await fetch(url)

        # Parse the content with BeautifulSoup
        soup = BeautifulSoup(html_content, 'html.parser')

        # Select the specific section
        section = soup.select_one('body > div:nth-of-type(2) > div:nth-of-type(1) > div:nth-of-type(2) > div > section')
        
        if section:
            #print("Section found!")  # Debugging output
            
            # Find all divs with class "tag-container field-name"
            tag_containers = section.find_all('div', class_='tag-container field-name')
            #print(f"Found {len(tag_containers)} tag containers.")  # Debugging output
            
            # Find the specific div containing "Languages:"
            languages_container = None
            for container in tag_containers:
                #print("Checking container:", container.get_text(strip=True))  # Debugging output
                if "Languages:" in container.get_text(strip=True):
                    languages_container = container
                    break
            
            if languages_container:
                #print("Languages container found!")  # Debugging output
                
                # Find all the anchor tags within the "tags" span
                tags_span = languages_container.find('span', class_='tags')
                links = tags_span.find_all('a')
                
                if links:
                    for link in links:
                        href = str(link['href'])
                        # Check if "english" is in the href
                        if "english" in href.lower():  # Use lower() to ensure case insensitivity
                            print("Found english comic")
                            return True  # Return True if "english" is found
                    # Only return False here if no links contained "english"
                    #print("No 'english' tag found in any links.")
                    return False  
                else:
                    #print("No tags found under the Languages div.")
                    return False
            else:
                #print("No Languages container found.")
                return False
        else:
            #print("Specified section not found.")
            return False
    
    except Exception as e:
        print(f"Error fetching the URL: {e}")
        return False

# Start tracking the time
start_time = time.time()

# Run the event loop for all galleries
total_pages_downloaded = asyncio.run(download_multiple_galleries(0, 999999, downloadDirectory))
#total_pages_downloaded = asyncio.run(download_multiple_galleries(514900, 515000, downloadDirectory))

# Calculate the total time taken
end_time = time.time()
total_time = end_time - start_time

# Print the results
print(f"Total time taken:       {total_time:.2f} seconds")
print(f"Total pages downloaded: {total_pages_downloaded}")

if total_pages_downloaded > 0:
    timePerPage = total_time / total_pages_downloaded
    print(f"Time taken per page:     {timePerPage:.2f} seconds")
    cTTDE_Seconds = 16619421 * timePerPage
    cTTDE_Days = cTTDE_Seconds / 86400
    print(f"Calculated time to download all of NHentai is {cTTDE_Days} days")
