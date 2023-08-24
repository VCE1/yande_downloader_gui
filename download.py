import os
import requests
import time
from concurrent.futures import ThreadPoolExecutor
from PyQt5.QtCore import QObject, pyqtSignal, QMutex
import concurrent.futures


class Downloader(QObject):
    log_signal = pyqtSignal(str)
    finished_signal = pyqtSignal()

    def __init__(self, max_workers=8, max_retries=3):
        super().__init__()
        self.directory = ""
        self.search_tag = ""
        self.start_page = 0
        self.end_page = 0
        self.download_original = True
        self.max_workers = max_workers
        self.max_retries = max_retries
        self.mutex = QMutex()

    def setup(self, directory, search_tag, start_page, end_page, download_original=True):
        self.directory = directory
        self.search_tag = search_tag
        self.start_page = start_page
        self.end_page = end_page
        self.download_original = download_original

    def download_images(self, limits):
        self.mutex.lock()
        try:
            with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                tasks = []

                for page in range(self.start_page, self.end_page + 1):
                    tasks.extend(self.download_page(page, executor, limits))

                tasks = [task for task in tasks if task is not None]  # 移除空任务

                if tasks:
                    for future in concurrent.futures.as_completed(tasks):
                        try:
                            result = future.result()
                            if not result:
                                self.log_signal.emit("Error occurred while downloading images.")
                        except Exception as e:
                            self.log_signal.emit(f"Error occurred while downloading images: {str(e)}")
                else:
                    self.log_signal.emit("No tasks to execute. Please check if the tag you entered exists.")
        finally:
            self.mutex.unlock()

        self.finished_signal.emit()

    def download_page(self, page, executor, limits):
        json_data = self.get_json(page, True, limits)

        if json_data is None:
            self.log_signal.emit(f"Error downloading images on page {page}. Skipping...")
            return []

        tasks = []

        for current_post in json_data:
            if self.download_original:
                image_url = current_post['file_url']
            else:
                image_url = current_post['jpeg_url']

            image_id = current_post['id']
            file_extension = os.path.splitext(image_url)[1]
            filename = os.path.join(self.directory, f"{image_id}{file_extension}")
            try:
                task = executor.submit(self.download_image, image_url, filename)
                tasks.append(task)
            except Exception as e:
                self.log_signal.emit(f"Error submitting download task: {str(e)}")

        self.log_signal.emit(f"Downloading images on page {page}...")
        concurrent.futures.wait(tasks)
        return tasks

    def download_image(self, url, filename, retry_count=0):
        if os.path.exists(filename):
            self.log_signal.emit(f"Skipping download, file already exists:\n{filename}")
            return True
        
        while retry_count <= self.max_retries:
            try:
                response = requests.get(url, stream=True)

                if response.status_code == 200:
                    with open(filename, 'wb') as f:
                        for chunk in response.iter_content(chunk_size=1024):
                            if chunk:
                                f.write(chunk)
                    self.log_signal.emit(f"Downloaded {filename}")
                    return True
            except Exception as e:
                self.log_signal.emit(f"Error while downloading {filename}: {e}")
            
            retry_count += 1
            self.log_signal.emit(f"Retrying download of {filename} (Attempt {retry_count}/{self.max_retries})")
            time.sleep(2)  # Wait before retrying

        self.log_signal.emit(f"Failed to download {filename} after {self.max_retries} attempts.")
        return False

    def get_json(self, page, retry=True, limits=40):
        try:
            url = f"https://yande.re/post.json?tags={self.search_tag}&limit={limits}&page={page}"
            self.log_signal.emit(f"Requesting URL: {url}")

            response = requests.get(url)
            if response.status_code == 200:
                return response.json()
            else:
                response.raise_for_status()

        except Exception as e:
            self.log_signal.emit(f"Error while getting JSON data: {e}")

            if retry:
                self.log_signal.emit("Retrying...")
                time.sleep(5)
                return self.get_json(page, retry=False, limits=limits)

        return None
