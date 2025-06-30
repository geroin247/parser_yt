import sqlite3
import json
import os
from datetime import datetime
from typing import List, Dict, Optional

class DatabaseManager:
    def __init__(self, db_path='bot_database.db'):
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """Инициализация базы данных"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Создаем таблицу пользователей
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                last_name TEXT,
                language_code TEXT,
                is_bot INTEGER DEFAULT 0,
                is_premium INTEGER DEFAULT 0,
                first_interaction TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_interaction TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                total_downloads INTEGER DEFAULT 0,
                is_active INTEGER DEFAULT 1
            )
        ''')
        
        # Создаем таблицу загрузок
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS downloads (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                video_url TEXT,
                video_title TEXT,
                download_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                file_size INTEGER,
                success INTEGER DEFAULT 1,
                FOREIGN KEY (user_id) REFERENCES users (user_id)
            )
        ''')
        
        # Создаем индексы для быстрого поиска
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_user_id ON downloads (user_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_download_time ON downloads (download_time)')
        
        conn.commit()
        conn.close()
    
    def save_user(self, user_data: Dict) -> bool:
        """Сохраняет или обновляет информацию о пользователе"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Проверяем существует ли пользователь
            cursor.execute('SELECT user_id FROM users WHERE user_id = ?', (user_data['user_id'],))
            exists = cursor.fetchone()
            
            current_time = datetime.now().isoformat()
            
            if exists:
                # Обновляем существующего пользователя
                cursor.execute('''
                    UPDATE users SET 
                        username = ?, first_name = ?, last_name = ?, 
                        language_code = ?, is_bot = ?, is_premium = ?,
                        last_interaction = ?
                    WHERE user_id = ?
                ''', (
                    user_data.get('username'),
                    user_data.get('first_name'),
                    user_data.get('last_name'),
                    user_data.get('language_code'),
                    user_data.get('is_bot', 0),
                    user_data.get('is_premium', 0),
                    current_time,
                    user_data['user_id']
                ))
            else:
                # Добавляем нового пользователя
                cursor.execute('''
                    INSERT INTO users (
                        user_id, username, first_name, last_name, 
                        language_code, is_bot, is_premium, 
                        first_interaction, last_interaction
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    user_data['user_id'],
                    user_data.get('username'),
                    user_data.get('first_name'),
                    user_data.get('last_name'),
                    user_data.get('language_code'),
                    user_data.get('is_bot', 0),
                    user_data.get('is_premium', 0),
                    current_time,
                    current_time
                ))
            
            conn.commit()
            conn.close()
            return True
            
        except Exception as e:
            print(f"Error saving user: {e}")
            return False
    
    def add_download(self, user_id: int, video_url: str, video_title: str = None, 
                    file_size: int = None, success: bool = True) -> bool:
        """Добавляет запись о загрузке"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Добавляем запись о загрузке
            cursor.execute('''
                INSERT INTO downloads (user_id, video_url, video_title, file_size, success)
                VALUES (?, ?, ?, ?, ?)
            ''', (user_id, video_url, video_title, file_size, 1 if success else 0))
            
            # Обновляем счетчик загрузок пользователя
            cursor.execute('''
                UPDATE users SET 
                    total_downloads = total_downloads + 1,
                    last_interaction = ?
                WHERE user_id = ?
            ''', (datetime.now().isoformat(), user_id))
            
            conn.commit()
            conn.close()
            return True
            
        except Exception as e:
            print(f"Error adding download: {e}")
            return False
    
    def get_user_info(self, user_id: int) -> Optional[Dict]:
        """Получает полную информацию о пользователе"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Получаем информацию о пользователе
            cursor.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
            user_row = cursor.fetchone()
            
            if not user_row:
                return None
            
            # Получаем загрузки пользователя
            cursor.execute('''
                SELECT video_url, video_title, download_time, file_size, success 
                FROM downloads WHERE user_id = ? 
                ORDER BY download_time DESC
            ''', (user_id,))
            downloads = cursor.fetchall()
            
            conn.close()
            
            # Формируем результат
            columns = [description[0] for description in cursor.description if description[0] != 'user_id']
            user_info = dict(zip(['user_id'] + columns[:-1], user_row))
            
            user_info['downloads'] = [
                {
                    'video_url': d[0],
                    'video_title': d[1],
                    'download_time': d[2],
                    'file_size': d[3],
                    'success': bool(d[4])
                }
                for d in downloads
            ]
            
            return user_info
            
        except Exception as e:
            print(f"Error getting user info: {e}")
            return None
    
    def get_all_users(self) -> List[Dict]:
        """Получает информацию о всех пользователях"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('SELECT * FROM users ORDER BY first_interaction DESC')
            users = cursor.fetchall()
            
            result = []
            for user_row in users:
                user_id = user_row[0]
                
                # Получаем загрузки для каждого пользователя
                cursor.execute('''
                    SELECT video_url, video_title, download_time, file_size, success 
                    FROM downloads WHERE user_id = ? 
                    ORDER BY download_time DESC
                ''', (user_id,))
                downloads = cursor.fetchall()
                
                # Формируем информацию о пользователе
                user_info = {
                    'user_id': user_row[0],
                    'username': user_row[1],
                    'first_name': user_row[2],
                    'last_name': user_row[3],
                    'language_code': user_row[4],
                    'is_bot': bool(user_row[5]),
                    'is_premium': bool(user_row[6]),
                    'first_interaction': user_row[7],
                    'last_interaction': user_row[8],
                    'total_downloads': user_row[9],
                    'is_active': bool(user_row[10]),
                    'downloads': [
                        {
                            'video_url': d[0],
                            'video_title': d[1],
                            'download_time': d[2],
                            'file_size': d[3],
                            'success': bool(d[4])
                        }
                        for d in downloads
                    ]
                }
                result.append(user_info)
            
            conn.close()
            return result
            
        except Exception as e:
            print(f"Error getting all users: {e}")
            return []
    
    def export_to_json(self, filepath: str = None) -> str:
        """Экспортирует всех пользователей в JSON"""
        if not filepath:
            filepath = f'users_export_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
        
        users_data = self.get_all_users()
        
        export_data = {
            'export_time': datetime.now().isoformat(),
            'total_users': len(users_data),
            'users': users_data
        }
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, ensure_ascii=False, indent=2)
        
        return filepath
    
    def export_to_sql(self, filepath: str = None) -> str:
        """Экспортирует базу данных в SQL файл"""
        if not filepath:
            filepath = f'database_export_{datetime.now().strftime("%Y%m%d_%H%M%S")}.sql'
        
        try:
            conn = sqlite3.connect(self.db_path)
            
            with open(filepath, 'w', encoding='utf-8') as f:
                # Добавляем заголовок
                f.write(f"-- Database export created at {datetime.now().isoformat()}\n")
                f.write("-- Bot Database Export\n\n")
                
                # Экспортируем схему и данные
                for line in conn.iterdump():
                    f.write(f"{line}\n")
            
            conn.close()
            return filepath
            
        except Exception as e:
            print(f"Error exporting to SQL: {e}")
            return None
    
    def get_statistics(self) -> Dict:
        """Получает статистику по базе данных"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Общая статистика пользователей
            cursor.execute('SELECT COUNT(*) FROM users')
            total_users = cursor.fetchone()[0]
            
            cursor.execute('SELECT COUNT(*) FROM users WHERE is_active = 1')
            active_users = cursor.fetchone()[0]
            
            # Статистика загрузок
            cursor.execute('SELECT COUNT(*) FROM downloads')
            total_downloads = cursor.fetchone()[0]
            
            cursor.execute('SELECT COUNT(*) FROM downloads WHERE success = 1')
            successful_downloads = cursor.fetchone()[0]
            
            # Топ пользователей по загрузкам
            cursor.execute('''
                SELECT u.user_id, u.username, u.first_name, COUNT(d.id) as download_count
                FROM users u
                LEFT JOIN downloads d ON u.user_id = d.user_id
                GROUP BY u.user_id
                ORDER BY download_count DESC
                LIMIT 10
            ''')
            top_users = cursor.fetchall()
            
            conn.close()
            
            return {
                'total_users': total_users,
                'active_users': active_users,
                'total_downloads': total_downloads,
                'successful_downloads': successful_downloads,
                'success_rate': (successful_downloads / total_downloads * 100) if total_downloads > 0 else 0,
                'top_users': [
                    {
                        'user_id': row[0],
                        'username': row[1],
                        'first_name': row[2],
                        'download_count': row[3]
                    }
                    for row in top_users
                ]
            }
            
        except Exception as e:
            print(f"Error getting statistics: {e}")
            return {}

# Создаем глобальный экземпляр менеджера базы данных
db_manager = DatabaseManager()