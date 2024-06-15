import sys
from PyQt5.QtWidgets import QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QTreeWidget, \
QTreeWidgetItem, QLineEdit, QDialog, QFormLayout, QMessageBox
import mysql.connector
from mysql.connector import errorcode
from functools import partial
import configparser

class AddRecordDialog(QDialog):
    def __init__(self, table_name, cnx, cursor, parent=None):
        super().__init__(parent)

        self.table_name = table_name
        self.cnx = cnx
        self.cursor = cursor

        self.initUI()

    def initUI(self):
        self.setGeometry(300, 300, 300, 200)
        self.setWindowTitle(f"Добавить запись в {self.table_name}")

        self.layout = QFormLayout()
        self.setLayout(self.layout)

        self.cursor.execute(f"SHOW COLUMNS FROM {self.table_name}")
        self.columns = [column[0] for column in self.cursor.fetchall()]

        self.fields = {}
        self.cursor.execute(f"SELECT MAX({self.columns[0]}) FROM {self.table_name}")
        max_id = self.cursor.fetchone()[0] or 0
        self.fields[self.columns[0]] = QLineEdit(str(max_id + 1))
        self.fields[self.columns[0]].setReadOnly(True)
        self.layout.addRow(self.columns[0], self.fields[self.columns[0]])

        for column in self.columns[1:]:
            self.fields[column] = QLineEdit()
            self.layout.addRow(column, self.fields[column])

        self.addButton = QPushButton("Добавить")
        self.addButton.clicked.connect(self.addRecord)
        self.layout.addRow(self.addButton)

        # Добавляем стиль
        self.setStyleSheet("""
            QDialog {
                background-color: #f9f9f9;
            }
            QLineEdit {
                background-color: #ffffff;
                border: 1px solid #cccccc;
                border-radius: 5px;
                padding: 5px;
            }
            QPushButton {
                background-color: #e0e0e0;
                border: 1px solid #cccccc;
                border-radius: 5px;
                padding: 5px;
            }
            QPushButton:hover {
                background-color: #d0d0d0;
            }
        """)

    def addRecord(self):
        try:
            values = []
            for column in self.columns:
                field_value = self.fields[column].text().strip()
                if not field_value:
                    QMessageBox.warning(self, "Ошибка", f"Поле '{column}' не может быть пустым.")
                    return
                values.append(field_value)

            # Проверка уникальности по всем полям, кроме первичного ключа
            conditions = " AND ".join([f"{column} = %s" for column in self.columns[1:]])
            check_query = f"SELECT COUNT(*) FROM {self.table_name} WHERE {conditions}"
            self.cursor.execute(check_query, values[1:])
            if self.cursor.fetchone()[0] > 0:
                QMessageBox.warning(self, "Ошибка", "Запись с такими данными уже существует.")
                return

            columns = self.columns
            query = f"INSERT INTO {self.table_name} ({', '.join(columns)}) VALUES ({', '.join(['%s'] * len(values))})"
            self.cursor.execute(query, values)
            self.cnx.commit()
            self.close()
            self.parent().refreshTable()
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Не удалось добавить запись: {str(e)}")

