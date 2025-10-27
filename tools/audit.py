import csv
import os
import ast
from PIL import Image

class ImageClassifierAudit:
    def __init__(self, tolerance=20):
        self.tolerance = tolerance
        self.images_folder = "images"
        self.annotations_file = "annotations.csv"
        self.pixel_data_file = "page_rec_pixels.csv"

        # Load data
        self.pixel_references = self.load_pixel_references()
        self.labeled_images = self.load_labeled_images()

    def load_pixel_references(self):
        """Load pixel reference data from page_rec_pixels.csv"""
        pixel_refs = {}
        if os.path.exists(self.pixel_data_file):
            with open(self.pixel_data_file, 'r', newline='') as f:
                reader = csv.reader(f)
                for row in reader:
                    if row and len(row) >= 2:
                        label = row[0]
                        # Parse the string representation of the list
                        pixel_data = ast.literal_eval(row[1])
                        pixel_refs[label] = pixel_data
        return pixel_refs

    def load_labeled_images(self):
        """Load labeled images from annotations.csv, grouped by label"""
        labeled_images = {}
        if os.path.exists(self.annotations_file):
            with open(self.annotations_file, 'r', newline='') as f:
                reader = csv.reader(f)
                for row in reader:
                    if row and len(row) >= 2:
                        image_name, label = row[0], row[1]
                        if label not in labeled_images:
                            labeled_images[label] = []
                        labeled_images[label].append(image_name)
        return labeled_images

    def check_pixel_match(self, ref_pixel, img_pixel):
        """Check if a pixel matches within tolerance"""
        # ref_pixel and img_pixel are in format [x, y, b, g, r]
        # Compare only the BGR values (indices 2, 3, 4)
        for i in range(2, 5):  # indices 2, 3, 4 for B, G, R
            if abs(ref_pixel[i] - img_pixel[i]) > self.tolerance:
                return False
        return True

    def classify_image(self, image_path, reference_pixels):
        """Check if an image matches all reference pixels within tolerance"""
        try:
            # Load image
            img = Image.open(image_path)

            # Check each reference pixel
            for ref_pixel in reference_pixels:
                x, y = ref_pixel[0], ref_pixel[1]
                ref_b, ref_g, ref_r = ref_pixel[2], ref_pixel[3], ref_pixel[4]

                # Get pixel from image at (x, y)
                if 0 <= x < img.width and 0 <= y < img.height:
                    img_pixel = img.getpixel((x, y))

                    # Extract BGR values
                    if len(img_pixel) >= 3:
                        img_r, img_g, img_b = img_pixel[0], img_pixel[1], img_pixel[2]

                        # Check if pixel matches within tolerance
                        img_pixel_data = [x, y, img_b, img_g, img_r]
                        if not self.check_pixel_match(ref_pixel, img_pixel_data):
                            return False
                else:
                    # Pixel coordinates out of bounds
                    return False

            # All pixels matched
            return True
        except Exception as e:
            print(f"Error processing image {image_path}: {e}")
            return False

    def audit_label(self, label):
        """Audit all images for a specific label"""
        if label not in self.pixel_references:
            return None

        if label not in self.labeled_images:
            return None

        reference_pixels = self.pixel_references[label]
        images = self.labeled_images[label]

        correct = 0
        incorrect = 0
        failed_images = []

        for image_name in images:
            image_path = os.path.join(self.images_folder, image_name)

            if os.path.exists(image_path):
                if self.classify_image(image_path, reference_pixels):
                    correct += 1
                else:
                    incorrect += 1
                    failed_images.append(image_name)
            else:
                # Image file not found
                incorrect += 1
                failed_images.append(image_name)

        total = correct + incorrect
        percent = (correct / total * 100) if total > 0 else 0.0

        return {
            'label': label,
            'correct': correct,
            'incorrect': incorrect,
            'percent': percent,
            'failed_images': failed_images
        }

    def run_audit(self):
        """Run audit for all labels and print results"""
        # Get all labels that have both pixel references and labeled images
        labels_to_audit = set(self.pixel_references.keys()) & set(self.labeled_images.keys())

        for label in sorted(labels_to_audit):
            result = self.audit_label(label)
            if result:
                label_str = "{:<25}".format(result['label'])
                correct_str = "{:^10}".format(result['correct'])
                incorrect_str = "{:^12}".format(result['incorrect'])
                percent_str = "{:^10}".format(f"{result['percent']:.1f}")
                failed_str = str(result['failed_images'])

                print(f"{label_str} | {correct_str} | {incorrect_str} | {percent_str} | {failed_str}")

def main():
    auditor = ImageClassifierAudit(tolerance=20)
    auditor.run_audit()

if __name__ == "__main__":
    main()
