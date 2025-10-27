import tkinter as tk
from PIL import Image, ImageTk, ImageDraw
import csv
import os
import random

class PixelExtractor:
    def __init__(self, root):
        self.root = root
        self.root.title("Image Color Pixel Extractor")

        # Paths
        self.images_folder = "images"
        self.annotations_file = "annotations.csv"
        self.output_file = "page_rec_pixels.csv"

        # Load labels and select images to process
        self.labels_to_process = self.load_labels_to_process()
        self.current_label_index = 0
        self.clicked_points = []

        # Current image data
        self.current_image_path = None
        self.current_image = None
        self.display_image = None
        self.photo = None

        # Setup GUI
        self.setup_gui()

        # Start processing
        if self.labels_to_process:
            self.load_next_label()
        else:
            self.show_completion_message()

    def load_labels_to_process(self):
        """Load unique labels from annotations.csv and select one random image per label"""
        # Read all annotations
        label_to_images = {}
        if os.path.exists(self.annotations_file):
            with open(self.annotations_file, 'r', newline='') as f:
                reader = csv.reader(f)
                for row in reader:
                    if row and len(row) >= 2:
                        image_name, label = row[0], row[1]
                        # Skip Null labels
                        if label.lower() != 'null':
                            if label not in label_to_images:
                                label_to_images[label] = []
                            label_to_images[label].append(image_name)

        # Load already processed labels
        processed_labels = set()
        if os.path.exists(self.output_file):
            with open(self.output_file, 'r', newline='') as f:
                reader = csv.reader(f)
                for row in reader:
                    if row:
                        processed_labels.add(row[0])

        # Select one random image per unprocessed label
        labels_to_process = []
        for label, images in label_to_images.items():
            if label not in processed_labels:
                random_image = random.choice(images)
                labels_to_process.append((label, random_image))

        return labels_to_process

    def setup_gui(self):
        """Setup the GUI components"""
        # Progress label at top
        self.progress_label = tk.Label(self.root, text="", font=("Arial", 14, "bold"))
        self.progress_label.pack(pady=10)

        # Main container with left and right sections
        main_container = tk.Frame(self.root)
        main_container.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Left side - Image display
        left_frame = tk.Frame(main_container)
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.canvas = tk.Canvas(left_frame, cursor="crosshair")
        self.canvas.pack()
        self.canvas.bind("<Button-1>", self.on_image_click)

        # Right side - Controls and info
        right_frame = tk.Frame(main_container)
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, padx=20)

        # Instructions
        instructions = tk.Label(right_frame, text="Click on the image to\nselect pixel points",
                               font=("Arial", 12), justify=tk.LEFT)
        instructions.pack(pady=10)

        # Points counter
        self.points_label = tk.Label(right_frame, text="Points selected: 0",
                                    font=("Arial", 11))
        self.points_label.pack(pady=10)

        # Points list
        list_label = tk.Label(right_frame, text="Selected Points:", font=("Arial", 10, "bold"))
        list_label.pack(pady=(20, 5))

        # Scrollable list of points
        list_frame = tk.Frame(right_frame)
        list_frame.pack(fill=tk.BOTH, expand=True)

        scrollbar = tk.Scrollbar(list_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.points_listbox = tk.Listbox(list_frame, yscrollcommand=scrollbar.set,
                                         font=("Courier", 9), width=30, height=15)
        self.points_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=self.points_listbox.yview)

        # Buttons
        button_frame = tk.Frame(right_frame)
        button_frame.pack(pady=20)

        self.clear_btn = tk.Button(button_frame, text="Clear All Points",
                                   command=self.clear_points,
                                   width=15, height=2, bg="#ffcccc")
        self.clear_btn.pack(pady=5)

        self.done_btn = tk.Button(button_frame, text="Done (Save & Next)",
                                 command=self.save_and_next,
                                 width=15, height=2, bg="#ccffcc",
                                 font=("Arial", 10, "bold"))
        self.done_btn.pack(pady=5)

    def load_next_label(self):
        """Load the next label's image"""
        if self.current_label_index >= len(self.labels_to_process):
            self.show_completion_message()
            return

        label, image_name = self.labels_to_process[self.current_label_index]
        self.current_label = label
        self.current_image_path = os.path.join(self.images_folder, image_name)
        self.clicked_points = []

        # Update progress
        total = len(self.labels_to_process)
        current = self.current_label_index + 1
        self.progress_label.config(text=f"Label: {label} ({current}/{total})")

        # Load and display image
        self.load_and_display_image()

    def load_and_display_image(self):
        """Load and display the current image"""
        # Load original image
        self.current_image = Image.open(self.current_image_path)

        # Convert BGR to RGB for display
        if self.current_image.mode == 'RGB':
            r, g, b = self.current_image.split()
            self.current_image = Image.merge('RGB', (b, g, r))

        # Create a copy for display with markers
        self.update_display()

    def update_display(self):
        """Update the display with current image and markers"""
        # Create a copy of the image
        display_img = self.current_image.copy()
        draw = ImageDraw.Draw(display_img)

        # Draw circles at clicked points
        for point in self.clicked_points:
            x, y = point['x'], point['y']
            r, g, b = point['r'], point['g'], point['b']
            radius = 5

            # Draw circle with the pixel's color as border
            draw.ellipse([x-radius, y-radius, x+radius, y+radius],
                        outline=(r, g, b), width=2)
            # Draw center point
            draw.ellipse([x-2, y-2, x+2, y+2], fill=(255, 255, 0))

        # Resize image to fit screen while maintaining aspect ratio
        max_width = 800
        max_height = 700
        display_img.thumbnail((max_width, max_height), Image.Resampling.LANCZOS)

        # Store scale factor for click coordinate conversion
        self.scale_x = display_img.width / self.current_image.width
        self.scale_y = display_img.height / self.current_image.height

        # Update canvas
        self.photo = ImageTk.PhotoImage(display_img)
        self.canvas.config(width=display_img.width, height=display_img.height)
        self.canvas.delete("all")
        self.canvas.create_image(0, 0, anchor=tk.NW, image=self.photo)

    def on_image_click(self, event):
        """Handle click on image to select a pixel"""
        # Convert display coordinates to original image coordinates
        orig_x = int(event.x / self.scale_x)
        orig_y = int(event.y / self.scale_y)

        # Ensure coordinates are within bounds
        if 0 <= orig_x < self.current_image.width and 0 <= orig_y < self.current_image.height:
            # Get pixel color from ORIGINAL image (before BGR to RGB conversion)
            original_img = Image.open(self.current_image_path)
            pixel = original_img.getpixel((orig_x, orig_y))

            # Store as BGR (swap R and B from RGB)
            if len(pixel) >= 3:
                r, g, b = pixel[0], pixel[1], pixel[2]
                # Store in BGR format
                point_data = {
                    'x': orig_x,
                    'y': orig_y,
                    'r': r,
                    'g': g,
                    'b': b
                }
                self.clicked_points.append(point_data)

                # Update display
                self.update_points_display()
                self.update_display()

    def update_points_display(self):
        """Update the points counter and list"""
        self.points_label.config(text=f"Points selected: {len(self.clicked_points)}")

        # Update listbox
        self.points_listbox.delete(0, tk.END)
        for i, point in enumerate(self.clicked_points):
            point_str = f"{i+1}. ({point['x']},{point['y']}) RGB({point['r']},{point['g']},{point['b']})"
            self.points_listbox.insert(tk.END, point_str)

    def clear_points(self):
        """Clear all selected points"""
        self.clicked_points = []
        self.update_points_display()
        self.update_display()

    def save_and_next(self):
        """Save current points to CSV and move to next label"""
        if not self.clicked_points:
            # Show warning if no points selected
            warning = tk.Toplevel(self.root)
            warning.title("Warning")
            tk.Label(warning, text="Please select at least one point!",
                    font=("Arial", 12), padx=20, pady=20).pack()
            tk.Button(warning, text="OK", command=warning.destroy,
                     width=10).pack(pady=10)
            return

        # Format points as [[x,y,r,g,b],[x,y,r,g,b],...]
        # But save in BGR format: [[x,y,b,g,r],[x,y,b,g,r],...]
        points_array = [[p['x'], p['y'], p['b'], p['g'], p['r']] for p in self.clicked_points]

        # Save to CSV
        with open(self.output_file, 'a', newline='') as f:
            writer = csv.writer(f)
            writer.writerow([self.current_label, str(points_array)])

        # Move to next label
        self.current_label_index += 1
        self.load_next_label()

    def show_completion_message(self):
        """Show message when all labels are processed"""
        self.progress_label.config(text="All labels have been processed!")
        self.canvas.delete("all")
        self.canvas.create_text(400, 300, text="Complete!",
                               font=("Arial", 24), fill="green")

        # Disable buttons
        self.clear_btn.config(state=tk.DISABLED)
        self.done_btn.config(state=tk.DISABLED)

def main():
    root = tk.Tk()
    app = PixelExtractor(root)
    root.mainloop()

if __name__ == "__main__":
    main()
