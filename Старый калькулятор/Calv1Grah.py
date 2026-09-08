import tkinter as tk
from tkinter import ttk, messagebox
from openpyxl import Workbook
from openpyxl.styles import Font, Border, Side, Alignment, PatternFill
from openpyxl.utils import get_column_letter
from tkinter import filedialog
import sqlite3
import logging
from datetime import datetime
import json
import os
import logging


# Настройка логирования для отладки
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class ComboboxWithSearch(ttk.Combobox):
    """Комбобокс с функцией поиска при вводе текста"""
    def __init__(self, parent, values, **kwargs):
        super().__init__(parent, **kwargs)
        self.all_values = values
        self['values'] = values
        
        # Привязываем событие ввода текста для поиска
        self.bind('<KeyRelease>', self.on_key_release)
        
    def on_key_release(self, event):
        # Получаем текущий текст из комбобокса
        current_text = self.get()
        
        # Если текст пустой, показываем все значения
        if not current_text:
            self['values'] = self.all_values
            return
            
        # Фильтруем значения по введенному тексту
        filtered_values = [value for value in self.all_values if current_text.lower() in value.lower()]
        self['values'] = filtered_values
        
        # Показываем выпадающий список
        self.event_generate('<Down>')

class HistoryManager:
    """Класс для управления историей сравнений и расчетов"""
    
    def __init__(self, main_app=None):
        self.history_file = 'calculation_history.json'
        self.comparison_history_file = 'comparison_history.json'
        self.main_app = main_app
        self.load_history()
    
    def load_history(self):
        """Загружает историю из файлов"""
        # История расчетов
        if os.path.exists(self.history_file):
            try:
                with open(self.history_file, 'r', encoding='utf-8') as f:
                    self.calculation_history = json.load(f)
            except Exception as e:
                logging.error(f"Ошибка загрузки истории расчетов: {e}")
                self.calculation_history = []
        else:
            self.calculation_history = []
        
        # История сравнений
        if os.path.exists(self.comparison_history_file):
            try:
                with open(self.comparison_history_file, 'r', encoding='utf-8') as f:
                    self.comparison_history = json.load(f)
            except Exception as e:
                logging.error(f"Ошибка загрузки истории сравнений: {e}")
                self.comparison_history = []
        else:
            self.comparison_history = []
    
    def open_coating_templates(self):
        """Открывает диалог управления шаблонными схемами покрытий"""
        try:
            CoatingTemplateDialog(self.master, self)
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось открыть шаблоны покрытий: {str(e)}")

    def save_history(self):
        """Сохраняет историю в файлы"""
        try:
            with open(self.history_file, 'w', encoding='utf-8') as f:
                json.dump(self.calculation_history, f, ensure_ascii=False, indent=2)
            
            with open(self.comparison_history_file, 'w', encoding='utf-8') as f:
                json.dump(self.comparison_history, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logging.error(f"Ошибка сохранения истории: {e}")
    
    def add_calculation(self, layers, total_cost, total_thickness, total_consumption_kg, total_consumption_l):
        """Добавляет запись в историю расчетов"""
        try:
            calculation = {
                'timestamp': datetime.now().isoformat(),
                'date_display': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'layers_count': len([layer for layer in layers if 'Разбавитель' not in layer[0] and 'Растворитель' not in layer[0]]),
                'total_cost': total_cost,
                'total_thickness': total_thickness,
                'total_consumption_kg': total_consumption_kg,
                'total_consumption_l': total_consumption_l,
                'layer_names': [layer[0] for layer in layers if 'Разбавитель' not in layer[0] and 'Растворитель' not in layer[0]],  # НОВОЕ: названия материалов
                'layers': [
                    {
                        'name': layer[0],
                        'binder': layer[1],
                        'ral': layer[2],
                        'dry_thickness': layer[6] if layer[6] is not None else 0,
                        'consumption_kg': layer[12] if layer[12] is not None else 0,
                        'consumption_l': layer[12] / layer[3] if layer[3] and layer[3] > 0 and layer[12] is not None else 0,
                        'cost': layer[14] if layer[14] is not None else 0
                    }
                    for layer in layers if 'Разбавитель' not in layer[0] and 'Растворитель' not in layer[0]
                ]
            }
            
            self.calculation_history.append(calculation)
            
            # Ограничиваем историю последними 5000 записями
            if len(self.calculation_history) > 5000:
                self.calculation_history = self.calculation_history[-5000:]
            
            self.save_history()
        except Exception as e:
            logging.error(f"Ошибка добавления расчета в историю: {e}")

    def add_comparison(self, systems_data, system_names, comparison_results):
        """Добавляет запись в историю сравнений"""
        try:
            comparison = {
                'timestamp': datetime.now().isoformat(),
                'date_display': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'systems_count': len(systems_data),
                'system_names': system_names,  # Сохраняем названия систем
                'best_system': comparison_results.get('best_system', ''),
                'best_cost': comparison_results.get('best_cost', 0),
                'economy_percent': comparison_results.get('economy_percent', 0),
                'systems_data': [
                    {
                        'name': name,
                        'layers_count': len([layer for layer in system if 'Разбавитель' not in layer[0] and 'Растворитель' not in layer[0]]),
                        'total_cost': self.calculate_system_cost(system),
                        'total_thickness': self.calculate_system_thickness(system),
                        'layer_names': [layer[0] for layer in system if 'Разбавитель' not in layer[0] and 'Растворитель' not in layer[0]],  # НОВОЕ: названия материалов
                        'layers': [  # НОВОЕ: полные данные слоев для возможности загрузки
                            {
                                'name': layer[0],
                                'binder': layer[1],
                                'ral': layer[2],
                                'density': layer[3],
                                'solid_content': layer[4],
                                'wet_thickness': layer[5],
                                'dry_thickness': layer[6],
                                'theor_covering': layer[7],
                                'losses': layer[8],
                                'pract_covering': layer[9],
                                'price_kg': layer[10],
                                'price_liter': layer[11],
                                'theor_consumption_kg': layer[12],
                                'pract_consumption_kg': layer[13],
                                'cost': layer[14],
                                'thinner_percent': layer[15]
                            }
                            for layer in system if 'Разбавитель' not in layer[0] and 'Растворитель' not in layer[0]
                        ]
                    }
                    for name, system in zip(system_names, systems_data)
                ]
            }
            
            self.comparison_history.append(comparison)
            
            # Ограничиваем историю последними 2000 записями
            if len(self.comparison_history) > 2000:
                self.comparison_history = self.comparison_history[-2000:]
            
            self.save_history()
        except Exception as e:
            logging.error(f"Ошибка добавления сравнения в историю: {e}")
    
    def calculate_system_cost(self, system):
        """Рассчитывает стоимость системы"""
        try:
            return sum(layer[14] if layer[14] is not None else 0 for layer in system)
        except:
            return 0
    
    def calculate_system_thickness(self, system):
        """Рассчитывает толщину системы"""
        try:
            return sum(layer[6] if layer[6] is not None else 0 for layer in system 
                      if 'Разбавитель' not in layer[0] and 'Растворитель' not in layer[0])
        except:
            return 0
    
    def get_calculation_history(self):
        """Возвращает историю расчетов"""
        return self.calculation_history
    
    def get_comparison_history(self):
        """Возвращает историю сравнений"""
        return self.comparison_history
    
    def clear_calculation_history(self):
        """Очищает историю расчетов"""
        self.calculation_history = []
        self.save_history()
    
    def clear_comparison_history(self):
        """Очищает историю сравнений"""
        self.comparison_history = []
        self.save_history()

class CalculationHistoryDialog:
    """Диалоговое окно для просмотра истории расчетов"""
    
    def __init__(self, parent, history_manager, main_app):
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("История расчетов")
        self.dialog.geometry("1000x600")
        self.history_manager = history_manager
        self.main_app = main_app
        
        self.create_widgets()
        self.load_history()
    
    def create_widgets(self):
        """Создает элементы интерфейса"""
        # Фрейм управления
        control_frame = ttk.Frame(self.dialog)
        control_frame.pack(fill="x", padx=10, pady=5)
        
        ttk.Button(control_frame, text="Обновить", 
                  command=self.load_history).pack(side=tk.LEFT, padx=5)
        ttk.Button(control_frame, text="Загрузить в редактор", 
              command=self.load_calculation_to_main).pack(side=tk.LEFT, padx=5)  # НОВАЯ КНОПКА
        ttk.Button(control_frame, text="Очистить историю", 
                  command=self.clear_history).pack(side=tk.LEFT, padx=5)
        ttk.Button(control_frame, text="Экспорт в Excel", 
                  command=self.export_history).pack(side=tk.LEFT, padx=5)
        
        # Фрейм для таблицы
        table_frame = ttk.LabelFrame(self.dialog, text="История расчетов")
        table_frame.pack(fill="both", expand=True, padx=10, pady=5)
        
        # Создаем Treeview
        columns = ('Дата', 'Кол-во слоев', 'Материалы', 'Толщина, мкм', 'Расход кг/м²', 'Расход л/м²', 'Стоимость руб/м²')  # ИЗМЕНЕНО: добавлена колонка 'Материалы'
        self.tree = ttk.Treeview(table_frame, columns=columns, show='headings')
        
        # Настраиваем заголовки
        for col in columns:
            self.tree.heading(col, text=col)
            if col == 'Материалы':
                self.tree.column(col, width=200)  # Шире для названий материалов
            else:
                self.tree.column(col, width=100)
        
        self.tree.pack(fill="both", expand=True, padx=5, pady=5)
            
        
        # Скроллбар
        scrollbar = ttk.Scrollbar(table_frame, orient="vertical", command=self.tree.yview)
        scrollbar.pack(side="right", fill="y")
        self.tree.configure(yscrollcommand=scrollbar.set)
        
        # Привязываем двойной клик
        self.tree.bind('<Double-1>', self.show_calculation_details)
    


    def load_history(self):
        """Загружает историю в таблицу"""
        # Очищаем таблицу
        for item in self.tree.get_children():
            self.tree.delete(item)
        
        history = self.history_manager.get_calculation_history()
        
        # Сортируем по дате (новые сверху)
        history.sort(key=lambda x: x['timestamp'], reverse=True)
        
        for calculation in history:
            # Формируем строку с названиями материалов (первые 3 материала)
            materials_text = ", ".join(calculation['layer_names'][:3])
            if len(calculation['layer_names']) > 3:
                materials_text += f" ... (+{len(calculation['layer_names']) - 3})"
            
            self.tree.insert('', 'end', values=(
                calculation['date_display'],
                calculation['layers_count'],
                materials_text,  # НОВОЕ: названия материалов
                f"{calculation['total_thickness']:.1f}",
                f"{calculation['total_consumption_kg']:.3f}",
                f"{calculation['total_consumption_l']:.3f}",
                f"{calculation['total_cost']:.2f}"
            ), tags=(calculation['timestamp'],))
    
    def clear_history(self):
        """Очищает историю"""
        if messagebox.askyesno("Подтверждение", "Действительно очистить всю историю расчетов?"):
            self.history_manager.clear_calculation_history()
            self.load_history()
    
    def show_calculation_details(self, event):
        """Показывает детали расчета"""
        selected = self.tree.selection()
        if not selected:
            return
        
        timestamp = self.tree.item(selected[0])['tags'][0]
        history = self.history_manager.get_calculation_history()
        
        calculation = next((calc for calc in history if calc['timestamp'] == timestamp), None)
        if not calculation:
            return
        
        # Создаем диалог с деталями
        detail_dialog = tk.Toplevel(self.dialog)
        detail_dialog.title(f"Детали расчета от {calculation['date_display']}")
        detail_dialog.geometry("800x400")
        
        # Создаем таблицу
        columns = ('Слой', 'Связующее', 'RAL', 'Толщина, мкм', 'Расход кг/м²', 'Расход л/м²', 'Стоимость руб/м²')
        tree = ttk.Treeview(detail_dialog, columns=columns, show='headings')
        
        for col in columns:
            tree.heading(col, text=col)
            tree.column(col, width=100)
        
        tree.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Заполняем данными
        for layer in calculation['layers']:
            tree.insert('', 'end', values=(
                layer['name'],
                layer['binder'],
                layer['ral'],
                f"{layer['dry_thickness']:.1f}" if layer['dry_thickness'] else "0.0",
                f"{layer['consumption_kg']:.3f}" if layer['consumption_kg'] else "0.000",
                f"{layer['consumption_l']:.3f}" if layer['consumption_l'] else "0.000",
                f"{layer['cost']:.2f}" if layer['cost'] else "0.00"
            ))
        
        # Итоговая строка
        tree.insert('', 'end', values=(
            "ИТОГО", "", "", 
            f"{calculation['total_thickness']:.1f}",
            f"{calculation['total_consumption_kg']:.3f}",
            f"{calculation['total_consumption_l']:.3f}",
            f"{calculation['total_cost']:.2f}"
        ), tags=('total',))
        
        tree.tag_configure('total', background='lightgreen', font=('Arial', 9, 'bold'))
    
    def export_history(self):
        """Экспортирует историю в Excel"""
        try:
            wb = Workbook()
            ws = wb.active
            ws.title = "История расчетов"
            
            # Заголовок
            ws['A1'] = "ИСТОРИЯ РАСЧЕТОВ СИСТЕМ ПОКРЫТИЙ"
            ws['A1'].font = Font(bold=True, size=14)
            ws.merge_cells('A1:F1')
            
            ws['A2'] = f"Дата экспорта: {datetime.now().strftime('%Y-%m-%d %H:%M')}"
            ws.merge_cells('A2:F2')
            
            # Заголовки таблицы
            headers = ['Дата расчета', 'Кол-во слоев', 'Толщина покрытия, мкм', 
                      'Расход теор. кг/м²', 'Расход теор. л/м²', 'Общая стоимость руб/м²']
            
            for col, header in enumerate(headers, 1):
                cell = ws.cell(row=4, column=col)
                cell.value = header
                cell.font = Font(bold=True)
                cell.border = Border(left=Side(style='thin'), right=Side(style='thin'),
                                top=Side(style='thin'), bottom=Side(style='thin'))
                cell.alignment = Alignment(horizontal='center', vertical='center', wrap_text=True)
                cell.fill = PatternFill(start_color="E6E6FA", end_color="E6E6FA", fill_type="solid")
            
            # Данные
            history = self.history_manager.get_calculation_history()
            history.sort(key=lambda x: x['timestamp'], reverse=True)
            
            for row, calculation in enumerate(history, 5):
                ws.cell(row=row, column=1).value = calculation['date_display']
                ws.cell(row=row, column=2).value = calculation['layers_count']
                ws.cell(row=row, column=3).value = calculation['total_thickness']
                ws.cell(row=row, column=4).value = calculation['total_consumption_kg']
                ws.cell(row=row, column=5).value = calculation['total_consumption_l']
                ws.cell(row=row, column=6).value = calculation['total_cost']
            
            # Форматирование чисел
            for row in range(5, len(history) + 5):
                ws.cell(row=row, column=3).number_format = '0.0'
                ws.cell(row=row, column=4).number_format = '0.000'
                ws.cell(row=row, column=5).number_format = '0.000'
                ws.cell(row=row, column=6).number_format = '#,##0.00'
            
            # Настройка ширины столбцов
            column_widths = {'A': 20, 'B': 12, 'C': 15, 'D': 15, 'E': 15, 'F': 18}
            for col, width in column_widths.items():
                ws.column_dimensions[col].width = width
            
            # Сохраняем файл
            file_path = filedialog.asksaveasfilename(
                defaultextension='.xlsx',
                filetypes=[("Excel files", "*.xlsx")],
                title="Сохранить историю расчетов"
            )
            
            if file_path:
                wb.save(file_path)
                messagebox.showinfo("Успех", "История расчетов экспортирована в Excel!")
                
        except Exception as e:
            messagebox.showerror("Ошибка", f"Ошибка при экспорте: {str(e)}")
    def load_calculation_to_main(self):
        """Загружает выбранный расчет в основное приложение для редактирования"""
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("Предупреждение", "Выберите расчет для загрузки")
            return
        
        timestamp = self.tree.item(selected[0])['tags'][0]
        history = self.history_manager.get_calculation_history()
        
        calculation = next((calc for calc in history if calc['timestamp'] == timestamp), None)
        if not calculation:
            return
        
        # Закрываем диалог
        self.dialog.destroy()
        
        # Загружаем расчет в основное приложение
        self.history_manager.main_app.load_calculation_from_history(calculation)
        
class ComparisonHistoryDialog:
    """Диалоговое окно для просмотра истории сравнений систем"""
    
    def __init__(self, parent, history_manager):
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("История сравнений систем")
        self.dialog.geometry("1200x600")
        self.history_manager = history_manager
        
        self.create_widgets()
        self.load_history()
    
    def create_widgets(self):
        """Создает элементы интерфейса"""
        # Фрейм управления
        control_frame = ttk.Frame(self.dialog)
        control_frame.pack(fill="x", padx=10, pady=5)
        
        ttk.Button(control_frame, text="Обновить", 
                  command=self.load_history).pack(side=tk.LEFT, padx=5)
        ttk.Button(control_frame, text="Загрузить систему в расчет",  # НОВАЯ КНОПКА
              command=self.load_system_to_calculation).pack(side=tk.LEFT, padx=5)
        ttk.Button(control_frame, text="Очистить историю", 
                  command=self.clear_history).pack(side=tk.LEFT, padx=5)
        ttk.Button(control_frame, text="Экспорт в Excel", 
                  command=self.export_history).pack(side=tk.LEFT, padx=5)
        
        # Фрейм для таблицы
        table_frame = ttk.LabelFrame(self.dialog, text="История сравнений систем")
        table_frame.pack(fill="both", expand=True, padx=10, pady=5)
        
        # Создаем Treeview с дополнительной колонкой для материалов
        columns = ('Дата', 'Кол-во систем', 'Системы', 'Лучшая система', 'Стоимость лучшей', 'Экономия %')  # ИЗМЕНЕНО: добавлена колонка 'Системы'
        self.tree = ttk.Treeview(table_frame, columns=columns, show='headings')
            
        # Настраиваем заголовки
        for col in columns:
            self.tree.heading(col, text=col)
            if col == 'Системы':
                self.tree.column(col, width=200)  # Шире для названий систем
            else:
                self.tree.column(col, width=120)
        
        self.tree.pack(fill="both", expand=True, padx=5, pady=5)
        
        # Скроллбар
        scrollbar = ttk.Scrollbar(table_frame, orient="vertical", command=self.tree.yview)
        scrollbar.pack(side="right", fill="y")
        self.tree.configure(yscrollcommand=scrollbar.set)
        
        # Привязываем двойной клик
        self.tree.bind('<Double-1>', self.show_comparison_details)
    
    def load_history(self):
        """Загружает историю в таблицу"""
        # Очищаем таблицу
        for item in self.tree.get_children():
            self.tree.delete(item)
        
        history = self.history_manager.get_comparison_history()
        
        # Сортируем по дате (новые сверху)
        history.sort(key=lambda x: x['timestamp'], reverse=True)
        
        for comparison in history:
            # Формируем строку с названиями систем (первые 2-3 системы для компактности)
            system_names = comparison.get('system_names', [])
            if system_names:
                systems_text = ", ".join(system_names[:2])  # Берем первые 2 системы
                if len(system_names) > 2:
                    systems_text += f" ... (+{len(system_names) - 2})"
            else:
                systems_text = "Не указано"
            
            self.tree.insert('', 'end', values=(
                comparison['date_display'],
                comparison['systems_count'],
                systems_text,  # НОВОЕ: названия систем
                comparison['best_system'],
                f"{comparison['best_cost']:.2f}",
                f"{comparison['economy_percent']:.1f}%"
            ), tags=(comparison['timestamp'],))
    
    def clear_history(self):
        """Очищает историю"""
        if messagebox.askyesno("Подтверждение", "Действительно очистить всю историю сравнений?"):
            self.history_manager.clear_comparison_history()
            self.load_history()
    
    def show_comparison_details(self, event):
        """Показывает детали сравнения с названиями материалов"""
        selected = self.tree.selection()
        if not selected:
            return
        
        timestamp = self.tree.item(selected[0])['tags'][0]
        history = self.history_manager.get_comparison_history()
        
        comparison = next((comp for comp in history if comp['timestamp'] == timestamp), None)
        if not comparison:
            return
        
        # Создаем диалог с деталями
        detail_dialog = tk.Toplevel(self.dialog)
        detail_dialog.title(f"Детали сравнения от {comparison['date_display']}")
        detail_dialog.geometry("1000x600")
        
        # Создаем Notebook для вкладок
        notebook = ttk.Notebook(detail_dialog)
        notebook.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Вкладка со сводной информацией по системам
        summary_frame = ttk.Frame(notebook)
        notebook.add(summary_frame, text="Сводка по системам")
        
        # Вкладка с деталями по материалам
        materials_frame = ttk.Frame(notebook)
        notebook.add(materials_frame, text="Материалы систем")
        
        self.create_summary_tab(summary_frame, comparison)
        self.create_materials_tab(materials_frame, comparison)

    def create_summary_tab(self, parent, comparison):
        """Создает вкладку со сводной информацией по системам"""
        # Создаем таблицу
        columns = ['Система', 'Кол-во слоев', 'Толщина, мкм', 'Стоимость руб/м²']
        tree = ttk.Treeview(parent, columns=columns, show='headings')
        
        for col in columns:
            tree.heading(col, text=col)
            tree.column(col, width=150)
        
        tree.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Заполняем данными
        for system_data in comparison['systems_data']:
            is_best = system_data['name'] == comparison['best_system']
            values = (
                system_data['name'],
                system_data['layers_count'],
                f"{system_data['total_thickness']:.1f}",
                f"{system_data['total_cost']:.2f}"
            )
            
            if is_best:
                tree.insert('', 'end', values=values, tags=('best',))
            else:
                tree.insert('', 'end', values=values)
        
        tree.tag_configure('best', background='lightgreen', font=('Arial', 9, 'bold'))

    def create_materials_tab(self, parent, comparison):
        """Создает вкладку с материалами систем"""
        # Создаем таблицу
        columns = ['Система', 'Слой', 'Материал', 'Связующее', 'RAL', 'Толщина, мкм', 'Стоимость руб/м²']
        tree = ttk.Treeview(parent, columns=columns, show='headings')
        
        for col in columns:
            tree.heading(col, text=col)
            if col == 'Материал':
                tree.column(col, width=200)
            else:
                tree.column(col, width=100)
        
        tree.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Заполняем данными
        for system_data in comparison['systems_data']:
            is_best = system_data['name'] == comparison['best_system']
            
            # Добавляем заголовок системы
            tree.insert('', 'end', values=(
                system_data['name'], '---', '---', '---', '---', '---', '---'
            ), tags=('system_header',))
            
            # Добавляем материалы системы
            for i, layer in enumerate(system_data['layers'], 1):
                values = (
                    '',  # Пусто для системы, так как уже есть заголовок
                    f"Слой {i}",
                    layer['name'],
                    layer['binder'] if layer['binder'] else '-',
                    layer['ral'] if layer['ral'] else '-',
                    f"{layer['dry_thickness']:.1f}" if layer['dry_thickness'] else "0.0",
                    f"{layer['cost']:.2f}" if layer['cost'] else "0.00"
                )
                
                if is_best:
                    tree.insert('', 'end', values=values, tags=('best_material',))
                else:
                    tree.insert('', 'end', values=values)
            
            # Добавляем пустую строку для разделения
            tree.insert('', 'end', values=('', '', '', '', '', '', ''))
        
        # Настраиваем теги для стилизации
        tree.tag_configure('system_header', background='lightblue', font=('Arial', 9, 'bold'))
        tree.tag_configure('best_material', background='lightgreen')

    def load_system_to_calculation(self):
        """Загружает выбранную систему из истории сравнений в расчет"""
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("Предупреждение", "Выберите сравнение для загрузки")
            return
        
        timestamp = self.tree.item(selected[0])['tags'][0]
        history = self.history_manager.get_comparison_history()
        
        comparison = next((comp for comp in history if comp['timestamp'] == timestamp), None)
        if not comparison:
            return
        
        # Диалог выбора системы
        system_dialog = tk.Toplevel(self.dialog)
        system_dialog.title("Выбор системы для загрузки")
        system_dialog.geometry("500x300")
        
        ttk.Label(system_dialog, text="Выберите систему для загрузки в расчет:", 
                font=("Arial", 10, "bold")).pack(pady=10)
        
        # Создаем список систем
        systems_frame = ttk.Frame(system_dialog)
        systems_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        systems_listbox = tk.Listbox(systems_frame, font=("Arial", 10))
        systems_listbox.pack(fill="both", expand=True)
        
        for system_data in comparison['systems_data']:
            systems_listbox.insert(tk.END, 
                                f"{system_data['name']} ({system_data['layers_count']} слоев, {system_data['total_cost']:.2f} руб/м²)")
        
        def load_selected_system():
            selection = systems_listbox.curselection()
            if not selection:
                messagebox.showwarning("Предупреждение", "Выберите систему для загрузки")
                return
            
            system_index = selection[0]
            system_data = comparison['systems_data'][system_index]
            
            # Закрываем диалоги
            system_dialog.destroy()
            self.dialog.destroy()
            
            # Загружаем систему в расчет
            self.history_manager.main_app.load_system_from_comparison(system_data)
        
        # Кнопки
        button_frame = ttk.Frame(system_dialog)
        button_frame.pack(fill="x", pady=10)
        
        ttk.Button(button_frame, text="Загрузить выбранную систему", 
                command=load_selected_system).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Отмена", 
                command=system_dialog.destroy).pack(side=tk.RIGHT, padx=5)        
    
    def export_history(self):
        """Экспортирует историю сравнений в Excel"""
        try:
            wb = Workbook()
            ws = wb.active
            ws.title = "История сравнений"
            
            # Заголовок
            ws['A1'] = "ИСТОРИЯ СРАВНЕНИЙ СИСТЕМ ПОКРЫТИЙ"
            ws['A1'].font = Font(bold=True, size=14)
            ws.merge_cells('A1:E1')
            
            ws['A2'] = f"Дата экспорта: {datetime.now().strftime('%Y-%m-%d %H:%M')}"
            ws.merge_cells('A2:E2')
            
            # Заголовки таблицы
            headers = ['Дата сравнения', 'Кол-во систем', 'Лучшая система', 
                      'Стоимость лучшей системы руб/м²', 'Экономия %']
            
            for col, header in enumerate(headers, 1):
                cell = ws.cell(row=4, column=col)
                cell.value = header
                cell.font = Font(bold=True)
                cell.border = Border(left=Side(style='thin'), right=Side(style='thin'),
                                top=Side(style='thin'), bottom=Side(style='thin'))
                cell.alignment = Alignment(horizontal='center', vertical='center', wrap_text=True)
                cell.fill = PatternFill(start_color="E6E6FA", end_color="E6E6FA", fill_type="solid")
            
            # Данные
            history = self.history_manager.get_comparison_history()
            history.sort(key=lambda x: x['timestamp'], reverse=True)
            
            for row, comparison in enumerate(history, 5):
                ws.cell(row=row, column=1).value = comparison['date_display']
                ws.cell(row=row, column=2).value = comparison['systems_count']
                ws.cell(row=row, column=3).value = comparison['best_system']
                ws.cell(row=row, column=4).value = comparison['best_cost']
                ws.cell(row=row, column=5).value = comparison['economy_percent'] / 100
            
            # Форматирование чисел
            for row in range(5, len(history) + 5):
                ws.cell(row=row, column=4).number_format = '#,##0.00'
                ws.cell(row=row, column=5).number_format = '0.00%'
            
            # Настройка ширины столбцов
            column_widths = {'A': 20, 'B': 12, 'C': 30, 'D': 20, 'E': 12}
            for col, width in column_widths.items():
                ws.column_dimensions[col].width = width
            
            # Сохраняем файл
            file_path = filedialog.asksaveasfilename(
                defaultextension='.xlsx',
                filetypes=[("Excel files", "*.xlsx")],
                title="Сохранить историю сравнений"
            )
            
            if file_path:
                wb.save(file_path)
                messagebox.showinfo("Успех", "История сравнений экспортирована в Excel!")
                
        except Exception as e:
            messagebox.showerror("Ошибка", f"Ошибка при экспорте: {str(e)}")

