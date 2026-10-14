
import csv
import os
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog


# ==========================================================
# СОБСТВЕННЫЕ ИСКЛЮЧЕНИЯ
# ==========================================================
class LibraryError(Exception):
    """Базовое исключение библиотеки"""


class InvalidPriceError(LibraryError):
    pass


class InvalidYearError(LibraryError):
    pass


class GameNotFoundError(LibraryError):
    pass


# ==========================================================
# КЛАСС 1: ИГРА
# ==========================================================
class Game:
    MIN_YEAR = 1980
    MAX_YEAR = 2026

    PRICE_CATEGORIES = {
        "Бесплатные (F2P)":      (0, 0),
        "Бюджетные (1-500₽)":    (1, 500),
        "Средние (501-1500₽)":  (501, 1500),
        "Премиум (1501-3000₽)": (1501, 3000),
        "AAA (3000₽+)":          (3001, float("inf")),
    }

    def __init__(self, title, year, genre, price):
        title = str(title).strip()
        if not title:
            raise ValueError("Название игры не может быть пустым")

        self.title = title
        self.genre = str(genre).strip() or "Без жанра"
        self.year = self._parse_year(year)
        self.price = self._parse_price(price)

    @classmethod
    def _parse_year(cls, value):
        try:
            year = int(float(value))
        except (ValueError, TypeError):
            raise InvalidYearError(f"Год '{value}' не является числом")
        if not (cls.MIN_YEAR <= year <= cls.MAX_YEAR):
            raise InvalidYearError(
                f"Год {year} вне диапазона {cls.MIN_YEAR}-{cls.MAX_YEAR}")
        return year

    @staticmethod
    def _parse_price(value):
        try:
            price = float(value)
        except (ValueError, TypeError):
            raise InvalidPriceError(f"Цена '{value}' не является числом")
        if price < 0:
            raise InvalidPriceError("Цена не может быть отрицательной")
        return round(price, 2)

    @property
    def price_text(self):
        if self.price == 0:
            return "F2P"
        return f"{self.price:,.0f}₽".replace(",", " ")

    def to_dict(self):
        return {"title": self.title, "year": self.year,
                "genre": self.genre, "price": self.price}


# ==========================================================
# КЛАСС 2: БИБЛИОТЕКА
# ==========================================================
class GameLibrary:
    REQUIRED_COLUMNS = {"title", "year", "genre", "price"}

    def __init__(self, filename="games_data.csv"):
        self.filename = filename
        self.games = []
        self.load_from_csv()

    def load_from_csv(self):
        if not os.path.exists(self.filename):
            return
        try:
            with open(self.filename, "r", encoding="utf-8-sig", newline="") as f:
                reader = csv.DictReader(f)
                if reader.fieldnames is None or \
                        not self.REQUIRED_COLUMNS.issubset(set(reader.fieldnames)):
                    raise LibraryError("Неверный формат CSV")
                for row in reader:
                    try:
                        self.games.append(Game(
                            row["title"], row["year"], row["genre"], row["price"]))
                    except (LibraryError, ValueError, TypeError, KeyError):
                        continue
        except (OSError, csv.Error, LibraryError):
            pass

    def append_to_csv(self, game):
        is_new = not os.path.exists(self.filename)
        try:
            with open(self.filename, "a", encoding="utf-8", newline="") as f:
                writer = csv.writer(f)
                if is_new:
                    writer.writerow(["title", "year", "genre", "price"])
                writer.writerow([game.title, game.year, game.genre, game.price])
        except OSError as e:
            raise LibraryError(f"Не удалось сохранить: {e}")

    def add_game(self, game, save=False):
        if not isinstance(game, Game):
            raise TypeError("Ожидается объект класса Game")
        if self.find(game.title):
            raise LibraryError(f"Игра '{game.title}' уже есть в базе")
        self.games.append(game)
        if save:
            self.append_to_csv(game)

    def find(self, title):
        t = title.strip().lower()
        for g in self.games:
            if g.title.lower() == t:
                return g
        return None

    def search(self, substring):
        s = substring.strip().lower()
        return [g for g in self.games if s in g.title.lower()]

    def by_genre(self, genre):
        return [g for g in self.games if g.genre.lower() == genre.strip().lower()]

    def by_year_range(self, y1, y2):
        return [g for g in self.games if y1 <= g.year <= y2]

    def by_price_range(self, p1, p2):
        return [g for g in self.games if p1 <= g.price <= p2]

    def all_genres(self):
        """Словарь жанров для выпадающего списка"""
        genres = {}
        for g in self.games:
            genres[g.genre] = genres.get(g.genre, 0) + 1
        return dict(sorted(genres.items(), key=lambda x: -x[1]))


