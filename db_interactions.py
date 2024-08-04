import sqlite3


class DBInteraction:

    def __init__(self, db_file):
        """Инициализация соединения с БД"""
        self.connection = sqlite3.connect(db_file)
        self.cursor = self.connection.cursor()

    def close_connection(self):
        """Закрыть соединение с БД"""
        self.connection.close()
        
    def get_all_items(self, table_name):
        """Получить все записи из таблицы"""
        try:
            all_items = self.cursor.execute(f"SELECT * FROM {table_name}")
            return all_items.fetchall()

        except sqlite3.Error as e:
            print(f"get_all_items ошибка: {e}")

    def add_item(self, name, quantity, photo_url):
        """Добавить новый элемент в таблицу"""
        try:
            insert_query = """INSERT INTO items (name, quantity, photo_url) VALUES (?, ?, ?)"""
            values = (name, quantity, photo_url)
            self.cursor.execute(insert_query, values)
            self.connection.commit()
            print("Запись успешно добавлена.")
            
        except sqlite3.Error as e:
            print(f"add_item ошибка: {e}")
    
    def remove_item(self, id):
        """Удалить элемент из таблицы"""
        try:
            delete_query = """DELETE FROM items WHERE id = ?"""
            self.cursor.execute(delete_query, (id,))
            self.connection.commit()
            
        except sqlite3.Error as e:
            print(f"remove_item ошибка: {e}")
    
    def change_quantity(self, new_quantity, id):
        """Изменить кол-во элемента в таблице"""
        update_query = """UPDATE items SET quantity = ? where id = ?"""
        self.cursor.execute(update_query, (new_quantity, id,))
        self.connection.commit()
    