import os
import yt_dlp
import uuid
from pathlib import Path

class Download:
    def __init__(self, url):
        self.url = url
        self.file = None
        self.download_video()
    
    def download_video(self):
        """Скачивает оригинальное видео в высоком качестве"""
        try:
            # Создаем папку для загрузок
            downloads_dir = Path("downloads")
            downloads_dir.mkdir(exist_ok=True)
            
            # Генерируем имя файла
            file_id = str(uuid.uuid4())[:8]
            output_path = downloads_dir / f"video_{file_id}.%(ext)s"
            
            # Настройки для скачивания оригинального видео в высоком качестве
            ydl_opts = {
                # Приоритет: высокое качество в форматах, поддерживаемых Telegram
                'format': (
                    'best[height>=2160][ext=mp4]/'
                    'best[height>=1440][ext=mp4]/'
                    'best[height>=1080][ext=mp4]/'
                    'bestvideo[height>=2160][ext=mp4]+bestaudio[ext=m4a]/best[height>=2160]/'
                    'bestvideo[height>=1440][ext=mp4]+bestaudio[ext=m4a]/best[height>=1440]/'
                    'bestvideo[height>=1080][ext=mp4]+bestaudio[ext=m4a]/best[height>=1080]/'
                    'best[ext=mp4]/'
                    'best'
                ),
                'outtmpl': str(output_path),
                'noplaylist': True,
                'merge_output_format': 'mp4',
            }
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([self.url])
                
                # Находим скачанный файл
                for file in downloads_dir.glob(f"video_{file_id}.*"):
                    if file.is_file():
                        self.file = str(file)
                        break
                
                if not self.file:
                    raise Exception("Файл не найден после скачивания")
                    
        except Exception as e:
            raise Exception(f"Ошибка: {str(e)}")
    
    def cleanup(self):
        """Удаляет файл"""
        if self.file and os.path.exists(self.file):
            try:
                os.remove(self.file)
            except:
                pass