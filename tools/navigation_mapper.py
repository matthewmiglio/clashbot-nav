import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import json
from pathlib import Path
from PIL import Image, ImageTk, ImageDraw
import os
import csv
import random


class NavigationMapper:
    def __init__(self, root):
        self.root = root
        self.root.title("Clash Bot Navigation Mapper")
        self.root.geometry("1400x800")

        self.project_root = Path(__file__).parent.parent
        self.classes_file = self.project_root / "data" / "training" / "image_classes.txt"
        self.output_file = self.project_root / "data" / "navigation_graph.json"
        self.images_dir = self.project_root / "data" / "training" / "images"
        self.annotations_file = self.project_root / "data" / "training" / "annotations.csv"

        self.page_types = self.load_page_types()
        self.label_to_images = self.load_annotations()
        self.navigation_data = {"navigation_graph": {}}
        self.load_existing_data()

        self.current_screenshot = None
        self.photo_image = None
        self.screenshot_scale = 1.0
        self.click_markers = []

        self.setup_ui()
        self.refresh_table()

    def load_page_types(self):
        if not self.classes_file.exists():
            messagebox.showerror("Error", f"Cannot find {self.classes_file}")
            return []

        with open(self.classes_file, 'r') as f:
            return [line.strip() for line in f if line.strip()]

    def load_annotations(self):
        if not self.annotations_file.exists():
            print(f"Warning: Cannot find {self.annotations_file}")
            return {}

        label_map = {}
        with open(self.annotations_file, 'r') as f:
            reader = csv.reader(f)
            for row in reader:
                if len(row) >= 2:
                    filename, label = row[0], row[1]
                    if label != "Null":
                        if label not in label_map:
                            label_map[label] = []
                        label_map[label].append(filename)

        return label_map

    def load_existing_data(self):
        if self.output_file.exists():
            try:
                with open(self.output_file, 'r') as f:
                    self.navigation_data = json.load(f)
                    if "navigation_graph" not in self.navigation_data:
                        self.navigation_data = {"navigation_graph": {}}
            except Exception as e:
                print(f"Error loading existing data: {e}")
                self.navigation_data = {"navigation_graph": {}}

    def setup_ui(self):
        main_container = ttk.PanedWindow(self.root, orient=tk.HORIZONTAL)
        main_container.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        left_frame = ttk.Frame(main_container)
        right_frame = ttk.Frame(main_container)

        main_container.add(left_frame, weight=2)
        main_container.add(right_frame, weight=3)

        left_frame.columnconfigure(0, weight=1)
        left_frame.rowconfigure(2, weight=1)

        title_label = ttk.Label(left_frame, text="Navigation Link Editor",
                                font=('Arial', 14, 'bold'))
        title_label.grid(row=0, column=0, pady=(0, 10), sticky=tk.W)

        input_frame = ttk.LabelFrame(left_frame, text="Add Navigation Link", padding="10")
        input_frame.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        input_frame.columnconfigure(1, weight=1)

        ttk.Label(input_frame, text="From Page:").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.from_page_var = tk.StringVar()
        self.from_page_combo = ttk.Combobox(input_frame, textvariable=self.from_page_var,
                                            values=self.page_types, state='readonly')
        self.from_page_combo.grid(row=0, column=1, sticky=(tk.W, tk.E), pady=5, padx=(5, 0))
        self.from_page_combo.bind('<<ComboboxSelected>>', lambda e: self.on_from_page_selected())

        ttk.Label(input_frame, text="To Page:").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.to_page_var = tk.StringVar()
        self.to_page_combo = ttk.Combobox(input_frame, textvariable=self.to_page_var,
                                          values=[], state='readonly')
        self.to_page_combo.grid(row=1, column=1, sticky=(tk.W, tk.E), pady=5, padx=(5, 0))

        coord_frame = ttk.Frame(input_frame)
        coord_frame.grid(row=2, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=5)

        ttk.Label(coord_frame, text="Click Coordinates:").grid(row=0, column=0, sticky=tk.W)
        self.coord_x_var = tk.StringVar()
        self.coord_y_var = tk.StringVar()

        coord_entry_frame = ttk.Frame(coord_frame)
        coord_entry_frame.grid(row=0, column=1, sticky=tk.W, padx=(5, 0))

        ttk.Label(coord_entry_frame, text="X:").pack(side=tk.LEFT, padx=(0, 5))
        ttk.Entry(coord_entry_frame, textvariable=self.coord_x_var, width=8).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Label(coord_entry_frame, text="Y:").pack(side=tk.LEFT, padx=(0, 5))
        ttk.Entry(coord_entry_frame, textvariable=self.coord_y_var, width=8).pack(side=tk.LEFT)

        ttk.Label(input_frame, text="Description:").grid(row=3, column=0, sticky=tk.W, pady=5)
        self.description_var = tk.StringVar()
        ttk.Entry(input_frame, textvariable=self.description_var).grid(
            row=3, column=1, sticky=(tk.W, tk.E), pady=5, padx=(5, 0))

        button_frame = ttk.Frame(input_frame)
        button_frame.grid(row=4, column=0, columnspan=2, pady=(10, 0))

        ttk.Button(button_frame, text="Add Link", command=self.add_link).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Clear Form", command=self.clear_form).pack(side=tk.LEFT, padx=5)

        table_frame = ttk.LabelFrame(left_frame, text="Navigation Links", padding="10")
        table_frame.grid(row=2, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 10))
        table_frame.columnconfigure(0, weight=1)
        table_frame.rowconfigure(0, weight=1)

        tree_scroll = ttk.Scrollbar(table_frame)
        tree_scroll.grid(row=0, column=1, sticky=(tk.N, tk.S))

        self.tree = ttk.Treeview(table_frame, columns=("From", "To", "Coords", "Description"),
                                 show='headings', yscrollcommand=tree_scroll.set)
        tree_scroll.config(command=self.tree.yview)

        self.tree.heading("From", text="From Page")
        self.tree.heading("To", text="To Page")
        self.tree.heading("Coords", text="Coordinates")
        self.tree.heading("Description", text="Description")

        self.tree.column("From", width=100)
        self.tree.column("To", width=100)
        self.tree.column("Coords", width=80)
        self.tree.column("Description", width=150)

        self.tree.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        self.tree.bind('<Delete>', lambda e: self.delete_selected())
        self.tree.bind('<Double-1>', lambda e: self.edit_selected())

        bottom_frame = ttk.Frame(left_frame)
        bottom_frame.grid(row=3, column=0, sticky=(tk.W, tk.E))

        ttk.Button(bottom_frame, text="Delete Selected", command=self.delete_selected).pack(side=tk.LEFT, padx=5)
        ttk.Button(bottom_frame, text="Export As...", command=self.export_data).pack(side=tk.LEFT, padx=5)

        right_frame.columnconfigure(0, weight=1)
        right_frame.rowconfigure(1, weight=1)

        screenshot_header = ttk.Frame(right_frame)
        screenshot_header.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 5))

        ttk.Label(screenshot_header, text="Screenshot Preview",
                 font=('Arial', 12, 'bold')).pack(side=tk.LEFT)

        ttk.Button(screenshot_header, text="Load Different Image",
                  command=self.load_different_screenshot).pack(side=tk.RIGHT, padx=5)
        ttk.Button(screenshot_header, text="Browse...",
                  command=self.load_screenshot).pack(side=tk.RIGHT, padx=5)

        screenshot_frame = ttk.LabelFrame(right_frame, text="Click on the screen to set coordinates", padding="5")
        screenshot_frame.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        screenshot_frame.columnconfigure(0, weight=1)
        screenshot_frame.rowconfigure(0, weight=1)

        self.canvas = tk.Canvas(screenshot_frame, bg='gray', cursor='crosshair')
        self.canvas.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        self.canvas.bind('<Button-1>', self.on_canvas_click)

        self.coord_label = ttk.Label(right_frame, text="Click on screenshot to capture coordinates",
                                     font=('Arial', 9))
        self.coord_label.grid(row=2, column=0, pady=(5, 0))

        self.editing_item = None

    def on_from_page_selected(self):
        from_page = self.from_page_var.get()
        if from_page:
            self.update_to_page_dropdown()

            if from_page in self.label_to_images and self.label_to_images[from_page]:
                random_image = random.choice(self.label_to_images[from_page])
                image_path = self.images_dir / random_image
                if image_path.exists():
                    self.load_specific_screenshot(image_path)
                else:
                    self.coord_label.config(
                        text=f"Image file not found: {random_image}")
            else:
                self.coord_label.config(
                    text=f"No screenshots found for '{from_page}' in annotations.csv")

    def update_to_page_dropdown(self):
        from_page = self.from_page_var.get()
        if not from_page:
            self.to_page_combo['values'] = []
            return

        already_mapped = set()
        if from_page in self.navigation_data["navigation_graph"]:
            for link in self.navigation_data["navigation_graph"][from_page]:
                already_mapped.add(link["to"])

        available_pages = [page for page in self.page_types if page not in already_mapped]
        self.to_page_combo['values'] = available_pages

        if self.to_page_var.get() in already_mapped:
            self.to_page_var.set('')

    def load_different_screenshot(self):
        from_page = self.from_page_var.get()
        if not from_page:
            messagebox.showinfo("Info", "Please select a 'From Page' first")
            return

        if from_page in self.label_to_images and self.label_to_images[from_page]:
            random_image = random.choice(self.label_to_images[from_page])
            image_path = self.images_dir / random_image
            if image_path.exists():
                self.load_specific_screenshot(image_path)
            else:
                self.coord_label.config(text=f"Image file not found: {random_image}")
        else:
            self.coord_label.config(
                text=f"No screenshots found for '{from_page}' in annotations.csv")

    def load_screenshot(self):
        file_path = filedialog.askopenfilename(
            title="Select a screenshot",
            initialdir=self.images_dir,
            filetypes=[("PNG files", "*.png"), ("JPEG files", "*.jpg"), ("All files", "*.*")]
        )

        if file_path:
            self.load_specific_screenshot(Path(file_path))

    def load_specific_screenshot(self, image_path):
        try:
            self.current_screenshot = Image.open(image_path)
            self.display_screenshot()
            self.coord_label.config(text=f"Loaded: {image_path.name}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load screenshot: {e}")

    def display_screenshot(self):
        if not self.current_screenshot:
            return

        canvas_width = self.canvas.winfo_width()
        canvas_height = self.canvas.winfo_height()

        if canvas_width <= 1 or canvas_height <= 1:
            canvas_width = 600
            canvas_height = 700

        img_width, img_height = self.current_screenshot.size

        scale_x = canvas_width / img_width
        scale_y = canvas_height / img_height
        self.screenshot_scale = min(scale_x, scale_y, 1.0)

        new_width = int(img_width * self.screenshot_scale)
        new_height = int(img_height * self.screenshot_scale)

        resized_img = self.current_screenshot.resize((new_width, new_height), Image.Resampling.LANCZOS)

        img_with_markers = resized_img.copy()
        draw = ImageDraw.Draw(img_with_markers)

        for marker_x, marker_y in self.click_markers:
            scaled_x = int(marker_x * self.screenshot_scale)
            scaled_y = int(marker_y * self.screenshot_scale)
            radius = 8
            draw.ellipse(
                [scaled_x - radius, scaled_y - radius, scaled_x + radius, scaled_y + radius],
                fill='red', outline='white', width=2
            )

        self.photo_image = ImageTk.PhotoImage(img_with_markers)
        self.canvas.delete('all')
        self.canvas.create_image(canvas_width // 2, canvas_height // 2,
                                image=self.photo_image, anchor=tk.CENTER)

    def on_canvas_click(self, event):
        if not self.current_screenshot:
            messagebox.showinfo("Info", "Please load a screenshot first")
            return

        canvas_width = self.canvas.winfo_width()
        canvas_height = self.canvas.winfo_height()

        img_width, img_height = self.current_screenshot.size
        scaled_width = int(img_width * self.screenshot_scale)
        scaled_height = int(img_height * self.screenshot_scale)

        offset_x = (canvas_width - scaled_width) // 2
        offset_y = (canvas_height - scaled_height) // 2

        click_x = event.x - offset_x
        click_y = event.y - offset_y

        if 0 <= click_x <= scaled_width and 0 <= click_y <= scaled_height:
            original_x = int(click_x / self.screenshot_scale)
            original_y = int(click_y / self.screenshot_scale)

            self.coord_x_var.set(str(original_x))
            self.coord_y_var.set(str(original_y))

            self.click_markers = [(original_x, original_y)]
            self.display_screenshot()

            self.coord_label.config(text=f"Coordinates set: ({original_x}, {original_y})")

    def clear_form(self):
        current_from = self.from_page_var.get()
        self.to_page_var.set('')
        self.coord_x_var.set('')
        self.coord_y_var.set('')
        self.description_var.set('')
        self.click_markers = []
        self.editing_item = None
        if self.current_screenshot:
            self.display_screenshot()

        if current_from:
            self.update_to_page_dropdown()

    def add_link(self):
        from_page = self.from_page_var.get()
        to_page = self.to_page_var.get()
        coord_x = self.coord_x_var.get().strip()
        coord_y = self.coord_y_var.get().strip()
        description = self.description_var.get().strip()

        if not from_page or not to_page:
            messagebox.showwarning("Validation", "Please select both From and To pages")
            return

        if not coord_x or not coord_y:
            messagebox.showwarning("Validation", "Please set coordinates by clicking on the screenshot")
            return

        try:
            coordinates = [int(coord_x), int(coord_y)]
        except ValueError:
            messagebox.showerror("Validation", "Coordinates must be integers")
            return

        link_data = {
            "to": to_page,
            "action": "click",
            "coordinates": coordinates
        }

        if description:
            link_data["description"] = description

        if from_page not in self.navigation_data["navigation_graph"]:
            self.navigation_data["navigation_graph"][from_page] = []

        if self.editing_item:
            old_from, old_to = self.editing_item
            if old_from in self.navigation_data["navigation_graph"]:
                self.navigation_data["navigation_graph"][old_from] = [
                    link for link in self.navigation_data["navigation_graph"][old_from]
                    if link["to"] != old_to
                ]
            self.editing_item = None
        else:
            existing = [link for link in self.navigation_data["navigation_graph"][from_page]
                       if link["to"] == to_page]
            if existing:
                response = messagebox.askyesno("Duplicate",
                    f"A link from {from_page} to {to_page} already exists. Replace it?")
                if not response:
                    return
                self.navigation_data["navigation_graph"][from_page] = [
                    link for link in self.navigation_data["navigation_graph"][from_page]
                    if link["to"] != to_page
                ]

        self.navigation_data["navigation_graph"][from_page].append(link_data)

        self.save_data(show_message=False)
        self.refresh_table()
        self.update_to_page_dropdown()
        self.clear_form()

    def delete_selected(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("Selection", "Please select a link to delete")
            return

        for item in selected:
            values = self.tree.item(item)['values']
            from_page = values[0]
            to_page = values[1]

            if from_page in self.navigation_data["navigation_graph"]:
                self.navigation_data["navigation_graph"][from_page] = [
                    link for link in self.navigation_data["navigation_graph"][from_page]
                    if link["to"] != to_page
                ]

                if not self.navigation_data["navigation_graph"][from_page]:
                    del self.navigation_data["navigation_graph"][from_page]

        self.save_data(show_message=False)
        self.refresh_table()
        self.update_to_page_dropdown()

    def edit_selected(self):
        selected = self.tree.selection()
        if not selected or len(selected) > 1:
            return

        values = self.tree.item(selected[0])['values']
        from_page = values[0]
        to_page = values[1]

        if from_page in self.navigation_data["navigation_graph"]:
            for link in self.navigation_data["navigation_graph"][from_page]:
                if link["to"] == to_page:
                    self.from_page_var.set(from_page)
                    self.to_page_var.set(to_page)

                    coords = link.get("coordinates", [])
                    if coords and len(coords) == 2:
                        self.coord_x_var.set(str(coords[0]))
                        self.coord_y_var.set(str(coords[1]))
                        self.click_markers = [(coords[0], coords[1])]
                        if self.current_screenshot:
                            self.display_screenshot()
                    else:
                        self.coord_x_var.set('')
                        self.coord_y_var.set('')
                        self.click_markers = []

                    self.description_var.set(link.get("description", ""))
                    self.editing_item = (from_page, to_page)
                    break

    def refresh_table(self):
        for item in self.tree.get_children():
            self.tree.delete(item)

        for from_page in sorted(self.navigation_data["navigation_graph"].keys()):
            for link in self.navigation_data["navigation_graph"][from_page]:
                to_page = link["to"]
                coords = link.get("coordinates", [])
                coord_str = f"[{coords[0]}, {coords[1]}]" if coords else ""
                description = link.get("description", "")

                self.tree.insert('', tk.END, values=(from_page, to_page, coord_str, description))

    def save_data(self, show_message=False):
        try:
            self.output_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.output_file, 'w') as f:
                json.dump(self.navigation_data, f, indent=2)
            if show_message:
                self.clear_form()
                self.canvas.delete('all')
                self.current_screenshot = None
                self.coord_label.config(text="Data saved! Select a 'From Page' to continue.")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save: {e}")

    def export_data(self):
        file_path = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
            initialfile="navigation_graph.json"
        )

        if file_path:
            try:
                with open(file_path, 'w') as f:
                    json.dump(self.navigation_data, f, indent=2)
                messagebox.showinfo("Success", f"Data exported to {file_path}")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to export: {e}")


def main():
    root = tk.Tk()
    app = NavigationMapper(root)
    root.mainloop()


if __name__ == "__main__":
    main()
