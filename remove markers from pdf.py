import fitz  # PyMuPDF
from PIL import Image
import numpy as np
import sys
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox

def remove_yellow_highlight(img):
    """
    Remove yellow highlighter marks while keeping white areas white.
    """
    # Convert to a numpy array for easier processing.
    img_array = np.array(img)
    r, g, b = img_array[:,:,0], img_array[:,:,1], img_array[:,:,2]
    
    # Detect white or near-white pixels.
    white_threshold = 235
    is_white = (r >= white_threshold) & (g >= white_threshold) & (b >= white_threshold)
    
    # Detect yellow/orange highlight marks using a broad rule.
    # Yellow usually means red + green are high and blue is low.
    yellow_ratio = (r.astype(float) + g.astype(float)) / (b.astype(float) + 1)
    is_yellowish = (yellow_ratio > 2.2) & (r > 120) & (g > 120) & (b < 150)
    
    # Create a new image.
    new_img = img_array.copy()
    
    # Keep white pixels white.
    new_img[is_white] = [255, 255, 255]
    
    # Remove yellow areas by turning them gray or white.
    yellow_mask = is_yellowish & ~is_white
    if np.any(yellow_mask):
        # Compute a gray value based on overall brightness.
        brightness = (r[yellow_mask] * 0.3 + g[yellow_mask] * 0.6 + b[yellow_mask] * 0.1)
        
        # If the highlight is bright, turn it white.
        bright_yellow = brightness > 180
        
        # Bright areas become white.
        if np.any(bright_yellow):
            yellow_indices = np.where(yellow_mask)
            bright_indices = (yellow_indices[0][bright_yellow], yellow_indices[1][bright_yellow])
            new_img[bright_indices] = [255, 255, 255]
        
        # Darker areas become gray.
        dark_yellow = brightness <= 180
        if np.any(dark_yellow):
            yellow_indices = np.where(yellow_mask)
            dark_indices = (yellow_indices[0][dark_yellow], yellow_indices[1][dark_yellow])
            gray_value = brightness[dark_yellow].astype(np.uint8)
            new_img[dark_indices] = np.column_stack([gray_value, gray_value, gray_value])
    
    return Image.fromarray(new_img.astype(np.uint8))

def process_pdf(input_path):
    """
    Process a PDF and save the result in a matching folder.
    """
    # Convert to a Path object.
    input_path = Path(input_path)
    
    # Check that the file exists.
    if not input_path.exists():
        print(f"Error: file '{input_path}' was not found")
        return False
    
    # Check that the file is a PDF.
    if input_path.suffix.lower() != '.pdf':
        print(f"Error: file '{input_path}' is not a PDF")
        return False
    
    # Create the output folder.
    output_dir = input_path.parent / "exams with answers removed"
    output_dir.mkdir(exist_ok=True)
    
    # Create the output file name.
    base_name = input_path.stem
    output_filename = f"{base_name} answers removed.pdf"
    output_path = output_dir / output_filename
    
    print(f"Processing: {input_path.name}")
    print(f"Output: {output_path}")
    
    try:
        # Open the PDF and process each page.
        with fitz.open(input_path) as doc:
            images = []

            for page_num, page in enumerate(doc):
                print(f"  Processing page {page_num + 1}/{len(doc)}...", end='\r')

                # Render the page at a higher resolution.
                pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
                img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)

                # Apply the filter.
                filtered_img = remove_yellow_highlight(img)
                images.append(filtered_img)

            print()

            # Save the new PDF.
            if images:
                images[0].save(output_path, save_all=True, append_images=images[1:], resolution=150)
                print(f"Success: created {output_path}")
                return True

            print("Error: no pages were found to process")
            return False
            
    except Exception as e:
        print(f"Error while processing the file: {e}")
        return False

def launch_gui():
    root = tk.Tk()
    root.title("Remove Yellow Marks from PDF")
    root.resizable(False, False)
    root.geometry("520x180")

    selected_file = tk.StringVar(value="No file selected")
    status_text = tk.StringVar(value="Choose a PDF to begin.")

    frame = tk.Frame(root, padx=16, pady=16)
    frame.pack(fill="both", expand=True)

    title_label = tk.Label(frame, text="Remove Yellow Marks from PDF", font=("Segoe UI", 14, "bold"))
    title_label.pack(anchor="w")

    file_label = tk.Label(frame, textvariable=selected_file, wraplength=480, justify="left")
    file_label.pack(anchor="w", pady=(12, 8))

    button_row = tk.Frame(frame)
    button_row.pack(anchor="w", pady=(0, 10))

    def browse_file():
        file_path = filedialog.askopenfilename(
            title="Select a PDF",
            filetypes=[("PDF files", "*.pdf"), ("All files", "*.*")],
        )
        if file_path:
            selected_file.set(file_path)
            status_text.set("Ready to process the selected file.")

    def run_processing():
        file_path = selected_file.get()
        if file_path == "No file selected":
            messagebox.showwarning("No file selected", "Please choose a PDF first.")
            return

        status_text.set("Processing...")
        root.update_idletasks()
        success = process_pdf(file_path)
        if success:
            status_text.set("Done. The output file was created successfully.")
            messagebox.showinfo("Finished", "The output PDF was created successfully.")
        else:
            status_text.set("Processing failed.")
            messagebox.showerror("Error", "The PDF could not be processed.")

    browse_button = tk.Button(button_row, text="Browse...", command=browse_file, width=12)
    browse_button.pack(side="left")

    process_button = tk.Button(button_row, text="Remove Marks", command=run_processing, width=14)
    process_button.pack(side="left", padx=(10, 0))

    status_label = tk.Label(frame, textvariable=status_text, fg="#444444", wraplength=480, justify="left")
    status_label.pack(anchor="w", pady=(6, 0))

    root.mainloop()

def main():
    if len(sys.argv) == 2:
        success = process_pdf(sys.argv[1])
        sys.exit(0 if success else 1)

    launch_gui()

if __name__ == "__main__":
    main()