# ==========================================================
# КЛАСС 3: GUI ПРИЛОЖЕНИЕ 
# ==========================================================
class GameApp:
    BG = "#0a0a0a"              # Почти черный фон
    FG = "#c084fc"              # Светло-фиолетовый текст
    ACCENT = "#a855f7"          # Насыщенный фиолетовый (акцент)
    ACCENT_HOVER = "#9333ea"    # Темнее для hover
    ACCENT_PRESSED = "#7e22ce"  # Еще темнее для pressed
    BUTTON_BG = "#1a1a1a"       # Темно-серый фон кнопок
    ROW_EVEN = "#0a0a0a"        # Черный для четных строк
    ROW_ODD = "#141414"         # Чуть светлее для нечетных
    HEADER_BG = "#2d1b4e"       # Темно-фиолетовый для заголовков таблицы
    STATUS_FG = "#9ca3af"       # Приглушенный серый для статус-бара

    def __init__(self, root):
        self.root = root
        self.root.title("🎮 Библиотека игр")
        self.root.geometry("1000x650")
        self.root.configure(bg=self.BG)
        self.root.minsize(800, 500)

        self.library = GameLibrary()
        self.current_games = self.library.games

        self._build_styles()
        self._build_ui()
        self._refresh_table()

    # ---------- СТИЛИ ----------
    def _build_styles(self):
        style = ttk.Style()
        style.theme_use("clam")

        style.configure("TFrame", background=self.BG)
        style.configure("TLabel", background=self.BG, foreground=self.FG,
                        font=("Segoe UI", 11))
        style.configure("Header.TLabel", font=("Segoe UI", 20, "bold"),
                        foreground=self.ACCENT, background=self.BG)
        style.configure("Status.TLabel", font=("Segoe UI", 10),
                        foreground=self.STATUS_FG, background=self.BG)

        style.configure("TButton", font=("Segoe UI", 11, "bold"),
                        background=self.BUTTON_BG, foreground=self.FG,
                        padding=(15, 8), borderwidth=0)
        style.map("TButton", background=[("active", self.ACCENT_HOVER),
                              ("pressed", self.ACCENT_PRESSED)])

        # Таблица
        style.configure("Treeview",
                        background=self.ROW_EVEN,
                        foreground=self.FG,
                        fieldbackground=self.ROW_EVEN,
                        font=("Segoe UI", 10),
                        rowheight=28,
                        borderwidth=0)
        style.configure("Treeview.Heading",
                        background=self.HEADER_BG,
                        foreground=self.FG,
                        font=("Segoe UI", 11, "bold"),
                        borderwidth=0)
        style.map("Treeview",
                  background=[("selected", self.ACCENT)],
                  foreground=[("selected", "white")])

        # Поля ввода
        style.configure("TEntry", font=("Segoe UI", 11), padding=6,
                        fieldbackground="#1a1a1a", foreground=self.FG,
                        insertcolor=self.FG)
        style.configure("TCombobox", font=("Segoe UI", 11), padding=6, 
                        fieldbackground="#1a1a1a", foreground=self.FG)

    # ---------- ИНТЕРФЕЙС ----------
    def _build_ui(self):
        # Заголовок
        header = ttk.Label(self.root, text="БИБЛИОТЕКА ИГР", style="Header.TLabel")
        header.pack(pady=(15, 10))

        # Панель кнопок
        btn_frame = ttk.Frame(self.root)
        btn_frame.pack(pady=10, padx=20, fill="x")

        buttons = [
            ("Все игры", self.show_all),
            ("Поиск", self.show_search),
            ("По жанру", self.show_by_genre),
            ("По годам", self.show_by_year),
            ("По цене", self.show_by_price),
            ("Добавить игру", self.add_game),
        ]

        for i, (text, cmd) in enumerate(buttons):
            btn = ttk.Button(btn_frame, text=text, command=cmd)
            btn.grid(row=0, column=i, padx=4)
            for c in range(len(buttons)):
                btn_frame.columnconfigure(c, weight=1)

        # Таблица
        table_frame = ttk.Frame(self.root)
        table_frame.pack(fill="both", expand=True, padx=20, pady=(10, 5))

        columns = ("num", "title", "year", "genre", "price")
        self.tree = ttk.Treeview(table_frame, columns=columns, show="headings",
                                 selectmode="browse")

        self.tree.heading("num", text="№", anchor="center")
        self.tree.heading("title", text="Название", anchor="w",
                          command=lambda: self._sort_by("title"))
        self.tree.heading("year", text="Год", anchor="center",
                          command=lambda: self._sort_by("year"))
        self.tree.heading("genre", text="Жанр", anchor="w",
                          command=lambda: self._sort_by("genre"))
        self.tree.heading("price", text="Цена", anchor="e",
                          command=lambda: self._sort_by("price"))

        self.tree.column("num", width=50, anchor="center")
        self.tree.column("title", width=380)
        self.tree.column("year", width=80, anchor="center")
        self.tree.column("genre", width=180)
        self.tree.column("price", width=120, anchor="e")

        scrollbar_y = ttk.Scrollbar(table_frame, orient="vertical",
                                    command=self.tree.yview)
        scrollbar_x = ttk.Scrollbar(table_frame, orient="horizontal",
                                    command=self.tree.xview)
        self.tree.configure(yscrollcommand=scrollbar_y.set,
                            xscrollcommand=scrollbar_x.set)

        self.tree.grid(row=0, column=0, sticky="nsew")
        scrollbar_y.grid(row=0, column=1, sticky="ns")
        scrollbar_x.grid(row=1, column=0, sticky="ew")

        table_frame.grid_rowconfigure(0, weight=1)
        table_frame.grid_columnconfigure(0, weight=1)

        # Чередование цветов строк
        self.tree.tag_configure("even", background=self.ROW_EVEN)
        self.tree.tag_configure("odd", background=self.ROW_ODD)

        # Статус-бар
        self.status_var = tk.StringVar()
        status_bar = ttk.Label(self.root, textvariable=self.status_var,
                               style="Status.TLabel", anchor="w")
        status_bar.pack(fill="x", padx=20, pady=(0, 10))

    # ---------- ОБНОВЛЕНИЕ ТАБЛИЦЫ ----------
    def _refresh_table(self, title=""):
        for row in self.tree.get_children():
            self.tree.delete(row)

        for i, game in enumerate(self.current_games, 1):
            tag = "even" if i % 2 == 0 else "odd"
            self.tree.insert("", "end", values=(
                i, game.title, game.year, game.genre, game.price_text
            ), tags=(tag,))

        total = len(self.current_games)
        all_total = len(self.library.games)
        if title:
            self.status_var.set(f"📊 {title}  |  Показано: {total} из {all_total}")
        else:
            self.status_var.set(f"Всего игр в базе: {all_total}")

    # ---------- СОРТИРОВКА ПО КЛИКУ НА ЗАГОЛОВОК ----------
    def _sort_by(self, column):
        reverse = getattr(self, f"_sort_reverse_{column}", False)
        setattr(self, f"_sort_reverse_{column}", not reverse)

        if column == "price":
            data = [(g.price, g) for g in self.current_games]
        elif column == "year":
            data = [(g.year, g) for g in self.current_games]
        else:
            data = [(getattr(g, column).lower(), g) for g in self.current_games]

        data.sort(key=lambda x: x[0], reverse=reverse)
        self.current_games = [g for _, g in data]
        self._refresh_table()

    # ---------- ДЕЙСТВИЯ ----------
    def show_all(self):
        self.current_games = self.library.games
        self._refresh_table("Все игры")

    def show_search(self):
        dialog = FilterDialog(self.root, "Поиск по названию",
                              fields=[("Название (или часть):", "str")])
        if dialog.result:
            substring = dialog.result[0]
            if not substring.strip():
                messagebox.showwarning("Пустой запрос",
                                       "Введите текст для поиска",
                                       parent=self.root)
                return
            self.current_games = self.library.search(substring)
            self._refresh_table(f"Поиск: '{substring}'")

    def show_by_genre(self):
        genres = self.library.all_genres()
        if not genres:
            messagebox.showinfo("Пусто", "В базе нет игр", parent=self.root)
            return

        dialog = FilterDialog(self.root, "Фильтр по жанру",
                              fields=[("Жанр:", "combo", list(genres.keys()))])
        if dialog.result:
            genre = dialog.result[0]
            self.current_games = self.library.by_genre(genre)
            self._refresh_table(f"Жанр: {genre}")

    def show_by_year(self):
        dialog = FilterDialog(self.root, "Фильтр по годам",
                              fields=[("Год от:", "int"), ("Год до:", "int")])
        if dialog.result:
            y1, y2 = dialog.result
            if y1 > y2:
                y1, y2 = y2, y1
            self.current_games = self.library.by_year_range(y1, y2)
            self._refresh_table(f"Годы: {y1}–{y2}")

    def show_by_price(self):
        dialog = FilterDialog(self.root, "Фильтр по цене",
                              fields=[("Цена от (₽):", "float"),
                                      ("Цена до (₽):", "float")])
        if dialog.result:
            p1, p2 = dialog.result
            if p1 > p2:
                p1, p2 = p2, p1
            self.current_games = self.library.by_price_range(p1, p2)
            self._refresh_table(f"Цена: {p1:.0f}–{p2:.0f}₽")

    def add_game(self):
        dialog = FilterDialog(self.root, "➕ Добавить игру",
                              fields=[
                                  ("Название:", "str"),
                                  ("Жанр:", "str"),
                                  ("Год выпуска:", "int"),
                                  ("Цена (₽, 0 = F2P):", "float"),
                              ],
                              is_add=True)
        if dialog.result:
            title, genre, year, price = dialog.result
            try:
                game = Game(title, year, genre, price)
                self.library.add_game(game, save=True)
                self.current_games = self.library.games
                self._refresh_table()
                messagebox.showinfo("Успех",
                                    f"Игра '{game.title}' добавлена и сохранена!",
                                    parent=self.root)
            except (LibraryError, ValueError) as e:
                messagebox.showerror("Ошибка", str(e), parent=self.root)