class DatabaseManager:
    """Класс для управления базой данных покрытий и растворителей"""
    def __init__(self):
        self.conn = sqlite3.connect('coatings.db')
        self.create_table()
        self.create_template_tables()  # шаблоны
        self.create_history_tables()   # история изменений

    def create_table(self):
        """Создает основную таблицу покрытий и растворителей"""
        cursor = self.conn.cursor()
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS coatings (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            binder TEXT,
            ral TEXT,
            density REAL,
            solid_content REAL,
            price_kg REAL,
            price_liter REAL,
            is_thinner INTEGER
        )
        ''')
        self.conn.commit()

    def create_template_tables(self):
        """Создает таблицы для шаблонов покрытий"""
        cursor = self.conn.cursor()
        
        # Основная таблица шаблонов
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS coating_templates (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL UNIQUE,
            description TEXT,
            protocol_number TEXT,
            test_conclusion TEXT,
            layers_count INTEGER DEFAULT 0,
            created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')
        
        # Таблица слоев шаблонов
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS template_layers (
            id INTEGER PRIMARY KEY,
            template_id INTEGER,
            coating_name TEXT NOT NULL,
            dry_thickness REAL NOT NULL,
            position INTEGER NOT NULL,
            FOREIGN KEY (template_id) REFERENCES coating_templates (id) ON DELETE CASCADE
        )
        ''')
        
        self.conn.commit()

    def get_coatings(self):
        """Возвращает список всех покрытий (не растворителей)"""
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM coatings WHERE is_thinner = 0 ORDER BY name')
        return cursor.fetchall()

    def get_thinners(self):
        """Возвращает список всех растворителей"""
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM coatings WHERE is_thinner = 1 ORDER BY name')
        return cursor.fetchall()

    def get_coating_by_name(self, name):
        """Возвращает покрытие по названию"""
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM coatings WHERE name = ?', (name,))
        return cursor.fetchone()

    def get_all_coatings(self):
        """Возвращает все покрытия и растворители"""
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM coatings ORDER BY name')
        return cursor.fetchall()

    # Добавьте также эти методы для работы с шаблонами:

    def get_all_coating_templates(self):
        """Возвращает все шаблоны покрытий"""
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM coating_templates ORDER BY created_date DESC')
        return cursor.fetchall()

    def search_coating_templates(self, search_term):
        """Ищет шаблоны по названию или описанию"""
        cursor = self.conn.cursor()
        cursor.execute('''
        SELECT * FROM coating_templates 
        WHERE name LIKE ? OR description LIKE ? OR protocol_number LIKE ?
        ORDER BY created_date DESC
        ''', (f'%{search_term}%', f'%{search_term}%', f'%{search_term}%'))
        return cursor.fetchall()

    def get_coating_template(self, template_id):
        """Возвращает шаблон по ID"""
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM coating_templates WHERE id = ?', (template_id,))
        return cursor.fetchone()

    def get_template_layers(self, template_id):
        """Возвращает слои шаблона"""
        cursor = self.conn.cursor()
        cursor.execute('''
        SELECT coating_name, dry_thickness, position 
        FROM template_layers 
        WHERE template_id = ? 
        ORDER BY position
        ''', (template_id,))
        return cursor.fetchall()

    def add_coating_template(self, name, description, protocol_number, test_conclusion, layers):
        """Добавляет новый шаблон покрытия"""
        cursor = self.conn.cursor()
        try:
            cursor.execute('''
            INSERT INTO coating_templates (name, description, protocol_number, test_conclusion, layers_count)
            VALUES (?, ?, ?, ?, ?)
            ''', (name, description, protocol_number, test_conclusion, len(layers)))
            
            template_id = cursor.lastrowid
            
            # Добавляем слои
            for i, (coating_name, dry_thickness) in enumerate(layers):
                cursor.execute('''
                INSERT INTO template_layers (template_id, coating_name, dry_thickness, position)
                VALUES (?, ?, ?, ?)
                ''', (template_id, coating_name, dry_thickness, i))
            
            self.conn.commit()
            return True
        except sqlite3.IntegrityError:
            self.conn.rollback()
            return False

    def update_coating_template(self, template_id, name, description, protocol_number, test_conclusion, layers):
        """Обновляет шаблон покрытия"""
        cursor = self.conn.cursor()
        try:
            # Обновляем основную информацию
            cursor.execute('''
            UPDATE coating_templates 
            SET name=?, description=?, protocol_number=?, test_conclusion=?, layers_count=?
            WHERE id=?
            ''', (name, description, protocol_number, test_conclusion, len(layers), template_id))
            
            # Удаляем старые слои
            cursor.execute('DELETE FROM template_layers WHERE template_id=?', (template_id,))
            
            # Добавляем новые слои
            for i, (coating_name, dry_thickness) in enumerate(layers):
                cursor.execute('''
                INSERT INTO template_layers (template_id, coating_name, dry_thickness, position)
                VALUES (?, ?, ?, ?)
                ''', (template_id, coating_name, dry_thickness, i))
            
            self.conn.commit()
            return True
        except sqlite3.IntegrityError:
            self.conn.rollback()
            return False

    def delete_coating_template(self, template_id):
        """Удаляет шаблон покрытия"""
        cursor = self.conn.cursor()
        cursor.execute('DELETE FROM coating_templates WHERE id=?', (template_id,))
        self.conn.commit()

    # ... остальные существующие методы DatabaseManager остаются без изменений

    def create_history_tables(self):
        """Создает таблицы для истории изменений"""
        cursor = self.conn.cursor()
        
        # История добавления материалов
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS coating_add_history (
            id INTEGER PRIMARY KEY,
            coating_id INTEGER,
            name TEXT NOT NULL,
            binder TEXT,
            ral TEXT,
            density REAL,
            solid_content REAL,
            price_kg REAL,
            price_liter REAL,
            is_thinner INTEGER,
            added_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            added_by TEXT DEFAULT 'system'
        )
        ''')
        
        # История обновления материалов
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS coating_update_history (
            id INTEGER PRIMARY KEY,
            coating_id INTEGER,
            old_name TEXT,
            new_name TEXT,
            old_binder TEXT,
            new_binder TEXT,
            old_ral TEXT,
            new_ral TEXT,
            old_density REAL,
            new_density REAL,
            old_solid_content REAL,
            new_solid_content REAL,
            old_price_kg REAL,
            new_price_kg REAL,
            old_price_liter REAL,
            new_price_liter REAL,
            old_is_thinner INTEGER,
            new_is_thinner INTEGER,
            update_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_by TEXT DEFAULT 'system'
        )
        ''')
        
        # История удаления материалов
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS coating_delete_history (
            id INTEGER PRIMARY KEY,
            coating_id INTEGER,
            name TEXT NOT NULL,
            binder TEXT,
            ral TEXT,
            density REAL,
            solid_content REAL,
            price_kg REAL,
            price_liter REAL,
            is_thinner INTEGER,
            deleted_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            deleted_by TEXT DEFAULT 'system'
        )
        ''')
        
        self.conn.commit()

    def add_coating(self, name, binder, ral, density, solid_content, price_kg, price_liter, is_thinner=False):
        """Добавляет новое покрытие или растворитель в базу данных"""
        cursor = self.conn.cursor()
        cursor.execute('''
        INSERT INTO coatings (name, binder, ral, density, solid_content, price_kg, price_liter, is_thinner)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (name, binder, ral, density, solid_content, price_kg, price_liter, 1 if is_thinner else 0))
        
        coating_id = cursor.lastrowid
        
        # Записываем в историю добавления
        cursor.execute('''
        INSERT INTO coating_add_history (coating_id, name, binder, ral, density, solid_content, price_kg, price_liter, is_thinner)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (coating_id, name, binder, ral, density, solid_content, price_kg, price_liter, 1 if is_thinner else 0))
        
        self.conn.commit()

    def update_coating(self, id, name, binder, ral, density, solid_content, price_kg, price_liter, is_thinner=False):
        """Обновляет данные покрытия или растворителя"""
        cursor = self.conn.cursor()
        
        # Получаем старые данные для истории
        cursor.execute('SELECT * FROM coatings WHERE id=?', (id,))
        old_coating = cursor.fetchone()
        
        if old_coating:
            # Обновляем данные
            cursor.execute('''
            UPDATE coatings 
            SET name=?, binder=?, ral=?, density=?, solid_content=?, price_kg=?, price_liter=?, is_thinner=?
            WHERE id=?
            ''', (name, binder, ral, density, solid_content, price_kg, price_liter, 1 if is_thinner else 0, id))
            
            # Записываем в историю изменений
            cursor.execute('''
            INSERT INTO coating_update_history (
                coating_id, old_name, new_name, old_binder, new_binder, old_ral, new_ral,
                old_density, new_density, old_solid_content, new_solid_content,
                old_price_kg, new_price_kg, old_price_liter, new_price_liter,
                old_is_thinner, new_is_thinner
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                id, old_coating[1], name, old_coating[2], binder, old_coating[3], ral,
                old_coating[4], density, old_coating[5], solid_content,
                old_coating[6], price_kg, old_coating[7], price_liter,
                old_coating[8], 1 if is_thinner else 0
            ))
            
            self.conn.commit()

    def delete_coating(self, id):
        """Удаляет покрытие или растворитель из базы данных"""
        cursor = self.conn.cursor()
        
        # Получаем данные для истории
        cursor.execute('SELECT * FROM coatings WHERE id=?', (id,))
        coating = cursor.fetchone()
        
        if coating:
            # Записываем в историю удаления
            cursor.execute('''
            INSERT INTO coating_delete_history (coating_id, name, binder, ral, density, solid_content, price_kg, price_liter, is_thinner)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (id, coating[1], coating[2], coating[3], coating[4], coating[5], coating[6], coating[7], coating[8]))
            
            # Удаляем запись
            cursor.execute('DELETE FROM coatings WHERE id=?', (id,))
            self.conn.commit()

    def get_coating_add_history(self, limit=5000):
        """Возвращает историю добавления материалов"""
        cursor = self.conn.cursor()
        cursor.execute('''
        SELECT * FROM coating_add_history 
        ORDER BY added_date DESC 
        LIMIT ?
        ''', (limit,))
        return cursor.fetchall()

    def get_coating_update_history(self, limit=5000):
        """Возвращает историю обновления материалов с полными данными"""
        cursor = self.conn.cursor()
        cursor.execute('''
        SELECT * FROM coating_update_history 
        ORDER BY update_date DESC 
        LIMIT ?
        ''', (limit,))
        return cursor.fetchall()

    def get_coating_delete_history(self, limit=5000):
        """Возвращает историю удаления материалов"""
        cursor = self.conn.cursor()
        cursor.execute('''
        SELECT * FROM coating_delete_history 
        ORDER BY deleted_date DESC 
        LIMIT ?
        ''', (limit,))
        return cursor.fetchall()

    def get_coating_full_history(self, coating_id=None, limit=5000):
        """Возвращает полную историю изменений по всем или конкретному материалу"""
        cursor = self.conn.cursor()
        
        if coating_id:
            # История для конкретного материала
            cursor.execute('''
            SELECT 
                'ADD' as action, 
                coating_id, name, binder, ral, density, solid_content, price_kg, price_liter, is_thinner,
                added_date as change_date,
                'system' as changed_by
            FROM coating_add_history 
            WHERE coating_id = ?
            
            UNION ALL
            
            SELECT 
                'UPDATE' as action,
                coating_id, new_name as name, new_binder as binder, new_ral as ral, 
                new_density as density, new_solid_content as solid_content,
                new_price_kg as price_kg, new_price_liter as price_liter,
                new_is_thinner as is_thinner,
                update_date as change_date,
                'system' as changed_by
            FROM coating_update_history 
            WHERE coating_id = ?
            
            UNION ALL
            
            SELECT 
                'DELETE' as action,
                coating_id, name, binder, ral, density, solid_content, price_kg, price_liter, is_thinner,
                deleted_date as change_date,
                'system' as changed_by
            FROM coating_delete_history 
            WHERE coating_id = ?
            
            ORDER BY change_date DESC 
            LIMIT ?
            ''', (coating_id, coating_id, coating_id, limit))
        else:
            # Вся история - ИСПРАВЛЕННЫЙ ЗАПРОС
            cursor.execute('''
            SELECT 
                'ADD' as action, 
                coating_id, name, binder, ral, density, solid_content, price_kg, price_liter, is_thinner,
                added_date as change_date,
                'system' as changed_by
            FROM coating_add_history 
            
            UNION ALL
            
            SELECT 
                'UPDATE' as action,
                coating_id, new_name as name, new_binder as binder, new_ral as ral, 
                new_density as density, new_solid_content as solid_content,
                new_price_kg as price_kg, new_price_liter as price_liter,
                new_is_thinner as is_thinner,
                update_date as change_date,
                'system' as changed_by
            FROM coating_update_history 
            
            UNION ALL
            
            SELECT 
                'DELETE' as action,
                coating_id, name, binder, ral, density, solid_content, price_kg, price_liter, is_thinner,
                deleted_date as change_date,
                'system' as changed_by
            FROM coating_delete_history 
            
            ORDER BY change_date DESC 
            LIMIT ?
            ''', (limit,))
        
        return cursor.fetchall()

class CoatingHistoryDialog:
    """Диалоговое окно для просмотра истории изменений материалов"""
    
    def __init__(self, parent, db):
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("История изменений материалов")
        self.dialog.geometry("1400x800")  # Увеличим размер для лучшего отображения
        self.db = db
        
        self.create_widgets()  # ИСПРАВЛЕНО: было create_widgeys
        self.load_history()

    def create_widgets(self):  # ИСПРАВЛЕНО: было create_widgeys
        """Создает элементы интерфейса"""
        main_frame = ttk.Frame(self.dialog)
        main_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Фрейм управления
        control_frame = ttk.Frame(main_frame)
        control_frame.pack(fill="x", pady=5)
        
        ttk.Button(control_frame, text="Обновить", 
                  command=self.load_history).pack(side=tk.LEFT, padx=5)
        ttk.Button(control_frame, text="Экспорт в Excel", 
                  command=self.export_history).pack(side=tk.LEFT, padx=5)
        
        # Вкладки для разных типов истории
        notebook = ttk.Notebook(main_frame)
        notebook.pack(fill="both", expand=True, pady=5)
        
        # Вкладка полной истории
        full_history_frame = ttk.Frame(notebook)
        notebook.add(full_history_frame, text="Полная история")
        
        # Вкладка истории добавлений
        add_history_frame = ttk.Frame(notebook)
        notebook.add(add_history_frame, text="История добавлений")
        
        # Вкладка истории изменений
        update_history_frame = ttk.Frame(notebook)
        notebook.add(update_history_frame, text="История изменений")
        
        # Вкладка истории удалений
        delete_history_frame = ttk.Frame(notebook)
        notebook.add(delete_history_frame, text="История удалений")
        
        # Создаем таблицы для каждой вкладки
        self.create_history_table(full_history_frame, "full")
        self.create_history_table(add_history_frame, "add")
        self.create_history_table(update_history_frame, "update")
        self.create_history_table(delete_history_frame, "delete")

    def create_history_table(self, parent, history_type):
        """Создает таблицу для отображения истории с детализацией изменений"""
        frame = ttk.Frame(parent)
        frame.pack(fill="both", expand=True, padx=5, pady=5)
        
        if history_type == "update":
            # Для истории изменений делаем расширенную таблицу с детализацией
            columns = ('Дата', 'Действие', 'ID', 'Название', 'Измененное поле', 
                      'Старое значение', 'Новое значение', 'Тип')
        else:
            # Для других типов истории оставляем как есть
            columns = ('Дата', 'Действие', 'ID', 'Название', 'Связующее', 'RAL', 'Плотность', 
                      'Сухой остаток', 'Цена за кг', 'Цена за литр', 'Тип')
        
        tree = ttk.Treeview(frame, columns=columns, show='headings')
        
        # Настраиваем заголовки
        for col in columns:
            tree.heading(col, text=col)
            if col in ['Измененное поле', 'Старое значение', 'Новое значение']:
                tree.column(col, width=150)
            else:
                tree.column(col, width=100)
        
        tree.column('Название', width=150)
        
        # Сохраняем ссылку на treeview
        if history_type == "full":
            self.full_tree = tree
        elif history_type == "add":
            self.add_tree = tree
        elif history_type == "update":
            self.update_tree = tree
        elif history_type == "delete":
            self.delete_tree = tree
        
        # Скроллбар
        scrollbar = ttk.Scrollbar(frame, orient="vertical", command=tree.yview)
        scrollbar.pack(side="right", fill="y")
        tree.configure(yscrollcommand=scrollbar.set)
        
        tree.pack(fill="both", expand=True)

    def load_history(self):
        """Загружает историю во все таблицы"""
        self.load_full_history()
        self.load_add_history()
        self.load_update_history()
        self.load_delete_history()

    def load_full_history(self):
        """Загружает полную историю с ПРАВИЛЬНЫМ определением типа материала"""
        for item in self.full_tree.get_children():
            self.full_tree.delete(item)
        
        history = self.db.get_coating_full_history()
        
        for record in history:
            # ПРАВИЛЬНОЕ определение типа материала
            # record[8] - это поле is_thinner (0 - покрытие, 1 - растворитель)
            is_thinner = record[8] if len(record) > 8 else 0
            material_type = 'Растворитель' if is_thinner else 'Покрытие'
            
            self.full_tree.insert('', 'end', values=(
                record[9],  # change_date
                record[0],  # action
                record[1],  # coating_id
                record[2],  # name
                record[3] or "",  # binder
                record[4] or "",  # ral
                f"{record[5]:.3f}" if record[5] else "0.000",  # density
                f"{record[6]:.1f}" if record[6] else "0.0",  # solid_content
                f"{record[7]:.2f}" if record[7] else "0.00",  # price_kg
                f"{record[8]:.2f}" if record[8] else "0.00",  # price_liter
                material_type  # ИСПРАВЛЕНО: правильное определение типа
            ))

    def load_add_history(self):
        """Загружает историю добавлений с правильным определением типа"""
        for item in self.add_tree.get_children():
            self.add_tree.delete(item)
        
        history = self.db.get_coating_add_history()
        
        for record in history:
            is_thinner = record[9] if len(record) > 9 else 0
            material_type = 'Растворитель' if is_thinner else 'Покрытие'
            
            self.add_tree.insert('', 'end', values=(
                record[10],  # added_date
                record[1],  # coating_id
                record[2],  # name
                record[3] or "",  # binder
                record[4] or "",  # ral
                f"{record[5]:.3f}" if record[5] else "0.000",  # density
                f"{record[6]:.1f}" if record[6] else "0.0",  # solid_content
                f"{record[7]:.2f}" if record[7] else "0.00",  # price_kg
                f"{record[8]:.2f}" if record[8] else "0.00",  # price_liter
                material_type  # ИСПРАВЛЕНО
            ))

    def load_update_history(self):
        """Загружает историю изменений с детализацией по полям"""
        for item in self.update_tree.get_children():
            self.update_tree.delete(item)
        
        history = self.db.get_coating_update_history()
        
        for record in history:
            # Для каждой записи обновления создаем отдельные строки для каждого измененного поля
            changed_fields = self.get_changed_fields(record)
            
            for field_name, old_val, new_val in changed_fields:
                self.update_tree.insert('', 'end', values=(
                    record[18],  # update_date
                    'ИЗМЕНЕНИЕ',
                    record[1],  # coating_id
                    record[3],  # new_name
                    field_name,
                    old_val,
                    new_val,
                    'Растворитель' if record[17] else 'Покрытие'
                ))

    def get_changed_fields(self, record):
        """Определяет какие поля были изменены и возвращает список изменений"""
        changed_fields = []
        
        # Сопоставление индексов полей с человеко-читаемыми названиями
        field_mapping = [
            (2, 3, 'Название'),
            (4, 5, 'Связующее'),
            (6, 7, 'RAL'),
            (8, 9, 'Плотность'),
            (10, 11, 'Сухой остаток'),
            (12, 13, 'Цена за кг'),
            (14, 15, 'Цена за литр'),
            (16, 17, 'Тип материала')
        ]
        
        for old_idx, new_idx, field_name in field_mapping:
            old_val = record[old_idx]
            new_val = record[new_idx]
            
            # Сравниваем значения, учитывая None и разные типы
            if self.values_different(old_val, new_val):
                # Форматируем значения для отображения
                old_display = self.format_value(old_val, field_name)
                new_display = self.format_value(new_val, field_name)
                
                changed_fields.append((field_name, old_display, new_display))
        
        return changed_fields

    def values_different(self, old_val, new_val):
        """Сравнивает два значения с учетом разных типов и None"""
        if old_val is None and new_val is None:
            return False
        if old_val is None or new_val is None:
            return True
        
        # Для числовых значений сравниваем с небольшой погрешностью
        if isinstance(old_val, (int, float)) and isinstance(new_val, (int, float)):
            return abs(old_val - new_val) > 0.001
        
        # Для строковых и других типов
        return str(old_val) != str(new_val)

    def format_value(self, value, field_name):
        """Форматирует значение для отображения в таблице"""
        if value is None:
            return "не задано"
        
        if field_name in ['Плотность', 'Цена за кг', 'Цена за литр']:
            if isinstance(value, (int, float)):
                return f"{value:.3f}"
        elif field_name == 'Сухой остаток':
            if isinstance(value, (int, float)):
                return f"{value:.1f}%"
        elif field_name == 'Тип материала':
            return 'Растворитель' if value else 'Покрытие'
        
        return str(value) if value is not None else ""

    def load_delete_history(self):
        """Загружает историю удалений с правильным определением типа"""
        for item in self.delete_tree.get_children():
            self.delete_tree.delete(item)
        
        history = self.db.get_coating_delete_history()
        
        for record in history:
            is_thinner = record[9] if len(record) > 9 else 0
            material_type = 'Растворитель' if is_thinner else 'Покрытие'
            
            self.delete_tree.insert('', 'end', values=(
                record[10],  # deleted_date
                record[1],  # coating_id
                record[2],  # name
                record[3] or "",  # binder
                record[4] or "",  # ral
                f"{record[5]:.3f}" if record[5] else "0.000",  # density
                f"{record[6]:.1f}" if record[6] else "0.0",  # solid_content
                f"{record[7]:.2f}" if record[7] else "0.00",  # price_kg
                f"{record[8]:.2f}" if record[8] else "0.00",  # price_liter
                material_type  # ИСПРАВЛЕНО
            ))

    def export_history(self):
        """Экспортирует историю в Excel"""
        try:
            wb = Workbook()
            
            # Лист с полной историей
            ws_full = wb.active
            ws_full.title = "Полная история"
            self.export_history_sheet(ws_full, "full")
            
            # Лист с историей добавлений
            ws_add = wb.create_sheet("История добавлений")
            self.export_history_sheet(ws_add, "add")
            
            # Лист с историей изменений
            ws_update = wb.create_sheet("История изменений")
            self.export_history_sheet(ws_update, "update")
            
            # Лист с историей удалений
            ws_delete = wb.create_sheet("История удалений")
            self.export_history_sheet(ws_delete, "delete")
            
            # Сохраняем файл
            file_path = filedialog.asksaveasfilename(
                defaultextension='.xlsx',
                filetypes=[("Excel files", "*.xlsx")],
                title="Сохранить историю изменений"
            )
            
            if file_path:
                wb.save(file_path)
                messagebox.showinfo("Успех", "История изменений экспортирована в Excel!")
                
        except Exception as e:
            messagebox.showerror("Ошибка", f"Ошибка при экспорте: {str(e)}")

    def export_history_sheet(self, ws, history_type):
        """Экспортирует конкретный тип истории на лист Excel с улучшенным форматированием для изменений"""
        if history_type == "full":
            headers = ['Дата', 'Действие', 'ID', 'Название', 'Связующее', 'RAL', 'Плотность', 
                      'Сухой остаток', 'Цена за кг', 'Цена за литр', 'Тип']
            history = self.db.get_coating_full_history()
        elif history_type == "add":
            headers = ['Дата добавления', 'ID', 'Название', 'Связующее', 'RAL', 'Плотность', 
                      'Сухой остаток', 'Цена за кг', 'Цена за литр', 'Тип']
            history = self.db.get_coating_add_history()
        elif history_type == "update":
            # Для изменений используем расширенные заголовки
            headers = ['Дата изменения', 'ID', 'Название', 'Измененное поле', 
                      'Старое значение', 'Новое значение', 'Тип']
            history = self.db.get_coating_update_history()
        elif history_type == "delete":
            headers = ['Дата удаления', 'ID', 'Название', 'Связующее', 'RAL', 'Плотность', 
                      'Сухой остаток', 'Цена за кг', 'Цена за литр', 'Тип']
            history = self.db.get_coating_delete_history()
        
        # Заголовки
        for col, header in enumerate(headers, 1):
            cell = ws.cell(row=1, column=col)
            cell.value = header
            cell.font = Font(bold=True)
            cell.fill = PatternFill(start_color="E6E6FA", end_color="E6E6FA", fill_type="solid")
        
        # Данные
        row_num = 2
        if history_type == "update":
            # Для изменений обрабатываем каждую запись отдельно
            for record in history:
                changed_fields = self.get_changed_fields(record)
                for field_name, old_val, new_val in changed_fields:
                    values = [
                        record[18],  # update_date
                        record[1],   # coating_id
                        record[3],   # new_name
                        field_name,
                        old_val,
                        new_val,
                        'Растворитель' if record[17] else 'Покрытие'
                    ]
                    
                    for col, value in enumerate(values, 1):
                        cell = ws.cell(row=row_num, column=col)
                        cell.value = value
                    
                    row_num += 1
        else:
            # Для других типов истории стандартная обработка
            for record in history:
                if history_type == "full":
                    values = [
                        record[9], record[0], record[1], record[2], record[3] or "",
                        record[4] or "", record[5] or 0, record[6] or 0, 
                        record[7] or 0, record[8] or 0, 
                        'Растворитель' if record[10] else 'Покрытие'
                    ]
                elif history_type == "add":
                    values = [
                        record[10], record[1], record[2], record[3] or "", record[4] or "",
                        record[5] or 0, record[6] or 0, record[7] or 0, record[8] or 0,
                        'Растворитель' if record[9] else 'Покрытие'
                    ]
                elif history_type == "delete":
                    values = [
                        record[10], record[1], record[2], record[3] or "", record[4] or "",
                        record[5] or 0, record[6] or 0, record[7] or 0, record[8] or 0,
                        'Растворитель' if record[9] else 'Покрытие'
                    ]
                
                for col, value in enumerate(values, 1):
                    cell = ws.cell(row=row_num, column=col)
                    cell.value = value
                
                row_num += 1
        
        # Настройка ширины столбцов
        for col in range(1, len(headers) + 1):
            ws.column_dimensions[get_column_letter(col)].width = 15

class CoatingTemplateDialog:
    """Диалоговое окно для управления шаблонными схемами покрытий"""
    
    def __init__(self, parent, main_app):
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("Шаблонные схемы покрытий")
        self.dialog.geometry("1000x700")
        self.main_app = main_app
        self.db = main_app.db
        self.selected_template_id = None
        
        self.create_widgets()
        self.load_templates()

    def create_widgets(self):
        """Создает элементы интерфейса"""
        main_frame = ttk.Frame(self.dialog)
        main_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Фрейм управления шаблонами
        control_frame = ttk.LabelFrame(main_frame, text="Управление шаблонами")
        control_frame.pack(fill="x", pady=5)
        
        btn_frame = ttk.Frame(control_frame)
        btn_frame.pack(fill="x", pady=5)
        
        ttk.Button(btn_frame, text="Создать шаблон", 
                  command=self.create_template).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Редактировать", 
                  command=self.edit_template).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Удалить шаблон", 
                  command=self.delete_template).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Загрузить в расчет", 
                  command=self.load_template_to_calculation).pack(side=tk.LEFT, padx=5)
        
        # Поиск
        search_frame = ttk.Frame(control_frame)
        search_frame.pack(fill="x", pady=5)
        
        ttk.Label(search_frame, text="Поиск:").pack(side=tk.LEFT, padx=5)
        self.search_entry = ttk.Entry(search_frame, width=30)
        self.search_entry.pack(side=tk.LEFT, padx=5)
        self.search_entry.bind('<KeyRelease>', self.on_search)
        
        # Таблица шаблонов
        list_frame = ttk.LabelFrame(main_frame, text="Шаблонные схемы покрытий")
        list_frame.pack(fill="both", expand=True, pady=5)
        
        columns = ('ID', 'Название', 'Описание', 'Протокол', 'Слоев', 'Дата создания')
        self.templates_tree = ttk.Treeview(list_frame, columns=columns, show='headings')
        
        for col in columns:
            self.templates_tree.heading(col, text=col)
            self.templates_tree.column(col, width=100)
        
        self.templates_tree.column('Название', width=200)
        self.templates_tree.column('Описание', width=250)
        
        self.templates_tree.pack(fill="both", expand=True, padx=5, pady=5)
        
        # Скроллбар
        scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=self.templates_tree.yview)
        scrollbar.pack(side="right", fill="y")
        self.templates_tree.configure(yscrollcommand=scrollbar.set)
        
        # Привязываем выбор
        self.templates_tree.bind('<<TreeviewSelect>>', self.on_template_select)

    def load_templates(self):
        """Загружает список шаблонов"""
        for item in self.templates_tree.get_children():
            self.templates_tree.delete(item)
        
        templates = self.db.get_all_coating_templates()
        for template in templates:
            self.templates_tree.insert('', 'end', values=(
                template[0],  # ID
                template[1],  # name
                template[2] or "",  # description
                template[3] or "",  # protocol_number
                template[5],  # layers_count
                template[4]    # created_date
            ))

    def on_search(self, event):
        """Обработчик поиска"""
        search_term = self.search_entry.get().strip()
        if not search_term:
            self.load_templates()
            return
        
        for item in self.templates_tree.get_children():
            self.templates_tree.delete(item)
        
        templates = self.db.search_coating_templates(search_term)
        for template in templates:
            self.templates_tree.insert('', 'end', values=(
                template[0], template[1], template[2] or "", 
                template[3] or "", template[5], template[4]
            ))

    def on_template_select(self, event):
        """Обработчик выбора шаблона"""
        selected = self.templates_tree.selection()
        if selected:
            self.selected_template_id = self.templates_tree.item(selected[0])['values'][0]

    def create_template(self):
        """Создает новый шаблон"""
        TemplateEditorDialog(self.dialog, self.db, self, None)

    def edit_template(self):
        """Редактирует выбранный шаблон"""
        if not self.selected_template_id:
            messagebox.showwarning("Предупреждение", "Выберите шаблон для редактирования")
            return
        
        TemplateEditorDialog(self.dialog, self.db, self, self.selected_template_id)

    def delete_template(self):
        """Удаляет выбранный шаблон"""
        if not self.selected_template_id:
            messagebox.showwarning("Предупреждение", "Выберите шаблон для удаления")
            return
        
        if messagebox.askyesno("Подтверждение", "Действительно удалить выбранный шаблон?"):
            self.db.delete_coating_template(self.selected_template_id)
            self.load_templates()
            self.selected_template_id = None

    def load_template_to_calculation(self):
        """Загружает выбранный шаблон в основной расчет"""
        if not self.selected_template_id:
            messagebox.showwarning("Предупреждение", "Выберите шаблон для загрузки")
            return
        
        template_layers = self.db.get_template_layers(self.selected_template_id)
        if not template_layers:
            messagebox.showwarning("Предупреждение", "Выбранный шаблон не содержит слоев")
            return
        
        # Добавляем слои из шаблона в основной расчет
        for layer_data in template_layers:
            coating_name, dry_thickness, position = layer_data
            
            # Ищем покрытие в базе данных
            coating = self.db.get_coating_by_name(coating_name)
            if not coating:
                messagebox.showwarning("Предупреждение", 
                                    f"Покрытие '{coating_name}' не найдено в базе данных")
                continue
            
            # Создаем слой
            layer = [
                coating[1],  # name
                coating[2],  # binder
                coating[3],  # ral
                coating[4],  # density
                coating[5],  # solid_content
                0.0,  # wet_thickness
                dry_thickness,  # dry_thickness из шаблона
                0.0,  # theor_covering
                10.0,  # losses по умолчанию
                0.0,  # pract_covering
                coating[6],  # price_kg
                coating[7],  # price_liter
                0.0,  # theor_consumption_kg
                0.0,  # pract_consumption_kg
                0.0,  # cost
                0.0   # thinner_percent
            ]
            
            # Пересчитываем слой
            layer = self.main_app.update_layer_calculations(layer)
            self.main_app.layers.append(layer)
        
        # Обновляем интерфейс основного приложения
        self.main_app.create_layer_table()
        self.main_app.update_total_cost_display()
        
        messagebox.showinfo("Успех", "Шаблон загружен в расчет!")
        self.dialog.destroy()

# Класс для редактирования шаблонов
class TemplateEditorDialog:
    """Диалог для создания/редактирования шаблонов покрытий"""
    
    def __init__(self, parent, db, template_manager, template_id=None):
        self.dialog = tk.Toplevel(parent)
        self.db = db
        self.template_manager = template_manager
        self.template_id = template_id
        self.layers = []
        
        if template_id:
            self.dialog.title("Редактирование шаблона")
            self.load_template_data()
        else:
            self.dialog.title("Создание шаблона")
        
        self.dialog.geometry("800x600")
        self.create_widgets()

    def create_widgets(self):
        """Создает элементы интерфейса"""
        main_frame = ttk.Frame(self.dialog)
        main_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Основные поля
        fields_frame = ttk.LabelFrame(main_frame, text="Основная информация")
        fields_frame.pack(fill="x", pady=5)
        
        ttk.Label(fields_frame, text="Название шаблона:").grid(row=0, column=0, padx=5, pady=2, sticky='w')
        self.name_entry = ttk.Entry(fields_frame, width=50)
        self.name_entry.grid(row=0, column=1, padx=5, pady=2, sticky='ew')
        
        ttk.Label(fields_frame, text="Описание:").grid(row=1, column=0, padx=5, pady=2, sticky='w')
        self.desc_entry = ttk.Entry(fields_frame, width=50)
        self.desc_entry.grid(row=1, column=1, padx=5, pady=2, sticky='ew')
        
        ttk.Label(fields_frame, text="Номер протокола:").grid(row=2, column=0, padx=5, pady=2, sticky='w')
        self.protocol_entry = ttk.Entry(fields_frame, width=50)
        self.protocol_entry.grid(row=2, column=1, padx=5, pady=2, sticky='ew')
        
        ttk.Label(fields_frame, text="Вывод из протокола:").grid(row=3, column=0, padx=5, pady=2, sticky='w')
        self.conclusion_text = tk.Text(fields_frame, width=50, height=4)
        self.conclusion_text.grid(row=3, column=1, padx=5, pady=2, sticky='ew')
        
        # Управление слоями
        layers_frame = ttk.LabelFrame(main_frame, text="Слои покрытия")
        layers_frame.pack(fill="both", expand=True, pady=5)
        
        # Панель управления слоями
        layers_control = ttk.Frame(layers_frame)
        layers_control.pack(fill="x", pady=5)
        
        ttk.Button(layers_control, text="Добавить слой", 
                  command=self.add_layer).pack(side=tk.LEFT, padx=5)
        ttk.Button(layers_control, text="Удалить слой", 
                  command=self.remove_layer).pack(side=tk.LEFT, padx=5)
        
        # Таблица слоев
        columns = ('Покрытие', 'Толщина сух., мкм')
        self.layers_tree = ttk.Treeview(layers_frame, columns=columns, show='headings', height=8)
        
        for col in columns:
            self.layers_tree.heading(col, text=col)
            self.layers_tree.column(col, width=200)
        
        self.layers_tree.pack(fill="both", expand=True, padx=5, pady=5)
        
        # Скроллбар
        scrollbar = ttk.Scrollbar(layers_frame, orient="vertical", command=self.layers_tree.yview)
        scrollbar.pack(side="right", fill="y")
        self.layers_tree.configure(yscrollcommand=scrollbar.set)
        
        # Кнопки сохранения/отмены
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill="x", pady=10)
        
        ttk.Button(button_frame, text="Сохранить", 
                  command=self.save_template).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Отмена", 
                  command=self.dialog.destroy).pack(side=tk.RIGHT, padx=5)

    def load_template_data(self):
        """Загружает данные шаблона для редактирования"""
        template = self.db.get_coating_template(self.template_id)
        if template:
            self.name_entry.insert(0, template[1])  # name
            self.desc_entry.insert(0, template[2] or "")  # description
            self.protocol_entry.insert(0, template[3] or "")  # protocol_number
            self.conclusion_text.insert('1.0', template[4] or "")  # test_conclusion
        
        # Загружаем слои
        template_layers = self.db.get_template_layers(self.template_id)
        for layer_data in template_layers:
            coating_name, dry_thickness, position = layer_data
            self.layers.append((coating_name, dry_thickness))
            self.layers_tree.insert('', 'end', values=(coating_name, f"{dry_thickness:.1f}"))

    def add_layer(self):
        """Добавляет новый слой в шаблон"""
        LayerSelectorDialog(self.dialog, self.db, self)

    def remove_layer(self):
        """Удаляет выбранный слой из шаблона"""
        selected = self.layers_tree.selection()
        if not selected:
            return
        
        index = self.layers_tree.index(selected[0])
        self.layers.pop(index)
        self.layers_tree.delete(selected[0])

    def add_layer_data(self, coating_name, dry_thickness):
        """Добавляет данные слоя в шаблон"""
        self.layers.append((coating_name, dry_thickness))
        self.layers_tree.insert('', 'end', values=(coating_name, f"{dry_thickness:.1f}"))

    def save_template(self):
        """Сохраняет шаблон"""
        name = self.name_entry.get().strip()
        if not name:
            messagebox.showerror("Ошибка", "Введите название шаблона")
            return
        
        if not self.layers:
            messagebox.showerror("Ошибка", "Добавьте хотя бы один слой в шаблон")
            return
        
        description = self.desc_entry.get().strip()
        protocol_number = self.protocol_entry.get().strip()
        test_conclusion = self.conclusion_text.get('1.0', 'end-1c').strip()
        
        if self.template_id:
            # Обновление существующего шаблона
            success = self.db.update_coating_template(
                self.template_id, name, description, protocol_number, test_conclusion, self.layers
            )
            if not success:
                messagebox.showerror("Ошибка", "Шаблон с таким названием уже существует")
                return
        else:
            # Создание нового шаблона
            success = self.db.add_coating_template(
                name, description, protocol_number, test_conclusion, self.layers
            )
            if not success:
                messagebox.showerror("Ошибка", "Шаблон с таким названием уже существует")
                return
        
        self.template_manager.load_templates()
        self.dialog.destroy()
        messagebox.showinfo("Успех", "Шаблон сохранен!")

# Диалог выбора покрытия и толщины для слоя шаблона
class LayerSelectorDialog:
    """Диалог для выбора покрытия и толщины для слоя шаблона"""
    
    def __init__(self, parent, db, template_editor):
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("Добавить слой в шаблон")
        self.dialog.geometry("400x300")
        self.db = db
        self.template_editor = template_editor
        
        self.create_widgets()

    def create_widgets(self):
        """Создает элементы интерфейса"""
        main_frame = ttk.Frame(self.dialog)
        main_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        ttk.Label(main_frame, text="Выберите покрытие:").pack(anchor='w', pady=5)
        
        # ComboBox с поиском для выбора покрытия
        coatings = [coating[1] for coating in self.db.get_coatings()]
        self.coating_combo = ComboboxWithSearch(main_frame, values=coatings, width=50)
        self.coating_combo.pack(fill="x", pady=5)
        
        ttk.Label(main_frame, text="Толщина сухого слоя (мкм):").pack(anchor='w', pady=5)
        self.thickness_entry = ttk.Entry(main_frame, width=20)
        self.thickness_entry.insert(0, "100.0")
        self.thickness_entry.pack(anchor='w', pady=5)
        
        # Кнопки
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill="x", pady=20)
        
        ttk.Button(button_frame, text="Добавить", 
                  command=self.add_layer).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Отмена", 
                  command=self.dialog.destroy).pack(side=tk.RIGHT, padx=5)

    def add_layer(self):
        """Добавляет выбранный слой в шаблон"""
        coating_name = self.coating_combo.get().strip()
        if not coating_name:
            messagebox.showwarning("Предупреждение", "Выберите покрытие")
            return
        
        try:
            thickness = float(self.thickness_entry.get().strip())
            if thickness <= 0:
                raise ValueError
        except ValueError:
            messagebox.showerror("Ошибка", "Введите корректное значение толщины")
            return
        
        self.template_editor.add_layer_data(coating_name, thickness)
        self.dialog.destroy()


class CoatingDatabaseDialog:
    """Диалоговое окно для управления базой данных покрытий и растворителей"""
    def __init__(self, parent):
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("База данных покрытий и растворителей")
        self.db = DatabaseManager()
        self.selected_id = None
        self.create_widgets()

    def create_widgets(self):
        """Создает элементы интерфейса диалогового окна"""
        # Создаем фрейм для ввода данных
        input_frame = ttk.LabelFrame(self.dialog, text="Добавить/Редактировать покрытие/растворитель")
        input_frame.pack(padx=5, pady=5, fill="x")

        # Поля ввода
        fields = [
            ('Название', ''),
            ('Связующее', ''),
            ('RAL', ''),
            ('Плотность', 0.0),
            ('Сухой остаток', 0.0),
            ('Цена за кг', 0.0),
            ('Цена за литр', 0.0)
        ]

        self.entries = {}
        for i, (field, default) in enumerate(fields):
            ttk.Label(input_frame, text=field).grid(row=i, column=0, padx=5, pady=2)
            entry = ttk.Entry(input_frame)
            entry.grid(row=i, column=1, padx=5, pady=2)
            entry.insert(0, str(default))
            self.entries[field] = entry

        # Чекбокс для отметки растворителя
        self.is_thinner_var = tk.BooleanVar()
        thinner_check = ttk.Checkbutton(input_frame, text="Это растворитель/разбавитель", 
                                       variable=self.is_thinner_var)
        thinner_check.grid(row=len(fields), column=0, columnspan=2, pady=5)
        
        # Кнопки управления
        button_frame = ttk.Frame(input_frame)
        button_frame.grid(row=len(fields)+1, column=0, columnspan=2, pady=10)
        
        ttk.Button(button_frame, text="Добавить", 
                  command=self.add_to_database).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Обновить", 
                  command=self.update_in_database).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Удалить", 
                  command=self.delete_from_database).pack(side=tk.LEFT, padx=5)

        # Создаем таблицу для отображения данных
        table_frame = ttk.LabelFrame(self.dialog, text="Существующие покрытия и растворители")
        table_frame.pack(padx=5, pady=5, fill="both", expand=True)

        # Создаем Treeview
        columns = ('ID', 'Название', 'Связующее', 'RAL', 'Плотность', 
                  'Сухой остаток', 'Цена за кг', 'Цена за литр', 'Тип')
        self.tree = ttk.Treeview(table_frame, columns=columns, show='headings')

        # Добавляем заголовки
        for col in columns:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=100)

        self.tree.pack(fill="both", expand=True)
        
        # Добавляем скроллар
        scrollbar = ttk.Scrollbar(table_frame, orient="vertical", command=self.tree.yview)
        scrollbar.pack(side="right", fill="y")
        self.tree.configure(yscrollcommand=scrollbar.set)

        # Привязываем событие выбора строки
        self.tree.bind('<<TreeviewSelect>>', self.on_select)

        # Привязываем автоматический расчет цен
        self.entries['Плотность'].bind('<KeyRelease>', self.calculate_prices)
        self.entries['Цена за кг'].bind('<KeyRelease>', self.calculate_price_liter)
        self.entries['Цена за литр'].bind('<KeyRelease>', self.calculate_price_kg)

        # Загружаем данные
        self.load_data()

    def calculate_prices(self, event=None):
        """Автоматический расчет цен при изменении плотности или одной из цен"""
        try:
            density = float(self.entries['Плотность'].get())
            price_kg = self.entries['Цена за кг'].get()
            price_liter = self.entries['Цена за литр'].get()
            
            if price_kg and not price_liter:
                price_kg = float(price_kg)
                self.entries['Цена за литр'].delete(0, tk.END)
                self.entries['Цена за литр'].insert(0, str(round(price_kg * density, 2)))
            elif price_liter and not price_kg:
                price_liter = float(price_liter)
                self.entries['Цена за кг'].delete(0, tk.END)
                self.entries['Цена за кг'].insert(0, str(round(price_liter / density, 2)))
        except ValueError:
            pass

    def calculate_price_liter(self, event=None):
        """Расчет цены за литр при изменении цены за кг"""
        try:
            density = float(self.entries['Плотность'].get())
            price_kg = float(self.entries['Цена за кг'].get())
            self.entries['Цена за литр'].delete(0, tk.END)
            self.entries['Цена за литр'].insert(0, str(round(price_kg * density, 2)))
        except ValueError:
            pass

    def calculate_price_kg(self, event=None):
        """Расчет цены за кг при изменении цены за литр"""
        try:
            density = float(self.entries['Плотность'].get())
            price_liter = float(self.entries['Цена за литр'].get())
            self.entries['Цена за кг'].delete(0, tk.END)
            self.entries['Цена за кг'].insert(0, str(round(price_liter / density, 2)))
        except ValueError:
            pass

    def on_select(self, event):
        """Обработчик выбора строки в таблице"""
        selected_items = self.tree.selection()
        if selected_items:
            item = self.tree.item(selected_items[0])
            values = item.get('values')
            self.selected_id = values[0]
            
            # Заполняем поля данными выбранной строки
            self.entries['Название'].delete(0, tk.END)
            self.entries['Название'].insert(0, values[1])
            self.entries['Связующее'].delete(0, tk.END)
            self.entries['Связующее'].insert(0, values[2])
            self.entries['RAL'].delete(0, tk.END)
            self.entries['RAL'].insert(0, values[3])
            self.entries['Плотность'].delete(0, tk.END)
            self.entries['Плотность'].insert(0, values[4])
            self.entries['Сухой остаток'].delete(0, tk.END)
            self.entries['Сухой остаток'].insert(0, values[5])
            self.entries['Цена за кг'].delete(0, tk.END)
            self.entries['Цена за кг'].insert(0, values[6])
            self.entries['Цена за литр'].delete(0, tk.END)
            self.entries['Цена за литр'].insert(0, values[7])
            
            # Устанавливаем чекбокс растворителя
            self.is_thinner_var.set(values[8] == 'Растворитель')

    def add_to_database(self):
        """Добавление нового материала в базу данных"""
        try:
            name = self.entries['Название'].get()
            binder = self.entries['Связующее'].get()
            ral = self.entries['RAL'].get()
            density = float(self.entries['Плотность'].get() or 0)
            solid_content = float(self.entries['Сухой остаток'].get() or 0)
            price_kg = float(self.entries['Цена за кг'].get() or 0)
            price_liter = float(self.entries['Цена за литр'].get() or 0)
            is_thinner = self.is_thinner_var.get()

            self.db.add_coating(name, binder, ral, density, solid_content, 
                              price_kg, price_liter, is_thinner)
            self.load_data()
            messagebox.showinfo("Успех", "Материал добавлен в базу данных")

            # Очищаем поля ввода
            for entry in self.entries.values():
                entry.delete(0, tk.END)
            self.is_thinner_var.set(False)

        except ValueError:
            messagebox.showerror("Ошибка", 
                               "Пожалуйста, проверьте правильность введенных данных")

    def update_in_database(self):
        """Обновление выбранного материала в базе данных"""
        if not self.selected_id:
            messagebox.showwarning("Предупреждение", "Выберите запись для обновления")
            return
        
        try:
            self.db.update_coating(
                self.selected_id,
                self.entries['Название'].get(),
                self.entries['Связующее'].get(),
                self.entries['RAL'].get(),
                float(self.entries['Плотность'].get() or 0),
                float(self.entries['Сухой остаток'].get() or 0),
                float(self.entries['Цена за кг'].get() or 0),
                float(self.entries['Цена за литр'].get() or 0),
                self.is_thinner_var.get()
            )
            self.load_data()
            messagebox.showinfo("Успех", "Запись обновлена")
        except ValueError:
            messagebox.showerror("Ошибка", 
                               "Пожалуйста, проверьте правильность введенных данных")

    def delete_from_database(self):
        """Удаление выбранного материала из базы данных"""
        if not self.selected_id:
            messagebox.showwarning("Предупреждение", "Выберите запись для удаления")
            return
        
        if messagebox.askyesno("Подтверждение", "Действительно удалить запись?"):
            self.db.delete_coating(self.selected_id)
            self.load_data()
            messagebox.showinfo("Успех", "Запись удалена")

    def load_data(self):
        """Загрузка и отображение данных из базы данных"""
        # Очищаем таблицу
        for item in self.tree.get_children():
            self.tree.delete(item)

        # Загружаем данные из базы
        coatings = self.db.get_all_coatings()
        for coating in coatings:
            # Преобразуем тип для отображения
            display_values = list(coating[:8])  # Берем первые 8 полей
            display_values.append('Растворитель' if coating[8] else 'Покрытие')  # Добавляем тип
            self.tree.insert('', 'end', values=display_values)

class SystemComparisonDialog:
    """Диалоговое окно для сравнения систем покрытий"""
    
    # Константы для индексов полей слоя (совместимость с основным классом)
    NAME = 0
    BINDER = 1
    RAL = 2
    DENSITY = 3
    SOLID_CONTENT = 4
    WET_THICKNESS = 5
    DRY_THICKNESS = 6
    THEOR_COVERING = 7
    LOSSES = 8
    PRACT_COVERING = 9
    PRICE_KG = 10
    PRICE_LITER = 11
    THEOR_CONSUMPTION_KG = 12
    PRACT_CONSUMPTION_KG = 13
    COST = 14
    THINNER_PERCENT = 15
    
    def __init__(self, parent, main_app):
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("Сравнение систем покрытий")
        self.dialog.geometry("1200x800")
        self.main_app = main_app
        
        # Хранилище для систем
        self.systems = []  # Каждая система - это копия self.layers из main_app
        self.system_names = []
        
        self.create_widgets()

    def create_widgets(self):
        """Создает элементы интерфейса диалогового окна"""
        # Создаем Notebook для вкладок
        notebook = ttk.Notebook(self.dialog)
        notebook.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Вкладка управления системами
        self.management_frame = ttk.Frame(notebook)
        notebook.add(self.management_frame, text="Управление системами")
        
        # Вкладка сравнения систем
        self.comparison_frame = ttk.Frame(notebook)
        notebook.add(self.comparison_frame, text="Сравнение систем")
        
        # Вкладка сравнения по слоям
        self.layers_comparison_frame = ttk.Frame(notebook)
        notebook.add(self.layers_comparison_frame, text="Сравнение по слоям")
        
        self.create_management_tab()
        self.create_system_comparison_tab()
        self.create_layers_comparison_tab()

    def create_management_tab(self):
        """Создает вкладку управления системами"""
        # Фрейм для управления системами
        control_frame = ttk.LabelFrame(self.management_frame, text="Управление системами")
        control_frame.pack(fill="x", padx=10, pady=5)
        
        # Кнопки управления
        btn_frame = ttk.Frame(control_frame)
        btn_frame.pack(fill="x", pady=5)
        
        ttk.Button(btn_frame, text="Добавить текущую систему", 
                  command=self.add_current_system).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Удалить систему", 
                  command=self.remove_system).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Сравнить системы", 
                  command=self.compare_systems).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Экспорт сравнения", 
                  command=self.export_comparison).pack(side=tk.LEFT, padx=5)
        
        # Поле для имени системы
        name_frame = ttk.Frame(control_frame)
        name_frame.pack(fill="x", pady=5)
        
        ttk.Label(name_frame, text="Название системы:").pack(side=tk.LEFT, padx=5)
        self.system_name_entry = ttk.Entry(name_frame, width=30)
        self.system_name_entry.pack(side=tk.LEFT, padx=5)
        self.system_name_entry.insert(0, f"Системa {len(self.systems) + 1}")
        
        # Список систем
        list_frame = ttk.LabelFrame(self.management_frame, text="Добавленные системы")
        list_frame.pack(fill="both", expand=True, padx=10, pady=5)
        
        # Treeview для отображения систем
        columns = ('Название', 'Кол-во слоев', 'Общая толщина', 'Стоимость м²', 'Расход кг/м²', 'Расход л/м²')
        self.systems_tree = ttk.Treeview(list_frame, columns=columns, show='headings')
        
        # Заголовки
        for col in columns:
            self.systems_tree.heading(col, text=col)
            self.systems_tree.column(col, width=120)
        
        self.systems_tree.pack(fill="both", expand=True, padx=5, pady=5)
        
        # Скроллбар
        scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=self.systems_tree.yview)
        scrollbar.pack(side="right", fill="y")
        self.systems_tree.configure(yscrollcommand=scrollbar.set)

    def create_system_comparison_tab(self):
        """Создает вкладку сравнения систем"""
        # Фрейм для результатов сравнения систем
        results_frame = ttk.LabelFrame(self.comparison_frame, text="Сравнение систем покрытий")
        results_frame.pack(fill="both", expand=True, padx=10, pady=5)
        
        # Создаем Treeview для сравнения систем
        self.comparison_tree = ttk.Treeview(results_frame, height=20)
        self.comparison_tree.pack(fill="both", expand=True, padx=5, pady=5)
        
        # Скроллбар
        scrollbar = ttk.Scrollbar(results_frame, orient="vertical", command=self.comparison_tree.yview)
        scrollbar.pack(side="right", fill="y")
        self.comparison_tree.configure(yscrollcommand=scrollbar.set)

    def create_layers_comparison_tab(self):
        """Создает вкладку сравнения по слоям"""
        # Фрейм для сравнения по слоям
        layers_frame = ttk.LabelFrame(self.layers_comparison_frame, text="Сравнение по слоям")
        layers_frame.pack(fill="both", expand=True, padx=10, pady=5)
        
        # Создаем Treeview для сравнения слоев
        self.layers_comparison_tree = ttk.Treeview(layers_frame, height=20)
        self.layers_comparison_tree.pack(fill="both", expand=True, padx=5, pady=5)
        
        # Скроллбар
        scrollbar = ttk.Scrollbar(layers_frame, orient="vertical", command=self.layers_comparison_tree.yview)
        scrollbar.pack(side="right", fill="y")
        self.layers_comparison_tree.configure(yscrollcommand=scrollbar.set)

    def add_current_system(self):
        """Добавляет текущую систему из основного приложения"""
        if not self.main_app.layers:
            messagebox.showwarning("Предупреждение", "Нет данных о системе покрытий")
            return
            
        system_name = self.system_name_entry.get().strip()
        if not system_name:
            messagebox.showwarning("Предупреждение", "Введите название системы")
            return
            
        # Создаем глубокую копию текущих слоев
        system_copy = [layer[:] for layer in self.main_app.layers]
        
        # Добавляем систему
        self.systems.append(system_copy)
        self.system_names.append(system_name)
        
        # Рассчитываем параметры системы
        total_cost = self.main_app.calculate_total_cost()
        total_thickness = self.main_app.calculate_total_dry_thickness()
        total_consumption_kg = self.main_app.calculate_total_theor_consumption_kg()
        total_consumption_l = self.main_app.calculate_total_theor_consumption_l()
        layer_count = len([layer for layer in system_copy if 'Разбавитель' not in layer[0] and 'Растворитель' not in layer[0]])
        
        # Добавляем в treeview
        self.systems_tree.insert('', 'end', values=(
            system_name,
            layer_count,
            f"{total_thickness:.1f} мкм",
            f"{total_cost:.2f} руб",
            f"{total_consumption_kg:.3f} кг",
            f"{total_consumption_l:.3f} л"
        ))
        
        # Обновляем поле имени для следующей системы
        self.system_name_entry.delete(0, tk.END)
        self.system_name_entry.insert(0, f"Система {len(self.systems) + 1}")

    def remove_system(self):
        """Удаляет выбранную систему"""
        selected = self.systems_tree.selection()
        if not selected:
            messagebox.showwarning("Предупреждение", "Выберите систему для удаления")
            return
            
        # Получаем индекс выбранной системы
        index = self.systems_tree.index(selected[0])
        
        # Удаляем из всех списков
        self.systems.pop(index)
        self.system_names.pop(index)
        self.systems_tree.delete(selected[0])
        
        # Обновляем имена в поле ввода
        if self.system_names:
            self.system_name_entry.delete(0, tk.END)
            self.system_name_entry.insert(0, f"Система {len(self.systems) + 1}")

    def calculate_system_parameters(self, system):
        """Рассчитывает основные параметры системы"""
        try:
            # Фильтруем основные слои (исключаем растворители)
            main_layers = [layer for layer in system if 'Разбавитель' not in layer[0] and 'Растворитель' not in layer[0]]
            thinner_layers = [layer for layer in system if 'Разбавитель' in layer[0] or 'Растворитель' in layer[0]]
            
            # Основные параметры с проверкой на None
            total_cost = sum(layer[self.COST] if layer[self.COST] is not None else 0 for layer in system)  # Стоимость всех слоев
            total_dry_thickness = sum(layer[self.DRY_THICKNESS] if layer[self.DRY_THICKNESS] is not None else 0 for layer in main_layers)
            total_theor_consumption_kg = sum(layer[self.THEOR_CONSUMPTION_KG] if layer[self.THEOR_CONSUMPTION_KG] is not None else 0 for layer in main_layers)
            total_pract_consumption_kg = sum(layer[self.PRACT_CONSUMPTION_KG] if layer[self.PRACT_CONSUMPTION_KG] is not None else 0 for layer in main_layers)
            
            # Расчет расхода в литрах с проверкой на ноль
            total_theor_consumption_l = 0
            for layer in main_layers:
                if layer[self.DENSITY] and layer[self.DENSITY] > 0 and layer[self.THEOR_CONSUMPTION_KG] is not None:  # Плотность и расход не None
                    total_theor_consumption_l += layer[self.THEOR_CONSUMPTION_KG] / layer[self.DENSITY]
            
            total_pract_consumption_l = 0
            for layer in main_layers:
                if layer[self.DENSITY] and layer[self.DENSITY] > 0 and layer[self.PRACT_CONSUMPTION_KG] is not None:  # Плотность и расход не None
                    total_pract_consumption_l += layer[self.PRACT_CONSUMPTION_KG] / layer[self.DENSITY]
            
            # Стоимость растворителей
            thinner_cost = sum(layer[self.COST] if layer[self.COST] is not None else 0 for layer in thinner_layers)
            
            return {
                'main_layers_count': len(main_layers),
                'thinner_layers_count': len(thinner_layers),
                'total_cost': total_cost or 0,
                'total_dry_thickness': total_dry_thickness or 0,
                'total_theor_consumption_kg': total_theor_consumption_kg or 0,
                'total_pract_consumption_kg': total_pract_consumption_kg or 0,
                'total_theor_consumption_l': total_theor_consumption_l or 0,
                'total_pract_consumption_l': total_pract_consumption_l or 0,
                'thinner_cost': thinner_cost or 0,
                'coating_cost': (total_cost - thinner_cost) or 0,
                'main_layers': main_layers,
                'thinner_layers': thinner_layers
            }
        except Exception as e:
            logging.error(f"Ошибка расчета параметров системы: {e}")
            # Возвращаем значения по умолчанию в случае ошибки
            return {
                'main_layers_count': 0,
                'thinner_layers_count': 0,
                'total_cost': 0,
                'total_dry_thickness': 0,
                'total_theor_consumption_kg': 0,
                'total_pract_consumption_kg': 0,
                'total_theor_consumption_l': 0,
                'total_pract_consumption_l': 0,
                'thinner_cost': 0,
                'coating_cost': 0,
                'main_layers': [],
                'thinner_layers': []
            }

    def compare_systems(self):
        """Сравнивает все добавленные системы"""
        if len(self.systems) < 2:
            messagebox.showwarning("Предупреждение", "Добавьте хотя бы 2 системы для сравнения")
            return
            
        # Сравнение систем
        self.compare_systems_tab()
        
        # Сравнение по слоям
        self.compare_layers_tab()
        
        # Сохраняем в историю сравнений
        self.save_comparison_to_history()

    def save_comparison_to_history(self):
        """Сохраняет текущее сравнение в историю"""
        try:
            # Рассчитываем параметры для всех систем
            system_params = [self.calculate_system_parameters(system) for system in self.systems]
            
            # Находим лучшую систему по стоимости
            costs = [params['total_cost'] for params in system_params]
            best_index = costs.index(min(costs))
            best_system = self.system_names[best_index]
            best_cost = costs[best_index]
            
            # Рассчитываем экономию относительно первой системы
            base_cost = costs[0] if costs else 0
            economy_percent = 0
            if base_cost > 0 and best_index > 0:
                economy_percent = ((base_cost - best_cost) / base_cost) * 100
            
            comparison_results = {
                'best_system': best_system,
                'best_cost': best_cost,
                'economy_percent': economy_percent
            }
            
            # Сохраняем в историю
            self.main_app.history_manager.add_comparison(
                self.systems, self.system_names, comparison_results
            )
            
        except Exception as e:
            logging.error(f"Ошибка сохранения сравнения в историю: {e}")

    def compare_systems_tab(self):
        """Сравнивает системы на вкладке сравнения систем"""
        # Очищаем старую таблицу
        for item in self.comparison_tree.get_children():
            self.comparison_tree.delete(item)
            
        # Настраиваем колонки
        columns = ['Параметр'] + self.system_names
        self.comparison_tree['columns'] = columns
        self.comparison_tree['show'] = 'headings'
        
        # Настраиваем заголовки
        for col in columns:
            self.comparison_tree.heading(col, text=col)
            self.comparison_tree.column(col, width=150)
        
        # Собираем данные по всем системам
        system_params = []
        for system in self.systems:
            system_params.append(self.calculate_system_parameters(system))
        
        # Основные параметры для сравнения
        parameters = [
            ("Количество основных слоев", "main_layers_count", ""),
            ("Количество растворителей", "thinner_layers_count", ""),
            ("Общая толщина покрытия", "total_dry_thickness", " мкм"),
            ("Теоретический расход материалов", "total_theor_consumption_kg", " кг/м²"),
            ("Практический расход материалов", "total_pract_consumption_kg", " кг/м²"),
            ("Теоретический расход (литры)", "total_theor_consumption_l", " л/м²"),
            ("Практический расход (литры)", "total_pract_consumption_l", " л/м²"),
            ("Стоимость покрытий", "coating_cost", " руб/м²"),
            ("Стоимость растворителей", "thinner_cost", " руб/м²"),
            ("ОБЩАЯ СТОИМОСТЬ", "total_cost", " руб/м²")
        ]
        
        # Заполняем таблицу сравнения
        for param_name, param_key, unit in parameters:
            row_data = [param_name + unit]
            for params in system_params:
                value = params.get(param_key, 0)
                if isinstance(value, float):
                    if 'стоимость' in param_name.lower() or 'cost' in param_key:
                        row_data.append(f"{value:.2f}")
                    elif 'расход' in param_name.lower() or 'consumption' in param_key:
                        row_data.append(f"{value:.3f}")
                    elif 'толщина' in param_name.lower() or 'thickness' in param_key:
                        row_data.append(f"{value:.1f}")
                    else:
                        row_data.append(f"{value}")
                else:
                    row_data.append(str(value))
            
            self.comparison_tree.insert('', 'end', values=row_data)
        
        # Добавляем строку с экономией (сравнение с первой системой)
        if len(system_params) > 1:
            base_cost = system_params[0]['total_cost']
            economy_row = ["Экономия относительно Системы 1", "0.00%"]
            
            for i in range(1, len(system_params)):
                current_cost = system_params[i]['total_cost']
                if base_cost > 0:
                    economy = ((base_cost - current_cost) / base_cost) * 100
                    economy_row.append(f"{economy:+.2f}%")
                else:
                    economy_row.append("N/A")
            
            self.comparison_tree.insert('', 'end', values=economy_row)

    def compare_layers_tab(self):
        """Сравнивает системы по слоям на отдельной вкладке"""
        # Очищаем старую таблицу
        for item in self.layers_comparison_tree.get_children():
            self.layers_comparison_tree.delete(item)
            
        # Находим максимальное количество слоев среди всех систем
        max_layers = max(len([layer for layer in system if 'Разбавитель' not in layer[0] and 'Растворитель' not in layer[0]]) 
                        for system in self.systems)
        
        # Создаем колонки: Слой + по колонке для каждой системы
        columns = ['Слой', 'Параметр']
        for system_name in self.system_names:
            columns.extend([f'{system_name}_кг', f'{system_name}_л', f'{system_name}_руб'])
        
        self.layers_comparison_tree['columns'] = columns
        self.layers_comparison_tree['show'] = 'headings'
        
        # Настраиваем заголовки
        for col in columns:
            self.layers_comparison_tree.heading(col, text=col)
            if col in ['Слой', 'Параметр']:
                self.layers_comparison_tree.column(col, width=120)
            else:
                self.layers_comparison_tree.column(col, width=100)
        
        # Собираем данные по слоям для каждой системы
        systems_layers_data = []
        for system in self.systems:
            system_layers_data = []
            main_layers = [layer for layer in system if 'Разбавитель' not in layer[0] and 'Растворитель' not in layer[0]]
            
            for layer in main_layers:
                # Расчет расхода в литрах
                consumption_l = 0.0
                if layer[self.DENSITY] and layer[self.DENSITY] > 0:  # Плотность
                    consumption_l = layer[self.THEOR_CONSUMPTION_KG] / layer[self.DENSITY] if layer[self.THEOR_CONSUMPTION_KG] is not None else 0  # Теоретический расход в л/м²
                
                layer_data = {
                    'name': layer[0],
                    'consumption_kg': layer[self.THEOR_CONSUMPTION_KG] if layer[self.THEOR_CONSUMPTION_KG] is not None else 0,  # Теоретический расход кг/м²
                    'consumption_l': consumption_l,  # Теоретический расход л/м²
                    'cost': layer[self.COST] if layer[self.COST] is not None else 0  # Стоимость на м²
                }
                system_layers_data.append(layer_data)
            
            systems_layers_data.append(system_layers_data)
        
        # Заполняем таблицу сравнения по слоям
        for layer_index in range(max_layers):
            # Инициализируем строки с правильной длиной
            layer_name_row = [''] * len(columns)
            consumption_kg_row = [''] * len(columns)
            consumption_l_row = [''] * len(columns)
            cost_row = [''] * len(columns)
            
            # Заполняем первые два столбца
            layer_name_row[0] = f'Слой {layer_index + 1}'
            layer_name_row[1] = 'Название'
            consumption_kg_row[1] = 'Расход теор. кг/м²'
            consumption_l_row[1] = 'Расход теор. л/м²'
            cost_row[1] = 'Стоимость руб/м²'
            
            col_index = 2
            for system_idx, system_layers in enumerate(systems_layers_data):
                if layer_index < len(system_layers):
                    layer_data = system_layers[layer_index]
                    
                    # Заполняем данные для текущей системы
                    layer_name_row[col_index] = layer_data['name']
                    layer_name_row[col_index + 1] = ''  # Пропускаем колонку литров для названия
                    layer_name_row[col_index + 2] = ''  # Пропускаем колонку рублей для названия
                    
                    consumption_kg_row[col_index] = f"{layer_data['consumption_kg']:.3f}" if layer_data['consumption_kg'] else "0.000"
                    consumption_kg_row[col_index + 1] = ""
                    consumption_kg_row[col_index + 2] = ""
                    
                    consumption_l_row[col_index] = ""
                    consumption_l_row[col_index + 1] = f"{layer_data['consumption_l']:.3f}" if layer_data['consumption_l'] else "0.000"
                    consumption_l_row[col_index + 2] = ""
                    
                    cost_row[col_index] = ""
                    cost_row[col_index + 1] = ""
                    cost_row[col_index + 2] = f"{layer_data['cost']:.2f}" if layer_data['cost'] else "0.00"
                else:
                    # Заполняем пустыми значениями если в системе меньше слоев
                    layer_name_row[col_index] = "-"
                    layer_name_row[col_index + 1] = "-"
                    layer_name_row[col_index + 2] = "-"
                    
                    consumption_kg_row[col_index] = "-"
                    consumption_kg_row[col_index + 1] = "-"
                    consumption_kg_row[col_index + 2] = "-"
                    
                    consumption_l_row[col_index] = "-"
                    consumption_l_row[col_index + 1] = "-"
                    consumption_l_row[col_index + 2] = "-"
                    
                    cost_row[col_index] = "-"
                    cost_row[col_index + 1] = "-"
                    cost_row[col_index + 2] = "-"
                
                col_index += 3
            
            # Вставляем строки в таблицу
            self.layers_comparison_tree.insert('', 'end', values=layer_name_row, tags=('layer_name',))
            self.layers_comparison_tree.insert('', 'end', values=consumption_kg_row)
            self.layers_comparison_tree.insert('', 'end', values=consumption_l_row)
            self.layers_comparison_tree.insert('', 'end', values=cost_row, tags=('cost_row',))
            
            # Добавляем пустую строку для разделения
            if layer_index < max_layers - 1:
                self.layers_comparison_tree.insert('', 'end', values=[''] * len(columns))
        
        # Добавляем итоговую строку
        total_row = ['ИТОГО', '']
        col_index = 2
        
        for system_params in [self.calculate_system_parameters(system) for system in self.systems]:
            total_row.extend([
                f"{system_params['total_theor_consumption_kg']:.3f}" if system_params['total_theor_consumption_kg'] else "0.000",
                f"{system_params['total_theor_consumption_l']:.3f}" if system_params['total_theor_consumption_l'] else "0.000",
                f"{system_params['total_cost']:.2f}" if system_params['total_cost'] else "0.00"
            ])
            col_index += 3
        
        self.layers_comparison_tree.insert('', 'end', values=total_row, tags=('total_row',))
        
        # Настраиваем теги для стилизации
        self.layers_comparison_tree.tag_configure('layer_name', background='lightblue')
        self.layers_comparison_tree.tag_configure('cost_row', background='lightyellow')
        self.layers_comparison_tree.tag_configure('total_row', background='lightgreen', font=('Arial', 9, 'bold'))

    def export_comparison(self):
        """Экспортирует сравнение систем в Excel в формате основного экспорта"""
        if len(self.systems) < 2:
            messagebox.showwarning("Предупреждение", "Нет данных для экспорта")
            return
            
        try:
            wb = Workbook()
            
            # Лист сравнения систем (основной)
            ws_systems = wb.active
            ws_systems.title = "Сравнение систем"
            
            # Создаем заголовки как в основном экспорте
            self.create_comparison_header(ws_systems)
            
            # Записываем данные сравнения
            self.export_systems_comparison_data(ws_systems)
            
            # Лист сравнения по слоям
            ws_layers = wb.create_sheet("Сравнение по слоям")
            self.create_layers_comparison_header(ws_layers)
            self.export_layers_comparison_data(ws_layers)
            
            # Сохраняем файл
            file_path = filedialog.asksaveasfilename(
                defaultextension='.xlsx',
                filetypes=[("Excel files", "*.xlsx")],
                title="Сохранить сравнение систем"
            )
            
            if file_path:
                wb.save(file_path)
                messagebox.showinfo("Успех", "Сравнение систем экспортировано в Excel!")
                
        except Exception as e:
            messagebox.showerror("Ошибка", f"Ошибка при экспорте: {str(e)}")

    def create_comparison_header(self, ws):
        """Создает заголовки для сравнения систем в стиле основного экспорта"""
        # Заголовок документа
        ws['A1'] = "СРАВНЕНИЕ СИСТЕМ ПОКРЫТИЙ"
        ws['A1'].font = Font(bold=True, size=14)
        ws.merge_cells('A1:H1')
        
        # Дата создания
        ws['A2'] = f"Дата создания: {datetime.now().strftime('%Y-%m-%d %H:%M')}"
        ws.merge_cells('A2:H2')
        
        # Основные заголовки таблицы
        headers = [
            'Система',
            'Кол-во слоев',
            'Толщина покрытия',
            'Расход теор. кг/м²',
            'Расход теор. л/м²', 
            'Расход практ. кг/м²',
            'Расход практ. л/м²',
            'Общая стоимость руб/м²',
            'Стоимость покрытий',
            'Стоимость растворителей',
            'Экономия относительно базовой %'
        ]
        
        # Записываем заголовки
        for col, header in enumerate(headers, 1):
            cell = ws.cell(row=4, column=col)
            cell.value = header
            cell.font = Font(bold=True)
            cell.border = Border(left=Side(style='thin'), right=Side(style='thin'),
                            top=Side(style='thin'), bottom=Side(style='thin'))
            cell.alignment = Alignment(horizontal='center', vertical='center', wrap_text=True)
            cell.fill = PatternFill(start_color="E6E6FA", end_color="E6E6FA", fill_type="solid")

    def export_systems_comparison_data(self, ws):
        """Экспортирует данные сравнения систем с правильным форматом растворителей"""
        system_params = [self.calculate_system_parameters(system) for system in self.systems]
        
        # Базовые параметры для расчета экономии
        base_cost = system_params[0]['total_cost'] if system_params else 0
        
        # Записываем данные по системам
        current_row = 5
        for i, (system_name, params) in enumerate(zip(self.system_names, system_params)):
            # Расчет экономии относительно первой системы
            economy = 0
            if i > 0 and base_cost > 0:
                economy = ((base_cost - params['total_cost']) / base_cost) * 100
            
            row_data = [
                system_name,
                params['main_layers_count'],
                self.round_value(params['total_dry_thickness']),
                self.round_value(params['total_theor_consumption_kg']),
                self.round_value(params['total_theor_consumption_l']),
                self.round_value(params['total_pract_consumption_kg']),
                self.round_value(params['total_pract_consumption_l']),
                self.round_value(params['total_cost']),
                self.round_value(params['coating_cost']),
                self.round_value(params['thinner_cost']),
                economy if i > 0 else 0
            ]
            
            # Записываем строку
            for col, value in enumerate(row_data, 1):
                cell = ws.cell(row=current_row, column=col)
                cell.value = value
                
                # Форматирование чисел
                if col in [3, 4, 5, 6]:  # Расходы и толщина
                    cell.number_format = '0.000'
                elif col in [7, 8, 9]:  # Стоимости
                    cell.number_format = '#,##0.00'
                elif col == 11:  # Экономия в %
                    cell.number_format = '0.00%'
                
                cell.border = Border(left=Side(style='thin'), right=Side(style='thin'),
                                top=Side(style='thin'), bottom=Side(style='thin'))
                cell.alignment = Alignment(horizontal='center', vertical='center', wrap_text=True)
            
            current_row += 1
        
        # Добавляем детали по слоям на отдельный лист или в дополнительную секцию
        self.export_layers_details(ws, current_row + 2, system_params)

    def export_layers_details(self, ws, start_row, system_params):
        """Экспортирует детали по слоям с правильным форматом растворителей"""
        current_row = start_row
        
        # Заголовок для деталей
        ws.cell(row=current_row, column=1).value = "ДЕТАЛИ СЛОЕВ И РАСТВОРИТЕЛЕЙ"
        ws.cell(row=current_row, column=1).font = Font(bold=True)
        ws.merge_cells(f'A{current_row}:K{current_row}')
        current_row += 1
        
        # Заголовки таблицы деталей
        detail_headers = ['Система', 'Тип', 'Название', 'Расход кг/м²', 'Расход л/м²', 'Стоимость руб/м²']
        for col, header in enumerate(detail_headers, 1):
            cell = ws.cell(row=current_row, column=col)
            cell.value = header
            cell.font = Font(bold=True)
            cell.fill = PatternFill(start_color="E6E6FA", end_color="E6E6FA", fill_type="solid")
        current_row += 1
        
        # Данные по слоям и растворителям
        for i, (system_name, params) in enumerate(zip(self.system_names, system_params)):
            # Основные слои
            for layer in params['main_layers']:
                row_data = [
                    system_name,
                    'Покрытие',
                    layer[self.NAME],
                    self.round_value(layer[self.THEOR_CONSUMPTION_KG]),
                    self.round_value(layer[self.THEOR_CONSUMPTION_KG] / layer[self.DENSITY] if layer[self.DENSITY] and layer[self.DENSITY] > 0 else 0),
                    self.round_value(layer[self.COST])
                ]
                
                for col, value in enumerate(row_data, 1):
                    ws.cell(row=current_row, column=col).value = value
                current_row += 1
            
            # Растворители - используем новый формат
            for thinner in params['thinner_layers']:
                display_name = self.format_thinner_for_export(thinner[self.NAME])
                row_data = [
                    system_name,
                    'Растворитель',
                    display_name,  # "Разбавитель Ксилол 5% для Бланк"
                    self.round_value(thinner[self.THEOR_CONSUMPTION_KG]),
                    self.round_value(thinner[self.THEOR_CONSUMPTION_KG] / thinner[self.DENSITY] if thinner[self.DENSITY] and thinner[self.DENSITY] > 0 else 0),
                    self.round_value(thinner[self.COST])
                ]
                
                for col, value in enumerate(row_data, 1):
                    ws.cell(row=current_row, column=col).value = value
                current_row += 1
            
            # Пустая строка между системами
            current_row += 1

    def format_thinner_for_export(self, thinner_full_name):
        """Форматирует название растворителя для экспорта в формате: Разбавитель [Название растворителя] [процент] для [Название слоя]"""
        try:
            # Убираем лишние пробелы
            thinner_full_name = thinner_full_name.strip()
            
            # Формат: "Растворитель Бланк (Ксилол 5%)"
            if '(' in thinner_full_name and ')' in thinner_full_name:
                # Извлекаем части
                main_part = thinner_full_name.split('(')[0].strip()  # "Растворитель Бланк"
                bracket_part = thinner_full_name.split('(')[1].split(')')[0].strip()  # "Ксилол 5%"
                
                # Разбираем скобочную часть
                bracket_parts = bracket_part.split()
                if len(bracket_parts) >= 2:
                    thinner_name = bracket_parts[0]  # "Ксилол"
                    percentage = bracket_parts[1]    # "5%"
                    
                    # Извлекаем название родительского слоя
                    parent_name = main_part.replace('Растворитель', '').replace('Разбавитель', '').strip()
                    
                    # Форматируем для экспорта: "Разбавитель Ксилол 5% для Бланк"
                    return f"Разбавитель {thinner_name} {percentage} для {parent_name}"
            
            # Формат: "Растворитель Бланк 5%"
            elif 'Растворитель' in thinner_full_name or 'Разбавитель' in thinner_full_name:
                # Убираем ключевые слова
                clean_name = thinner_full_name.replace('Растворитель', '').replace('Разбавитель', '').strip()
                
                # Разделяем на части
                parts = clean_name.split()
                if len(parts) >= 2:
                    # Предполагаем, что последняя часть - это процент
                    percentage = parts[-1]
                    parent_name = ' '.join(parts[:-1])
                    
                    # Если процент не содержит %, добавляем его
                    if '%' not in percentage:
                        percentage += '%'
                    
                    # Ищем название растворителя в базе данных
                    thinner_real_name = self.extract_thinner_real_name(thinner_full_name)
                    
                    return f"Разбавитель {thinner_real_name} {percentage} для {parent_name}"
            
            # Если не удалось разобрать, возвращаем исходное название
            return thinner_full_name
            
        except Exception as e:
            logging.error(f"Ошибка форматирования растворителя для экспорта: {e}")
            return thinner_full_name

    def extract_thinner_real_name(self, thinner_full_name):
        """Извлекает настоящее название растворителя из полного имени"""
        try:
            # Формат: "Растворитель Бланк (Ксилол 5%)"
            if '(' in thinner_full_name and ')' in thinner_full_name:
                bracket_content = thinner_full_name.split('(')[1].split(')')[0]
                thinner_name = bracket_content.split()[0]
                return thinner_name
            
            # Формат: "Растворитель Бланк 5%"
            else:
                # Пытаемся найти растворитель в базе данных по имени родительского слоя
                parent_name = self.extract_parent_name_from_thinner(thinner_full_name)
                if parent_name:
                    # Ищем родительский слой
                    for system in self.systems:
                        for layer in system:
                            if (layer[self.NAME] == parent_name and 
                                'Разбавитель' not in layer[self.NAME] and 
                                'Растворитель' not in layer[self.NAME]):
                                # Предполагаем, что используется стандартный растворитель
                                return "Ксилол"  # или другое значение по умолчанию
                
            return "Растворитель"  # значение по умолчанию
            
        except Exception as e:
            logging.error(f"Ошибка извлечения названия растворителя: {e}")
            return "Растворитель"

    def create_layers_comparison_header(self, ws):
        """Создает заголовки для сравнения по слоям"""
        ws['A1'] = "СРАВНЕНИЕ СИСТЕМ ПО СЛОЯМ"
        ws['A1'].font = Font(bold=True, size=14)
        ws.merge_cells('A1:Z1')
        
        # Заголовки для каждого типа данных
        base_headers = ['Слой', 'Параметр']
        
        # Добавляем колонки для каждой системы
        all_headers = base_headers.copy()
        for system_name in self.system_names:
            all_headers.extend([
                f'{system_name} (кг/м²)',
                f'{system_name} (л/м²)', 
                f'{system_name} (руб/м²)'
            ])
        
        # Записываем заголовки
        for col, header in enumerate(all_headers, 1):
            cell = ws.cell(row=3, column=col)
            cell.value = header
            cell.font = Font(bold=True)
            cell.border = Border(left=Side(style='thin'), right=Side(style='thin'),
                            top=Side(style='thin'), bottom=Side(style='thin'))
            cell.alignment = Alignment(horizontal='center', vertical='center', wrap_text=True)
            cell.fill = PatternFill(start_color="E6E6FA", end_color="E6E6FA", fill_type="solid")

    def export_layers_comparison_data(self, ws):
        """Экспортирует данные сравнения по слоям"""
        # Находим максимальное количество слоев
        max_layers = max(len([layer for layer in system if 'Разбавитель' not in layer[0] and 'Растворитель' not in layer[0]]) 
                        for system in self.systems)
        
        # Собираем данные по слоям
        systems_layers_data = []
        for system in self.systems:
            system_layers_data = []
            main_layers = [layer for layer in system if 'Разбавитель' not in layer[0] and 'Растворитель' not in layer[0]]
            
            for layer in main_layers:
                consumption_l = 0.0
                if layer[self.DENSITY] and layer[self.DENSITY] > 0:
                    consumption_l = layer[self.THEOR_CONSUMPTION_KG] / layer[self.DENSITY] if layer[self.THEOR_CONSUMPTION_KG] is not None else 0
                
                layer_data = {
                    'name': layer[0],
                    'consumption_kg': layer[self.THEOR_CONSUMPTION_KG] if layer[self.THEOR_CONSUMPTION_KG] is not None else 0,
                    'consumption_l': consumption_l,
                    'cost': layer[self.COST] if layer[self.COST] is not None else 0
                }
                system_layers_data.append(layer_data)
            
            systems_layers_data.append(system_layers_data)
        
        # Записываем данные
        current_row = 4
        for layer_index in range(max_layers):
            # Строка с названием слоя
            name_row = [''] * (2 + len(self.systems) * 3)  # 2 базовых + по 3 колонки на систему
            name_row[0] = f'Слой {layer_index + 1}'
            name_row[1] = 'Название'
            
            # Строки с данными
            kg_row = [''] * (2 + len(self.systems) * 3)
            kg_row[1] = 'Расход теор. кг/м²'
            
            l_row = [''] * (2 + len(self.systems) * 3)
            l_row[1] = 'Расход теор. л/м²'
            
            cost_row = [''] * (2 + len(self.systems) * 3)
            cost_row[1] = 'Стоимость руб/м²'
            
            # Заполняем данные для каждой системы
            col_index = 2
            for system_layers in systems_layers_data:
                if layer_index < len(system_layers):
                    layer_data = system_layers[layer_index]
                    name_row[col_index] = layer_data['name']
                    kg_row[col_index] = self.round_value(layer_data['consumption_kg'])
                    l_row[col_index + 1] = self.round_value(layer_data['consumption_l'])
                    cost_row[col_index + 2] = self.round_value(layer_data['cost'])
                else:
                    name_row[col_index] = "-"
                    kg_row[col_index] = "-"
                    l_row[col_index + 1] = "-"
                    cost_row[col_index + 2] = "-"
                
                col_index += 3
            
            # Записываем строки
            for row_data in [name_row, kg_row, l_row, cost_row]:
                for col, value in enumerate(row_data, 1):
                    cell = ws.cell(row=current_row, column=col)
                    cell.value = value
                    cell.border = Border(left=Side(style='thin'), right=Side(style='thin'),
                                    top=Side(style='thin'), bottom=Side(style='thin'))
                    cell.alignment = Alignment(horizontal='center', vertical='center', wrap_text=True)
                
                current_row += 1
            
            # Пустая строка между слоями
            current_row += 1
        
        # Итоговая строка
        total_row = ['ИТОГО', '']
        for system_params in [self.calculate_system_parameters(system) for system in self.systems]:
            total_row.extend([
                self.round_value(system_params['total_theor_consumption_kg']),
                self.round_value(system_params['total_theor_consumption_l']),
                self.round_value(system_params['total_cost'])
            ])
        
        # Записываем итоговую строку
        for col, value in enumerate(total_row, 1):
            cell = ws.cell(row=current_row, column=col)
            cell.value = value
            cell.font = Font(bold=True)
            cell.fill = PatternFill(start_color="C6EFCE", end_color="C6EFCE", fill_type="solid")
            cell.border = Border(left=Side(style='thin'), right=Side(style='thin'),
                            top=Side(style='thin'), bottom=Side(style='thin'))
            cell.alignment = Alignment(horizontal='center', vertical='center', wrap_text=True)
        
        # Настройка ширины столбцов
        ws.column_dimensions['A'].width = 15
        ws.column_dimensions['B'].width = 20
        for i in range(3, len(total_row) + 1):
            ws.column_dimensions[get_column_letter(i)].width = 15

    def round_value(self, value):
        """Округляет значение до 3 знаков после запятой"""
        if value is None:
            return 0.0
        try:
            return round(float(value), 3)
        except (ValueError, TypeError):
            return 0.0

class ExcelExporterApp:
    """Основной класс приложения для расчета и экспорта систем покрытий"""
    # Константы для индексов полей слоя (16 полей)
    NAME = 0
    BINDER = 1
    RAL = 2
    DENSITY = 3
    SOLID_CONTENT = 4
    WET_THICKNESS = 5
    DRY_THICKNESS = 6
    THEOR_COVERING = 7  # Укрывистость теоретическая (м²/л)
    LOSSES = 8
    PRACT_COVERING = 9  # Укрывистость практическая (м²/л)
    PRICE_KG = 10
    PRICE_LITER = 11
    THEOR_CONSUMPTION_KG = 12
    PRACT_CONSUMPTION_KG = 13
    COST = 14
    THINNER_PERCENT = 15  # Процент разбавителя
    
    # Новое поле для хранения расхода растворителя в л/м²
    THINNER_CONSUMPTION_L = 16  # Добавляем дополнительное поле
      
    def __init__(self, master):
        self.master = master
        self.master.title("Калькулятор покрытий")
        
        # Инициализируем менеджер истории
        self.history_manager = HistoryManager(self)
        
        # Добавляем поле для ввода площади
        self.area_frame = ttk.Frame(self.master)
        self.area_frame.pack(pady=5)
        ttk.Label(self.area_frame, text="Площадь (м2):").pack(side=tk.LEFT, padx=5)
        self.area_entry = ttk.Entry(self.area_frame)
        self.area_entry.pack(side=tk.LEFT, padx=5)
        self.area_entry.insert(0, "1")  # Значение по умолчанию
        
            # Привязываем событие изменения площади к обновлению информации
        self.area_entry.bind('<KeyRelease>', lambda e: self.auto_update_display())

        # Инициализируем список слоев
        self.layers = []
        
        # Инициализируем базу данных
        self.db = DatabaseManager()
        
        self.create_widgets()

    def auto_update_display(self):
        """Автоматическое обновление отображения при изменении площади"""
        try:
            # Проверяем, что введено корректное число
            area_text = self.area_entry.get().strip()
            if area_text:  # Если поле не пустое
                float(area_text)  # Проверяем, что это число
                self.update_total_cost_display()
        except ValueError:
            # Если введено не число, не обновляем
            pass        

    def load_system_from_comparison(self, system_data):
        """Загружает систему из истории сравнений в основной расчет"""
        # Очищаем текущие слои
        self.layers = []
        
        # Восстанавливаем слои из данных сравнения
        for layer_data in system_data['layers']:
            # Создаем слой в формате основного приложения
            layer = [
                layer_data['name'],
                layer_data['binder'],
                layer_data['ral'],
                layer_data['density'],
                layer_data['solid_content'],
                layer_data['wet_thickness'],
                layer_data['dry_thickness'],
                layer_data['theor_covering'],
                layer_data['losses'],
                layer_data['pract_covering'],
                layer_data['price_kg'],
                layer_data['price_liter'],
                layer_data['theor_consumption_kg'],
                layer_data['pract_consumption_kg'],
                layer_data['cost'],
                layer_data['thinner_percent']
            ]
            
            # Пересчитываем слой (на случай, если нужны дополнительные расчеты)
            layer = self.update_layer_calculations(layer)
            self.layers.append(layer)
        
        # Обновляем интерфейс
        self.create_layer_table()
        self.update_total_cost_display()
        
        messagebox.showinfo("Успех", f"Система '{system_data['name']}' загружена в расчет!")

    def load_calculation_from_history(self, calculation):
        """Загружает расчет из истории в основной редактор"""
        # Очищаем текущие слои
        self.layers = []
        
        # Восстанавливаем слои из истории
        for layer_data in calculation['layers']:
            # Ищем покрытие в базе данных по названию
            db_coating = self.db.get_coating_by_name(layer_data['name'])
            
            if db_coating:
                # Используем данные из базы, но сохраняем толщину и расчеты из истории
                layer = [
                    db_coating[1],  # name
                    db_coating[2],  # binder
                    db_coating[3],  # ral
                    db_coating[4],  # density
                    db_coating[5],  # solid_content
                    0.0,  # wet_thickness (будет пересчитано)
                    layer_data['dry_thickness'],  # dry_thickness из истории
                    0.0,  # theor_covering (будет пересчитано)
                    0.0,  # losses (будет установлено позже)
                    0.0,  # pract_covering (будет пересчитано)
                    db_coating[6],  # price_kg
                    db_coating[7],  # price_liter
                    0.0,  # theor_consumption_kg (будет пересчитано)
                    0.0,  # pract_consumption_kg (будет пересчитано)
                    0.0,  # cost (будет пересчитано)
                    0.0   # thinner_percent
                ]
            else:
                # Если покрытие не найдено в базе, создаем на основе данных из истории
                layer = [
                    layer_data['name'],
                    layer_data['binder'],
                    layer_data['ral'],
                    1.0,  # density по умолчанию
                    100.0,  # solid_content по умолчанию
                    0.0,  # wet_thickness
                    layer_data['dry_thickness'],
                    0.0,  # theor_covering
                    10.0,  # losses по умолчанию
                    0.0,  # pract_covering
                    0.0,  # price_kg
                    0.0,  # price_liter
                    0.0,  # theor_consumption_kg
                    0.0,  # pract_consumption_kg
                    0.0,  # cost
                    0.0   # thinner_percent
                ]
            
            # Пересчитываем слой
            layer = self.update_layer_calculations(layer)
            self.layers.append(layer)
        
        # Обновляем интерфейс
        self.create_layer_table()
        self.update_total_cost_display()
        
        messagebox.showinfo("Успех", f"Расчет от {calculation['date_display']} загружен в редактор!")

    def round_value(self, value):
        """Округляет значение математически до 3 знаков после запятой"""
        if value is None:
            return 0.0
        try:
            return round(float(value), 3)
        except (ValueError, TypeError):
            return 0.0
        
    def calculate_total_cost(self):
        """Рассчитывает общую стоимость всех слоев на 1 кв.м."""
        total_cost = 0.0
        for layer in self.layers:
            total_cost += layer[self.COST] if layer[self.COST] is not None else 0  # Стоимость с учетом потерь
        return self.round_value(total_cost)
    
    def calculate_total_theor_cost(self):
        """Рассчитывает общую стоимость всех слоев на 1 кв.м. без учета потерь"""
        total_cost = 0.0
        for layer in self.layers:
            # Для всех слоев (включая растворители) рассчитываем стоимость по теоретическому расходу
            if layer[self.THEOR_CONSUMPTION_KG] is not None and layer[self.PRICE_KG] is not None:
                theor_cost = layer[self.THEOR_CONSUMPTION_KG] * layer[self.PRICE_KG]
                total_cost += theor_cost
        return self.round_value(total_cost)


    
    def calculate_total_dry_thickness(self):
        """Рассчитывает общую толщину покрытия (только основные слои)"""
        total_thickness = 0.0
        for layer in self.layers:
            if 'Разбавитель' not in layer[self.NAME] and 'Растворитель' not in layer[self.NAME]:
                total_thickness += layer[self.DRY_THICKNESS] if layer[self.DRY_THICKNESS] is not None else 0
        return self.round_value(total_thickness)
    
    def calculate_total_theor_consumption_kg(self):
        """Рассчитывает общий теоретический расход материалов (кг/м²)"""
        total_consumption = 0.0
        for layer in self.layers:
            if 'Разбавитель' not in layer[self.NAME] and 'Растворитель' not in layer[self.NAME]:
                total_consumption += layer[self.THEOR_CONSUMPTION_KG] if layer[self.THEOR_CONSUMPTION_KG] is not None else 0
        return self.round_value(total_consumption)
    
    def calculate_total_theor_consumption_l(self):
        """Рассчитывает общий теоретический расход материалов (л/м²)"""
        total_consumption = 0.0
        for layer in self.layers:
            if 'Разбавитель' not in layer[self.NAME] and 'Растворитель' not in layer[self.NAME]:
                # ДОБАВИТЬ проверку на ноль:
                if layer[self.DENSITY] and layer[self.DENSITY] > 0 and layer[self.THEOR_CONSUMPTION_KG] is not None:
                    consumption_l = layer[self.THEOR_CONSUMPTION_KG] / layer[self.DENSITY]
                    total_consumption += consumption_l
        return self.round_value(total_consumption)

    def calculate_total_pract_consumption_kg(self):
        """Рассчитывает общий практический расход материалов (кг/м²) с учетом потерь"""
        total_consumption = 0.0
        for layer in self.layers:
            if 'Разбавитель' not in layer[self.NAME] and 'Растворитель' not in layer[self.NAME]:
                total_consumption += layer[self.PRACT_CONSUMPTION_KG] if layer[self.PRACT_CONSUMPTION_KG] is not None else 0
        return self.round_value(total_consumption)

    def calculate_total_pract_consumption_l(self):
            """Рассчитывает общий практический расход материалов (л/м²) с учетом потерь"""
            total_consumption = 0.0
            for layer in self.layers:
                if 'Разбавитель' not in layer[self.NAME] and 'Растворитель' not in layer[self.NAME]:
                    if layer[self.DENSITY] and layer[self.DENSITY] > 0 and layer[self.PRACT_CONSUMPTION_KG] is not None:
                        consumption_l = layer[self.PRACT_CONSUMPTION_KG] / layer[self.DENSITY]
                        total_consumption += consumption_l
            return self.round_value(total_consumption)        
        
    def calculate_total_theor_material_kg(self, area):
        """Рассчитывает общее количество материала в кг на заданную площадь без учета потерь"""
        total_material = 0.0
        for layer in self.layers:
            if 'Разбавитель' not in layer[self.NAME] and 'Растворитель' not in layer[self.NAME]:
                if layer[self.THEOR_CONSUMPTION_KG] is not None:
                    total_material += layer[self.THEOR_CONSUMPTION_KG] * area
        return self.round_value(total_material)
    
    def calculate_total_theor_material_l(self, area):
        """Рассчитывает общее количество материала в л на заданную площадь без учета потерь"""
        total_material = 0.0
        for layer in self.layers:
            if 'Разбавитель' not in layer[self.NAME] and 'Растворитель' not in layer[self.NAME]:
                if layer[self.DENSITY] and layer[self.DENSITY] > 0 and layer[self.THEOR_CONSUMPTION_KG] is not None:
                    consumption_l = layer[self.THEOR_CONSUMPTION_KG] / layer[self.DENSITY]
                    total_material += consumption_l * area
        return self.round_value(total_material)



    def calculate_total_material_kg(self, area):
        """Рассчитывает общее количество материала в кг на заданную площадь"""
        total_material = 0.0
        for layer in self.layers:
            if 'Разбавитель' not in layer[self.NAME] and 'Растворитель' not in layer[self.NAME]:
                if layer[self.PRACT_CONSUMPTION_KG] is not None:
                    total_material += layer[self.PRACT_CONSUMPTION_KG] * area
        return self.round_value(total_material)
    
    def calculate_total_material_l(self, area):
        """Рассчитывает общее количество материала в л на заданную площадь"""
        total_material = 0.0
        for layer in self.layers:
            if 'Разбавитель' not in layer[self.NAME] and 'Растворитель' not in layer[self.NAME]:
                if layer[self.DENSITY] and layer[self.DENSITY] > 0 and layer[self.PRACT_CONSUMPTION_KG] is not None:
                    consumption_l = layer[self.PRACT_CONSUMPTION_KG] / layer[self.DENSITY]
                    total_material += consumption_l * area
        return self.round_value(total_material)





    def update_total_cost_display(self):
        """Обновляет отображение общей стоимости и других параметров БЕЗ автоматического сохранения в историю"""
        total_cost = self.calculate_total_cost()
        total_theor_cost = self.calculate_total_theor_cost()
        total_thickness = self.calculate_total_dry_thickness()
        total_consumption_kg = self.calculate_total_theor_consumption_kg()
        total_consumption_l = self.calculate_total_theor_consumption_l()
        
        # Практические расходы и количество на площадь
        total_pract_consumption_kg = self.calculate_total_pract_consumption_kg()
        total_pract_consumption_l = self.calculate_total_pract_consumption_l()
        
        # Получаем площадь
        try:
            area_text = self.area_entry.get().strip()
            area = float(area_text) if area_text else 1.0
        except ValueError:
            area = 1.0
            
        # Количество материалов с учетом потерь
        total_material_kg = self.calculate_total_material_kg(area)
        total_material_l = self.calculate_total_material_l(area)
        
        # Количество материалов без учета потерь
        total_theor_material_kg = self.calculate_total_theor_material_kg(area)
        total_theor_material_l = self.calculate_total_theor_material_l(area)
        
        # НОВОЕ: Получаем параметры первого основного слоя для отображения
        main_layer_params = self.get_main_layer_parameters()
        
        # ОБНОВЛЕННЫЙ ТЕКСТ С ВСЕМИ ПАРАМЕТРАМИ
        display_text = (
            f"СТОИМОСТЬ:\n"
            f"• С учетом потерь: {total_cost:.2f} руб/м²\n"
            f"• Без учета потерь: {total_theor_cost:.2f} руб/м²\n"
            f"\nОСНОВНЫЕ ПАРАМЕТРЫ:\n"
            f"• Толщина покрытия: {total_thickness:.1f} мкм\n"
        )
        
        # Добавляем плотность и сухой остаток, если есть основные слои
        #if main_layer_params:
        #    display_text += (
        #        f"• Плотность материала: {main_layer_params['density']:.3f} кг/л\n"
        #       f"• Сухой остаток материала: {main_layer_params['solid_content']:.1f}%\n"
        #    )
        
        display_text += (
            f"\nРАСХОД НА 1 М²:\n"
            f"• Теоретический: {total_consumption_kg:.3f} кг/м² ({total_consumption_l:.3f} л/м²)\n"
            f"• С учетом потерь: {total_pract_consumption_kg:.3f} кг/м² ({total_pract_consumption_l:.3f} л/м²)\n"
            f"\nОБЩЕЕ КОЛИЧЕСТВО НА {area:.1f} М²:\n"
            f"• Без потерь: {total_theor_material_kg:.3f} кг ({total_theor_material_l:.3f} л)\n"
            f"• С учетом потерь: {total_material_kg:.3f} кг ({total_material_l:.3f} л)"
        )
        
        self.total_cost_label.config(text=display_text)

    def get_main_layer_parameters(self):
        """Возвращает параметры первого основного слоя для отображения"""
        for layer in self.layers:
            if ('Разбавитель' not in layer[self.NAME] and 
                'Растворитель' not in layer[self.NAME] and
                layer[self.DENSITY] is not None and
                layer[self.SOLID_CONTENT] is not None):
                return {
                    'density': layer[self.DENSITY],
                    'solid_content': layer[self.SOLID_CONTENT]
                }
        return None        

    def save_to_history(self):
        """Явное сохранение текущего расчета в историю"""
        if self.layers:
            total_cost = self.calculate_total_cost()
            total_theor_cost = self.calculate_total_theor_cost()
            total_thickness = self.calculate_total_dry_thickness()
            total_consumption_kg = self.calculate_total_theor_consumption_kg()
            total_consumption_l = self.calculate_total_theor_consumption_l()
            total_pract_consumption_kg = self.calculate_total_pract_consumption_kg()
            total_pract_consumption_l = self.calculate_total_pract_consumption_l()
            
            # Получаем площадь для сохранения количества материалов
            try:
                area_text = self.area_entry.get().strip()
                area = float(area_text) if area_text else 1.0
            except ValueError:
                area = 1.0
                
            total_theor_material_kg = self.calculate_total_theor_material_kg(area)
            total_theor_material_l = self.calculate_total_theor_material_l(area)
            total_material_kg = self.calculate_total_material_kg(area)
            total_material_l = self.calculate_total_material_l(area)
            
            # Проверяем, не является ли этот расчет дубликатом последнего
            history = self.history_manager.get_calculation_history()
            if history:
                last_calc = history[-1]
                # Сравниваем с последней записью (допустимая разница 0.01%)
                if (abs(last_calc['total_cost'] - total_cost) < 0.01 and
                    abs(last_calc['total_thickness'] - total_thickness) < 0.01 and
                    abs(last_calc['total_consumption_kg'] - total_consumption_kg) < 0.001):
                    return  # Пропускаем дубликат
            
            # Обновляем запись истории, чтобы включить все новые параметры
            calculation = {
                'timestamp': datetime.now().isoformat(),
                'date_display': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'layers_count': len([layer for layer in self.layers if 'Разбавитель' not in layer[0] and 'Растворитель' not in layer[0]]),
                'total_cost': total_cost,
                'total_theor_cost': total_theor_cost,
                'total_thickness': total_thickness,
                'total_consumption_kg': total_consumption_kg,
                'total_consumption_l': total_consumption_l,
                'total_pract_consumption_kg': total_pract_consumption_kg,
                'total_pract_consumption_l': total_pract_consumption_l,
                'area': area,  # НОВОЕ: сохраняем площадь
                'total_theor_material_kg': total_theor_material_kg,  # НОВОЕ
                'total_theor_material_l': total_theor_material_l,    # НОВОЕ
                'total_material_kg': total_material_kg,              # НОВОЕ
                'total_material_l': total_material_l,                # НОВОЕ
                'layer_names': [layer[0] for layer in self.layers if 'Разбавитель' not in layer[0] and 'Растворитель' not in layer[0]],
                'layers': [
                    {
                        'name': layer[0],
                        'binder': layer[1],
                        'ral': layer[2],
                        'dry_thickness': layer[6] if layer[6] is not None else 0,
                        'theor_consumption_kg': layer[12] if layer[12] is not None else 0,
                        'pract_consumption_kg': layer[13] if layer[13] is not None else 0,
                        'theor_consumption_l': layer[12] / layer[3] if layer[3] and layer[3] > 0 and layer[12] is not None else 0,
                        'pract_consumption_l': layer[13] / layer[3] if layer[3] and layer[3] > 0 and layer[13] is not None else 0,
                        'cost': layer[14] if layer[14] is not None else 0,
                        'theor_cost': (layer[12] * layer[10]) if layer[12] is not None and layer[10] is not None else 0
                    }
                    for layer in self.layers if 'Разбавитель' not in layer[0] and 'Растворитель' not in layer[0]
                ]
            }
            
            self.history_manager.calculation_history.append(calculation)
            
            # Ограничиваем историю последними 50 записями
            if len(self.history_manager.calculation_history) > 50:
                self.history_manager.calculation_history = self.history_manager.calculation_history[-50:]
            
            self.history_manager.save_history()
            messagebox.showinfo("Успех", "Расчет сохранен в историю!")


    def open_database(self):
        """Открывает диалоговое окно базы данных"""
        try:
            CoatingDatabaseDialog(self.master)  # Открываем диалог базы данных
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось открыть базу данных: {str(e)}")
            
    def open_system_comparison(self):
        """Открывает диалог сравнения систем покрытий"""
        try:
            SystemComparisonDialog(self.master, self)
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось открыть сравнение систем: {str(e)}")
            
    def open_calculation_history(self):
        """Открывает диалог истории расчетов"""
        try:
            CalculationHistoryDialog(self.master, self.history_manager, self,)
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось открыть историю расчетов: {str(e)}")
    
    def open_comparison_history(self):
        """Открывает диалог истории сравнений"""
        try:
            ComparisonHistoryDialog(self.master, self.history_manager)
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось открыть историю сравнений: {str(e)}")

    def show_about(self):
        """Показывает информацию о программе"""
        about_info = f"""
Калькулятор лакокрасочных материалов (ЛКМ)


Автор: Веселов Е.В.
Контакты: evv@spkeffa.ru +79829059348


Программа предназначена для расчета:
- Расхода лакокрасочных материалов
- Стоимости покрытий
- Толщины покрытий
- Теоретического и практического расхода

Функционал пополняется
"""
        messagebox.showinfo("О программе", about_info)
            
    def update_layer_calculations(self, layer):
        """
        Полностью пересчитывает ВСЕ значения слоя с правильными формулами
        Укрывистость в м²/л (обратная величина расходу)
        С правильным расчетом потерь: K_потерь = 100% / (100% - потери%)
        """
        # Распаковываем данные
        name = layer[self.NAME]
        density = layer[self.DENSITY] if layer[self.DENSITY] is not None else 0
        solid_content = layer[self.SOLID_CONTENT] if layer[self.SOLID_CONTENT] is not None else 0
        dry_thickness = layer[self.DRY_THICKNESS] if layer[self.DRY_THICKNESS] is not None else 0
        losses = layer[self.LOSSES] if layer[self.LOSSES] is not None else 0
        price_kg = layer[self.PRICE_KG] if layer[self.PRICE_KG] is not None else 0
        
        # Пропускаем расчеты для разбавителей и растворителей
        if 'Разбавитель' in name or 'Растворитель' in name:
            return layer
            
        try:
            # 1. Толщина мокрого слоя (мкм) = толщина сухой пленки * 100 / сухой остаток
            if dry_thickness > 0 and solid_content > 0:
                wet_thickness = dry_thickness * 100 / solid_content
                layer[self.WET_THICKNESS] = self.round_value(wet_thickness)
            else:
                wet_thickness = layer[self.WET_THICKNESS] if layer[self.WET_THICKNESS] is not None else 0
            
            # 2. УКРЫВИСТОСТЬ (м²/л) = 1000 / толщина мокрой пленки (мкм)
            # Это ОБРАТНАЯ величина расходу!
            if wet_thickness > 0:
                covering_capacity = 1000 / wet_thickness  # м²/л
                layer[self.THEOR_COVERING] = self.round_value(covering_capacity)
            else:
                covering_capacity = layer[self.THEOR_COVERING] if layer[self.THEOR_COVERING] is not None else 0
            
            # 3. РАСХОД (л/м²) = 1 / укрывистость (м²/л)
            if covering_capacity > 0:
                consumption_l_per_m2 = 1 / covering_capacity
            else:
                consumption_l_per_m2 = 0
            
            # 4. ПРАВИЛЬНЫЙ РАСЧЕТ: Коэффициент потерь = 100% / (100% - потери%)
            if losses >= 0 and losses < 100:
                loss_coefficient = 100 / (100 - losses)
            else:
                loss_coefficient = 1.0
            
            # 5. Практическая укрывистость с учетом потерь (м²/л)
            if covering_capacity > 0:
                pract_covering_capacity = covering_capacity / loss_coefficient
                layer[self.PRACT_COVERING] = self.round_value(pract_covering_capacity)
                
                # Практический расход с учетом потерь (л/м²)
                pract_consumption_l = 1 / pract_covering_capacity
            else:
                pract_consumption_l = 0
            
            # 6. Теоретический расход (кг/м²) = расход (л/м²) * плотность (кг/л)
            if consumption_l_per_m2 > 0 and density > 0:
                theor_consumption_kg = consumption_l_per_m2 * density
                layer[self.THEOR_CONSUMPTION_KG] = self.round_value(theor_consumption_kg)
            
            # 7. Расход с учетом потерь (кг/м²) = практический расход (л/м²) * плотность
            if pract_consumption_l > 0 and density > 0:
                pract_consumption_kg = pract_consumption_l * density
                layer[self.PRACT_CONSUMPTION_KG] = self.round_value(pract_consumption_kg)
            
            # 8. Стоимость (руб/м²) = расход с учетом потерь (кг/м²) * цена за кг
            if (layer[self.PRACT_CONSUMPTION_KG] is not None and 
                layer[self.PRACT_CONSUMPTION_KG] > 0 and 
                price_kg > 0):
                cost = layer[self.PRACT_CONSUMPTION_KG] * price_kg
                layer[self.COST] = self.round_value(cost)
                
        except (ValueError, ZeroDivisionError) as e:
            logging.error(f"Ошибка расчета слоя: {e}")
        
        return layer

    def calculate_thinner_consumption(self, thinner_layer, parent_layer):
        """Рассчитывает расход растворителя на основе родительского слоя"""
        try:
            logging.info(f"Расчет растворителя: {thinner_layer[self.NAME]}")
            logging.info(f"Родительский слой: {parent_layer[self.NAME]}")
            
            thinner_percent = (thinner_layer[self.THINNER_PERCENT] / 100.0) if thinner_layer[self.THINNER_PERCENT] is not None else 0.05
            
            # Если процент растворителя некорректный, устанавливаем значение по умолчанию
            if thinner_percent <= 0:
                thinner_percent = 0.05
                
            logging.info(f"Процент растворителя: {thinner_percent}")
            
            # Если плотность растворителя не задана или равна 0, принимаем равной 1
            thinner_density = thinner_layer[self.DENSITY] if (thinner_layer[self.DENSITY] is not None and thinner_layer[self.DENSITY] > 0) else 1.0
            
            # Получаем плотность родительского слоя с проверкой на ноль
            parent_density = parent_layer[self.DENSITY] if (parent_layer[self.DENSITY] is not None and parent_layer[self.DENSITY] > 0) else 1.0
            
            logging.info(f"Плотность растворителя: {thinner_density}, Плотность родителя: {parent_density}")
            
            # === РАСХОД С УЧЕТОМ ПОТЕРЬ ===
            
            # Расход родительского ЛКМ в кг/м² с учетом потерь
            parent_consumption_kg_pract = parent_layer[self.PRACT_CONSUMPTION_KG] if parent_layer[self.PRACT_CONSUMPTION_KG] is not None else 0
            
            # Расход родительского ЛКМ в л/м² с учетом потерь
            parent_consumption_l_pract = parent_consumption_kg_pract / parent_density if parent_density > 0 else 0
            
            logging.info(f"Расход родителя (кг/м²): {parent_consumption_kg_pract}, (л/м²): {parent_consumption_l_pract}")
            
            # Расход растворителя в л/м² с учетом потерь
            thinner_consumption_l_pract = parent_consumption_l_pract * thinner_percent
            
            # Расход растворителя в кг/м² с учетом потерь
            thinner_consumption_kg_pract = thinner_consumption_l_pract * thinner_density
            
            logging.info(f"Расход растворителя (кг/м²): {thinner_consumption_kg_pract}, (л/м²): {thinner_consumption_l_pract}")
            
            # === ТЕОРЕТИЧЕСКИЙ РАСХОД (без потерь) ===
            
            # Расход родительского ЛКМ в кг/м² (теоретический)
            parent_consumption_kg_theor = parent_layer[self.THEOR_CONSUMPTION_KG] if parent_layer[self.THEOR_CONSUMPTION_KG] is not None else 0
            
            # Расход родительского ЛКМ в л/м² (теоретический)
            parent_consumption_l_theor = parent_consumption_kg_theor / parent_density if parent_density > 0 else 0
            
            # Расход растворителя в л/м² (теоретический)
            thinner_consumption_l_theor = parent_consumption_l_theor * thinner_percent
            
            # Расход растворителя в кг/м² (теоретический)
            thinner_consumption_kg_theor = thinner_consumption_l_theor * thinner_density
                
            # Сохраняем все рассчитанные значения
            thinner_layer[self.THEOR_COVERING] = self.round_value(thinner_consumption_l_theor)
            thinner_layer[self.THEOR_CONSUMPTION_KG] = self.round_value(thinner_consumption_kg_theor)
            thinner_layer[self.PRACT_CONSUMPTION_KG] = self.round_value(thinner_consumption_kg_pract)
            
            # Сохраняем расход в литрах
            thinner_layer[self.WET_THICKNESS] = self.round_value(thinner_consumption_l_pract)
            
            # Стоимость = расход с учетом потерь (кг/м²) * цена за кг
            thinner_layer[self.COST] = self.round_value(thinner_consumption_kg_pract * thinner_layer[self.PRICE_KG])
            
            logging.info(f"Итоговые значения - Расход кг: {thinner_layer[self.PRACT_CONSUMPTION_KG]}, Стоимость: {thinner_layer[self.COST]}")
            
        except (ValueError, ZeroDivisionError) as e:
            logging.error(f"Ошибка расчета растворителя: {e}")
            # Устанавливаем значения по умолчанию в случае ошибки
            thinner_layer[self.THEOR_COVERING] = 0
            thinner_layer[self.THEOR_CONSUMPTION_KG] = 0
            thinner_layer[self.PRACT_CONSUMPTION_KG] = 0
            thinner_layer[self.WET_THICKNESS] = 0
            thinner_layer[self.COST] = 0
        
        return thinner_layer

    def validate_and_calculate(self, entries, field_name, event=None):
        """
        Автоматический пересчет при редактировании полей
        Укрывистость в м²/л (обратная величина расходу)
        С правильным расчетом потерь
        """
        try:
            values = {
                'density': float(entries['Плотность'].get() or 0),
                'solid_content': float(entries['Сухой остаток'].get() or 0),
                'dry_thickness': float(entries['Толщина сухой'].get() or 0),
                'wet_thickness': float(entries['Толщина мокрой'].get() or 0),
                'theor_covering': float(entries['Укрывистость теор.'].get() or 0),
                'losses': float(entries['Потери'].get() or 0),
                'pract_covering': float(entries['Укрывистость практ.'].get() or 0),
                'price_kg': float(entries['Цена с НДС за кг'].get() or 0),
                'price_liter': float(entries['Цена с НДС за литр'].get() or 0)
            }
            
            # Расчет толщины мокрого слоя и укрывистости
            if field_name in ['Сухой остаток', 'Толщина сухой']:
                if values['solid_content'] > 0 and values['dry_thickness'] > 0:
                    wet_thickness = values['dry_thickness'] * 100 / values['solid_content']
                    entries['Толщина мокрой'].delete(0, tk.END)
                    entries['Толщина мокрой'].insert(0, str(self.round_value(wet_thickness)))
                    
                    # Расчет укрывистости (м²/л)
                    if wet_thickness > 0:
                        covering_capacity = 1000 / wet_thickness  # м²/л
                        entries['Укрывистость теор.'].delete(0, tk.END)
                        entries['Укрывистость теор.'].insert(0, str(self.round_value(covering_capacity)))
                        
                        # ПРАВИЛЬНЫЙ ПЕРЕСЧЕТ практической укрывистости
                        if values['losses'] >= 0 and values['losses'] < 100:
                            loss_coefficient = 100 / (100 - values['losses'])
                            pract_covering = covering_capacity / loss_coefficient
                            entries['Укрывистость практ.'].delete(0, tk.END)
                            entries['Укрывистость практ.'].insert(0, str(self.round_value(pract_covering)))
            
            # Расчет при изменении укрывистости
            elif field_name == 'Укрывистость теор.':
                if values['theor_covering'] > 0:
                    wet_thickness = 1000 / values['theor_covering']  # обратный расчет
                    entries['Толщина мокрой'].delete(0, tk.END)
                    entries['Толщина мокрой'].insert(0, str(self.round_value(wet_thickness)))
                    
                    # Расчет сухой толщины если известен сухой остаток
                    if values['solid_content'] > 0:
                        dry_thickness = wet_thickness * values['solid_content'] / 100
                        entries['Толщина сухой'].delete(0, tk.END)
                        entries['Толщина сухой'].insert(0, str(self.round_value(dry_thickness)))
                
                # ПРАВИЛЬНЫЙ ПЕРЕСЧЕТ практической укрывистости
                if values['theor_covering'] > 0 and values['losses'] >= 0 and values['losses'] < 100:
                    loss_coefficient = 100 / (100 - values['losses'])
                    pract_covering = values['theor_covering'] / loss_coefficient
                    entries['Укрывистость практ.'].delete(0, tk.END)
                    entries['Укрывистость практ.'].insert(0, str(self.round_value(pract_covering)))
            
            # ПРАВИЛЬНЫЙ ПЕРЕСЧЕТ укрывистости при изменении потерь
            elif field_name == 'Потери':
                if values['theor_covering'] > 0 and values['losses'] >= 0 and values['losses'] < 100:
                    loss_coefficient = 100 / (100 - values['losses'])
                    pract_covering = values['theor_covering'] / loss_coefficient
                    entries['Укрывистость практ.'].delete(0, tk.END)
                    entries['Укрывистость практ.'].insert(0, str(self.round_value(pract_covering)))
            
            # Взаимный пересчет цен
            elif field_name in ['Плотность', 'Цена с НДС за кг']:
                if values['density'] > 0 and values['price_kg'] > 0:
                    price_liter = values['price_kg'] * values['density']
                    entries['Цена с НДС за литр'].delete(0, tk.END)
                    entries['Цена с НДС за литр'].insert(0, str(round(price_liter, 2)))
            
            elif field_name in ['Плотность', 'Цена с НДС за литр']:
                if values['density'] > 0 and values['price_liter'] > 0:
                    price_kg = values['price_liter'] / values['density']
                    entries['Цена с НДС за кг'].delete(0, tk.END)
                    entries['Цена с НДС за кг'].insert(0, str(round(price_kg, 2)))
                    
        except ValueError:
            pass

    def edit_layer(self):
        """Открывает диалог редактирования слоя"""
        if len(self.layers) > 0:
            # Создаем диалоговое окно для выбора слоя для редактирования
            dialog = tk.Toplevel(self.master)
            dialog.title("Редактировать слой")
            
            # Создаем список слоев
            for i, layer in enumerate(self.layers):
                text = f"{layer[0]}"  # Название слоя
                
                def make_command(index=i):
                    return lambda: self.open_edit_dialog(index, dialog)
                    
                ttk.Button(dialog, text=text, command=make_command()).pack(pady=2)


    def recalculate_all_thinners(self):
        """Принудительно пересчитывает ВСЕ растворители в системе"""
        try:
            updated_count = 0
            
            for i, thinner_layer in enumerate(self.layers):
                thinner_name = thinner_layer[self.NAME]
                
                if 'Разбавитель' in thinner_name or 'Растворитель' in thinner_name:
                    # Извлекаем имя родительского слоя
                    parent_name = self.extract_parent_name_from_thinner(thinner_name)
                    
                    if parent_name:
                        # Ищем родительский слой по извлеченному имени
                        parent_layer = None
                        for layer in self.layers:
                            if (layer[self.NAME] == parent_name and 
                                'Разбавитель' not in layer[self.NAME] and 
                                'Растворитель' not in layer[self.NAME]):
                                parent_layer = layer
                                break
                        
                        # Если не нашли по извлеченному имени, пробуем найти по частичному совпадению
                        if not parent_layer:
                            for layer in self.layers:
                                if (parent_name in layer[self.NAME] and 
                                    'Разбавитель' not in layer[self.NAME] and 
                                    'Растворитель' not in layer[self.NAME]):
                                    parent_layer = layer
                                    logging.info(f"Найден родитель по частичному совпадению: {layer[self.NAME]} для {thinner_name}")
                                    break
                        
                        if parent_layer:
                            # Сохраняем оригинальный процент
                            original_percent = thinner_layer[self.THINNER_PERCENT]
                            
                            # Пересчитываем
                            updated_thinner = self.calculate_thinner_consumption(thinner_layer, parent_layer)
                            updated_thinner[self.THINNER_PERCENT] = original_percent
                            
                            self.layers[i] = updated_thinner
                            updated_count += 1
                            logging.info(f"Пересчитан растворитель: {thinner_name}")
            
            if updated_count > 0:
                self.create_layer_table()
                self.update_total_cost_display()
                messagebox.showinfo("Успех", f"Пересчитано {updated_count} растворителей!")
            else:
                messagebox.showinfo("Информация", "Не найдено растворителей для пересчета")
                
        except Exception as e:
            logging.error(f"Ошибка пересчета всех растворителей: {e}")
            messagebox.showerror("Ошибка", f"Не удалось пересчитать растворители: {str(e)}")        

        
    def force_recalculate_thinners(self):
        """Принудительно пересчитывает расход всех растворителей"""
        try:
            updated_count = 0
            
            # Находим все слои растворителей и пересчитываем их
            for i, layer in enumerate(self.layers):
                layer_name = layer[self.NAME]
                
                # Проверяем, является ли слой растворителем
                if 'Разбавитель' in layer_name or 'Растворитель' in layer_name:
                    logging.info(f"Найден растворитель: {layer_name}")
                    
                    # Пробуем несколько способов извлечения имени родительского слоя
                    parent_name = self.extract_parent_name_from_thinner(layer_name)
                    
                    if parent_name:
                        logging.info(f"Извлечено имя родительского слоя: '{parent_name}'")
                        
                        # Ищем родительский слой
                        parent_layer = self.find_parent_layer_for_thinner(layer_name)
                        
                        if parent_layer:
                            logging.info(f"Найден родительский слой: {parent_layer[self.NAME]}")
                            
                            # Сохраняем оригинальный процент разбавителя
                            original_percent = layer[self.THINNER_PERCENT]
                            
                            # Пересчитываем растворитель
                            updated_thinner = self.calculate_thinner_consumption(layer, parent_layer)
                            
                            # Восстанавливаем процент разбавителя
                            updated_thinner[self.THINNER_PERCENT] = original_percent
                            
                            self.layers[i] = updated_thinner
                            updated_count += 1
                            logging.info(f"Успешно пересчитан растворитель: {layer_name}")
                        else:
                            logging.warning(f"Родительский слой '{parent_name}' не найден для растворителя: {layer_name}")
                    else:
                        logging.warning(f"Не удалось извлечь имя родительского слоя из: {layer_name}")
            
            # Обновляем интерфейс
            self.create_layer_table()
            self.update_total_cost_display()
            
            if updated_count > 0:
                messagebox.showinfo("Успех", f"Пересчитано {updated_count} растворителей!")
            else:
                # Покажем более информативное сообщение
                thinner_count = len([l for l in self.layers if 'Разбавитель' in l[self.NAME] or 'Растворитель' in l[self.NAME]])
                if thinner_count == 0:
                    messagebox.showinfo("Информация", "В системе нет растворителей для пересчета")
                else:
                    messagebox.showwarning("Предупреждение", 
                        f"Найдено {thinner_count} растворителей, но не удалось их пересчитать. Проверьте логи.")
            
        except Exception as e:
            logging.error(f"Ошибка пересчета растворителей: {e}")
            messagebox.showerror("Ошибка", f"Не удалось пересчитать растворители: {str(e)}")

    def extract_parent_name_from_thinner(self, thinner_full_name):
        """Извлекает имя родительского слоя из полного имени растворителя"""
        try:
            # Формат: "Растворитель Бланк (Ксилол 5%)"
            if 'Растворитель' in thinner_full_name and '(' in thinner_full_name:
                # Извлекаем часть между "Растворитель" и "("
                parts = thinner_full_name.split('(')
                if len(parts) >= 2:
                    parent_part = parts[0]  # "Растворитель Бланк "
                    parent_name = parent_part.replace('Растворитель', '').strip()
                    return parent_name
            elif 'Растворитель' in thinner_full_name:
                # Старый формат: "Растворитель Бланк 5%"
                clean_name = thinner_full_name.replace('Растворитель', '').strip()
                # Убираем процент и числа в конце
                import re
                clean_name = re.sub(r'\s*\d+%?$', '', clean_name).strip()
                return clean_name
            
            return None
            
        except Exception as e:
            logging.error(f"Ошибка извлечения имени родительского слоя из '{thinner_full_name}': {e}")
            return None

    def find_parent_layer_for_thinner(self, thinner_name):
        """Находит родительский слой для растворителя"""
        parent_name = self.extract_parent_name_from_thinner(thinner_name)
        if not parent_name:
            logging.warning(f"Не удалось извлечь имя родительского слоя из: {thinner_name}")
            return None
        
        logging.info(f"Поиск родительского слоя для '{thinner_name}' -> извлечено: '{parent_name}'")
        
        # Сначала ищем точное совпадение
        for layer in self.layers:
            if (layer[self.NAME] == parent_name and 
                'Разбавитель' not in layer[self.NAME] and 
                'Растворитель' not in layer[self.NAME]):
                logging.info(f"Найден родительский слой по точному совпадению: {layer[self.NAME]}")
                return layer
        
        # Если точного совпадения нет, ищем по частичному
        for layer in self.layers:
            if (parent_name in layer[self.NAME] and 
                'Разбавитель' not in layer[self.NAME] and 
                'Растворитель' not in layer[self.NAME]):
                logging.info(f"Найден родительский слой по частичному совпадению: {layer[self.NAME]}")
                return layer
        
        logging.warning(f"Родительский слой '{parent_name}' не найден для растворителя: {thinner_name}")
        return None

    def find_layer_by_name(self, layer_name):
        """Находит слой по имени (игнорируя растворители)"""
        for layer in self.layers:
            if (layer[self.NAME] == layer_name and 
                'Разбавитель' not in layer[self.NAME] and 
                'Растворитель' not in layer[self.NAME]):
                return layer
        return None

        # Запускаем первоначальный расчет
        def initial_calculation():
            try:
                dry_thickness = float(entries['Толщина сухой'].get() or 0)
                solid_content = float(entries['Сухой остаток'].get() or 0)
                if dry_thickness and solid_content:
                    self.validate_and_calculate(entries, 'Сухой остаток')
            except:
                pass

        edit_dialog.after(100, initial_calculation)
        
        # Кнопка сохранения
        ttk.Button(edit_dialog, text="Сохранить изменения", 
                command=save_changes).pack(pady=10)
        
        # Запускаем первоначальный расчет
        def initial_calculation():
            try:
                dry_thickness = float(entries['Толщина сухой'].get() or 0)
                solid_content = float(entries['Сухой остаток'].get() or 0)
                if dry_thickness and solid_content:
                    self.validate_and_calculate(entries, 'Сухой остаток')
            except:
                pass

        edit_dialog.after(100, initial_calculation)
        
        # Кнопка сохранения
        ttk.Button(edit_dialog, text="Сохранить изменения", 
                command=save_changes).pack(pady=10)

    def open_edit_dialog(self, index, parent_dialog):

        """Открывает диалог редактирования конкретного слоя с автоматическим пересчетом растворителей"""
        # Создаем новое окно для редактирования
        edit_dialog = tk.Toplevel(self.master)
        edit_dialog.title(f"Редактировать слой {self.layers[index][0]}")
        edit_dialog.geometry("600x700")
        
        # Сохраняем оригинальное имя слоя для поиска связанных растворителей
        original_name = self.layers[index][0]
        
        # Проверяем, является ли слой растворителем
        is_thinner = 'Разбавитель' in original_name or 'Растворитель' in original_name
        
        # Создаем основной фрейм с прокруткой
        main_frame = ttk.Frame(edit_dialog)
        main_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Создаем canvas и скроллбар для прокрутки
        canvas = tk.Canvas(main_frame)
        scrollbar = ttk.Scrollbar(main_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # Упаковываем canvas и scrollbar
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Создаем вкладки внутри прокручиваемой области
        notebook = ttk.Notebook(scrollable_frame)
        notebook.pack(pady=5, expand=True, fill='both', padx=5)
        
        # Вкладка для основного покрытия
        main_frame_tab = ttk.Frame(notebook)
        notebook.add(main_frame_tab, text='Основное покрытие')
        
        # ВСЕ поля, включая расчетные
        fields = [
            'Система покрытия', 'Связующее', 'RAL', 'Плотность', 
            'Сухой остаток', 'Толщина мокрой', 'Толщина сухой',
            'Укрывистость теор.', 'Потери', 'Укрывистость практ.',
            'Цена с НДС за кг', 'Цена с НДС за литр'
        ]
        
        entries = {}
        for i, field in enumerate(fields):
            ttk.Label(main_frame_tab, text=field).grid(row=i, column=0, padx=5, pady=5, sticky='w')
            entry = ttk.Entry(main_frame_tab, width=40)
            entry.grid(row=i, column=1, padx=5, pady=5, sticky='ew')
            
            # Заполняем значениями
            current_value = self.layers[index][i] if self.layers[index][i] is not None else 0
            entry.insert(0, str(current_value))
            entries[field] = entry
            
            # Для растворителей блокируем редактирование некоторых полей
            if is_thinner and field in ['Сухой остаток', 'Толщина мокрой', 'Толщина сухой', 
                                    'Укрывистость теор.', 'Потери', 'Укрывистость практ.']:
                entry.config(state='disabled')
            
            # Автоматический пересчет для ключевых полей (только для основных слоев)
            if not is_thinner and field in ['Плотность', 'Сухой остаток', 'Толщина сухой', 
                                        'Цена с НДС за кг', 'Цена с НДС за литр', 'Потери']:
                entry.bind('<KeyRelease>', 
                        lambda e, f=field: self.validate_and_calculate(entries, f, e))
        
        # Настраиваем вес колонок для правильного растяжения
        main_frame_tab.columnconfigure(1, weight=1)
        
        # Фрейм для кнопок внизу диалога (ВНЕ прокручиваемой области)
        button_frame = ttk.Frame(edit_dialog)
        button_frame.pack(fill="x", pady=10, padx=10)
        
        def save_changes():
            """Сохранение изменений в слое с полным перерасчетом системы и связанных растворителей"""
            try:
                if is_thinner:
                    # Для растворителя сохраняем только основные поля
                    updated_layer = [
                        entries['Система покрытия'].get(),
                        entries['Связующее'].get(),
                        entries['RAL'].get(),
                        float(entries['Плотность'].get() or 0),
                        self.layers[index][4],  # Сухой остаток (не изменяем)
                        self.layers[index][5],  # Толщина мокрой (не изменяем)
                        self.layers[index][6],  # Толщина сухой (не изменяем)
                        self.layers[index][7],  # Укрывистость теор. (не изменяем)
                        self.layers[index][8],  # Потери (не изменяем)
                        self.layers[index][9],  # Укрывистость практ. (не изменяем)
                        float(entries['Цена с НДС за кг'].get() or 0),
                        float(entries['Цена с НДС за литр'].get() or 0),
                        self.layers[index][12],  # theor_consumption_kg
                        self.layers[index][13],  # pract_consumption_kg
                        self.layers[index][14],  # cost
                        self.layers[index][15]   # thinner_percent
                    ]
                    
                    # Сохраняем растворитель
                    self.layers[index] = updated_layer
                    
                else:
                    # Для основного слоя сохраняем все поля
                    updated_layer = [
                        entries['Система покрытия'].get(),
                        entries['Связующее'].get(),
                        entries['RAL'].get(),
                        float(entries['Плотность'].get() or 0),
                        float(entries['Сухой остаток'].get() or 0),
                        float(entries['Толщина мокрой'].get() or 0),
                        float(entries['Толщина сухой'].get() or 0),
                        float(entries['Укрывистость теор.'].get() or 0),
                        float(entries['Потери'].get() or 0),
                        float(entries['Укрывистость практ.'].get() or 0),
                        float(entries['Цена с НДС за кг'].get() or 0),
                        float(entries['Цена с НДС за литр'].get() or 0),
                        0.0,  # теоретический расход кг/м2 (будет рассчитан)
                        0.0,  # расход с учетом потерь кг/м2 (будет рассчитан)
                        0.0,  # стоимость (будет рассчитана)
                        0.0   # процент разбавителя (для совместимости)
                    ]
                    
                    # ЗАПУСКАЕМ ПОЛНЫЙ ПЕРЕСЧЕТ ОСНОВНОГО СЛОЯ
                    updated_layer = self.update_layer_calculations(updated_layer)
                    
                    # Сохраняем основной слой
                    self.layers[index] = updated_layer
                    
                    # НАХОДИМ И ПЕРЕСЧИТЫВАЕМ ВСЕ СВЯЗАННЫЕ РАСТВОРИТЕЛИ
                    new_layer_name = updated_layer[0]
                    associated_thinners = self.find_associated_thinners(original_name)
                    
                    for thinner_index, thinner_layer in associated_thinners:
                        # ОБНОВЛЯЕМ ИМЯ РАСТВОРИТЕЛЯ, если изменилось имя основного слоя
                        if original_name != new_layer_name:
                            # Извлекаем процент из старого имени растворителя
                            thinner_percentage = self.extract_thinner_percentage(thinner_layer[self.NAME])
                            # Создаем новое имя растворителя
                            new_thinner_name = f"Растворитель {new_layer_name} {thinner_percentage}%"
                            thinner_layer[self.NAME] = new_thinner_name
                            logging.info(f"Обновлено имя растворителя: {new_thinner_name}")
                        
                        # Пересчитываем растворитель на основе обновленного основного слоя
                        updated_thinner = self.calculate_thinner_consumption(thinner_layer, updated_layer)
                        self.layers[thinner_index] = updated_thinner
                        logging.info(f"Пересчитан растворитель для слоя: {new_layer_name}")
                
                # Обновляем таблицу
                self.create_layer_table()
                # Обновляем отображение общей стоимости
                self.update_total_cost_display()
                
                edit_dialog.destroy()
                parent_dialog.destroy()
                
                messagebox.showinfo("Успех", "Изменения сохранены!")
                
            except ValueError as e:
                messagebox.showerror("Ошибка", f"Проверьте правильность данных: {str(e)}")
        
        # Кнопка сохранения
        ttk.Button(button_frame, text="Сохранить изменения", 
                command=save_changes).pack(side=tk.LEFT, padx=5)
        
        # Кнопка отмены
        ttk.Button(button_frame, text="Отмена", 
                command=edit_dialog.destroy).pack(side=tk.RIGHT, padx=5)
        
        # Запускаем первоначальный расчет
        def initial_calculation():
            try:
                dry_thickness = float(entries['Толщина сухой'].get() or 0)
                solid_content = float(entries['Сухой остаток'].get() or 0)
                if dry_thickness and solid_content:
                    self.validate_and_calculate(entries, 'Сухой остаток')
            except:
                pass

        edit_dialog.after(100, initial_calculation)

    def create_widgets(self):
        """Создает основные элементы интерфейса приложения"""
        # Сначала создаем фрейм для отображения общей информации
        self.info_frame = ttk.LabelFrame(self.master, text="Общая информация")
        self.info_frame.pack(pady=10, padx=10, fill="x")
        
        self.total_cost_label = ttk.Label(
            self.info_frame, 
            text="СТОИМОСТЬ:\n"
                 "• С учетом потерь: 0.00 руб/м²\n"
                 "• Без учета потерь: 0.00 руб/м²\n"
                 "\nОСНОВНЫЕ ПАРАМЕТРЫ:\n"
                 "• Толщина покрытия: 0.0 мкм\n"
                 
        
                 "\nРАСХОД НА 1 М²:\n"
                 "• Теоретический: 0.000 кг/м² (0.000 л/м²)\n"
                 "• С учетом потерь: 0.000 кг/м² (0.000 л/м²)\n"
                 "\nОБЩЕЕ КОЛИЧЕСТВО НА 1.0 М²:\n"
                 "• Без потерь: 0.000 кг (0.000 л)\n"
                 "• С учетом потерь: 0.000 кг (0.000 л)",
            font=("Arial", 10), 
            foreground="blue",
            justify=tk.LEFT
        )
        self.total_cost_label.pack(pady=5, padx=5, anchor="w")

        # Затем создаем остальные элементы
        # Создаем фрейм для кнопок управления слоями
        control_frame = ttk.Frame(self.master)
        control_frame.pack(pady=10)

        ttk.Button(control_frame, text="База данных", 
                  command=self.open_database).pack(side=tk.LEFT, padx=5)
        ttk.Button(control_frame, text="История изменений", 
          command=self.open_coating_history).pack(side=tk.LEFT, padx=5)
        ttk.Button(control_frame, text="Шаблоны покрытий",
                  command=self.open_coating_templates).pack(side=tk.LEFT, padx=5)

        ttk.Button(control_frame, text="Добавить слой", 
                  command=self.add_layer).pack(side=tk.LEFT, padx=5)
        ttk.Button(control_frame, text="Удалить слой", 
                  command=self.remove_layer).pack(side=tk.LEFT, padx=5)
        ttk.Button(control_frame, text="Редактировать слой", 
                  command=self.edit_layer).pack(side=tk.LEFT, padx=5)
        ttk.Button(control_frame, text="Пересчитать растворители", 
                command=self.force_recalculate_thinners).pack(side=tk.LEFT, padx=5)
        ttk.Button(control_frame, text="Пересчитать ВСЕ растворители", 
          command=self.recalculate_all_thinners).pack(side=tk.LEFT, padx=5)
        
        # ОБНОВЛЕННЫЕ КНОПКИ ЭКСПОРТА
        ttk.Button(control_frame, text="Полный предпросмотр", 
              command=self.open_full_preview).pack(side=tk.LEFT, padx=5)
        ttk.Button(control_frame, text="Выборочный экспорт", 
              command=self.open_selective_export).pack(side=tk.LEFT, padx=5)
    
        ttk.Button(control_frame, text="Сравнить системы", 
              command=self.open_system_comparison).pack(side=tk.LEFT, padx=5)
        ttk.Button(control_frame, text="Полный экспорт в Excel", 
              command=self.export_to_excel).pack(side=tk.LEFT, padx=5)
        
        # Добавляем кнопки истории
        history_frame = ttk.Frame(self.master)
        history_frame.pack(pady=5)
        
        ttk.Button(history_frame, text="Сохранить в историю", 
                  command=self.save_to_history).pack(side=tk.LEFT, padx=5)
        ttk.Button(history_frame, text="История расчетов", 
                  command=self.open_calculation_history).pack(side=tk.LEFT, padx=5)
        ttk.Button(history_frame, text="История сравнений", 
                  command=self.open_comparison_history).pack(side=tk.LEFT, padx=5)
        

        # НОВАЯ КНОПКА: Обновить информацию
        ttk.Button(history_frame, text="Обновить", 
                  command=self.force_update_display).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(history_frame, text="О программе", 
                  command=self.show_about).pack(side=tk.LEFT, padx=5)

        # Создаем таблицу для отображения слоев
        self.create_layer_table()

    def force_update_display(self):
        """Принудительное обновление отображения общей информации"""
        try:
            self.update_total_cost_display()
            messagebox.showinfo("Обновлено", "Общая информация успешно обновлена!")
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось обновить информацию: {str(e)}")    
 
    def open_coating_history(self):
        """Открывает диалог истории изменений материалов"""
        try:
            CoatingHistoryDialog(self.master, self.db)
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось открыть историю изменений: {str(e)}")

    def open_full_preview(self):
        """Открывает предпросмотр в полном формате экспорта"""
        try:
            if not self.layers:
                messagebox.showwarning("Предупреждение", "Нет данных для предпросмотра")
                return
            FullFormatPreviewDialog(self.master, self)
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось открыть предпросмотр: {str(e)}")

    def open_selective_export(self):
        """Открывает диалог выборочного экспорта"""
        try:
            if not self.layers:
                messagebox.showwarning("Предупреждение", "Нет данных для экспорта")
                return
            SelectiveExportDialog(self.master, self)
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось открыть выборочный экспорт: {str(e)}")
                    
    def open_preview(self):
        """Открывает диалог предпросмотра расчета"""
        try:
            if not self.layers:
                messagebox.showwarning("Предупреждение", "Нет данных для предпросмотра")
                return
            CalculationPreviewDialog(self.master, self)
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось открыть предпросмотр: {str(e)}")
    def open_advanced_preview(self):
        """Открывает расширенный диалог предпросмотра расчета"""
        try:
            if not self.layers:
                messagebox.showwarning("Предупреждение", "Нет данных для предпросмотра")
                return
            CalculationPreviewDialog(self.master, self)
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось открыть предпросмотр: {str(e)}")
    def open_selective_export(self):
        """Открывает диалог выборочного экспорта"""
        try:
            if not self.layers:
                messagebox.showwarning("Предупреждение", "Нет данных для экспорта")
                return
            SelectiveExportDialog(self.master, self)
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось открыть выборочный экспорт: {str(e)}")

   # def force_recalculate_thinners(self):
        """Принудительно пересчитывает расход всех растворителей"""
        try:
            updated_count = 0
            
            # Находим все слои растворителей и пересчитываем их
            for i, layer in enumerate(self.layers):
                if 'Разбавитель' in layer[self.NAME] or 'Растворитель' in layer[self.NAME]:
                    # Извлекаем название родительского слоя из имени растворителя
                    # Формат: "Растворитель {название} {процент}%" или "Разбавитель {название} {процент}%"
                    thinner_name = layer[self.NAME]
                    
                    # Убираем "Растворитель" или "Разбавитель" из начала названия
                    base_name = thinner_name.replace('Растворитель', '').replace('Разбавитель', '').strip()
                    
                    # Разделяем на части и убираем процент в конце
                    parts = base_name.split()
                    if len(parts) >= 2:
                        # Берем все части кроме последней (процента)
                        parent_name = ' '.join(parts[:-1])
                        
                        # Ищем родительский слой
                        parent_layer_found = None
                        for parent_layer in self.layers:
                            if (parent_layer[self.NAME] == parent_name and 
                                'Разбавитель' not in parent_layer[self.NAME] and 
                                'Растворитель' not in parent_layer[self.NAME]):
                                parent_layer_found = parent_layer
                                break
                        
                        if parent_layer_found:
                            # Сохраняем оригинальный процент разбавителя
                            original_percent = layer[self.THINNER_PERCENT]
                            
                            # Пересчитываем растворитель
                            updated_thinner = self.calculate_thinner_consumption(layer, parent_layer_found)
                            
                            # Восстанавливаем процент разбавителя (на случай если он был изменен)
                            updated_thinner[self.THINNER_PERCENT] = original_percent
                            
                            self.layers[i] = updated_thinner
                            updated_count += 1
                            logging.info(f"Пересчитан растворитель: {thinner_name} для слоя: {parent_name}")
            
            # Обновляем интерфейс
            self.create_layer_table()
            self.update_total_cost_display()
            
            if updated_count > 0:
                messagebox.showinfo("Успех", f"Пересчитано {updated_count} растворителей!")
            else:
                messagebox.showinfo("Информация", "Не найдено растворителей для пересчета")
            
        except Exception as e:
            logging.error(f"Ошибка пересчета растворителей: {e}")
            messagebox.showerror("Ошибка", f"Не удалось пересчитать растворители: {str(e)}")

    def create_layer_table(self):
        """Создает таблицу для отображения информации о слоях"""
        # Удаляем старую таблицу, если она существует
        if hasattr(self, 'table_frame'):
            self.table_frame.destroy()

        # Создаем новый фрейм для таблицы
        self.table_frame = ttk.Frame(self.master)
        self.table_frame.pack(pady=10, padx=10, fill="both", expand=True)

        # ОБНОВЛЕННЫЕ ЗАГОЛОВКИ СТОЛБЦОВ
        headers = [
            'Система покрытия', 
            'Связующее', 
            'RAL', 
            'Плотность, кг/л',      # НОВЫЙ СТОЛБЕЦ
            'Сухой остаток, %',     # НОВЫЙ СТОЛБЕЦ
            'Толщина сух., мкм',
            'Расход теор., кг/м²',
            'Расход теор., л/м²',
            'Стоимость без потерь, руб/м²',  # НОВЫЙ СТОЛБЕЦ
            'Стоимость с потерями, руб/м²'   # НОВЫЙ СТОЛБЕЦ
        ]
        
        # Создаем заголовки таблицы
        for col, header in enumerate(headers):
            label = ttk.Label(self.table_frame, text=header, font=("Arial", 9, "bold"))
            label.grid(row=0, column=col, padx=5, pady=5, sticky="ew")
            # Настраиваем вес столбцов для правильного растяжения
            self.table_frame.columnconfigure(col, weight=1)

        # Заполняем таблицу данными
        for row, layer in enumerate(self.layers, start=1):
            # Определяем тип слоя (основной или растворитель)
            is_thinner = 'Разбавитель' in layer[self.NAME] or 'Растворитель' in layer[self.NAME]
            
            # Расчет стоимости без потерь
            theor_cost = 0.0
            if layer[self.THEOR_CONSUMPTION_KG] is not None and layer[self.PRICE_KG] is not None:
                theor_cost = layer[self.THEOR_CONSUMPTION_KG] * layer[self.PRICE_KG]
            
            if is_thinner:
                # Для растворителей показываем название самого растворителя
                thinner_real_name = self.extract_thinner_real_name(layer[0])
                values = [
                    thinner_real_name,  # Название самого растворителя (Ксилол)
                    "-",       # Связующее
                    "-",       # RAL
                    f"{layer[3]:.3f}" if layer[3] is not None else "-",  # Плотность
                    "-",       # Сухой остаток
                    "-",       # Толщина
                    f"{layer[12]:.3f}" if layer[12] is not None else "-",  # Расход кг/м²
                    f"{layer[13] / layer[3]:.3f}" if layer[3] and layer[3] > 0 and layer[13] is not None else "-",  # Расход л/м²
                    f"{theor_cost:.2f}" if theor_cost else "0.00",  # Стоимость без потерь
                    f"{layer[14]:.2f}" if layer[14] is not None else "0.00"  # Стоимость с потерями
                ]
            else:
                # Для основных слоев показываем все данные
                consumption_l = 0.0
                if layer[self.DENSITY] and layer[self.DENSITY] > 0:
                    consumption_l = layer[self.THEOR_CONSUMPTION_KG] / layer[self.DENSITY] if layer[self.THEOR_CONSUMPTION_KG] is not None else 0
                
                values = [
                    layer[0],  # Название
                    layer[1] if layer[1] else "-",  # Связующее
                    layer[2] if layer[2] else "-",  # RAL
                    f"{layer[3]:.3f}" if layer[3] is not None else "-",  # Плотность
                    f"{layer[4]:.1f}" if layer[4] is not None else "-",  # Сухой остаток
                    f"{layer[6]:.1f}" if layer[6] is not None else "-",  # Толщина сухая
                    f"{layer[12]:.3f}" if layer[12] is not None else "-",  # Теоретический расход кг/м²
                    f"{consumption_l:.3f}" if consumption_l else "-",  # Теоретический расход л/м²
                    f"{theor_cost:.2f}" if theor_cost else "0.00",  # Стоимость без потерь
                    f"{layer[14]:.2f}" if layer[14] is not None else "0.00"   # Стоимость с потерями
                ]
            
            # Создаем ячейки для текущего слоя
            for col, value in enumerate(values):
                label = ttk.Label(self.table_frame, text=str(value))
                label.grid(row=row, column=col, padx=5, pady=2, sticky="w")
                
                # Выделяем растворители другим цветом
                if is_thinner:
                    label.config(foreground="gray")
                
                # Выделяем стоимостные колонки
                if col in [8, 9]:  # Колонки со стоимостью
                    label.config(foreground="red", font=("Arial", 9, "bold"))

        # Если нет слоев, показываем сообщение
        if not self.layers:
            empty_label = ttk.Label(self.table_frame, text="Нет добавленных слоев", font=("Arial", 10, "italic"))
            empty_label.grid(row=1, column=0, columnspan=len(headers), pady=20)

        # Обновляем отображение общей информации (БЕЗ сохранения в историю)
        self.update_total_cost_display()

    def extract_thinner_real_name(self, thinner_full_name):
        """Извлекает настоящее название растворителя из полного имени"""
        try:
            # Формат: "Растворитель Бланк (Ксилол 5%)"
            if '(' in thinner_full_name and ')' in thinner_full_name:
                # Извлекаем часть в скобках: "Ксилол 5%"
                bracket_content = thinner_full_name.split('(')[1].split(')')[0]
                # Убираем процент, оставляем только название: "Ксилол"
                thinner_name = bracket_content.split()[0]
                return thinner_name
            else:
                # Старый формат - пытаемся извлечь название
                parts = thinner_full_name.replace('Растворитель', '').replace('Разбавитель', '').strip().split()
                if parts:
                    return parts[0]  # Первое слово после "Растворитель"
                return thinner_full_name
        except:
            return thinner_full_name

    def add_layer(self):
        """Открывает диалог добавления нового слоя"""
        dialog = tk.Toplevel(self.master)
        dialog.title("Добавить новый слой")
        dialog.geometry("700x500")
        
        # Сохраняем ссылку на диалог для использования в save_layer
        self.dialog = dialog
        
        # Создаем вкладки (УБЕРАЕМ ДУБЛИРОВАНИЕ - создается только один Notebook)
        notebook = ttk.Notebook(dialog)
        notebook.pack(pady=5, expand=True, fill='both')
        self.notebook = notebook  # Сохраняем для доступа из save_layer
        
        # === Вкладка для основного покрытия ===
        main_frame = ttk.Frame(notebook)  # СОЗДАЕМ main_frame
        notebook.add(main_frame, text='Основное покрытие')
        
        # === Вкладка для растворителя ===
        thinner_frame = ttk.Frame(notebook)
        notebook.add(thinner_frame, text='Растворитель')

        # === Основное покрытие ===
        ttk.Label(main_frame, text="Выбрать из базы:").grid(row=0, column=0, padx=5, pady=2, sticky='w')
        coating_names = [coating[1] for coating in self.db.get_coatings()]
        # ЗАМЕНА: Используем ComboboxWithSearch вместо обычного Combobox
        coating_combo = ComboboxWithSearch(main_frame, values=coating_names, width=40)
        coating_combo.grid(row=0, column=1, padx=5, pady=2, sticky='ew')

        # Создаем поля ввода для основного покрытия
        fields = ['Система покрытия', 'Связующее', 'RAL', 'Плотность', 
                 'Сухой остаток', 'Толщина мокрой', 'Толщина сухой', 'Укрывистость теор.',
                 'Потери', 'Укрывистость практ.', 'Цена с НДС за кг', 'Цена с НДС за литр']
        
        entries = {}  # ИСПРАВЛЕНО: создаем entries здесь
        for i, field in enumerate(fields):
            ttk.Label(main_frame, text=field).grid(row=i+1, column=0, padx=5, pady=2, sticky='w')
            entry = ttk.Entry(main_frame, width=30)
            entry.grid(row=i+1, column=1, padx=5, pady=2, sticky='ew')
            entries[field] = entry
            
            # Привязываем обработчики событий для автоматических расчетов
            if field in ['Плотность', 'Сухой остаток', 'Толщина сухой', 
                        'Цена с НДС за кг', 'Цена с НДС за литр', 'Потери']:
                entry.bind('<KeyRelease>', 
                         lambda e, f=field: self.validate_and_calculate(entries, f, e))

        def on_coating_selected(event):
            """Обработчик выбора покрытия из базы данных"""
            coating = self.db.get_coating_by_name(coating_combo.get())
            if coating:
                entries['Система покрытия'].delete(0, tk.END)
                entries['Система покрытия'].insert(0, coating[1])
                entries['Связующее'].delete(0, tk.END)
                entries['Связующее'].insert(0, coating[2] or '')
                entries['RAL'].delete(0, tk.END)
                entries['RAL'].insert(0, coating[3] or '')
                entries['Плотность'].delete(0, tk.END)
                entries['Плотность'].insert(0, str(coating[4] or ''))
                entries['Сухой остаток'].delete(0, tk.END)
                entries['Сухой остаток'].insert(0, str(coating[5] or ''))
                entries['Цена с НДС за кг'].delete(0, tk.END)
                entries['Цена с НДС за кг'].insert(0, str(coating[6] or ''))
                entries['Цена с НДС за литр'].delete(0, tk.END)
                entries['Цена с НДС за литр'].insert(0, str(coating[7] or ''))
                
                # Запускаем расчеты после заполнения полей
                self.validate_and_calculate(entries, 'Сухой остаток')

        coating_combo.bind('<<ComboboxSelected>>', on_coating_selected)

        # === Растворитель ===
        # Фрейм для выбора родительского слоя
        parent_frame = ttk.LabelFrame(thinner_frame, text="Выбор основного слоя")
        parent_frame.pack(fill='x', padx=5, pady=5)
        
        ttk.Label(parent_frame, text="К какому слою относится растворитель:").grid(row=0, column=0, padx=5, pady=2, sticky='w')
        parent_layer_names = [layer[0] for layer in self.layers if 'Растворитель' not in layer[0] and 'Разбавитель' not in layer[0]]
        parent_combo = ttk.Combobox(parent_frame, values=parent_layer_names, width=40)
        parent_combo.grid(row=0, column=1, padx=5, pady=2, sticky='ew')
        
        # Фрейм для выбора растворителя
        thinner_select_frame = ttk.LabelFrame(thinner_frame, text="Выбор растворителя")
        thinner_select_frame.pack(fill='x', padx=5, pady=5)
        
        ttk.Label(thinner_select_frame, text="Выбрать растворитель:").grid(row=0, column=0, padx=5, pady=2, sticky='w')
        thinner_names = [coating[1] for coating in self.db.get_thinners()]
        # ЗАМЕНА: Используем ComboboxWithSearch вместо обычного Combobox
        thinner_combo = ComboboxWithSearch(thinner_select_frame, values=thinner_names, width=40)
        thinner_combo.grid(row=0, column=1, padx=5, pady=2, sticky='ew')
        
        # Процент растворителя
        ttk.Label(thinner_select_frame, text="Процент растворителя (%):").grid(row=1, column=0, padx=5, pady=2, sticky='w')
        thinner_percent = ttk.Entry(thinner_select_frame, width=30)
        thinner_percent.insert(0, "5")  # значение по умолчанию
        thinner_percent.grid(row=1, column=1, padx=5, pady=2, sticky='ew')

        # Фрейм для отображения данных растворителя
        thinner_data_frame = ttk.LabelFrame(thinner_frame, text="Данные растворителя")
        thinner_data_frame.pack(fill='x', padx=5, pady=5)
        
        thinner_entries = {}
        thinner_fields = ['Плотность', 'Цена с НДС за кг', 'Цена с НДС за литр']
        
        for i, field in enumerate(thinner_fields):
            ttk.Label(thinner_data_frame, text=field).grid(row=i, column=0, padx=5, pady=2, sticky='w')
            entry = ttk.Entry(thinner_data_frame, width=30)
            entry.grid(row=i, column=1, padx=5, pady=2, sticky='ew')
            thinner_entries[field] = entry

        def on_thinner_selected(event):
            """Обработчик выбора растворителя из базы данных"""
            thinner = self.db.get_coating_by_name(thinner_combo.get())
            if thinner:
                thinner_entries['Плотность'].delete(0, tk.END)
                thinner_entries['Плотность'].insert(0, str(thinner[4] or ''))
                thinner_entries['Цена с НДС за кг'].delete(0, tk.END)
                thinner_entries['Цена с НДС за кг'].insert(0, str(thinner[6] or ''))
                thinner_entries['Цена с НДС за литр'].delete(0, tk.END)
                thinner_entries['Цена с НДС за литр'].insert(0, str(thinner[7] or ''))

        thinner_combo.bind('<<ComboboxSelected>>', on_thinner_selected)

        # Кнопка сохранения
        ttk.Button(dialog, text="Сохранить", command=lambda: self.save_layer(
            entries, coating_combo, parent_combo, thinner_combo, thinner_entries, thinner_percent
        )).pack(pady=10)
        
        # Сохраняем ссылки на элементы интерфейса для использования в save_layer
        self.entries = entries
        self.coating_combo = coating_combo
        self.parent_combo = parent_combo
        self.thinner_combo = thinner_combo
        self.thinner_entries = thinner_entries
        self.thinner_percent = thinner_percent

    def save_layer(self, entries, coating_combo, parent_combo, thinner_combo, thinner_entries, thinner_percent):
        """Сохранение нового слоя с автоматическим добавлением в базу данных"""
        try:
            # Определяем, какая вкладка активна
            current_tab = self.notebook.index(self.notebook.select())
            
            if current_tab == 0:  # Основное покрытие
                coating_name = entries['Система покрытия'].get().strip()
                if not coating_name:
                    messagebox.showerror("Ошибка", "Введите название системы покрытия")
                    return
                
                # Проверяем, существует ли покрытие в базе данных
                existing_coating = self.db.get_coating_by_name(coating_name)
                if not existing_coating:
                    # Добавляем новое покрытие в базу данных
                    self.db.add_coating(
                        name=coating_name,
                        binder=entries['Связующее'].get(),
                        ral=entries['RAL'].get(),
                        density=float(entries['Плотность'].get() or 0),
                        solid_content=float(entries['Сухой остаток'].get() or 0),
                        price_kg=float(entries['Цена с НДС за кг'].get() or 0),
                        price_liter=float(entries['Цена с НДС за литр'].get() or 0),
                        is_thinner=False
                    )
                    logging.info(f"Добавлено новое покрытие в базу: {coating_name}")
                
                # Создаем основной слой (16 полей)
                new_layer = [
                    coating_name,
                    entries['Связующее'].get(),
                    entries['RAL'].get(),
                    float(entries['Плотность'].get() or 0),
                    float(entries['Сухой остаток'].get() or 0),
                    float(entries['Толщина мокрой'].get() or 0),
                    float(entries['Толщина сухой'].get() or 0),
                    float(entries['Укрывистость теор.'].get() or 0),
                    float(entries['Потери'].get() or 0),
                    float(entries['Укрывистость практ.'].get() or 0),
                    float(entries['Цена с НДС за кг'].get() or 0),
                    float(entries['Цена с НДС за литр'].get() or 0),
                    0.0,  # теоретический расход кг/м2
                    0.0,  # расход с учетом потерь кг/м2
                    0.0,  # стоимость
                    0.0   # процент растворителя
                ]
                
                # Выполняем расчеты для основного слоя
                new_layer = self.update_layer_calculations(new_layer)
                self.layers.append(new_layer)

            elif current_tab == 1:  # Растворитель
                # Проверяем, выбран ли родительский слой
                parent_layer_name = parent_combo.get().strip()
                if not parent_layer_name:
                    messagebox.showerror("Ошибка", "Выберите основной слой, к которому относится растворитель")
                    return
                
                # Находим родительский слой
                parent_layer = None
                for layer in self.layers:
                    if layer[0] == parent_layer_name:
                        parent_layer = layer
                        break
                
                if not parent_layer:
                    messagebox.showerror("Ошибка", "Основной слой не найден")
                    return
                
                # Проверяем, выбран ли растворитель
                thinner_name = thinner_combo.get().strip()
                if not thinner_name:
                    messagebox.showerror("Ошибка", "Выберите растворитель из базы данных")
                    return
                
                # Проверяем, существует ли растворитель в базе данных
                existing_thinner = self.db.get_coating_by_name(thinner_name)
                if not existing_thinner:
                    # Добавляем новый растворитель в базу данных
                    self.db.add_coating(
                        name=thinner_name,
                        binder='',  # у растворителя нет связующего
                        ral='',     # у растворителя нет RAL
                        density=float(thinner_entries['Плотность'].get() or 0),
                        solid_content=0,  # у растворителя сухой остаток 0
                        price_kg=float(thinner_entries['Цена с НДС за кг'].get() or 0),
                        price_liter=float(thinner_entries['Цена с НДС за литр'].get() or 0),
                        is_thinner=True
                    )
                    logging.info(f"Добавлен новый растворитель в базу: {thinner_name}")
                
                # Создаем слой растворителя
                thinner_layer = [
                    f"Растворитель {parent_layer_name} ({thinner_name} {thinner_percent.get()}%)",
                    '',  # связующее
                    '',  # RAL
                    float(thinner_entries['Плотность'].get() or 0),
                    0,  # сухой остаток
                    0,  # толщина мокрой
                    0,  # толщина сухой
                    0,  # укрывистость теор
                    0,  # потери
                    0,  # укрывистость практ
                    float(thinner_entries['Цена с НДС за кг'].get() or 0),
                    float(thinner_entries['Цена с НДС за литр'].get() or 0),
                    0.0,  # теоретический расход кг/м2
                    0.0,  # расход с учетом потерь кг/м2
                    0.0,  # стоимость
                    float(thinner_percent.get() or 5)  # процент растворителя
                ]
                
                # Рассчитываем расход растворителя на основе родительского слоя
                thinner_layer = self.calculate_thinner_consumption(thinner_layer, parent_layer)
                self.layers.append(thinner_layer)

            self.create_layer_table()
            # ЯВНОЕ сохранение в историю после добавления слоя
            self.save_to_history()
            self.dialog.destroy()
            
        except ValueError as e:
            messagebox.showerror("Ошибка", f"Пожалуйста, проверьте правильность введенных данных: {str(e)}")
        
    def remove_layer(self):
        """Открывает диалог удаления слоя"""
        if len(self.layers) > 0:
            # Создаем диалоговое окно для выбора слоя для удаления
            dialog = tk.Toplevel(self.master)
            dialog.title("Удалить слой")
            
            # Создаем список слоев
            for i, layer in enumerate(self.layers):
                text = f"{layer[0]}"  # Показываем только название слоя
                def make_command(index=i):
                    return lambda: self.delete_layer(index, dialog)
                ttk.Button(dialog, text=text, command=make_command()).pack(pady=2)

    def delete_layer(self, index, dialog):
        """Удаляет выбранный слой"""
        self.layers.pop(index)
        self.create_layer_table()  # Обновляем таблицу
        # ЯВНОЕ сохранение в историю после удаления слоя
        self.save_to_history()
        dialog.destroy()

    def safe_merge_cells(self, ws, range_str):
        """Безопасное объединение ячеек с обработкой ошибок"""
        try:
            ws.merge_cells(range_str)
            return True
        except Exception as e:
            logging.error(f"Ошибка объединения ячеек {range_str}: {e}")
            return False

    def format_cell(self, cell, value, number_format='#,##0.000'):
        """Безопасное форматирование ячеек с обработкой ошибок"""
        try:
            # Обработка None и пустых строк
            if value is None:
                cell.value = 0
            elif isinstance(value, str):
                value = value.strip()
                if value == '':
                    cell.value = 0
                else:
                    # Пробуем преобразовать строку в число
                    try:
                        cell.value = float(value)
                    except ValueError:
                        cell.value = value
            else:
                cell.value = value
                
            # Форматирование
            cell.border = Border(left=Side(style='thin'), right=Side(style='thin'),
                               top=Side(style='thin'), bottom=Side(style='thin'))
            cell.alignment = Alignment(horizontal='center', vertical='center', wrap_text=True)
            
            if isinstance(cell.value, (int, float)):
                cell.number_format = number_format
                
        except Exception as e:
            logging.error(f"Ошибка форматирования ячейки: {e}")
            cell.value = 0
            cell.number_format = number_format

    def create_header_row(self, ws):
        """Создание заголовков Excel с безопасным объединением ячеек"""
        headers = [
            ('Площадь', 'A1:A2'), 
            ('Система покрытия', 'B1:B2'), 
            ('Связующее', 'C1:C2'),
            ('Цвет', 'D1:D2'), 
            ('Плотность', 'E1:E2'), 
            ('Сухой остаток', 'F1:F2'),
            ('Толщина пленки', 'G1:H1'), 
            ('Укрывистость', 'I1:K1'),
            ('Цена с НДС за кг', 'L1:L2'), 
            ('Цена с НДС за литр', 'M1:M2'),
            ('Теоретический расход', 'N1:O2'),  # ИЗМЕНЕНО: объединяем N1:O2
            ('Расход с учетом потерь', 'P1:Q2'),  # ИЗМЕНЕНО: объединяем P1:Q2
            ('Стоимость на 1 м² (теория) , с НДС', 'R1:R2'),
            ('Стоимость на 1 м² (с учетом потерь), с НДС', 'S1:S2'),
            ('Количество материала на заданную площадь (теория)', 'T1:U2'),  # ИЗМЕНЕНО: объединяем T1:U2
            ('Стоимость материалов (теория)', 'V1:V2'),
            ('Количество материала на заданную площадь (с учетом потерь)', 'W1:X2'),  # ИЗМЕНЕНО: объединяем W1:X2
            ('Стоимость материалов (с учётом потерь)', 'Y1:Y2')
        ]

        subheaders = {
            'A3': 'м2', 'B3': 'слой', 'C3': 'тип', 'D3': 'RAL', 'E3': 'кг/л', 'F3': '%',
            'G3': 'мкм', 'H3': 'мкм', 'I3': 'м²/л',
            'J3': '%', 'K3': 'м²/л', 'L3': 'Руб', 'M3': 'Руб',
            'N3': 'л/м2', 'O3': 'кг/м2', 'P3': 'л/м2', 'Q3': 'кг/м2',
            'R3': 'Руб', 'S3': 'Руб', 'T3': 'л', 'U3': 'кг',
            'V3': 'Руб',
            'W3': 'л', 'X3': 'кг',
            'Y3': 'Руб'
        }

        # Применяем основные заголовки
        for header, range_cell in headers:
            start_cell = range_cell.split(':')[0]
            ws[start_cell] = header
            if ':' in range_cell:
                self.safe_merge_cells(ws, range_cell)

        # Применяем подзаголовки
        for cell, value in subheaders.items():
            ws[cell] = value

        # Безопасное объединение ячеек
        self.safe_merge_cells(ws, 'G1:H1')
        self.safe_merge_cells(ws, 'I1:K1')
        
        # ЗАГОЛОВКИ ВТОРОГО УРОВНЯ (отдельные ячейки, не объединенные):
        ws['G2'] = 'мокрая'
        ws['H2'] = 'сухая'
        ws['I2'] = 'теор.'
        ws['J2'] = 'потери'
        ws['K2'] = 'практ.'
        
        # Стили для всех ячеек заголовка
        for row in ws['A1:Y3']:
            for cell in row:
                cell.font = Font(bold=True, size=11)
                cell.border = Border(left=Side(style='thin'), right=Side(style='thin'),
                               top=Side(style='thin'), bottom=Side(style='thin'))
                cell.alignment = Alignment(horizontal='center', vertical='center', wrap_text=True)

    def calculate_total_values(self):
        """
        Рассчитывает итоговые значения для всех слоев
        """
        total_dry_thickness = 0
        total_theor_consumption_kg = 0
        total_pract_consumption_kg = 0
        total_theor_cost = 0
        total_pract_cost = 0

        for layer in self.layers:
            if 'Разбавитель' not in layer[0] and 'Растворитель' not in layer[0]:
                total_dry_thickness += float(layer[6] or 0)  # Сухая толщина
                total_theor_consumption_kg += float(layer[12] or 0)  # Теоретический расход в кг
                total_pract_consumption_kg += float(layer[13] or 0)  # Расход с потерями в кг
                total_pract_cost += float(layer[14] or 0)  # Стоимость с учетом потерь
                
            # Стоимость по теоретическому расходу для всех слоев
            theor_cost = (layer[self.THEOR_CONSUMPTION_KG] or 0) * (layer[self.PRICE_KG] or 0)
            total_theor_cost += theor_cost

        return {
            'total_dry_thickness': total_dry_thickness,
            'total_consumption_kg': total_theor_consumption_kg,
            'total_consumption_with_losses': total_pract_consumption_kg,
            'total_cost': total_pract_cost,
            'total_theor_cost': total_theor_cost
        }
    
    def find_associated_thinners(self, parent_layer_name):
        """Находит все растворители, связанные с родительским слоем"""
        associated = []
        
        for i, layer in enumerate(self.layers):
            layer_name = layer[self.NAME]
            
            if 'Разбавитель' in layer_name or 'Растворитель' in layer_name:
                # Извлекаем имя родительского слоя из имени растворителя
                extracted_parent_name = self.extract_parent_name_from_thinner(layer_name)
                
                # Сравниваем с текущим именем родительского слоя
                if extracted_parent_name == parent_layer_name:
                    associated.append((i, layer))
                    logging.info(f"Найден связанный растворитель: {layer_name} для родителя: {parent_layer_name}")
        
        return associated
    
    def recalculate_all_layers(self):
        """Полный пересчет всех слоев системы"""
        # Сначала пересчитываем все основные слои
        for i, layer in enumerate(self.layers):
            # Пропускаем растворители на первом этапе
            if 'Разбавитель' in layer[self.NAME] or 'Растворитель' in layer[self.NAME]:
                continue
                
            # Пересчитываем основной слой
            updated_layer = self.update_layer_calculations(layer)
            self.layers[i] = updated_layer
        
        # Затем пересчитываем все растворители на основе обновленных основных слоев
        self.recalculate_all_thinners()
        
        # Обновляем интерфейс
        self.create_layer_table()
        self.update_total_cost_display()

    def recalculate_all_thinners(self):
        """Пересчет всех растворителей в системе"""
        for i, layer in enumerate(self.layers):
            if 'Разбавитель' in layer[self.NAME] or 'Растворитель' in layer[self.NAME]:
                # Извлекаем название основного слоя
                thinner_name_parts = layer[self.NAME].split()
                if len(thinner_name_parts) >= 3:
                    main_layer_name = ' '.join(thinner_name_parts[1:-1])
                    main_layer = self.find_layer_by_name(main_layer_name)
                    
                    if main_layer:
                        # Пересчитываем растворитель на основе обновленного основного слоя
                        updated_thinner = self.calculate_thinner_consumption(layer, main_layer)
                        self.layers[i] = updated_thinner    

    def validate_export_data(self):
        """Проверяет данные перед экспортом"""
        for i, layer in enumerate(self.layers):
            if len(layer) != 16:
                return False, f"Слой {i} имеет некорректное количество полей: {len(layer)}"
            
            # Проверяем обязательные числовые поля
            required_fields = [self.DENSITY, self.SOLID_CONTENT, self.DRY_THICKNESS, 
                             self.PRICE_KG, self.PRICE_LITER]
            for field_idx in required_fields:
                if not isinstance(layer[field_idx], (int, float)) or layer[field_idx] < 0:
                    return False, f"Слой {i} имеет некорректные числовые данные"
                    
        return True, "Данные валидны"

    def apply_standard_row_heights(self, worksheet, config=None):
        """
        Универсальный метод для установки высот строк
        config: словарь с настройками высот
        """
        if config is None:
            config = {
                'title_row': 60,       # Основной заголовок
                'subtitle_row': 35,    # Подзаголовок
                'header_row': 28,      # Заголовки столбцов
                'data_row': 18,        # Обычные данные
                'summary_row': 22,     # Итоги
                'spacer_row': 5        # Пустые строки-разделители
            }
        
        for row_num in range(1, worksheet.max_row + 1):
            row_cells = list(worksheet[row_num])
            row_values = [cell.value for cell in row_cells if cell.value]
            
            if not row_values:
                # Пустая строка
                worksheet.row_dimensions[row_num].height = config['spacer_row']
            elif row_num == 1:
                # Первая строка
                worksheet.row_dimensions[row_num].height = config['title_row']
            elif row_num == 2:
                # Вторая строка
                worksheet.row_dimensions[row_num].height = config['subtitle_row']
            elif any(cell.font and cell.font.bold for cell in row_cells if cell.value):
                # Заголовки столбцов
                worksheet.row_dimensions[row_num].height = config['header_row']
            elif any('итог' in str(cell.value).lower() for cell in row_cells if cell.value):
                # Итоговые строки
                worksheet.row_dimensions[row_num].height = config['summary_row']
            else:
                # Обычные данные
                worksheet.row_dimensions[row_num].height = config['data_row']


    def apply_smart_text_wrapping(self, worksheet):
        """Умное применение переноса текста с выравниванием по середине для заголовков"""
        for row in worksheet.iter_rows():
            for cell in row:
                if cell.value is not None:
                    cell_value = str(cell.value)
                    
                    # Базовые настройки выравнивания
                    alignment = Alignment(
                        wrap_text=True,
                        vertical='center',  # Всегда по вертикали по середине
                        horizontal='left'   # По умолчанию по левому краю
                    )
                    
                    font = Font()
                    
                    # ЛОГИКА ВЫРАВНИВАНИЯ ПО СЕРЕДИНЕ:
                    
                    # 1. ЗАГОЛОВОЧНЫЕ СТРОКИ (1-4 строки)
                    if cell.row <= 4:
                        alignment.horizontal = 'center'
                        if cell.row == 1:  # Главный заголовок
                            font = Font(bold=True, size=11)
                        elif cell.row == 2:  # Подзаголовок
                            font = Font(bold=True, size=11)
                        elif cell.row in [3, 4]:  # Заголовки столбцов
                            font = Font(bold=True)
                    
                    # 2. ЧИСЛОВЫЕ ЗНАЧЕНИЯ
                    elif (cell_value.replace('.', '').replace(',', '').replace(' ', '').isdigit() or
                        (cell_value.replace(' ', '') and 
                        cell_value.replace(' ', '').replace('.', '').replace(',', '').isdigit())):
                        alignment.horizontal = 'right'
                    
                    # 3. ИТОГОВЫЕ СТРОКИ
                    elif any(keyword in cell_value.lower() for keyword in ['итого', 'всего', 'сумма', 'total', 'итог']):
                        alignment.horizontal = 'center'
                        font = Font(bold=True)
                    
                    # 4. НАЗВАНИЯ СТОЛБЦОВ В ТЕЛЕ ТАБЛИЦЫ
                    elif (cell.column in [1, 2, 3] and  # Первые три столбца (названия, связующее, RAL)
                        cell.row > 4 and 
                        not any(keyword in cell_value.lower() for keyword in ['растворитель', 'разбавитель'])):
                        alignment.horizontal = 'left'
                    
                    # 5. РАСТВОРИТЕЛИ
                    elif any(keyword in cell_value.lower() for keyword in ['растворитель', 'разбавитель', 'thinner']):
                        alignment.horizontal = 'center'
                        font = Font(color="666666", italic=True)
                    
                    # 6. ПУСТЫЕ ЗНАЧЕНИЯ И РАЗДЕЛИТЕЛИ
                    elif cell_value.strip() in ['-', '---', '']:
                        alignment.horizontal = 'center'
                    
                    # 7. ОСТАЛЬНЫЕ ТЕКСТОВЫЕ ЗНАЧЕНИЯ
                    else:
                        alignment.horizontal = 'left'
                    
                    # Применяем выравнивание и шрифт
                    cell.alignment = alignment
                    if font.bold or font.size or font.color or font.italic:
                        cell.font = font
   
 

    def export_to_excel(self):
        """Экспортирует данные в файл Excel"""
        try:
            if not self.layers:
                messagebox.showwarning("Предупреждение", "Нет данных для экспорта")
                return

            # Проверяем данные перед экспортом
            is_valid, message = self.validate_export_data()
            if not is_valid:
                messagebox.showerror("Ошибка", f"Некорректные данные: {message}")
                return

            # ЯВНОЕ сохранение в историю перед экспортом
            self.save_to_history()
            
            wb = Workbook()
            ws = wb.active
            ws.title = "Расчет покрытий"


            # Создаем заголовки
            self.create_header_row(ws)

            # В любом методе экспорта после заполнения данных:
            self.apply_standard_row_heights(ws)
            self.apply_smart_text_wrapping(ws)

            # Получаем значение площади
            try:
                area_text = self.area_entry.get().strip()
                area = float(area_text) if area_text else 1.0
            except ValueError:
                messagebox.showerror("Ошибка", "Неверное значение площади")
                return

            # Записываем данные основных слоев
            current_row = 4  # Начинаем с 4-й строки
            
            # Инициализируем итоговые переменные
            total_theor_material_liters = 0.0
            total_theor_material_kg = 0.0
            total_pract_material_liters = 0.0
            total_pract_material_kg = 0.0
            total_theor_material_cost = 0.0
            total_pract_material_cost = 0.0
            total_theor_consumption_l = 0.0
            total_pract_consumption_l = 0.0
            
            for row_data in self.layers:
                # Проверяем длину данных слоя
                if len(row_data) < 16:
                    logging.warning(f"Пропущен слой с некорректными данными: {row_data}")
                    continue
                    
                # Определяем, является ли слой растворителем
                is_thinner = 'Разбавитель' in row_data[self.NAME] or 'Растворитель' in row_data[self.NAME]
                
                # Создаем список данных для экспорта с правильным порядком
                export_data = []
                
                # Основные данные (первые 12 полей)
                for i in range(12):
                    export_data.append(row_data[i])
                
                # Для растворителей убираем слово "Растворитель" из названия и очищаем поля F-K
                if is_thinner:
                    # Убираем "Растворитель" из названия
                    original_name = export_data[0]
                    if 'Растворитель' in original_name:
                        # Убираем слово "Растворитель" и оставляем только название и процент
                        new_name = original_name.replace('Растворитель', '').strip()
                        export_data[0] = new_name
                    
                    # Очищаем поля F-K (индексы 4-9 в export_data)
                    # F: Сухой остаток, G: Толщина мокрой, H: Толщина сухой, I: Укрывистость теор., J: Потери, K: Укрывистость практ.
                    for i in [4, 5, 6, 7, 8, 9]:
                        export_data[i] = ''
                
                # Расчет теоретического расхода (л/м²)
                if is_thinner:
                    # Для растворителя: используем уже рассчитанное значение из THEOR_COVERING
                    theor_consumption_l = row_data[self.THEOR_COVERING] if row_data[self.THEOR_COVERING] is not None else 0
                else:
                    # Для обычных покрытий: 1 / укрывистость
                    if row_data[self.THEOR_COVERING] and row_data[self.THEOR_COVERING] > 0:
                        theor_consumption_l = 1 / row_data[self.THEOR_COVERING]
                    else:
                        theor_consumption_l = 0
                
                export_data.append(self.round_value(theor_consumption_l))  # N столбец
                
                # Теоретический расход кг/м2 (уже есть в данных)
                export_data.append(self.round_value(row_data[self.THEOR_CONSUMPTION_KG] if row_data[self.THEOR_CONSUMPTION_KG] is not None else 0))  # O столбец
                
                # РАСЧЕТ РАСХОДА С УЧЕТОМ ПОТЕРЬ В Л/М²
                if is_thinner:
                    # Для растворителя: используем сохраненное значение из WET_THICKNESS
                    pract_consumption_l = row_data[self.WET_THICKNESS] if row_data[self.WET_THICKNESS] is not None else 0
                else:
                    # Для обычных покрытий: 1 / практическая укрывистость
                    if row_data[self.PRACT_COVERING] and row_data[self.PRACT_COVERING] > 0:
                        pract_consumption_l = 1 / row_data[self.PRACT_COVERING]
                    else:
                        pract_consumption_l = 0
                export_data.append(self.round_value(pract_consumption_l))  # P столбец - расход с учетом потерь л/м²
                
                # Расход с учетом потерь кг/м2 (уже есть в данных)
                export_data.append(self.round_value(row_data[self.PRACT_CONSUMPTION_KG] if row_data[self.PRACT_CONSUMPTION_KG] is not None else 0))  # Q столбец - расход с учетом потерь кг/м2
                
                # Стоимость по теоретическому расходу = теоретический расход кг/м2 * цена за кг
                theor_cost = (row_data[self.THEOR_CONSUMPTION_KG] or 0) * (row_data[self.PRICE_KG] or 0)
                export_data.append(self.round_value(theor_cost))  # R столбец
                
                # Стоимость с учетом потерь
                export_data.append(self.round_value(row_data[self.COST] if row_data[self.COST] is not None else 0))  # S столбец - стоимость с учетом потерь
                
                # РАСЧЕТ КОЛИЧЕСТВА МАТЕРИАЛА ПО ТЕОРЕТИЧЕСКОМУ РАСХОДУ
                # Количество в литрах = теоретический расход (л/м²) * площадь
                theor_material_liters = theor_consumption_l * area
                export_data.append(self.round_value(theor_material_liters))  # T столбец - количество по теоретическому расходу в литрах
                
                # Количество в килограммах = теоретический расход (кг/м²) * площадь
                theor_material_kg = (row_data[self.THEOR_CONSUMPTION_KG] or 0) * area
                export_data.append(self.round_value(theor_material_kg))  # U столбец - количество по теоретическому расходу в кг
                
                # СТОИМОСТЬ МАТЕРИАЛОВ ПО ТЕОРЕТИЧЕСКОМУ РАСХОДУ
                # Стоимость = количество материала (кг) * цена за кг
                theor_material_cost = theor_material_kg * (row_data[self.PRICE_KG] or 0)
                export_data.append(self.round_value(theor_material_cost))  # V столбец - стоимость материалов по теоретическому расходу
                
                # РАСЧЕТ КОЛИЧЕСТВА МАТЕРИАЛА С УЧЕТОМ ПОТЕРЬ
                # Количество в литрах = расход с учетом потерь (л/м²) * площадь
                pract_material_liters = pract_consumption_l * area
                export_data.append(self.round_value(pract_material_liters))  # W столбец - количество с учетом потерь в литрах
                
                # Количество в килограммах = расход с учетом потерь (кг/м²) * площадь
                pract_material_kg = (row_data[self.PRACT_CONSUMPTION_KG] or 0) * area
                export_data.append(self.round_value(pract_material_kg))  # X столбец - количество с учетом потерь в кг
                
                # СТОИМОСТЬ МАТЕРИАЛОВ С УЧЕТОМ ПОТЕРЬ
                # Стоимость = количество материала (кг) * цена за кг
                pract_material_cost = pract_material_kg * (row_data[self.PRICE_KG] or 0)
                export_data.append(self.round_value(pract_material_cost))  # Y столбец - стоимость материалов с учетом потерь
                
                # Суммируем общее количество
                total_theor_material_liters += theor_material_liters
                total_theor_material_kg += theor_material_kg
                total_pract_material_liters += pract_material_liters
                total_pract_material_kg += pract_material_kg
                total_theor_material_cost += theor_material_cost
                total_pract_material_cost += pract_material_cost
                
                # Суммируем расходы в л/м² только для основных слоев (без растворителей)
                if not is_thinner:
                    total_theor_consumption_l += theor_consumption_l
                    total_pract_consumption_l += pract_consumption_l
                
                # Записываем площадь в первый столбец
                cell = ws.cell(row=current_row, column=1)
                self.format_cell(cell, area)
                
                # Записываем остальные данные (теперь до столбца Y)
                for col_idx, value in enumerate(export_data):
                    cell = ws.cell(row=current_row, column=col_idx+2)
                    self.format_cell(cell, value)
                
                current_row += 1

            # Рассчитываем итоговые значения
            totals = self.calculate_total_values()
            totals['total_theor_material_liters'] = total_theor_material_liters
            totals['total_theor_material_kg'] = total_theor_material_kg
            totals['total_pract_material_liters'] = total_pract_material_liters
            totals['total_pract_material_kg'] = total_pract_material_kg
            totals['total_theor_material_cost'] = total_theor_material_cost
            totals['total_pract_material_cost'] = total_pract_material_cost
            totals['total_theor_consumption_l'] = total_theor_consumption_l
            totals['total_pract_consumption_l'] = total_pract_consumption_l

            # ИТОГОВАЯ СТРОКА с сложными объединениями ячеек
            total_row = current_row

            # Объединяем ячейки A-F для надписи "Толщина покрытия (мкм)"
            self.safe_merge_cells(ws, f'A{total_row}:F{total_row}')
            ws[f'A{total_row}'] = 'Толщина покрытия (мкм)'
            ws[f'A{total_row}'].alignment = Alignment(horizontal='center', vertical='center')

            # Объединяем ячейки I-M для надписи "Итого по таблице"
            self.safe_merge_cells(ws, f'I{total_row}:M{total_row}')
            ws[f'I{total_row}'] = 'Итого по таблице'
            ws[f'I{total_row}'].alignment = Alignment(horizontal='center', vertical='center')

            # Заполняем значения в итоговой строке с правильным форматированием
            values_row = {
                f'H{total_row}': self.round_value(totals['total_dry_thickness']),
                f'N{total_row}': self.round_value(totals['total_theor_consumption_l']),  # Итого теоретический расход л/м²
                f'O{total_row}': self.round_value(totals['total_consumption_kg']),
                f'P{total_row}': self.round_value(totals['total_pract_consumption_l']),  # Итого практический расход л/м²
                f'Q{total_row}': self.round_value(totals['total_consumption_with_losses']),
                f'R{total_row}': self.round_value(totals['total_theor_cost']),
                f'S{total_row}': self.round_value(totals['total_cost']),
                f'T{total_row}': self.round_value(totals['total_theor_material_liters']),  # Итого в литрах по теоретическому расходу
                f'U{total_row}': self.round_value(totals['total_theor_material_kg']),  # Итого в кг по теоретическому расходу
                f'V{total_row}': self.round_value(totals['total_theor_material_cost']),  # Итого стоимость по теоретическому расходу
                f'W{total_row}': self.round_value(totals['total_pract_material_liters']),  # Итого в литрах с учетом потерь
                f'X{total_row}': self.round_value(totals['total_pract_material_kg']),  # Итого в кг с учетом потерь
                f'Y{total_row}': self.round_value(totals['total_pract_material_cost'])  # Итого стоимость с учетом потерь
            }

            # Применяем форматирование ко всем числовым ячейкам в строке "Итого по таблице"
            for cell_ref, value in values_row.items():
                cell = ws[cell_ref]
                # Определяем формат чисел в зависимости от типа данных
                if 'стоимость' in cell_ref.lower() or 'cost' in cell_ref.lower():
                    # Для стоимостей используем формат с 2 знаками после запятой
                    self.format_cell(cell, value, number_format='#,##0.00')
                elif 'расход' in cell_ref.lower() or 'consumption' in cell_ref.lower():
                    # Для расходов используем формат с 3 знаками после запятой
                    self.format_cell(cell, value, number_format='#,##0.000')
                elif 'толщина' in cell_ref.lower() or 'thickness' in cell_ref.lower():
                    # Для толщины используем формат с 1 знаком после запятой
                    self.format_cell(cell, value, number_format='#,##0.0')
                else:
                    # По умолчанию используем формат с 3 знаками после запятой
                    self.format_cell(cell, value, number_format='#,##0.000')

            # Добавляем границы для ВСЕХ ячеек в итоговой строке
            for col in range(1, 26):  # A through Y
                cell = ws.cell(row=total_row, column=col)
                cell.border = Border(
                    left=Side(style='thin'),
                    right=Side(style='thin'),
                    top=Side(style='thin'),
                    bottom=Side(style='thin')
                )
                cell.alignment = Alignment(horizontal='center', vertical='center', wrap_text=True)

            # Устанавливаем ширину столбцов
            column_widths = {
                'A': 10, 'B': 35, 'C': 20, 'D': 10, 'E': 11,
                'F': 10, 'G': 10, 'H': 10, 'I': 10, 'J': 10,
                'K': 10, 'L': 10, 'M': 10, 'N': 10, 'O': 10,
                'P': 10, 'Q': 10, 'R': 15, 'S': 15, 'T': 12,
                'U': 12, 'V': 15, 'W': 12, 'X': 12, 'Y': 15
            }

            for column, width in column_widths.items():
                ws.column_dimensions[column].width = width

            # Сохраняем файл
            file_path = filedialog.asksaveasfilename(
                defaultextension='.xlsx',
                filetypes=[("Excel files", "*.xlsx")],
                title="Сохранить файл Excel"
            )
            if file_path:
                wb.save(file_path)
                messagebox.showinfo("Успех", "Данные успешно экспортированы в Excel!")
                
        except Exception as e:
            logging.error(f"Ошибка экспорта: {e}")
            messagebox.showerror("Ошибка экспорта", f"Произошла ошибка при экспорте: {str(e)}")

    def open_coating_templates(self):
        """Открывает диалог управления шаблонными схемами покрытий"""
        try:
            CoatingTemplateDialog(self.master, self)
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось открыть шаблоны покрытий: {str(e)}")    
 
class CalculationPreviewDialog:
    """Диалоговое окно предпросмотра расчета с расширенной информацией о расходах"""
    
    def __init__(self, parent, main_app):
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("Предпросмотр расчета - Детальная информация")
        self.dialog.geometry("1400x800")
        self.main_app = main_app
        
        self.create_widgets()
        self.update_preview()
    
    def create_widgets(self):
        """Создает элементы интерфейса предпросмотра"""
        # Основной фрейм
        main_frame = ttk.Frame(self.dialog)
        main_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Заголовок и информация о площади
        header_frame = ttk.Frame(main_frame)
        header_frame.pack(fill="x", pady=5)
        
        title_label = ttk.Label(header_frame, text="ПРЕДПРОСМОТР РАСЧЕТА СИСТЕМЫ ПОКРЫТИЙ", 
                               font=("Arial", 12, "bold"))
        title_label.pack(pady=5)
        
        # Информация о системе
        self.info_frame = ttk.LabelFrame(main_frame, text="Сводная информация системы")
        self.info_frame.pack(fill="x", pady=5)
        
        self.info_label = ttk.Label(self.info_frame, text="", justify=tk.LEFT, font=("Arial", 9))
        self.info_label.pack(padx=10, pady=10, anchor="w")
        
        # Таблица слоев с расширенной информацией
        table_frame = ttk.LabelFrame(main_frame, text="Детализация по слоям")
        table_frame.pack(fill="both", expand=True, pady=5)
        
        # Создаем Treeview с расширенными колонками
        columns = [
            'Слой', 'Тип', 'Связующее', 'RAL', 'Толщина сух. мкм',
            'Теор. расход кг/м²', 'Теор. расход л/м²',
            'Практ. расход кг/м²', 'Практ. расход л/м²',
            'Теор. кол-во кг', 'Теор. кол-во л', 
            'Практ. кол-во кг', 'Практ. кол-во л',
            'Стоимость руб/м²'
        ]
        
        self.tree = ttk.Treeview(table_frame, columns=columns, show='headings', height=12)
        
        # Настраиваем колонки
        column_widths = {
            'Слой': 180, 'Тип': 80, 'Связующее': 120, 'RAL': 70, 'Толщина сух. мкм': 100,
            'Теор. расход кг/м²': 110, 'Теор. расход л/м²': 110,
            'Практ. расход кг/м²': 110, 'Практ. расход л/м²': 110,
            'Теор. кол-во кг': 100, 'Теор. кол-во л': 100,
            'Практ. кол-во кг': 100, 'Практ. кол-во л': 100,
            'Стоимость руб/м²': 100
        }
        
        for col in columns:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=column_widths.get(col, 100))
        
        # Скроллбары
        v_scrollbar = ttk.Scrollbar(table_frame, orient="vertical", command=self.tree.yview)
        h_scrollbar = ttk.Scrollbar(table_frame, orient="horizontal", command=self.tree.xview)
        
        self.tree.configure(yscrollcommand=v_scrollbar.set, xscrollcommand=h_scrollbar.set)
        
        v_scrollbar.pack(side="right", fill="y")
        h_scrollbar.pack(side="bottom", fill="x")
        self.tree.pack(fill="both", expand=True, padx=5, pady=5)
        
        # Панель управления
        control_frame = ttk.Frame(main_frame)
        control_frame.pack(fill="x", pady=10)
        
        ttk.Button(control_frame, text="Обновить расчет", 
                  command=self.update_preview).pack(side=tk.LEFT, padx=5)
        ttk.Button(control_frame, text="Быстрый экспорт в Excel", 
                  command=self.quick_export).pack(side=tk.LEFT, padx=5)
        ttk.Button(control_frame, text="Расширенный экспорт", 
                  command=self.advanced_export).pack(side=tk.LEFT, padx=5)
        ttk.Button(control_frame, text="Закрыть", 
                  command=self.dialog.destroy).pack(side=tk.RIGHT, padx=5)
    
    def get_area(self):
        """Получает площадь из основного приложения"""
        try:
            area_text = self.main_app.area_entry.get().strip()
            return float(area_text) if area_text else 1.0
        except ValueError:
            return 1.0
    
    def calculate_layer_consumption(self, layer, area):
        """Рассчитывает все виды расходов для слоя"""
        is_thinner = 'Разбавитель' in layer[0] or 'Растворитель' in layer[0]
        
        if is_thinner:
            # Для растворителей
            theor_consumption_kg_m2 = layer[self.main_app.THEOR_CONSUMPTION_KG] if layer[self.main_app.THEOR_CONSUMPTION_KG] is not None else 0
            pract_consumption_kg_m2 = layer[self.main_app.PRACT_CONSUMPTION_KG] if layer[self.main_app.PRACT_CONSUMPTION_KG] is not None else 0
            
            # Расчет в литрах
            density = layer[self.main_app.DENSITY] if layer[self.main_app.DENSITY] and layer[self.main_app.DENSITY] > 0 else 1.0
            theor_consumption_l_m2 = theor_consumption_kg_m2 / density
            pract_consumption_l_m2 = pract_consumption_kg_m2 / density
            
            # Количества на заданную площадь
            theor_quantity_kg = theor_consumption_kg_m2 * area
            theor_quantity_l = theor_consumption_l_m2 * area
            pract_quantity_kg = pract_consumption_kg_m2 * area
            pract_quantity_l = pract_consumption_l_m2 * area
            
            layer_type = "Растворитель"
            dry_thickness = "-"
            
        else:
            # Для основных покрытий
            theor_consumption_kg_m2 = layer[self.main_app.THEOR_CONSUMPTION_KG] if layer[self.main_app.THEOR_CONSUMPTION_KG] is not None else 0
            pract_consumption_kg_m2 = layer[self.main_app.PRACT_CONSUMPTION_KG] if layer[self.main_app.PRACT_CONSUMPTION_KG] is not None else 0
            
            # Расчет в литрах
            density = layer[self.main_app.DENSITY] if layer[self.main_app.DENSITY] and layer[self.main_app.DENSITY] > 0 else 1.0
            theor_consumption_l_m2 = theor_consumption_kg_m2 / density
            pract_consumption_l_m2 = pract_consumption_kg_m2 / density
            
            # Количества на заданную площадь
            theor_quantity_kg = theor_consumption_kg_m2 * area
            theor_quantity_l = theor_consumption_l_m2 * area
            pract_quantity_kg = pract_consumption_kg_m2 * area
            pract_quantity_l = pract_consumption_l_m2 * area
            
            layer_type = "Покрытие"
            dry_thickness = f"{layer[self.main_app.DRY_THICKNESS]:.1f}" if layer[self.main_app.DRY_THICKNESS] is not None else "0.0"
        
        cost = layer[self.main_app.COST] if layer[self.main_app.COST] is not None else 0
        
        return {
            'name': layer[0],
            'type': layer_type,
            'binder': layer[1] if layer[1] else "-",
            'ral': layer[2] if layer[2] else "-",
            'dry_thickness': dry_thickness,
            'theor_consumption_kg_m2': theor_consumption_kg_m2,
            'theor_consumption_l_m2': theor_consumption_l_m2,
            'pract_consumption_kg_m2': pract_consumption_kg_m2,
            'pract_consumption_l_m2': pract_consumption_l_m2,
            'theor_quantity_kg': theor_quantity_kg,
            'theor_quantity_l': theor_quantity_l,
            'pract_quantity_kg': pract_quantity_kg,
            'pract_quantity_l': pract_quantity_l,
            'cost': cost,
            'is_thinner': is_thinner
        }
    
    def update_preview(self):
        """Обновляет данные в предпросмотре"""
        area = self.get_area()
        
        # Рассчитываем общие параметры системы
        total_cost = self.main_app.calculate_total_cost()
        total_thickness = self.main_app.calculate_total_dry_thickness()
        total_theor_consumption_kg = self.main_app.calculate_total_theor_consumption_kg()
        total_theor_consumption_l = self.main_app.calculate_total_theor_consumption_l()
        
        # Рассчитываем практические расходы
        total_pract_consumption_kg = 0.0
        total_pract_consumption_l = 0.0
        total_theor_quantity_kg = 0.0
        total_theor_quantity_l = 0.0
        total_pract_quantity_kg = 0.0
        total_pract_quantity_l = 0.0
        
        # Собираем данные по слоям
        layers_data = []
        for layer in self.main_app.layers:
            layer_data = self.calculate_layer_consumption(layer, area)
            layers_data.append(layer_data)
            
            # Суммируем общие количества (все слои)
            total_theor_quantity_kg += layer_data['theor_quantity_kg']
            total_theor_quantity_l += layer_data['theor_quantity_l']
            total_pract_quantity_kg += layer_data['pract_quantity_kg']
            total_pract_quantity_l += layer_data['pract_quantity_l']
            
            # Суммируем практические расходы (только покрытия)
            if not layer_data['is_thinner']:
                total_pract_consumption_kg += layer_data['pract_consumption_kg_m2']
                total_pract_consumption_l += layer_data['pract_consumption_l_m2']
        
        # Обновляем сводную информацию
        info_text = (
            f"▪ Общая стоимость системы: {total_cost:.2f} руб/м²\n"
            f"▪ Общая толщина покрытия: {total_thickness:.1f} мкм\n"
            f"▪ Площадь поверхности: {area} м²\n\n"
            
            f"РАСХОДЫ НА 1 м²:\n"
            f"▪ Теоретический: {total_theor_consumption_kg:.3f} кг/м² ({total_theor_consumption_l:.3f} л/м²)\n"
            f"▪ Практический: {total_pract_consumption_kg:.3f} кг/м² ({total_pract_consumption_l:.3f} л/м²)\n\n"
            
            f"ОБЩЕЕ КОЛИЧЕСТВО МАТЕРИАЛОВ НА {area} м²:\n"
            f"▪ По теоретическому расходу: {total_theor_quantity_kg:.3f} кг ({total_theor_quantity_l:.3f} л)\n"
            f"▪ По практическому расходу: {total_pract_quantity_kg:.3f} кг ({total_pract_quantity_l:.3f} л)\n\n"
            
            f"Количество слоев: {len([l for l in self.main_app.layers if not l[0].startswith(('Разбавитель', 'Растворитель'))])} покрытий + "
            f"{len([l for l in self.main_app.layers if l[0].startswith(('Разбавитель', 'Растворитель'))])} растворителей"
        )
        self.info_label.config(text=info_text)
        
        # Обновляем таблицу
        for item in self.tree.get_children():
            self.tree.delete(item)
            
        for layer_data in layers_data:
            values = (
                layer_data['name'],
                layer_data['type'],
                layer_data['binder'],
                layer_data['ral'],
                layer_data['dry_thickness'],
                f"{layer_data['theor_consumption_kg_m2']:.3f}",
                f"{layer_data['theor_consumption_l_m2']:.3f}",
                f"{layer_data['pract_consumption_kg_m2']:.3f}",
                f"{layer_data['pract_consumption_l_m2']:.3f}",
                f"{layer_data['theor_quantity_kg']:.3f}",
                f"{layer_data['theor_quantity_l']:.3f}",
                f"{layer_data['pract_quantity_kg']:.3f}",
                f"{layer_data['pract_quantity_l']:.3f}",
                f"{layer_data['cost']:.2f}"
            )
            
            self.tree.insert('', 'end', values=values)
    
    def quick_export(self):
        """Быстрый экспорт основных данных в Excel"""
        try:
            area = self.get_area()
            wb = Workbook()
            ws = wb.active
            ws.title = "Быстрый экспорт расчета"
            
            # Заголовок
            ws['A1'] = "БЫСТРЫЙ ЭКСПОРТ РАСЧЕТА СИСТЕМЫ ПОКРЫТИЙ"
            ws['A1'].font = Font(bold=True, size=14)
            ws.merge_cells('A1:N1')
            
            # Основная информация
            total_cost = self.main_app.calculate_total_cost()
            total_thickness = self.main_app.calculate_total_dry_thickness()
            
            ws['A3'] = "Сводная информация системы:"
            ws['A3'].font = Font(bold=True)
            
            info_rows = [
                f"Общая стоимость системы: {total_cost:.2f} руб/м²",
                f"Общая толщина покрытия: {total_thickness:.1f} мкм",
                f"Площадь поверхности: {area} м²",
                f"Дата расчета: {datetime.now().strftime('%Y-%m-%d %H:%M')}"
            ]
            
            for i, text in enumerate(info_rows, 4):
                ws[f'A{i}'] = text
                ws.merge_cells(f'A{i}:N{i}')
            
            # Заголовки таблицы
            headers = [
                'Слой', 'Тип', 'Связующее', 'RAL', 'Толщина сух. мкм',
                'Теор. расход кг/м²', 'Теор. расход л/м²',
                'Практ. расход кг/м²', 'Практ. расход л/м²',
                'Теор. кол-во кг', 'Теор. кол-во л', 
                'Практ. кол-во кг', 'Практ. кол-во л',
                'Стоимость руб/м²'
            ]
            
            start_row = len(info_rows) + 6
            
            for col, header in enumerate(headers, 1):
                cell = ws.cell(row=start_row, column=col)
                cell.value = header
                cell.font = Font(bold=True)
                cell.border = Border(left=Side(style='thin'), right=Side(style='thin'),
                                top=Side(style='thin'), bottom=Side(style='thin'))
                cell.alignment = Alignment(horizontal='center', vertical='center', wrap_text=True)
                cell.fill = PatternFill(start_color="E6E6FA", end_color="E6E6FA", fill_type="solid")
            
            # Данные слоев
            current_row = start_row + 1
            total_theor_quantity_kg = 0
            total_theor_quantity_l = 0
            total_pract_quantity_kg = 0
            total_pract_quantity_l = 0
            total_cost_sum = 0
            
            for layer in self.main_app.layers:
                layer_data = self.calculate_layer_consumption(layer, area)
                
                values = [
                    layer_data['name'],
                    layer_data['type'],
                    layer_data['binder'],
                    layer_data['ral'],
                    layer_data['dry_thickness'] if not layer_data['is_thinner'] else "-",
                    layer_data['theor_consumption_kg_m2'],
                    layer_data['theor_consumption_l_m2'],
                    layer_data['pract_consumption_kg_m2'],
                    layer_data['pract_consumption_l_m2'],
                    layer_data['theor_quantity_kg'],
                    layer_data['theor_quantity_l'],
                    layer_data['pract_quantity_kg'],
                    layer_data['pract_quantity_l'],
                    layer_data['cost']
                ]
                
                # Суммируем итоги
                total_theor_quantity_kg += layer_data['theor_quantity_kg']
                total_theor_quantity_l += layer_data['theor_quantity_l']
                total_pract_quantity_kg += layer_data['pract_quantity_kg']
                total_pract_quantity_l += layer_data['pract_quantity_l']
                total_cost_sum += layer_data['cost']
                
                # Записываем строку
                for col, value in enumerate(values, 1):
                    cell = ws.cell(row=current_row, column=col)
                    
                    if isinstance(value, (int, float)):
                        cell.value = value
                        # Форматирование чисел
                        if col in [6, 7, 8, 9, 10, 11, 12, 13]:  # Расходы и количества
                            cell.number_format = '0.000'
                        elif col == 14:  # Стоимость
                            cell.number_format = '#,##0.00'
                        elif col == 5 and value != "-":  # Толщина
                            cell.number_format = '0.0'
                    else:
                        cell.value = value
                    
                    cell.border = Border(left=Side(style='thin'), right=Side(style='thin'),
                                    top=Side(style='thin'), bottom=Side(style='thin'))
                    cell.alignment = Alignment(horizontal='center', vertical='center', wrap_text=True)
                
                current_row += 1
            
            # Итоговая строка
            total_row = current_row
            ws.cell(row=total_row, column=1).value = "ВСЕГО ПО СИСТЕМЕ:"
            ws.merge_cells(f'A{total_row}:E{total_row}')
            
            total_values = [
                "", "", "", "", "",  # Объединенные ячейки
                "", "", "", "",  # Пропускаем расходы на м²
                total_theor_quantity_kg,
                total_theor_quantity_l,
                total_pract_quantity_kg,
                total_pract_quantity_l,
                total_cost_sum
            ]
            
            for col, value in enumerate(total_values, 1):
                if value != "":
                    cell = ws.cell(row=total_row, column=col)
                    cell.value = value
                    cell.font = Font(bold=True)
                    cell.fill = PatternFill(start_color="C6EFCE", end_color="C6EFCE", fill_type="solid")
                    
                    if col in [10, 11, 12, 13]:  # Количества
                        cell.number_format = '0.000'
                    elif col == 14:  # Стоимость
                        cell.number_format = '#,##0.00'
                    
                    cell.border = Border(left=Side(style='thin'), right=Side(style='thin'),
                                    top=Side(style='thin'), bottom=Side(style='thin'))
                    cell.alignment = Alignment(horizontal='center', vertical='center', wrap_text=True)
            
            # Настройка ширины столбцов
            column_widths = {
                'A': 25, 'B': 10, 'C': 15, 'D': 10, 'E': 12,
                'F': 12, 'G': 12, 'H': 12, 'I': 12,
                'J': 12, 'K': 12, 'L': 12, 'M': 12, 'N': 12
            }
            
            for col, width in column_widths.items():
                ws.column_dimensions[col].width = width
            
            # Сохраняем файл
            file_path = filedialog.asksaveasfilename(
                defaultextension='.xlsx',
                filetypes=[("Excel files", "*.xlsx")],
                title="Сохранить быстрый экспорт расчета"
            )
            
            if file_path:
                wb.save(file_path)
                messagebox.showinfo("Успех", "Быстрый экспорт выполнен успешно!")
                
        except Exception as e:
            messagebox.showerror("Ошибка", f"Ошибка при быстром экспорте: {str(e)}")
    
    def advanced_export(self):
        """Расширенный экспорт с дополнительной аналитикой"""
        try:
            area = self.get_area()
            wb = Workbook()
            
            # Лист с детализацией
            ws_detail = wb.active
            ws_detail.title = "Детализация расчета"
            
            # Заголовок
            ws_detail['A1'] = "ДЕТАЛИЗИРОВАННЫЙ РАСЧЕТ СИСТЕМЫ ПОКРЫТИЙ"
            ws_detail['A1'].font = Font(bold=True, size=14)
            ws_detail.merge_cells('A1:O1')
            
            # Аналитическая информация
            total_cost = self.main_app.calculate_total_cost()
            total_thickness = self.main_app.calculate_total_dry_thickness()
            total_theor_consumption_kg = self.main_app.calculate_total_theor_consumption_kg()
            total_theor_consumption_l = self.main_app.calculate_total_theor_consumption_l()
            
            # Рассчитываем практические расходы
            total_pract_consumption_kg = 0
            total_pract_consumption_l = 0
            for layer in self.main_app.layers:
                if 'Разбавитель' not in layer[0] and 'Растворитель' not in layer[0]:
                    pract_kg = layer[self.main_app.PRACT_CONSUMPTION_KG] if layer[self.main_app.PRACT_CONSUMPTION_KG] is not None else 0
                    density = layer[self.main_app.DENSITY] if layer[self.main_app.DENSITY] and layer[self.main_app.DENSITY] > 0 else 1.0
                    pract_l = pract_kg / density
                    total_pract_consumption_kg += pract_kg
                    total_pract_consumption_l += pract_l
            
            ws_detail['A3'] = "АНАЛИТИКА СИСТЕМЫ:"
            ws_detail['A3'].font = Font(bold=True)
            ws_detail.merge_cells('A3:O3')
            
            analytics = [
                f"Площадь поверхности: {area} м²",
                f"Общая стоимость системы: {total_cost:.2f} руб/м²",
                f"Стоимость на всю площадь: {total_cost * area:.2f} руб",
                f"Общая толщина покрытия: {total_thickness:.1f} мкм",
                "",
                "РАСХОД МАТЕРИАЛОВ НА 1 м²:",
                f"  Теоретический: {total_theor_consumption_kg:.3f} кг/м² ({total_theor_consumption_l:.3f} л/м²)",
                f"  Практический: {total_pract_consumption_kg:.3f} кг/м² ({total_pract_consumption_l:.3f} л/м²)",
                f"  Разница: {(total_pract_consumption_kg - total_theor_consumption_kg):.3f} кг/м² ({(total_pract_consumption_l - total_theor_consumption_l):.3f} л/м²)",
                "",
                "ОБЩЕЕ КОЛИЧЕСТВО МАТЕРИАЛОВ:"
            ]
            
            # Рассчитываем общие количества
            total_theor_quantity_kg = total_theor_consumption_kg * area
            total_theor_quantity_l = total_theor_consumption_l * area
            total_pract_quantity_kg = total_pract_consumption_kg * area
            total_pract_quantity_l = total_pract_consumption_l * area
            
            analytics.extend([
                f"  По теоретическому расходу: {total_theor_quantity_kg:.3f} кг ({total_theor_quantity_l:.3f} л)",
                f"  По практическому расходу: {total_pract_quantity_kg:.3f} кг ({total_pract_quantity_l:.3f} л)",
                f"  Необходимый запас: {(total_pract_quantity_kg - total_theor_quantity_kg):.3f} кг ({(total_pract_quantity_l - total_theor_quantity_l):.3f} л)",
                "",
                f"Коэффициент потерь: {(total_pract_consumption_kg/total_theor_consumption_kg - 1)*100:.1f}%",
                f"Дата расчета: {datetime.now().strftime('%Y-%m-%d %H:%M')}"
            ])
            
            for i, text in enumerate(analytics, 4):
                ws_detail[f'A{i}'] = text
                if i >= 9:  # Выделяем важные строки
                    ws_detail[f'A{i}'].font = Font(bold=(i in [6, 11, 15, 16, 17]))
                if i in [6, 11]:
                    ws_detail[f'A{i}'].font = Font(bold=True, size=11)
            
            # Данные слоев (аналогично быстрому экспорту, но с дополнительными колонками)
            start_row = len(analytics) + 6
            
            # Остальной код аналогичен quick_export, но с дополнительными колонками
            # ... (можно скопировать из quick_export и расширить)
            
            # Лист с итогами
            ws_summary = wb.create_sheet("Итоги и рекомендации")
            
            # Заполняем лист с итогами
            ws_summary['A1'] = "ИТОГИ И РЕКОМЕНДАЦИИ"
            ws_summary['A1'].font = Font(bold=True, size=14)
            ws_summary.merge_cells('A1:D1')
            
            recommendations = [
                "РЕКОМЕНДУЕМЫЕ ДЕЙСТВИЯ:",
                f"1. Закупить материалов по практическому расходу: {total_pract_quantity_kg:.1f} кг",
                f"2. Учесть запас на потери: {(total_pract_quantity_kg - total_theor_quantity_kg):.1f} кг",
                f"3. Планируемый бюджет: {total_cost * area:.0f} руб",
                "",
                "ТЕХНИЧЕСКИЕ ХАРАКТЕРИСТИКИ:",
                f"• Общая толщина системы: {total_thickness} мкм",
                f"• Количество слоев покрытий: {len([l for l in self.main_app.layers if 'Разбавитель' not in l[0] and 'Растворитель' not in l[0]])}",
                f"• Количество растворителей: {len([l for l in self.main_app.layers if 'Разбавитель' in l[0] or 'Растворитель' in l[0]])}",
                f"• Средняя стоимость м²: {total_cost:.2f} руб"
            ]
            
            for i, text in enumerate(recommendations, 3):
                ws_summary[f'A{i}'] = text
                if i in [3, 9]:
                    ws_summary[f'A{i}'].font = Font(bold=True)
            
            # Сохраняем файл
            file_path = filedialog.asksaveasfilename(
                defaultextension='.xlsx',
                filetypes=[("Excel files", "*.xlsx")],
                title="Сохранить расширенный экспорт расчета"
            )
            
            if file_path:
                wb.save(file_path)
                messagebox.showinfo("Успех", "Расширенный экспорт выполнен успешно!")
                
        except Exception as e:
            messagebox.showerror("Ошибка", f"Ошибка при расширенном экспорте: {str(e)}")

class SelectiveExportDialog:
    """Диалоговое окно выборочного экспорта на основе полного формата экспорта"""
    
    def __init__(self, parent, main_app):
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("Выборочный экспорт - Полный формат")
        self.dialog.geometry("800x600")
        self.main_app = main_app
        self.selected_columns = {}
        
        self.create_widgets()
    
    def create_widgets(self):
        """Создает элементы интерфейса выборочного экспорта"""
        main_frame = ttk.Frame(self.dialog)
        main_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Заголовок
        title_label = ttk.Label(main_frame, text="ВЫБЕРИТЕ СТОЛБЦЫ ДЛЯ ЭКСПОРТА В ПОЛНОМ ФОРМАТЕ", 
                               font=("Arial", 11, "bold"))
        title_label.pack(pady=10)
        
        # Описание
        desc_label = ttk.Label(main_frame, text="Будут экспортированы только выбранные столбцы, сохраняя структуру полного отчета",
                              font=("Arial", 9), foreground="gray")
        desc_label.pack(pady=5)
        
        # Фрейм для чекбоксов
        check_frame = ttk.LabelFrame(main_frame, text="Столбцы полного отчета")
        check_frame.pack(fill="both", expand=True, pady=5)
        
        # Создаем скроллируемый фрейм для чекбоксов
        canvas = tk.Canvas(check_frame)
        scrollbar = ttk.Scrollbar(check_frame, orient="vertical", command=canvas.yview)
        self.scrollable_frame = ttk.Frame(canvas)
        
        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.pack(side="left", fill="both", expand=True, padx=5, pady=5)
        scrollbar.pack(side="right", fill="y")
        
        # Столбцы полного отчета (соответствуют экспорту из export_to_excel)
        column_groups = {
            "Основные данные": [
                ('name', 'Система покрытия'),
                ('binder', 'Связующее'),
                ('ral', 'Цвет (RAL)'),
                ('density', 'Плотность (кг/л)'),
                ('solid_content', 'Сухой остаток (%)')
            ],
            "Толщины покрытия": [
                ('wet_thickness', 'Толщина мокрая (мкм)'),
                ('dry_thickness', 'Толщина сухая (мкм)')
            ],
            "Укрывистость": [
                ('theor_covering', 'Укрывистость теор. (м²/л)'),
                ('losses', 'Потери (%)'),
                ('pract_covering', 'Укрывистость практ. (м²/л)')
            ],
            "Цены": [
                ('price_kg', 'Цена с НДС за кг (руб)'),
                ('price_liter', 'Цена с НДС за литр (руб)')
            ],
            "Теоретический расход": [
                ('theor_consumption_l_m2', 'Теор. расход (л/м²)'),
                ('theor_consumption_kg_m2', 'Теор. расход (кг/м²)')
            ],
            "Расход с учетом потерь": [
                ('pract_consumption_l_m2', 'Практ. расход (л/м²)'),
                ('pract_consumption_kg_m2', 'Практ. расход (кг/м²)')
            ],
            "Стоимости": [
                ('theor_cost_m2', 'Стоимость теор. (руб/м²)'),
                ('pract_cost_m2', 'Стоимость практ. (руб/м²)')
            ],
            "Количество по теор. расходу": [
                ('theor_quantity_l', 'Теор. количество (л)'),
                ('theor_quantity_kg', 'Теор. количество (кг)')
            ],
            "Стоимость по теор. расходу": [
                ('theor_material_cost', 'Стоимость теор. (руб)')
            ],
            "Количество с учетом потерь": [
                ('pract_quantity_l', 'Практ. количество (л)'),
                ('pract_quantity_kg', 'Практ. количество (кг)')
            ],
            "Стоимость с учетом потерь": [
                ('pract_material_cost', 'Стоимость практ. (руб)')
            ]
        }
        
        # Создаем чекбоксы для каждой группы
        for group_name, columns in column_groups.items():
            group_frame = ttk.LabelFrame(self.scrollable_frame, text=group_name)
            group_frame.pack(fill="x", padx=5, pady=5)
            
            for key, display_name in columns:
                var = tk.BooleanVar(value=True)  # По умолчанию все выбраны
                self.selected_columns[key] = var
                
                cb = ttk.Checkbutton(group_frame, text=display_name, variable=var)
                cb.pack(anchor="w", padx=10, pady=2)
        
        # Кнопки управления выбором
        control_frame = ttk.Frame(main_frame)
        control_frame.pack(fill="x", pady=10)
        
        ttk.Button(control_frame, text="Выбрать все", 
                  command=self.select_all).pack(side=tk.LEFT, padx=5)
        ttk.Button(control_frame, text="Снять все", 
                  command=self.deselect_all).pack(side=tk.LEFT, padx=5)
        ttk.Button(control_frame, text="Только основные", 
                  command=self.basic_selection).pack(side=tk.LEFT, padx=5)
        
        # Кнопки действия
        action_frame = ttk.Frame(main_frame)
        action_frame.pack(fill="x", pady=10)
        
        ttk.Button(action_frame, text="Выполнить выборочный экспорт", 
                  command=self.execute_export, style="Accent.TButton").pack(side=tk.LEFT, padx=5)
        ttk.Button(action_frame, text="Предпросмотр выбранных столбцов", 
                  command=self.preview_selection).pack(side=tk.LEFT, padx=5)
        ttk.Button(action_frame, text="Отмена", 
                  command=self.dialog.destroy).pack(side=tk.RIGHT, padx=5)
    
    def select_all(self):
        """Выбирает все столбцы"""
        for var in self.selected_columns.values():
            var.set(True)
    
    def deselect_all(self):
        """Снимает выбор со всех столбцов"""
        for var in self.selected_columns.values():
            var.set(False)
    
    def basic_selection(self):
        """Устанавливает выбор только основных столбцов"""
        basic_columns = ['name', 'binder', 'ral', 'dry_thickness', 
                        'theor_consumption_kg_m2', 'pract_consumption_kg_m2', 
                        'pract_cost_m2']
        
        for key, var in self.selected_columns.items():
            var.set(key in basic_columns)
    
    def get_column_mapping(self):
        """Возвращает маппинг ключей на заголовки и методы расчета"""
        return {
            'name': ('Система покрытия', lambda layer: layer[self.main_app.NAME]),
            'binder': ('Связующее', lambda layer: layer[self.main_app.BINDER]),
            'ral': ('Цвет (RAL)', lambda layer: layer[self.main_app.RAL]),
            'density': ('Плотность (кг/л)', lambda layer: layer[self.main_app.DENSITY]),
            'solid_content': ('Сухой остаток (%)', lambda layer: layer[self.main_app.SOLID_CONTENT]),
            'wet_thickness': ('Толщина мокрая (мкм)', lambda layer: layer[self.main_app.WET_THICKNESS]),
            'dry_thickness': ('Толщина сухая (мкм)', lambda layer: layer[self.main_app.DRY_THICKNESS]),
            'theor_covering': ('Укрывистость теор. (м²/л)', lambda layer: layer[self.main_app.THEOR_COVERING]),
            'losses': ('Потери (%)', lambda layer: layer[self.main_app.LOSSES]),
            'pract_covering': ('Укрывистость практ. (м²/л)', lambda layer: layer[self.main_app.PRACT_COVERING]),
            'price_kg': ('Цена с НДС за кг (руб)', lambda layer: layer[self.main_app.PRICE_KG]),
            'price_liter': ('Цена с НДС за литр (руб)', lambda layer: layer[self.main_app.PRICE_LITER]),
            'theor_consumption_l_m2': ('Теор. расход (л/м²)', self.calculate_theor_consumption_l),
            'theor_consumption_kg_m2': ('Теор. расход (кг/м²)', lambda layer: layer[self.main_app.THEOR_CONSUMPTION_KG]),
            'pract_consumption_l_m2': ('Практ. расход (л/м²)', self.calculate_pract_consumption_l),
            'pract_consumption_kg_m2': ('Практ. расход (кг/м²)', lambda layer: layer[self.main_app.PRACT_CONSUMPTION_KG]),
            'theor_cost_m2': ('Стоимость теор. (руб/м²)', self.calculate_theor_cost),
            'pract_cost_m2': ('Стоимость практ. (руб/м²)', lambda layer: layer[self.main_app.COST]),
            'theor_quantity_l': ('Теор. количество (л)', self.calculate_theor_quantity_l),
            'theor_quantity_kg': ('Теор. количество (кг)', self.calculate_theor_quantity_kg),
            'theor_material_cost': ('Стоимость теор. (руб)', self.calculate_theor_material_cost),
            'pract_quantity_l': ('Практ. количество (л)', self.calculate_pract_quantity_l),
            'pract_quantity_kg': ('Практ. количество (кг)', self.calculate_pract_quantity_kg),
            'pract_material_cost': ('Стоимость практ. (руб)', self.calculate_pract_material_cost)
        }
    
    def calculate_theor_consumption_l(self, layer):
        """Расчет теоретического расхода в л/м²"""
        if layer[self.main_app.DENSITY] and layer[self.main_app.DENSITY] > 0:
            return layer[self.main_app.THEOR_CONSUMPTION_KG] / layer[self.main_app.DENSITY] if layer[self.main_app.THEOR_CONSUMPTION_KG] is not None else 0
        return 0
    
    def calculate_pract_consumption_l(self, layer):
        """Расчет практического расхода в л/м²"""
        if layer[self.main_app.DENSITY] and layer[self.main_app.DENSITY] > 0:
            return layer[self.main_app.PRACT_CONSUMPTION_KG] / layer[self.main_app.DENSITY] if layer[self.main_app.PRACT_CONSUMPTION_KG] is not None else 0
        return 0
    
    def calculate_theor_cost(self, layer):
        """Расчет теоретической стоимости на м²"""
        return (layer[self.main_app.THEOR_CONSUMPTION_KG] or 0) * (layer[self.main_app.PRICE_KG] or 0)
    
    def get_area(self):
        """Получает площадь из основного приложения"""
        try:
            area_text = self.main_app.area_entry.get().strip()
            return float(area_text) if area_text else 1.0
        except ValueError:
            return 1.0
    
    def calculate_theor_quantity_l(self, layer):
        """Расчет теоретического количества в литрах"""
        area = self.get_area()
        consumption_l = self.calculate_theor_consumption_l(layer)
        return consumption_l * area
    
    def calculate_theor_quantity_kg(self, layer):
        """Расчет теоретического количества в кг"""
        area = self.get_area()
        return (layer[self.main_app.THEOR_CONSUMPTION_KG] or 0) * area
    
    def calculate_theor_material_cost(self, layer):
        """Расчет теоретической стоимости материалов"""
        quantity_kg = self.calculate_theor_quantity_kg(layer)
        return quantity_kg * (layer[self.main_app.PRICE_KG] or 0)
    
    def calculate_pract_quantity_l(self, layer):
        """Расчет практического количества в литрах"""
        area = self.get_area()
        consumption_l = self.calculate_pract_consumption_l(layer)
        return consumption_l * area
    
    def calculate_pract_quantity_kg(self, layer):
        """Расчет практического количества в кг"""
        area = self.get_area()
        return (layer[self.main_app.PRACT_CONSUMPTION_KG] or 0) * area
    
    def calculate_pract_material_cost(self, layer):
        """Расчет практической стоимости материалов"""
        quantity_kg = self.calculate_pract_quantity_kg(layer)
        return quantity_kg * (layer[self.main_app.PRICE_KG] or 0)
    
    def execute_export(self):
        """Выполняет выборочный экспорт в полном формате"""
        try:
            # Получаем выбранные столбцы
            selected_keys = [key for key, var in self.selected_columns.items() if var.get()]
            
            if not selected_keys:
                messagebox.showwarning("Предупреждение", "Выберите хотя бы один столбец для экспорта")
                return
            
            # Создаем Workbook
            wb = Workbook()
            ws = wb.active
            ws.title = "Выборочный экспорт"
            
            column_mapping = self.get_column_mapping()
            
            # Создаем заголовки в стиле полного экспорта
            self.create_selective_header(ws, selected_keys, column_mapping)
            
            # Записываем данные
            self.export_selective_data(ws, selected_keys, column_mapping)
            
            # Сохраняем файл
            file_path = filedialog.asksaveasfilename(
                defaultextension='.xlsx',
                filetypes=[("Excel files", "*.xlsx")],
                title="Сохранить выборочный экспорт"
            )
            
            if file_path:
                wb.save(file_path)
                messagebox.showinfo("Успех", "Выборочный экспорт выполнен успешно!")
                self.dialog.destroy()
                
        except Exception as e:
            messagebox.showerror("Ошибка", f"Ошибка при выборочном экспорте: {str(e)}")
    
    def create_selective_header(self, ws, selected_keys, column_mapping):
        """Создает заголовки для выборочного экспорта в стиле полного отчета"""
        # Основной заголовок
        ws['A1'] = "ВЫБОРОЧНЫЙ ЭКСПОРТ СИСТЕМЫ ПОКРЫТИЙ"
        ws['A1'].font = Font(bold=True, size=14)
        ws.merge_cells(f'A1:{get_column_letter(len(selected_keys))}1')
        
        # Информация о выборе
        ws['A2'] = f"Экспортированные столбцы: {len(selected_keys)} из {len(column_mapping)} | Дата: {datetime.now().strftime('%Y-%m-%d %H:%M')}"
        ws.merge_cells(f'A2:{get_column_letter(len(selected_keys))}2')
        
        # Заголовки столбцов
        for col, key in enumerate(selected_keys, 1):
            cell = ws.cell(row=4, column=col)
            cell.value = column_mapping[key][0]
            cell.font = Font(bold=True)
            cell.border = Border(left=Side(style='thin'), right=Side(style='thin'),
                            top=Side(style='thin'), bottom=Side(style='thin'))
            cell.alignment = Alignment(horizontal='center', vertical='center', wrap_text=True)
            cell.fill = PatternFill(start_color="E6E6FA", end_color="E6E6FA", fill_type="solid")
            
            # Настройка ширины столбцов
            ws.column_dimensions[get_column_letter(col)].width = 15
    
    def export_selective_data(self, ws, selected_keys, column_mapping):
        """Экспортирует данные выбранных столбцов"""
        area = self.get_area()
        current_row = 5
        
        # Записываем данные слоев
        for layer in self.main_app.layers:
            for col, key in enumerate(selected_keys, 1):
                display_name, calculation_func = column_mapping[key]
                value = calculation_func(layer)
                
                cell = ws.cell(row=current_row, column=col)
                cell.value = value
                cell.border = Border(left=Side(style='thin'), right=Side(style='thin'),
                                top=Side(style='thin'), bottom=Side(style='thin'))
                
                # Форматирование чисел
                if isinstance(value, (int, float)):
                    if any(x in display_name.lower() for x in ['цена', 'стоимость', 'руб']):
                        cell.number_format = '#,##0.00'
                    elif any(x in display_name.lower() for x in ['расход', 'плотность', 'количество']):
                        cell.number_format = '0.000'
                    elif any(x in display_name.lower() for x in ['толщина', 'остаток', 'потери']):
                        cell.number_format = '0.0'
                    elif 'укрывистость' in display_name.lower():
                        cell.number_format = '0.00'
                
                cell.alignment = Alignment(horizontal='center', vertical='center', wrap_text=True)
            
            current_row += 1
        
        # Добавляем итоговую информацию
        current_row += 1
        self.add_selective_totals(ws, selected_keys, column_mapping, current_row, area)
    
    def add_selective_totals(self, ws, selected_keys, column_mapping, start_row, area):
        """Добавляет итоговую информацию в выборочный экспорт"""
        # Рассчитываем общие итоги
        total_cost = self.main_app.calculate_total_cost()
        total_thickness = self.main_app.calculate_total_dry_thickness()
        total_theor_consumption_kg = self.main_app.calculate_total_theor_consumption_kg()
        total_theor_consumption_l = self.main_app.calculate_total_theor_consumption_l()
        
        # Рассчитываем практические расходы
        total_pract_consumption_kg = 0
        total_pract_consumption_l = 0
        for layer in self.main_app.layers:
            if 'Разбавитель' not in layer[0] and 'Растворитель' not in layer[0]:
                pract_kg = layer[self.main_app.PRACT_CONSUMPTION_KG] if layer[self.main_app.PRACT_CONSUMPTION_KG] is not None else 0
                density = layer[self.main_app.DENSITY] if layer[self.main_app.DENSITY] and layer[self.main_app.DENSITY] > 0 else 1.0
                pract_l = pract_kg / density
                total_pract_consumption_kg += pract_kg
                total_pract_consumption_l += pract_l
        
        # Записываем итоги
        ws.cell(row=start_row, column=1).value = "ИТОГИ СИСТЕМЫ:"
        ws.cell(row=start_row, column=1).font = Font(bold=True)
        ws.merge_cells(f'A{start_row}:{get_column_letter(len(selected_keys))}{start_row}')
        
        summary_rows = [
            f"Общая стоимость: {total_cost:.2f} руб/м²",
            f"Общая толщина: {total_thickness:.1f} мкм",
            f"Площадь: {area} м²",
            f"Теор. расход: {total_theor_consumption_kg:.3f} кг/м² ({total_theor_consumption_l:.3f} л/м²)",
            f"Практ. расход: {total_pract_consumption_kg:.3f} кг/м² ({total_pract_consumption_l:.3f} л/м²)",
            f"Общее теор. количество: {total_theor_consumption_kg * area:.3f} кг ({total_theor_consumption_l * area:.3f} л)",
            f"Общее практ. количество: {total_pract_consumption_kg * area:.3f} кг ({total_pract_consumption_l * area:.3f} л)"
        ]
        
        for i, text in enumerate(summary_rows, start_row + 1):
            ws.cell(row=i, column=1).value = text
            ws.merge_cells(f'A{i}:{get_column_letter(len(selected_keys))}{i}')
    
    def preview_selection(self):
        """Предпросмотр выбранных столбцов"""
        try:
            # Получаем выбранные столбцы
            selected_keys = [key for key, var in self.selected_columns.items() if var.get()]
            
            if not selected_keys:
                messagebox.showwarning("Предупреждение", "Выберите хотя бы один столбец для предпросмотра")
                return
            
            FullFormatPreviewDialog(self.dialog, self.main_app, selected_keys)
                
        except Exception as e:
            messagebox.showerror("Ошибка", f"Ошибка при предпросмотре: {str(e)}")


class FullFormatPreviewDialog:
    """Диалоговое окно предпросмотра в полном формате экспорта"""
    
    def __init__(self, parent, main_app, selected_columns=None):
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("Предпросмотр - Полный формат экспорта")
        self.dialog.geometry("1200x700")
        self.main_app = main_app
        self.selected_columns = selected_columns
        
        self.create_widgets()
        self.update_preview()
    
    def create_widgets(self):
        """Создает элементы интерфейса предпросмотра"""
        # Основной фрейм
        main_frame = ttk.Frame(self.dialog)
        main_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Заголовок
        title_label = ttk.Label(main_frame, text="ПРЕДПРОСМОТР ПОЛНОГО ФОРМАТА ЭКСПОРТА", 
                               font=("Arial", 12, "bold"))
        title_label.pack(pady=5)
        
        # Информация о выборе
        if self.selected_columns:
            info_text = f"Отображается: {len(self.selected_columns)} столбцов"
        else:
            info_text = "Отображаются все столбцы полного формата"
        
        info_label = ttk.Label(main_frame, text=info_text, font=("Arial", 9), foreground="blue")
        info_label.pack(pady=2)
        
        # Таблица предпросмотра
        table_frame = ttk.LabelFrame(main_frame, text="Данные для экспорта")
        table_frame.pack(fill="both", expand=True, pady=5)
        
        # Создаем Treeview
        self.tree = ttk.Treeview(table_frame, show='headings', height=15)
        self.tree.pack(fill="both", expand=True, padx=5, pady=5)
        
        # Скроллбары
        v_scrollbar = ttk.Scrollbar(table_frame, orient="vertical", command=self.tree.yview)
        h_scrollbar = ttk.Scrollbar(table_frame, orient="horizontal", command=self.tree.xview)
        
        self.tree.configure(yscrollcommand=v_scrollbar.set, xscrollcommand=h_scrollbar.set)
        
        v_scrollbar.pack(side="right", fill="y")
        h_scrollbar.pack(side="bottom", fill="x")
        
        # Панель управления
        control_frame = ttk.Frame(main_frame)
        control_frame.pack(fill="x", pady=10)
        
        ttk.Button(control_frame, text="Обновить", 
                  command=self.update_preview).pack(side=tk.LEFT, padx=5)
        ttk.Button(control_frame, text="Экспорт в Excel", 
                  command=self.export_from_preview).pack(side=tk.LEFT, padx=5)
        
        if self.selected_columns:
            ttk.Button(control_frame, text="Изменить выбор столбцов", 
                      command=self.modify_selection).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(control_frame, text="Закрыть", 
                  command=self.dialog.destroy).pack(side=tk.RIGHT, padx=5)
    
    def get_column_data(self):
        """Возвращает данные столбцов для отображения"""
        column_mapping = {
            'name': 'Система покрытия',
            'binder': 'Связующее', 
            'ral': 'RAL',
            'density': 'Плотность кг/л',
            'solid_content': 'Сухой остаток %',
            'wet_thickness': 'Толщ. мокрая мкм',
            'dry_thickness': 'Толщ. сухая мкм',
            'theor_covering': 'Укрыв. теор. м²/л',
            'losses': 'Потери %',
            'pract_covering': 'Укрыв. практ. м²/л',
            'price_kg': 'Цена за кг руб',
            'price_liter': 'Цена за литр руб',
            'theor_consumption_l_m2': 'Теор. расх. л/м²',
            'theor_consumption_kg_m2': 'Теор. расх. кг/м²',
            'pract_consumption_l_m2': 'Практ. расх. л/м²', 
            'pract_consumption_kg_m2': 'Практ. расх. кг/м²',
            'theor_cost_m2': 'Стоим. теор. руб/м²',
            'pract_cost_m2': 'Стоим. практ. руб/м²',
            'theor_quantity_l': 'Теор. кол-во л',
            'theor_quantity_kg': 'Теор. кол-во кг',
            'theor_material_cost': 'Стоим. теор. руб',
            'pract_quantity_l': 'Практ. кол-во л',
            'pract_quantity_kg': 'Практ. кол-во кг',
            'pract_material_cost': 'Стоим. практ. руб'
        }
        
        if self.selected_columns:
            # Фильтруем только выбранные столбцы
            return {k: v for k, v in column_mapping.items() if k in self.selected_columns}
        else:
            # Все столбцы
            return column_mapping
    
    def calculate_value(self, layer, column_key):
        """Вычисляет значение для столбца"""
        area = self.get_area()
        
        calculations = {
            'name': lambda: layer[self.main_app.NAME],
            'binder': lambda: layer[self.main_app.BINDER] or "",
            'ral': lambda: layer[self.main_app.RAL] or "",
            'density': lambda: layer[self.main_app.DENSITY] or 0,
            'solid_content': lambda: layer[self.main_app.SOLID_CONTENT] or 0,
            'wet_thickness': lambda: layer[self.main_app.WET_THICKNESS] or 0,
            'dry_thickness': lambda: layer[self.main_app.DRY_THICKNESS] or 0,
            'theor_covering': lambda: layer[self.main_app.THEOR_COVERING] or 0,
            'losses': lambda: layer[self.main_app.LOSSES] or 0,
            'pract_covering': lambda: layer[self.main_app.PRACT_COVERING] or 0,
            'price_kg': lambda: layer[self.main_app.PRICE_KG] or 0,
            'price_liter': lambda: layer[self.main_app.PRICE_LITER] or 0,
            'theor_consumption_kg_m2': lambda: layer[self.main_app.THEOR_CONSUMPTION_KG] or 0,
            'pract_consumption_kg_m2': lambda: layer[self.main_app.PRACT_CONSUMPTION_KG] or 0,
            'pract_cost_m2': lambda: layer[self.main_app.COST] or 0,
            'theor_consumption_l_m2': lambda: (layer[self.main_app.THEOR_CONSUMPTION_KG] / layer[self.main_app.DENSITY]) if layer[self.main_app.DENSITY] and layer[self.main_app.DENSITY] > 0 else 0,
            'pract_consumption_l_m2': lambda: (layer[self.main_app.PRACT_CONSUMPTION_KG] / layer[self.main_app.DENSITY]) if layer[self.main_app.DENSITY] and layer[self.main_app.DENSITY] > 0 else 0,
            'theor_cost_m2': lambda: (layer[self.main_app.THEOR_CONSUMPTION_KG] or 0) * (layer[self.main_app.PRICE_KG] or 0),
            'theor_quantity_l': lambda: ((layer[self.main_app.THEOR_CONSUMPTION_KG] / layer[self.main_app.DENSITY]) if layer[self.main_app.DENSITY] and layer[self.main_app.DENSITY] > 0 else 0) * area,
            'theor_quantity_kg': lambda: (layer[self.main_app.THEOR_CONSUMPTION_KG] or 0) * area,
            'theor_material_cost': lambda: (layer[self.main_app.THEOR_CONSUMPTION_KG] or 0) * area * (layer[self.main_app.PRICE_KG] or 0),
            'pract_quantity_l': lambda: ((layer[self.main_app.PRACT_CONSUMPTION_KG] / layer[self.main_app.DENSITY]) if layer[self.main_app.DENSITY] and layer[self.main_app.DENSITY] > 0 else 0) * area,
            'pract_quantity_kg': lambda: (layer[self.main_app.PRACT_CONSUMPTION_KG] or 0) * area,
            'pract_material_cost': lambda: (layer[self.main_app.PRACT_CONSUMPTION_KG] or 0) * area * (layer[self.main_app.PRICE_KG] or 0)
        }
        
        return calculations.get(column_key, lambda: 0)()
    
    def get_area(self):
        """Получает площадь из основного приложения"""
        try:
            area_text = self.main_app.area_entry.get().strip()
            return float(area_text) if area_text else 1.0
        except ValueError:
            return 1.0
    
    def update_preview(self):
        """Обновляет данные в предпросмотре"""
        # Получаем столбцы для отображения
        column_data = self.get_column_data()
        columns = list(column_data.values())
        
        # Настраиваем Treeview
        self.tree['columns'] = columns
        for col in columns:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=100, minwidth=80)
        
        # Очищаем старые данные
        for item in self.tree.get_children():
            self.tree.delete(item)
        
        # Заполняем данными
        for layer in self.main_app.layers:
            values = []
            for col_key in column_data.keys():
                value = self.calculate_value(layer, col_key)
                
                # Форматирование значений
                if isinstance(value, float):
                    if any(x in column_data[col_key].lower() for x in ['цена', 'стоимость', 'руб']):
                        values.append(f"{value:.2f}")
                    elif any(x in column_data[col_key].lower() for x in ['расход', 'плотность', 'количество']):
                        values.append(f"{value:.3f}")
                    elif any(x in column_data[col_key].lower() for x in ['толщина', 'остаток', 'потери']):
                        values.append(f"{value:.1f}")
                    elif 'укрывистость' in column_data[col_key].lower():
                        values.append(f"{value:.2f}")
                    else:
                        values.append(f"{value}")
                else:
                    values.append(str(value))
            
            self.tree.insert('', 'end', values=values)
    
    def export_from_preview(self):
        """Экспорт данных из предпросмотра"""
        if self.selected_columns:
            # Используем выборочный экспорт
            selective_export = SelectiveExportDialog(self.dialog, self.main_app)
            # Устанавливаем выбранные столбцы
            for key, var in selective_export.selected_columns.items():
                var.set(key in self.selected_columns)
            selective_export.execute_export()
        else:
            # Полный экспорт
            self.main_app.export_to_excel()
    
    def modify_selection(self):
        """Изменяет выбор столбцов"""
        self.dialog.destroy()
        SelectiveExportDialog(self.main_app.master, self.main_app)


def main():
    """Основная функция приложения"""
    root = tk.Tk()
    app = ExcelExporterApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()