class EditRecordDialog(QDialog):
    def __init__(self, table_name, cnx, cursor, record_id, parent=None):
        super().__init__(parent)
        self.table_name = table_name
        self.cnx = cnx
        self.cursor = cursor
        self.record_id = record_id

        self.initUI()

    def initUI(self):
        self.setGeometry(300, 300, 300, 200)
        self.setWindowTitle(f"Редактировать запись в {self.table_name}")

        self.layout = QFormLayout()
        self.setLayout(self.layout)

        self.cursor.execute(f"SHOW COLUMNS FROM {self.table_name}")
        self.columns = [column[0] for column in self.cursor.fetchall()]

        self.fields = {}
        self.cursor.execute(f"SELECT * FROM {self.table_name} WHERE {self.columns[0]} = %s", (self.record_id,))
        record = self.cursor.fetchone()

        for idx, column in enumerate(self.columns):
            self.fields[column] = QLineEdit(str(record[idx]))
            if idx == 0:  # First column is assumed to be the ID
                self.fields[column].setReadOnly(True)
            self.layout.addRow(column, self.fields[column])

        self.saveButton = QPushButton("Сохранить")
        self.saveButton.clicked.connect(self.saveRecord)
        self.layout.addRow(self.saveButton)

        # Добавляем стиль
        self.setStyleSheet("""
            QDialog {
                background-color: #f9f9f9;
            }
            QLineEdit {
                background-color: #ffffff;
                border: 1px solid #cccccc;
                border-radius: 5px;
                padding: 5px;
            }
            QPushButton {
                background-color: #e0e0e0;
                border: 1px solid #cccccc;
                border-radius: 5px;
                padding: 5px;
            }
            QPushButton:hover {
                background-color: #d0d0d0;
            }
        """)

    def saveRecord(self):
        try:
            values = [self.fields[column].text().strip() for column in self.columns]

            # Проверка на пустые значения
            for idx, value in enumerate(values):
                if idx != 0 and not value:  # Пропускаем проверку для первичного ключа
                    QMessageBox.warning(self, "Ошибка", f"Поле '{self.columns[idx]}' не может быть пустым.")
                    return

            # Проверка уникальности по всем полям, кроме первичного ключа
            conditions = " AND ".join([f"{column} = %s" for column in self.columns[1:]])
            check_query = f"SELECT COUNT(*) FROM {self.table_name} WHERE {conditions} AND {self.columns[0]} != %s"
            self.cursor.execute(check_query, values[1:] + [self.record_id])
            if self.cursor.fetchone()[0] > 0:
                QMessageBox.warning(self, "Ошибка", "Запись с такими данными уже существует.")
                return

            set_clause = ", ".join([f"{col} = %s" for col in self.columns[1:]])
            query = f"UPDATE {self.table_name} SET {set_clause} WHERE {self.columns[0]} = %s"
            self.cursor.execute(query, values[1:] + [self.record_id])
            self.cnx.commit()
            self.close()
            self.parent().refreshTable()
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Не удалось сохранить изменения: {str(e)}")

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.initUI()

    def initUI(self):
        self.setGeometry(300, 300, 800, 600)
        self.setWindowTitle("База данных выпускников")

        self.centralWidget = QWidget()
        self.setCentralWidget(self.centralWidget)

        self.mainLayout = QHBoxLayout()
        self.centralWidget.setLayout(self.mainLayout)

        self.navFrame = QWidget()
        self.mainLayout.addWidget(self.navFrame)

        self.navLayout = QVBoxLayout()
        self.navFrame.setLayout(self.navLayout)

        self.tables = ["Graduates", "Specialty", "PlaceOfWorks", "ScientificSupervisors", "Donations"]
        self.tableWindows = []

        self.tableButtons = []
        for table in self.tables:
            button = QPushButton(table)
            button.clicked.connect(partial(self.showTable, table))
            self.navLayout.addWidget(button)
            self.tableButtons.append(button)

        self.showAllButton = QPushButton("Показать все таблицы")
        self.showAllButton.clicked.connect(self.showAllTables)
        self.navLayout.addWidget(self.showAllButton)

        # Считывание сведений о подключении к базе данных из файла
        config = configparser.ConfigParser()
        config.read('db_config.ini')

        self.cnx = mysql.connector.connect(
            user=config.get('database', 'user'),
            password=config.get('database', 'password'),
            host=config.get('database', 'host'),
            database=config.get('database', 'database')
        )

        self.cursor = self.cnx.cursor()

        # Добавляем стиль
        self.setStyleSheet("""
            QMainWindow {
                background-color: #f9f9f9;
            }
            QPushButton {
                background-color: #e0e0e0;
                border: 1px solid #cccccc;
                border-radius: 5px;
                padding: 10px;
            }
            QPushButton:hover {
                background-color: #d0d0d0;
            }
        """)

    def showTable(self, table_name):
        tableWindow = TableWindow(table_name, self.cnx, self.cursor)
        tableWindow.show()
        self.tableWindows.append(tableWindow)

    def showAllTables(self):
        for table in self.tables:
            tableWindow = TableWindow(table, self.cnx, self.cursor)
            tableWindow.show()
            self.tableWindows.append(tableWindow)


