import tkinter as tk
from tkinter import messagebox, ttk
from PIL import Image, ImageTk, ImageDraw
import csv
import os
import ast
from pathlib import Path
from audit import ImageClassifierAudit

class PixelDebugger:
    def __init__(self, root):
        self.root = root
        self.root.title("Pixel Debugger - Fix Failed Classifications")

        # Get the project root (parent of tools/)
        script_dir = Path(__file__).parent
        project_root = script_dir.parent

        # Set paths relative to project root
        self.images_folder = str(project_root / "data" / "training" / "images")
        self.annotations_file = str(project_root / "data" / "training" / "annotations.csv")
        self.pixel_data_file = str(project_root / "data" / "models" / "page_rec_pixels.csv")

        # State
        self.tolerance = 20
        self.current_label = None
        self.current_image_index = 0
        self.failed_images = []
        self.reference_pixels = []
        self.pixels_to_remove = set()  # Set of pixel indices to remove
        self.audit_results = {}
        self.hide_marked_pixels = tk.BooleanVar(value=True)  # Hide marked pixels by default
        self.scale_x = 1.0  # Scale factor for display
        self.scale_y = 1.0
        self.pixel_positions = []  # Store pixel positions on scaled canvas

        # GUI setup
        self.setup_gui()

        # Run initial audit
        self.run_audit()

    def setup_gui(self):
        """Setup the GUI components"""
        # Top controls
        top_frame = tk.Frame(self.root)
        top_frame.pack(fill=tk.X, padx=10, pady=10)

        tk.Label(top_frame, text="Tolerance:", font=("Arial", 10)).pack(side=tk.LEFT, padx=5)
        self.tolerance_spinbox = tk.Spinbox(top_frame, from_=0, to=100, width=5,
                                           command=self.update_tolerance)
        self.tolerance_spinbox.delete(0, tk.END)
        self.tolerance_spinbox.insert(0, str(self.tolerance))
        self.tolerance_spinbox.pack(side=tk.LEFT, padx=5)

        tk.Button(top_frame, text="Re-run Audit", command=self.run_audit,
                 bg="#cce5ff").pack(side=tk.LEFT, padx=20)

        # Hide marked pixels checkbox
        hide_checkbox = tk.Checkbutton(top_frame, text="Hide marked pixels",
                                      variable=self.hide_marked_pixels,
                                      command=self.on_hide_toggle)
        hide_checkbox.pack(side=tk.LEFT, padx=10)

        self.status_label = tk.Label(top_frame, text="", font=("Arial", 10, "bold"))
        self.status_label.pack(side=tk.LEFT, padx=20)

        # Main container
        main_container = tk.Frame(self.root)
        main_container.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Left side - Label selection
        left_frame = tk.Frame(main_container, width=250)
        left_frame.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 10))
        left_frame.pack_propagate(False)

        tk.Label(left_frame, text="Failed Labels:", font=("Arial", 12, "bold")).pack(pady=5)

        listbox_frame = tk.Frame(left_frame)
        listbox_frame.pack(fill=tk.BOTH, expand=True)

        scrollbar = tk.Scrollbar(listbox_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.labels_listbox = tk.Listbox(listbox_frame, yscrollcommand=scrollbar.set,
                                        font=("Courier", 9))
        self.labels_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=self.labels_listbox.yview)
        self.labels_listbox.bind('<<ListboxSelect>>', self.on_label_select)

        # Middle - Image display
        middle_frame = tk.Frame(main_container)
        middle_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.image_info_label = tk.Label(middle_frame, text="", font=("Arial", 11, "bold"))
        self.image_info_label.pack(pady=5)

        self.canvas = tk.Canvas(middle_frame, width=400, height=650, bg='white', cursor="crosshair")
        self.canvas.pack()
        self.canvas.bind("<Button-1>", self.on_canvas_click)

        # Navigation buttons
        nav_frame = tk.Frame(middle_frame)
        nav_frame.pack(pady=10)

        self.prev_btn = tk.Button(nav_frame, text="< Previous Image",
                                  command=self.prev_image, width=15)
        self.prev_btn.pack(side=tk.LEFT, padx=5)

        self.next_btn = tk.Button(nav_frame, text="Next Image >",
                                  command=self.next_image, width=15)
        self.next_btn.pack(side=tk.LEFT, padx=5)

        # Right side - Pixel details
        right_frame = tk.Frame(main_container, width=350)
        right_frame.pack(side=tk.LEFT, fill=tk.Y, padx=(10, 0))
        right_frame.pack_propagate(False)

        tk.Label(right_frame, text="Reference Pixels:", font=("Arial", 12, "bold")).pack(pady=5)

        tk.Label(right_frame, text="Click circles on image or list entries",
                font=("Arial", 9, "italic")).pack(pady=2)

        # Pixel list with scrollbar
        pixel_list_frame = tk.Frame(right_frame)
        pixel_list_frame.pack(fill=tk.BOTH, expand=True, pady=5)

        pixel_scrollbar = tk.Scrollbar(pixel_list_frame)
        pixel_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.pixels_listbox = tk.Listbox(pixel_list_frame,
                                        yscrollcommand=pixel_scrollbar.set,
                                        font=("Courier", 8), selectmode=tk.SINGLE)
        self.pixels_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        pixel_scrollbar.config(command=self.pixels_listbox.yview)
        self.pixels_listbox.bind('<<ListboxSelect>>', self.on_pixel_select)

        # Legend
        legend_frame = tk.Frame(right_frame)
        legend_frame.pack(pady=10)

        tk.Label(legend_frame, text="Legend:", font=("Arial", 10, "bold")).pack()
        tk.Label(legend_frame, text="● Green = Match", fg="green",
                font=("Arial", 9)).pack(anchor=tk.W)
        tk.Label(legend_frame, text="● Red = Fail", fg="red",
                font=("Arial", 9)).pack(anchor=tk.W)
        tk.Label(legend_frame, text="● Orange = Marked (when shown)", fg="orange",
                font=("Arial", 9)).pack(anchor=tk.W)
        tk.Label(legend_frame, text="● Hidden = Marked for removal", fg="gray",
                font=("Arial", 9)).pack(anchor=tk.W)

        # Action buttons
        action_frame = tk.Frame(right_frame)
        action_frame.pack(pady=10)

        tk.Button(action_frame, text="Clear Selection",
                 command=self.clear_removal_selection,
                 width=15, bg="#ffe5cc").pack(pady=5)

        tk.Button(action_frame, text="Save Changes",
                 command=self.save_changes,
                 width=15, height=2, bg="#ccffcc",
                 font=("Arial", 10, "bold")).pack(pady=5)

    def update_tolerance(self):
        """Update tolerance value"""
        try:
            self.tolerance = int(self.tolerance_spinbox.get())
            if self.current_label and self.failed_images:
                self.display_current_image()
        except ValueError:
            pass

    def on_hide_toggle(self):
        """Handle hide marked pixels checkbox toggle"""
        if self.current_label and self.failed_images:
            self.display_current_image()

    def on_canvas_click(self, event):
        """Handle click on canvas to select pixel"""
        if not self.pixel_positions:
            return

        # Find the closest pixel to the click
        click_x = event.x
        click_y = event.y

        min_distance = float('inf')
        closest_idx = None

        for pixel_info in self.pixel_positions:
            px, py = pixel_info['display_x'], pixel_info['display_y']
            distance = ((click_x - px) ** 2 + (click_y - py) ** 2) ** 0.5

            if distance < min_distance:
                min_distance = distance
                closest_idx = pixel_info['idx']

        # If click is within reasonable distance (30 pixels), toggle that pixel
        if closest_idx is not None and min_distance < 30:
            self.toggle_pixel_removal(closest_idx)

    def toggle_pixel_removal(self, pixel_idx):
        """Toggle a pixel for removal and refresh display"""
        if pixel_idx in self.pixels_to_remove:
            self.pixels_to_remove.remove(pixel_idx)
            action = "Unmarked"
        else:
            self.pixels_to_remove.add(pixel_idx)
            action = "Marked"

        # Update status
        self.status_label.config(
            text=f"{action} pixel {pixel_idx} for removal ({len(self.pixels_to_remove)} total)",
            fg="blue"
        )

        # Refresh display
        self.display_current_image()

    def run_audit(self):
        """Run the audit and populate failed labels"""
        self.status_label.config(text="Running audit...", fg="orange")
        self.root.update()

        try:
            auditor = ImageClassifierAudit(tolerance=self.tolerance)

            # Get all labels
            labels_to_audit = set(auditor.pixel_references.keys()) & set(auditor.labeled_images.keys())

            self.audit_results = {}
            failed_labels = []

            for label in sorted(labels_to_audit):
                result = auditor.audit_label(label)
                if result and result['incorrect'] > 0:
                    self.audit_results[label] = result
                    failed_labels.append(label)

            # Update labels listbox
            self.labels_listbox.delete(0, tk.END)
            for label in failed_labels:
                result = self.audit_results[label]
                display_text = f"{label}: {result['incorrect']} failed"
                self.labels_listbox.insert(tk.END, display_text)

            if failed_labels:
                self.status_label.config(text=f"Found {len(failed_labels)} labels with failures", fg="red")
            else:
                self.status_label.config(text="No failures found!", fg="green")

        except Exception as e:
            messagebox.showerror("Error", f"Failed to run audit: {e}")
            self.status_label.config(text="Audit failed", fg="red")

    def on_label_select(self, event):
        """Handle label selection"""
        selection = self.labels_listbox.curselection()
        if not selection:
            return

        idx = selection[0]
        label_text = self.labels_listbox.get(idx)
        label = label_text.split(':')[0]

        self.current_label = label
        self.current_image_index = 0
        self.pixels_to_remove.clear()

        # Load failed images for this label
        if label in self.audit_results:
            self.failed_images = self.audit_results[label]['failed_images']

            # Load reference pixels for this label
            self.reference_pixels = self.load_pixel_references_for_label(label)

            # Display first failed image
            self.display_current_image()

    def load_pixel_references_for_label(self, label):
        """Load pixel references for a specific label"""
        if os.path.exists(self.pixel_data_file):
            with open(self.pixel_data_file, 'r', newline='') as f:
                reader = csv.reader(f)
                for row in reader:
                    if row and len(row) >= 2 and row[0] == label:
                        return ast.literal_eval(row[1])
        return []

    def display_current_image(self):
        """Display the current failed image with pixel overlays"""
        if not self.failed_images or self.current_image_index >= len(self.failed_images):
            return

        image_name = self.failed_images[self.current_image_index]
        image_path = os.path.join(self.images_folder, image_name)

        if not os.path.exists(image_path):
            messagebox.showerror("Error", f"Image not found: {image_path}")
            return

        # Update info label
        self.image_info_label.config(
            text=f"Label: {self.current_label} | Image {self.current_image_index + 1}/{len(self.failed_images)}: {image_name}"
        )

        # Load image
        img = Image.open(image_path)
        display_img = img.copy()
        draw = ImageDraw.Draw(display_img)

        # Check each reference pixel and draw markers
        pixel_results = []
        self.pixel_positions = []  # Reset pixel positions for click detection
        hide_mode = self.hide_marked_pixels.get()

        for idx, ref_pixel in enumerate(self.reference_pixels):
            x, y = ref_pixel[0], ref_pixel[1]
            ref_b, ref_g, ref_r = ref_pixel[2], ref_pixel[3], ref_pixel[4]

            if 0 <= x < img.width and 0 <= y < img.height:
                img_pixel = img.getpixel((x, y))

                if len(img_pixel) >= 3:
                    img_r, img_g, img_b = img_pixel[0], img_pixel[1], img_pixel[2]

                    # Check if pixel matches
                    matches = (abs(ref_b - img_b) <= self.tolerance and
                             abs(ref_g - img_g) <= self.tolerance and
                             abs(ref_r - img_r) <= self.tolerance)

                    # Store result
                    pixel_results.append({
                        'idx': idx,
                        'x': x,
                        'y': y,
                        'ref': (ref_r, ref_g, ref_b),
                        'actual': (img_r, img_g, img_b),
                        'matches': matches
                    })

                    # Skip drawing if this pixel is marked for removal and hide mode is on
                    is_marked = idx in self.pixels_to_remove
                    if hide_mode and is_marked:
                        continue

                    # Draw marker
                    radius = 8

                    # Choose color based on state
                    if is_marked:
                        color = (255, 165, 0)  # Orange
                        fill = (255, 200, 100, 128)
                    elif matches:
                        color = (0, 255, 0)  # Green
                        fill = (100, 255, 100, 128)
                    else:
                        color = (255, 0, 0)  # Red
                        fill = (255, 100, 100, 128)

                    # Draw circle
                    draw.ellipse([x-radius, y-radius, x+radius, y+radius],
                               outline=color, width=3, fill=fill)

                    # Draw index number
                    draw.text((x-5, y-5), str(idx), fill=color)

        # Resize for display
        max_width = 400
        max_height = 650
        orig_width, orig_height = display_img.size
        display_img.thumbnail((max_width, max_height), Image.Resampling.LANCZOS)

        # Calculate scale factors
        self.scale_x = display_img.width / orig_width
        self.scale_y = display_img.height / orig_height

        # Store scaled pixel positions for click detection
        for result in pixel_results:
            if hide_mode and result['idx'] in self.pixels_to_remove:
                continue  # Don't add hidden pixels to clickable positions

            self.pixel_positions.append({
                'idx': result['idx'],
                'display_x': int(result['x'] * self.scale_x),
                'display_y': int(result['y'] * self.scale_y)
            })

        # Update canvas
        self.photo = ImageTk.PhotoImage(display_img)
        self.canvas.config(width=display_img.width, height=display_img.height)
        self.canvas.delete("all")
        self.canvas.create_image(0, 0, anchor=tk.NW, image=self.photo)

        # Update pixel listbox
        self.update_pixel_listbox(pixel_results)

    def update_pixel_listbox(self, pixel_results):
        """Update the pixel listbox with results"""
        self.pixels_listbox.delete(0, tk.END)

        for result in pixel_results:
            idx = result['idx']
            x, y = result['x'], result['y']
            ref = result['ref']
            actual = result['actual']
            matches = result['matches']

            status = "PASS" if matches else "FAIL"
            marker = "X" if idx in self.pixels_to_remove else " "

            line = f"[{marker}] {idx:2d} ({x:3d},{y:3d}) {status}"
            self.pixels_listbox.insert(tk.END, line)

            line2 = f"     Ref: RGB{ref}"
            self.pixels_listbox.insert(tk.END, line2)

            line3 = f"     Act: RGB{actual}"
            self.pixels_listbox.insert(tk.END, line3)

            # Color code the status line
            if idx in self.pixels_to_remove:
                self.pixels_listbox.itemconfig(self.pixels_listbox.size()-3, fg='orange')
            elif matches:
                self.pixels_listbox.itemconfig(self.pixels_listbox.size()-3, fg='green')
            else:
                self.pixels_listbox.itemconfig(self.pixels_listbox.size()-3, fg='red')

    def on_pixel_select(self, event):
        """Handle pixel selection to toggle removal"""
        selection = self.pixels_listbox.curselection()
        if not selection:
            return

        idx = selection[0]
        line = self.pixels_listbox.get(idx)

        # Only process status lines (those starting with [)
        if not line.startswith('['):
            return

        # Extract pixel index from line
        try:
            parts = line.split()
            pixel_idx = int(parts[1])

            # Toggle removal using shared method
            self.toggle_pixel_removal(pixel_idx)

        except (ValueError, IndexError):
            pass

    def clear_removal_selection(self):
        """Clear all pixels marked for removal"""
        self.pixels_to_remove.clear()
        self.display_current_image()

    def prev_image(self):
        """Show previous failed image"""
        if self.current_image_index > 0:
            self.current_image_index -= 1
            self.display_current_image()

    def next_image(self):
        """Show next failed image"""
        if self.current_image_index < len(self.failed_images) - 1:
            self.current_image_index += 1
            self.display_current_image()

    def save_changes(self):
        """Save the updated pixel references to CSV"""
        if not self.pixels_to_remove:
            messagebox.showinfo("Info", "No pixels marked for removal")
            return

        # Confirm action
        msg = f"Remove {len(self.pixels_to_remove)} pixel(s) from label '{self.current_label}'?"
        if not messagebox.askyesno("Confirm", msg):
            return

        try:
            # Read all data
            all_data = []
            if os.path.exists(self.pixel_data_file):
                with open(self.pixel_data_file, 'r', newline='') as f:
                    reader = csv.reader(f)
                    all_data = list(reader)

            # Update the current label's pixels
            for i, row in enumerate(all_data):
                if row and row[0] == self.current_label:
                    pixels = ast.literal_eval(row[1])
                    # Remove selected pixels (in reverse order to maintain indices)
                    for idx in sorted(self.pixels_to_remove, reverse=True):
                        if 0 <= idx < len(pixels):
                            del pixels[idx]

                    # Update row
                    all_data[i] = [self.current_label, str(pixels)]
                    break

            # Write back to file
            with open(self.pixel_data_file, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerows(all_data)

            messagebox.showinfo("Success", f"Removed {len(self.pixels_to_remove)} pixel(s)")

            # Clear selection and reload
            self.pixels_to_remove.clear()
            self.reference_pixels = self.load_pixel_references_for_label(self.current_label)

            # Re-run audit
            self.run_audit()

            # Try to reselect the same label if it still has failures
            for i in range(self.labels_listbox.size()):
                if self.labels_listbox.get(i).startswith(self.current_label + ':'):
                    self.labels_listbox.selection_clear(0, tk.END)
                    self.labels_listbox.selection_set(i)
                    self.on_label_select(None)
                    break

        except Exception as e:
            messagebox.showerror("Error", f"Failed to save changes: {e}")

def main():
    root = tk.Tk()
    root.geometry("1200x800")
    app = PixelDebugger(root)
    root.mainloop()

if __name__ == "__main__":
    main()