# ==========================================================
# ОКНО ДЛЯ ВВОДА ДАННЫХ
# ==========================================================
class FilterDialog(tk.Toplevel):
    """Универсальный диалог с полями разного типа"""

    def __init__(self, parent, title, fields, is_add=False):
        super().__init__(parent)
        self.title(title)
        self.geometry("420x300")
        self.configure(bg="#0a0a0a")
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()

        self.result = None
        self.entries = []
        self.is_add = is_add

        self._build(fields)
        self.wait_window(self)

    def _build(self, fields):
        main = ttk.Frame(self)
        main.pack(padx=25, pady=20, fill="both", expand=True)

        for i, field in enumerate(fields):
            label_text = field[0]
            field_type = field[1]

            ttk.Label(main, text=label_text,
                      font=("Segoe UI", 10),
                      foreground="#c084fc").grid(row=i, column=0,
                                                  sticky="w", pady=6)

            if field_type == "combo":
                options = field[2]
                var = tk.StringVar(value=options[0] if options else "")
                combo = ttk.Combobox(main, textvariable=var, values=options,
                                     state="readonly", width=28)
                combo.grid(row=i, column=1, padx=(10, 0), pady=6)
                self.entries.append(("combo", var))
            else:
                entry = ttk.Entry(main, width=30)
                entry.grid(row=i, column=1, padx=(10, 0), pady=6)
                self.entries.append((field_type, entry))

        # Кнопки
        btn_frame = ttk.Frame(main)
        btn_frame.grid(row=len(fields), column=0, columnspan=2, pady=20)

        ttk.Button(btn_frame, text="OK", command=self._on_ok).pack(
            side="left", padx=10)
        ttk.Button(btn_frame, text="Отмена", command=self.destroy).pack(
            side="left", padx=10)

        self.bind("<Return>", lambda e: self._on_ok())
        self.bind("<Escape>", lambda e: self.destroy())

    def _on_ok(self):
        values = []
        for field_type, widget in self.entries:
            raw = widget.get().strip() if field_type != "combo" else widget.get()

            if not raw and field_type != "combo":
                messagebox.showwarning("Пустое поле",
                                       "Заполните все поля", parent=self)
                return

            try:
                if field_type == "int":
                    values.append(int(raw))
                elif field_type == "float":
                    values.append(float(raw.replace(",", ".")))
                else:
                    values.append(raw)
            except ValueError:
                type_name = "целое число" if field_type == "int" else "число"
                messagebox.showerror("Ошибка ввода",
                                     f"Ожидалось {type_name}", parent=self)
                return

        self.result = values
        self.destroy()


# ==========================================================
# ЗАПУСК
# ==========================================================
if __name__ == "__main__":
    root = tk.Tk()
    app = GameApp(root)
    root.mainloop()