class TableWindow(QMainWindow):
    def __init__(self, table_name, cnx, cursor):
        super().__init__()

        self.table_name = table_name
        self.cnx = cnx
        self.cursor = cursor

        self.initUI()

    def initUI(self):
        self.setGeometry(300, 300, 800, 600)
        self.setWindowTitle(self.table_name)

        self.centralWidget = QWidget()
        self.setCentralWidget(self.centralWidget)

        self.mainLayout = QVBoxLayout()
        self.centralWidget.setLayout(self.mainLayout)

        self.searchLayout = QHBoxLayout()
        self.searchBox = QLineEdit()
        self.searchButton = QPushButton("Поиск")
        self.searchButton.clicked.connect(self.searchRecords)
        self.searchLayout.addWidget(self.searchBox)
        self.searchLayout.addWidget(self.searchButton)

        self.mainLayout.addLayout(self.searchLayout)

        self.outputTree = QTreeWidget()
        self.mainLayout.addWidget(self.outputTree)

        self.addButton = QPushButton("Добавить запись")
        self.addButton.clicked.connect(self.addRecord)
        self.mainLayout.addWidget(self.addButton)
        
        self.editButton = QPushButton("Редактировать запись")
        self.editButton.clicked.connect(self.editRecord)
        self.mainLayout.addWidget(self.editButton)

        self.deleteButton = QPushButton("Удалить запись")
        self.deleteButton.clicked.connect(self.deleteRecord)
        self.mainLayout.addWidget(self.deleteButton)

        self.refreshTable()

        # Добавляем стиль
        self.setStyleSheet("""
            QMainWindow {
                background-color: #f9f9f9;
            }
            QTreeWidget {
                background-color: #ffffff;
                border: 1px solid #cccccc;
                border-radius: 5px;
            }
            QPushButton {
                background-color: #e0e0e0;
                border: 1px solid #cccccc;
                border-radius: 5px;
                padding: 10px;
            }
            QPushButton:hover {
                background-color: #d0d0d0;
            }
        """)

    def addRecord(self):
        self.addRecordDialog = AddRecordDialog(self.table_name, self.cnx, self.cursor, self)
        self.addRecordDialog.exec_()

    def editRecord(self):
        selected = self.outputTree.selectedItems()
        if selected:
            row = selected[0]
            record_id = row.text(0)  # Предполагаем, что идентификатор находится в первом столбце
            self.editRecordDialog = EditRecordDialog(self.table_name, self.cnx, self.cursor, record_id, self)
            self.editRecordDialog.exec_()

    def deleteRecord(self):
        selected = self.outputTree.selectedItems()
        if selected:
            row = selected[0]
            id = row.text(0)  # Также предполагаем, что идентификатор находится в первом столбце

            # Определеяем словарь для сопоставления имен таблиц с именами столбцов их первичного ключа.
            primary_keys = {
                "Graduates": "Graduation_ID",
                "Specialty": "Speciality_ID",
                "PlaceOfWorks": "Work_ID",
                "ScientificSupervisors": "Scientific_Director_ID",
                "Donations": "DONATION_ID"
            }

            # Получаем имя столбца первичного ключа для текущей таблицы
            primary_key = primary_keys[self.table_name]

            # Выполняем запрос на УДАЛЕНИЕ
            query = f"DELETE FROM {self.table_name} WHERE {primary_key} = %s"
            self.cursor.execute(query, (id,))
            self.cnx.commit()

            # Обновляем таблицу
            self.refreshTable()

    def refreshTable(self):
        self.outputTree.clear()  # Очищаем таблицу
        try:
            self.cursor.execute(f"SELECT * FROM {self.table_name}")
            rows = self.cursor.fetchall()
            columns = [desc[0] for desc in self.cursor.description]
            self.outputTree.setColumnCount(len(columns))
            self.outputTree.setHeaderLabels(columns)
            for row in rows:
                item = QTreeWidgetItem([str(elem) for elem in row])
                self.outputTree.addTopLevelItem(item)
        except mysql.connector.Error as err:
            if err.errno == errorcode.ER_NO_SUCH_TABLE:
                QMessageBox.critical(self, "Ошибка", f"Таблица '{self.table_name}' не существует.")
            else:
                QMessageBox.critical(self, "Ошибка", f"Ошибка выполнения запроса: {err}")

    def searchRecords(self):
        query = self.searchBox.text().strip()
        if not query:
            self.refreshTable()
            return

        self.outputTree.clear()
        try:
            self.cursor.execute(f"SHOW COLUMNS FROM {self.table_name}")
            columns = [column[0] for column in self.cursor.fetchall()]
            search_conditions = " OR ".join([f"{col} LIKE %s" for col in columns])
            search_query = f"SELECT * FROM {self.table_name} WHERE {search_conditions}"
            search_values = [f"%{query}%"] * len(columns)
            self.cursor.execute(search_query, search_values)
            rows = self.cursor.fetchall()
            self.outputTree.setColumnCount(len(columns))
            self.outputTree.setHeaderLabels(columns)
            if rows:
                for row in rows:
                    item = QTreeWidgetItem([str(elem) for elem in row])
                    self.outputTree.addTopLevelItem(item)
            else:
                QMessageBox.information(self, "Поиск", "Ничего не найдено.")
        except mysql.connector.Error as err:
            QMessageBox.critical(self, "Ошибка", f"Ошибка выполнения запроса: {err}")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())