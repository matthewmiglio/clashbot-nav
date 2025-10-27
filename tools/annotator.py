import tkinter as tk
from tkinter import ttk
from PIL import Image, ImageTk
import os
import csv
import random
from pathlib import Path

class ImageClassifier:
    def __init__(self, root):
        self.root = root
        self.root.title("Image Classifier")

        # Get the project root (parent of tools/)
        script_dir = Path(__file__).parent
        project_root = script_dir.parent

        # Set paths relative to project root
        self.images_folder = str(project_root / "data" / "training" / "images")
        self.classes_file = str(project_root / "data" / "training" / "image_classes.txt")
        self.csv_file = str(project_root / "data" / "training" / "annotations.csv")

        # Load classes
        self.classes = self.load_classes()

        # Load images and filter out already labeled ones
        self.images = self.load_images()
        self.current_index = 0

        # Setup GUI
        self.setup_gui()

        # Display first image
        if self.images:
            self.display_image()
        else:
            self.show_completion_message()

    def load_classes(self):
        """Load classes from image_classes.txt and add Null class"""
        classes = []
        if os.path.exists(self.classes_file):
            with open(self.classes_file, 'r') as f:
                classes = [line.strip() for line in f if line.strip()]
        classes.append("Null")
        return classes

    def load_images(self):
        """Load images from folder, filter out labeled ones, and shuffle"""
        # Get all images
        all_images = []
        if os.path.exists(self.images_folder):
            all_images = [f for f in os.listdir(self.images_folder)
                         if f.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp', '.gif'))]

        # Load already labeled images
        labeled_images = set()
        if os.path.exists(self.csv_file):
            with open(self.csv_file, 'r', newline='') as f:
                reader = csv.reader(f)
                for row in reader:
                    if row:
                        labeled_images.add(row[0])

        # Filter out labeled images
        unlabeled_images = [img for img in all_images if img not in labeled_images]

        # Shuffle the unlabeled images
        random.shuffle(unlabeled_images)

        return unlabeled_images

    def setup_gui(self):
        """Setup the GUI components"""
        # Progress label at top
        self.progress_label = tk.Label(self.root, text="", font=("Arial", 12))
        self.progress_label.pack(pady=10)

        # Main container with left and right sections
        main_container = tk.Frame(self.root)
        main_container.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Left side - Image display
        left_frame = tk.Frame(main_container)
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.image_label = tk.Label(left_frame)
        self.image_label.pack()

        # Right side - Buttons in 2 columns
        right_frame = tk.Frame(main_container)
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, padx=20)

        # Rainbow colors for button borders (consistent each runtime)
        rainbow_colors = ["#FF0000", "#FF7F00", "#FFFF00", "#00FF00", "#0000FF", "#4B0082", "#9400D3"]

        # Create a frame for buttons
        self.buttons_frame = tk.Frame(right_frame)
        self.buttons_frame.pack()

        # Keyboard bindings: 1-0 for first 10, then q-p for next 10
        key_bindings = ['1', '2', '3', '4', '5', '6', '7', '8', '9', '0',
                       'q', 'w', 'e', 'r', 't', 'y', 'u', 'i', 'o', 'p']

        # Create buttons in 2 columns
        buttons_per_col = 2
        col_frames = []

        for col in range(buttons_per_col):
            col_frame = tk.Frame(self.buttons_frame)
            col_frame.pack(side=tk.LEFT, padx=5)
            col_frames.append(col_frame)

        # Create buttons for each class
        for i, class_name in enumerate(self.classes):
            key = key_bindings[i] if i < len(key_bindings) else ""
            button_text = f"{class_name} ({key})" if key else class_name

            # Get rainbow color for this button
            border_color = rainbow_colors[i % len(rainbow_colors)]

            # Determine which column this button goes in
            col_index = i % buttons_per_col

            # Create a colored frame as border
            border_frame = tk.Frame(col_frames[col_index], bg=border_color, padx=3, pady=3)
            border_frame.pack(pady=5)

            btn = tk.Button(border_frame, text=button_text,
                          command=lambda c=class_name: self.label_image(c),
                          width=25, height=2)
            btn.pack()

            # Bind keyboard shortcuts
            if key:
                self.root.bind(key, lambda e, c=class_name: self.label_image(c))

    def display_image(self):
        """Display the current image"""
        if self.current_index >= len(self.images):
            self.show_completion_message()
            return

        # Update progress
        total = len(self.images)
        current = self.current_index + 1
        self.progress_label.config(text=f"Image {current} / {total}")

        # Load and display image
        image_path = os.path.join(self.images_folder, self.images[self.current_index])
        image = Image.open(image_path)

        # Convert BGR to RGB if needed
        if image.mode == 'RGB':
            # PIL loads as RGB, but if the image was saved as BGR we need to swap channels
            r, g, b = image.split()
            image = Image.merge('RGB', (b, g, r))

        # Resize image to fit screen while maintaining aspect ratio
        max_width = 800
        max_height = 600
        image.thumbnail((max_width, max_height), Image.Resampling.LANCZOS)

        # Convert to PhotoImage
        self.photo = ImageTk.PhotoImage(image)
        self.image_label.config(image=self.photo)

    def label_image(self, class_label):
        """Save the label and move to next image"""
        if self.current_index >= len(self.images):
            return

        # Get image basename
        image_basename = self.images[self.current_index]

        # Save to CSV
        with open(self.csv_file, 'a', newline='') as f:
            writer = csv.writer(f)
            writer.writerow([image_basename, class_label])

        # Move to next image
        self.current_index += 1
        self.display_image()

    def show_completion_message(self):
        """Show message when all images are labeled"""
        self.image_label.config(image='', text="All images have been labeled!")
        self.progress_label.config(text="Complete!")

        # Disable all buttons
        for widget in self.buttons_frame.winfo_children():
            # Only disable if widget supports state option (skip Frames)
            if isinstance(widget, tk.Button):
                widget.config(state=tk.DISABLED)
            else:
                # For Frame widgets containing buttons, disable their children
                for child in widget.winfo_children():
                    if isinstance(child, tk.Button):
                        child.config(state=tk.DISABLED)

def main():
    root = tk.Tk()
    app = ImageClassifier(root)
    root.mainloop()

if __name__ == "__main__":
    main()
