import fitz  # PyMuPDF
from PIL import Image
import numpy as np
import sys
import os
from pathlib import Path

def remove_yellow_highlight(img):
    """
    מסיר צבעי צהוב של מרקר תוך שמירה על לבן כלבן
    """
    # המרה ל-numpy array לעיבוד קל יותר
    img_array = np.array(img)
    r, g, b = img_array[:,:,0], img_array[:,:,1], img_array[:,:,2]
    
    # זיהוי פיקסלים לבנים או כמעט לבנים
    white_threshold = 235
    is_white = (r >= white_threshold) & (g >= white_threshold) & (b >= white_threshold)
    
    # זיהוי צהוב/כתום (מרקר) - גישה רחבה יותר
    # צהוב הוא כאשר אדום+ירוק גבוהים וכחול נמוך
    yellow_ratio = (r.astype(float) + g.astype(float)) / (b.astype(float) + 1)  # +1 למניעת חלוקה באפס
    is_yellowish = (yellow_ratio > 2.2) & (r > 120) & (g > 120) & (b < 150)
    
    # יצירת תמונה חדשה
    new_img = img_array.copy()
    
    # שמירת לבן כלבן
    new_img[is_white] = [255, 255, 255]
    
    # להעלמת צהוב - הפיכה לאפור או לבן
    yellow_mask = is_yellowish & ~is_white
    if np.any(yellow_mask):
        # חישוב ערך אפור על בסיס הבהירות הכללית
        brightness = (r[yellow_mask] * 0.3 + g[yellow_mask] * 0.6 + b[yellow_mask] * 0.1)
        
        # אם הבהירות גבוהה (מרקר בהיר), הפוך ללבן
        bright_yellow = brightness > 180
        
        # אזורים בהירים -> לבן
        if np.any(bright_yellow):
            yellow_indices = np.where(yellow_mask)
            bright_indices = (yellow_indices[0][bright_yellow], yellow_indices[1][bright_yellow])
            new_img[bright_indices] = [255, 255, 255]
        
        # אזורים כהים יותר -> אפור
        dark_yellow = brightness <= 180
        if np.any(dark_yellow):
            yellow_indices = np.where(yellow_mask)
            dark_indices = (yellow_indices[0][dark_yellow], yellow_indices[1][dark_yellow])
            gray_value = brightness[dark_yellow].astype(np.uint8)
            new_img[dark_indices] = np.column_stack([gray_value, gray_value, gray_value])
    
    return Image.fromarray(new_img.astype(np.uint8))

def process_pdf(input_path):
    """
    מעבד PDF ושומר אותו בתיקייה מתאימה
    """
    # המרה ל-Path object
    input_path = Path(input_path)
    
    # בדיקה שהקובץ קיים
    if not input_path.exists():
        print(f"שגיאה: הקובץ '{input_path}' לא נמצא")
        return False
    
    # בדיקה שזה PDF
    if input_path.suffix.lower() != '.pdf':
        print(f"שגיאה: הקובץ '{input_path}' אינו PDF")
        return False
    
    # יצירת התיקייה היעד
    output_dir = input_path.parent / "exams with answers removed"
    output_dir.mkdir(exist_ok=True)
    
    # יצירת שם הקובץ החדש
    base_name = input_path.stem  # שם הקובץ ללא סיומת
    output_filename = f"{base_name} answers removed.pdf"
    output_path = output_dir / output_filename
    
    print(f"מעבד: {input_path.name}")
    print(f"יעד: {output_path}")
    
    try:
        # פתיחת הPDF ועיבוד
        doc = fitz.open(input_path)
        images = []
        
        for page_num, page in enumerate(doc):
            print(f"  מעבד עמוד {page_num + 1}/{len(doc)}...", end='\r')
            
            # המרת הדף לתמונה ברזולוציה גבוהה
            pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            
            # הפעלת הפילטר
            filtered_img = remove_yellow_highlight(img)
            images.append(filtered_img)
        
        print()  # שורה חדשה אחרי הלולאה
        
        # שמירת הPDF החדש
        if images:
            images[0].save(output_path, save_all=True, append_images=images[1:], resolution=150)
            print(f"✓ הקובץ נוצר בהצלחה: {output_path}")
            doc.close()
            return True
        else:
            print("שגיאה: לא נמצאו עמודים לעיבוד")
            doc.close()
            return False
            
    except Exception as e:
        print(f"שגיאה בעיבוד הקובץ: {e}")
        return False

def main():
    if len(sys.argv) != 2:
        print("שימוש: python filter.py <file_name>")
        print("דוגמה: python filter.py example.pdf")
        sys.exit(1)
    
    input_file = sys.argv[1]
    success = process_pdf(input_file)
    
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
