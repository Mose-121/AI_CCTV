# รายละเอียดฟังก์ชันในไฟล์ ai_no_pattern.py

---

### ฟังก์ชันที่ 1: validate_image

| หัวข้อ | รายละเอียด |
|---|---|
| ชื่อฟังก์ชัน (Function Name) | ตรวจสอบความถูกต้องของภาพ |
| โค้ดชื่อฟังก์ชัน (Function Name Code) | [validate_image(img)](file:///d:/gog/AI_ocr/ai_no_pattern.py#51-59) |
| คำอธิบาย (Description) | ตรวจสอบว่าภาพที่รับเข้ามาถูกต้องและมีขนาดเพียงพอสำหรับการประมวลผล โดยต้องไม่เป็น None, มีข้อมูล, มีอย่างน้อย 2 มิติ และมีขนาดขั้นต่ำ 10×10 พิกเซล |
| ข้อมูลนำเข้า (Input Data) | img: np.ndarray |
| ตัวอย่างข้อมูลนำเข้า (Example of Input Data) | img = cv2.imread("label.jpg") ได้ np.ndarray shape (480, 640, 3) |
| ข้อมูลนำออก (Output Data) | bool (True = ภาพถูกต้อง, False = ไม่ผ่าน) |
| ตัวอย่างข้อมูลนำออก (Example of Output Data) | True |

---

### ฟังก์ชันที่ 2: preprocess_v1_clahe

| หัวข้อ | รายละเอียด |
|---|---|
| ชื่อฟังก์ชัน (Function Name) | ปรับปรุงภาพด้วย CLAHE |
| โค้ดชื่อฟังก์ชัน (Function Name Code) | [preprocess_v1_clahe(img)](file:///d:/gog/AI_ocr/ai_no_pattern.py#65-76) |
| คำอธิบาย (Description) | Strategy 1: ขยายภาพ 2 เท่า แปลงเป็น grayscale แล้วปรับ contrast แบบ local ด้วย CLAHE (clipLimit=2.5) เหมาะกับภาพที่มี contrast ไม่สม่ำเสมอ เป็นวิธีที่เร็วที่สุด |
| ข้อมูลนำเข้า (Input Data) | img: np.ndarray (ภาพสี BGR) |
| ตัวอย่างข้อมูลนำเข้า (Example of Input Data) | img = crop ป้ายรหัสครุภัณฑ์ shape (100, 200, 3) |
| ข้อมูลนำออก (Output Data) | Optional[np.ndarray] (ภาพ grayscale ที่ปรับ contrast แล้ว หรือ None ถ้า error) |
| ตัวอย่างข้อมูลนำออก (Example of Output Data) | np.ndarray shape (200, 400) dtype uint8 |

---

### ฟังก์ชันที่ 3: preprocess_v2_adaptive_thresh

| หัวข้อ | รายละเอียด |
|---|---|
| ชื่อฟังก์ชัน (Function Name) | ปรับปรุงภาพด้วย Adaptive Threshold |
| โค้ดชื่อฟังก์ชัน (Function Name Code) | [preprocess_v2_adaptive_thresh(img)](file:///d:/gog/AI_ocr/ai_no_pattern.py#78-95) |
| คำอธิบาย (Description) | Strategy 2: ขยายภาพ 2 เท่า แปลงเป็น grayscale ลด noise ด้วย fastNlMeansDenoising แล้วแปลงเป็นภาพขาว-ดำด้วย Adaptive Gaussian Threshold เหมาะกับภาพที่มีแสงไม่สม่ำเสมอหรือมีเงา |
| ข้อมูลนำเข้า (Input Data) | img: np.ndarray (ภาพสี BGR) |
| ตัวอย่างข้อมูลนำเข้า (Example of Input Data) | img = crop ป้ายรหัสครุภัณฑ์ shape (100, 200, 3) |
| ข้อมูลนำออก (Output Data) | Optional[np.ndarray] (ภาพ binary ขาว-ดำ หรือ None ถ้า error) |
| ตัวอย่างข้อมูลนำออก (Example of Output Data) | np.ndarray shape (200, 400) dtype uint8 ค่า 0 หรือ 255 |

---

### ฟังก์ชันที่ 4: preprocess_v3_otsu

| หัวข้อ | รายละเอียด |
|---|---|
| ชื่อฟังก์ชัน (Function Name) | ปรับปรุงภาพด้วย Otsu's Threshold |
| โค้ดชื่อฟังก์ชัน (Function Name Code) | [preprocess_v3_otsu(img)](file:///d:/gog/AI_ocr/ai_no_pattern.py#97-108) |
| คำอธิบาย (Description) | Strategy 3: ขยายภาพ 2 เท่า แปลงเป็น grayscale เบลอด้วย Gaussian Blur แล้วหา threshold อัตโนมัติด้วย Otsu's method เหมาะกับภาพที่พื้นหลังกับตัวอักษรแยกกันชัดเจน |
| ข้อมูลนำเข้า (Input Data) | img: np.ndarray (ภาพสี BGR) |
| ตัวอย่างข้อมูลนำเข้า (Example of Input Data) | img = crop ป้ายรหัสครุภัณฑ์ shape (100, 200, 3) |
| ข้อมูลนำออก (Output Data) | Optional[np.ndarray] (ภาพ binary ขาว-ดำ หรือ None ถ้า error) |
| ตัวอย่างข้อมูลนำออก (Example of Output Data) | np.ndarray shape (200, 400) dtype uint8 ค่า 0 หรือ 255 |

---

### ฟังก์ชันที่ 5: preprocess_v4_sharpened

| หัวข้อ | รายละเอียด |
|---|---|
| ชื่อฟังก์ชัน (Function Name) | ปรับปรุงภาพด้วย Sharpening + CLAHE |
| โค้ดชื่อฟังก์ชัน (Function Name Code) | [preprocess_v4_sharpened(img)](file:///d:/gog/AI_ocr/ai_no_pattern.py#110-122) |
| คำอธิบาย (Description) | Strategy 4: ขยายภาพ 3 เท่า แปลงเป็น grayscale เพิ่มความคมด้วย Unsharp Mask แล้วปรับ contrast ด้วย CLAHE (clipLimit=3.0) เหมาะกับภาพเบลอหรือตัวอักษรไม่คม |
| ข้อมูลนำเข้า (Input Data) | img: np.ndarray (ภาพสี BGR) |
| ตัวอย่างข้อมูลนำเข้า (Example of Input Data) | img = crop ป้ายรหัสครุภัณฑ์ shape (100, 200, 3) |
| ข้อมูลนำออก (Output Data) | Optional[np.ndarray] (ภาพ grayscale ที่ sharpen แล้ว หรือ None ถ้า error) |
| ตัวอย่างข้อมูลนำออก (Example of Output Data) | np.ndarray shape (300, 600) dtype uint8 |

---

### ฟังก์ชันที่ 6: preprocess_v5_inverted

| หัวข้อ | รายละเอียด |
|---|---|
| ชื่อฟังก์ชัน (Function Name) | ปรับปรุงภาพด้วยการกลับสี + CLAHE |
| โค้ดชื่อฟังก์ชัน (Function Name Code) | [preprocess_v5_inverted(img)](file:///d:/gog/AI_ocr/ai_no_pattern.py#124-135) |
| คำอธิบาย (Description) | Strategy 5: ขยายภาพ 2 เท่า แปลงเป็น grayscale กลับสีภาพ (bitwise_not) แล้วปรับ contrast ด้วย CLAHE เหมาะกับป้ายที่มีตัวอักษรสีอ่อนบนพื้นมืด |
| ข้อมูลนำเข้า (Input Data) | img: np.ndarray (ภาพสี BGR) |
| ตัวอย่างข้อมูลนำเข้า (Example of Input Data) | img = crop ป้ายรหัสครุภัณฑ์ shape (100, 200, 3) |
| ข้อมูลนำออก (Output Data) | Optional[np.ndarray] (ภาพ grayscale กลับสี หรือ None ถ้า error) |
| ตัวอย่างข้อมูลนำออก (Example of Output Data) | np.ndarray shape (200, 400) dtype uint8 |

---

### ฟังก์ชันที่ 7: preprocess_v6_morph

| หัวข้อ | รายละเอียด |
|---|---|
| ชื่อฟังก์ชัน (Function Name) | ปรับปรุงภาพด้วย Morphology + CLAHE + Otsu |
| โค้ดชื่อฟังก์ชัน (Function Name Code) | [preprocess_v6_morph(img)](file:///d:/gog/AI_ocr/ai_no_pattern.py#137-151) |
| คำอธิบาย (Description) | Strategy 6: ขยายภาพ 2 เท่า แปลงเป็น grayscale ขยายเส้นตัวอักษรด้วย dilate (kernel 2×2) ปรับ contrast ด้วย CLAHE แล้วแปลงเป็น binary ด้วย Otsu เหมาะกับตัวอักษรเส้นบางหรือขาดเป็นช่วง |
| ข้อมูลนำเข้า (Input Data) | img: np.ndarray (ภาพสี BGR) |
| ตัวอย่างข้อมูลนำเข้า (Example of Input Data) | img = crop ป้ายรหัสครุภัณฑ์ shape (100, 200, 3) |
| ข้อมูลนำออก (Output Data) | Optional[np.ndarray] (ภาพ binary หรือ None ถ้า error) |
| ตัวอย่างข้อมูลนำออก (Example of Output Data) | np.ndarray shape (200, 400) dtype uint8 ค่า 0 หรือ 255 |

---

### ฟังก์ชันที่ 8: preprocess_v7_bilateral

| หัวข้อ | รายละเอียด |
|---|---|
| ชื่อฟังก์ชัน (Function Name) | ปรับปรุงภาพด้วย Bilateral Filter + CLAHE |
| โค้ดชื่อฟังก์ชัน (Function Name Code) | [preprocess_v7_bilateral(img)](file:///d:/gog/AI_ocr/ai_no_pattern.py#153-163) |
| คำอธิบาย (Description) | Strategy 7: ขยายภาพ 3 เท่า แปลงเป็น grayscale ลด noise ด้วย Bilateral Filter (เก็บขอบไว้) แล้วปรับ contrast ด้วย CLAHE (clipLimit=3.0) เหมาะกับภาพที่มี noise เยอะแต่ต้องการเก็บขอบตัวอักษร |
| ข้อมูลนำเข้า (Input Data) | img: np.ndarray (ภาพสี BGR) |
| ตัวอย่างข้อมูลนำเข้า (Example of Input Data) | img = crop ป้ายรหัสครุภัณฑ์ shape (100, 200, 3) |
| ข้อมูลนำออก (Output Data) | Optional[np.ndarray] (ภาพ grayscale ที่กรอง noise แล้ว หรือ None ถ้า error) |
| ตัวอย่างข้อมูลนำออก (Example of Output Data) | np.ndarray shape (300, 600) dtype uint8 |

---

### ฟังก์ชันที่ 9: preprocess_v8_highres

| หัวข้อ | รายละเอียด |
|---|---|
| ชื่อฟังก์ชัน (Function Name) | ปรับปรุงภาพด้วยการขยายความละเอียดสูง + CLAHE + Otsu |
| โค้ดชื่อฟังก์ชัน (Function Name Code) | [preprocess_v8_highres(img)](file:///d:/gog/AI_ocr/ai_no_pattern.py#165-176) |
| คำอธิบาย (Description) | Strategy 8: ขยายภาพ 4 เท่า แปลงเป็น grayscale ปรับ contrast ด้วย CLAHE แล้วแปลงเป็น binary ด้วย Otsu เหมาะกับภาพเล็กมากที่ต้องขยายเพื่อให้ OCR อ่านได้ |
| ข้อมูลนำเข้า (Input Data) | img: np.ndarray (ภาพสี BGR) |
| ตัวอย่างข้อมูลนำเข้า (Example of Input Data) | img = crop ป้ายรหัสครุภัณฑ์ shape (50, 100, 3) |
| ข้อมูลนำออก (Output Data) | Optional[np.ndarray] (ภาพ binary ความละเอียดสูง หรือ None ถ้า error) |
| ตัวอย่างข้อมูลนำออก (Example of Output Data) | np.ndarray shape (200, 400) dtype uint8 ค่า 0 หรือ 255 |

---

### ฟังก์ชันที่ 10: clean_ocr_text

| หัวข้อ | รายละเอียด |
|---|---|
| ชื่อฟังก์ชัน (Function Name) | ทำความสะอาดข้อความ OCR |
| โค้ดชื่อฟังก์ชัน (Function Name Code) | [clean_ocr_text(text)](file:///d:/gog/AI_ocr/ai_no_pattern.py#194-200) |
| คำอธิบาย (Description) | ทำความสะอาดข้อความที่ OCR อ่านได้เบื้องต้น ลบช่องว่างหัวท้าย แปลง newline/tab เป็นช่องว่าง และลบอักขระพิเศษที่ไม่จำเป็นออก |
| ข้อมูลนำเข้า (Input Data) | text: str |
| ตัวอย่างข้อมูลนำเข้า (Example of Input Data) | "  SSH-04622!@  " |
| ข้อมูลนำออก (Output Data) | str (ข้อความที่ทำความสะอาดแล้ว) |
| ตัวอย่างข้อมูลนำออก (Example of Output Data) | "SSH-04622" |

---

### ฟังก์ชันที่ 11: _is_label_noise

| หัวข้อ | รายละเอียด |
|---|---|
| ชื่อฟังก์ชัน (Function Name) | ตรวจสอบคำ noise บนป้าย |
| โค้ดชื่อฟังก์ชัน (Function Name Code) | [_is_label_noise(text)](file:///d:/gog/AI_ocr/ai_no_pattern.py#202-223) |
| คำอธิบาย (Description) | ตรวจสอบว่าข้อความที่ OCR อ่านได้เป็นคำที่พิมพ์อยู่บนป้ายแต่ไม่ใช่รหัสครุภัณฑ์หรือไม่ ใช้ 3 วิธี: exact match กับรายการ noise words, partial match สำหรับคำที่ OCR อ่านบางส่วน และตรวจว่าเป็นตัวอักษรล้วน (ไม่มีตัวเลข) ≥ 3 ตัว |
| ข้อมูลนำเข้า (Input Data) | text: str |
| ตัวอย่างข้อมูลนำเข้า (Example of Input Data) | "CALIBRATION" |
| ข้อมูลนำออก (Output Data) | bool (True = เป็น noise, False = ไม่ใช่ noise) |
| ตัวอย่างข้อมูลนำออก (Example of Output Data) | True |

---

### ฟังก์ชันที่ 12: extract_text_no_pattern

| หัวข้อ | รายละเอียด |
|---|---|
| ชื่อฟังก์ชัน (Function Name) | ดึงข้อความรหัสครุภัณฑ์โดยไม่กำหนด pattern |
| โค้ดชื่อฟังก์ชัน (Function Name Code) | [extract_text_no_pattern(text)](file:///d:/gog/AI_ocr/ai_no_pattern.py#225-252) |
| คำอธิบาย (Description) | ดึงข้อความที่น่าจะเป็นรหัสครุภัณฑ์จากผลลัพธ์ OCR โดยไม่กำหนด pattern ตายตัว เงื่อนไข: ความยาว ≥ 4, ต้องมีทั้งตัวอักษรและตัวเลข, ตัวเลขอย่างน้อย 3 ตัว, ไม่เป็น noise word พร้อมคำนวณคะแนนความน่าเชื่อถือ |
| ข้อมูลนำเข้า (Input Data) | text: str |
| ตัวอย่างข้อมูลนำเข้า (Example of Input Data) | "SSH04622" |
| ข้อมูลนำออก (Output Data) | Optional[Tuple[str, float]] (cleaned_text, score) หรือ None |
| ตัวอย่างข้อมูลนำออก (Example of Output Data) | ("SSH04622", 1.0) |

---

### ฟังก์ชันที่ 13: correct_ocr_by_context

| หัวข้อ | รายละเอียด |
|---|---|
| ชื่อฟังก์ชัน (Function Name) | แก้ไข OCR misread ด้วยบริบทตำแหน่ง |
| โค้ดชื่อฟังก์ชัน (Function Name Code) | [correct_ocr_by_context(text)](file:///d:/gog/AI_ocr/ai_no_pattern.py#268-328) |
| คำอธิบาย (Description) | แก้ไขการอ่านผิดของ OCR โดยอาศัยหลักการว่ารหัสครุภัณฑ์มีโครงสร้าง prefix ตัวอักษร + suffix ตัวเลข จึงแปลงตัวเลขใน prefix เป็นตัวอักษร (เช่น 8→S) และแปลงตัวอักษรใน suffix เป็นตัวเลข (เช่น O→0) |
| ข้อมูลนำเข้า (Input Data) | text: str |
| ตัวอย่างข้อมูลนำเข้า (Example of Input Data) | "89H04622" |
| ข้อมูลนำออก (Output Data) | str (ข้อความที่แก้ไขแล้ว) |
| ตัวอย่างข้อมูลนำออก (Example of Output Data) | "SSH04622" |

---

### ฟังก์ชันที่ 14: build_positional_consensus

| หัวข้อ | รายละเอียด |
|---|---|
| ชื่อฟังก์ชัน (Function Name) | สร้างรหัส consensus ด้วย positional voting |
| โค้ดชื่อฟังก์ชัน (Function Name Code) | [build_positional_consensus(all_candidates)](file:///d:/gog/AI_ocr/ai_no_pattern.py#330-353) |
| คำอธิบาย (Description) | สร้างรหัส consensus จาก candidates หลายตัว โดย vote ทีละตำแหน่ง เลือก candidates ที่มีความยาวเท่ากัน (ความยาวที่พบมากที่สุด) แล้วสำหรับแต่ละตำแหน่งจะนับคะแนนถ่วงด้วย confidence เพื่อเลือกตัวอักษรที่ดีที่สุด |
| ข้อมูลนำเข้า (Input Data) | all_candidates: List[Tuple[str, float, str]] |
| ตัวอย่างข้อมูลนำเข้า (Example of Input Data) | [("SSH04622", 0.9, "easyocr"), ("SSH04622", 0.8, "easyocr"), ("SSH04612", 0.6, "easyocr")] |
| ข้อมูลนำออก (Output Data) | Optional[str] (รหัส consensus หรือ None) |
| ตัวอย่างข้อมูลนำออก (Example of Output Data) | "SSH04622" |

---

### ฟังก์ชันที่ 15: run_easyocr

| หัวข้อ | รายละเอียด |
|---|---|
| ชื่อฟังก์ชัน (Function Name) | รัน EasyOCR อ่านข้อความจากภาพ |
| โค้ดชื่อฟังก์ชัน (Function Name Code) | [run_easyocr(img_gray, top_crop)](file:///d:/gog/AI_ocr/ai_no_pattern.py#359-382) |
| คำอธิบาย (Description) | รัน EasyOCR engine บนภาพ grayscale/binary รองรับการตัดส่วนบน 45% ออก (top_crop=True) เพื่อเอาเฉพาะส่วนรหัสที่มักอยู่ด้านล่างของป้าย จำกัดตัวอักษรที่อนุญาตเป็น A-Z, 0-9 และ - เท่านั้น |
| ข้อมูลนำเข้า (Input Data) | img_gray: np.ndarray, top_crop: bool |
| ตัวอย่างข้อมูลนำเข้า (Example of Input Data) | img_gray = ภาพ grayscale shape (200, 400), top_crop = True |
| ข้อมูลนำออก (Output Data) | List[Tuple[str, float]] (รายการ text, confidence) |
| ตัวอย่างข้อมูลนำออก (Example of Output Data) | [("SSH04622", 0.92), ("HEALTH", 0.45)] |

---

### ฟังก์ชันที่ 16: rotate_image

| หัวข้อ | รายละเอียด |
|---|---|
| ชื่อฟังก์ชัน (Function Name) | หมุนภาพตามองศาที่กำหนด |
| โค้ดชื่อฟังก์ชัน (Function Name Code) | [rotate_image(img, angle)](file:///d:/gog/AI_ocr/ai_no_pattern.py#384-389) |
| คำอธิบาย (Description) | หมุนภาพตามองศาที่กำหนด (บวก = ทวนเข็มนาฬิกา, ลบ = ตามเข็ม) โดยเติมพื้นที่ว่างด้วยสีขาว ใช้แก้ปัญหาป้ายเอียงเล็กน้อยที่ทำให้ OCR อ่านผิด |
| ข้อมูลนำเข้า (Input Data) | img: np.ndarray, angle: float |
| ตัวอย่างข้อมูลนำเข้า (Example of Input Data) | img = ภาพ grayscale shape (200, 400), angle = 2.0 |
| ข้อมูลนำออก (Output Data) | np.ndarray (ภาพที่หมุนแล้ว ขนาดเท่าเดิม) |
| ตัวอย่างข้อมูลนำออก (Example of Output Data) | np.ndarray shape (200, 400) dtype uint8 |

---

### ฟังก์ชันที่ 17: try_all_ocr

| หัวข้อ | รายละเอียด |
|---|---|
| ชื่อฟังก์ชัน (Function Name) | ลอง OCR หลายมุมและหลายโหมด |
| โค้ดชื่อฟังก์ชัน (Function Name Code) | [try_all_ocr(processed_img)](file:///d:/gog/AI_ocr/ai_no_pattern.py#391-415) |
| คำอธิบาย (Description) | ลอง EasyOCR หลายมุม (0°, +2°, -2°) ทั้งโหมด crop และ full image รวม 6 ครั้งต่อภาพ เก็บทุก text ที่ผ่านเงื่อนไข extract_text_no_pattern พร้อมคำนวณ confidence × score เป็น candidates สำหรับ voting |
| ข้อมูลนำเข้า (Input Data) | processed_img: np.ndarray (ภาพที่ผ่าน preprocessing แล้ว) |
| ตัวอย่างข้อมูลนำเข้า (Example of Input Data) | processed_img = ภาพ grayscale shape (200, 400) |
| ข้อมูลนำออก (Output Data) | List[Tuple[str, float, str]] (cleaned_text, confidence×score, engine_name) |
| ตัวอย่างข้อมูลนำออก (Example of Output Data) | [("SSH04622", 0.85, "easyocr_crop"), ("SSH04622", 0.78, "easyocr_full_rot2")] |

---

### ฟังก์ชันที่ 18: correct_ocr_format

| หัวข้อ | รายละเอียด |
|---|---|
| ชื่อฟังก์ชัน (Function Name) | แก้ไขรูปแบบ OCR ทั้ง prefix และ suffix |
| โค้ดชื่อฟังก์ชัน (Function Name Code) | [correct_ocr_format(text)](file:///d:/gog/AI_ocr/ai_no_pattern.py#417-466) |
| คำอธิบาย (Description) | แก้ไข OCR misread ตามโครงสร้างรหัสครุภัณฑ์ (3 ตัวอักษร + ตัวเลข): ส่วนท้ายแปลงตัวอักษรคล้ายเลขเป็นตัวเลข (O→0, S→5) ส่วนหัวแปลงตัวเลขเป็นตัวอักษร (8→S, 5→S) และแก้ multi-character misread (F1→H, FI→H) |
| ข้อมูลนำเข้า (Input Data) | text: str |
| ตัวอย่างข้อมูลนำเข้า (Example of Input Data) | "89HO3558" |
| ข้อมูลนำออก (Output Data) | str (ข้อความที่แก้ไขแล้ว) |
| ตัวอย่างข้อมูลนำออก (Example of Output Data) | "SSH03558" |

---

### ฟังก์ชันที่ 19: pick_best_candidate

| หัวข้อ | รายละเอียด |
|---|---|
| ชื่อฟังก์ชัน (Function Name) | เลือก candidate ที่ดีที่สุดด้วย voting |
| โค้ดชื่อฟังก์ชัน (Function Name Code) | [pick_best_candidate(all_candidates)](file:///d:/gog/AI_ocr/ai_no_pattern.py#468-507) |
| คำอธิบาย (Description) | เลือก text ที่ดีที่สุดจาก candidates ทั้งหมดด้วย VOTE-FIRST strategy: นับจำนวน votes ของแต่ละ text จัดอันดับตาม votes > confidence แล้วส่งผ่าน correct_ocr_format เพื่อแก้ไขขั้นสุดท้าย |
| ข้อมูลนำเข้า (Input Data) | all_candidates: List[Tuple[str, float, str]] |
| ตัวอย่างข้อมูลนำเข้า (Example of Input Data) | [("SSH04622", 0.9, "easyocr_fast+v1_clahe"), ("SSH04622", 0.8, "easyocr_fast+v3_otsu"), ("SSH04612", 0.6, "easyocr_fast+v2_adaptive")] |
| ข้อมูลนำออก (Output Data) | Optional[Tuple[str, float, str]] (final_text, best_conf, best_engine) หรือ None |
| ตัวอย่างข้อมูลนำออก (Example of Output Data) | ("SSH04622", 0.9, "easyocr_fast+v1_clahe") |

---

### ฟังก์ชันที่ 20: detect_code (Main Pipeline)

| หัวข้อ | รายละเอียด |
|---|---|
| ชื่อฟังก์ชัน (Function Name) | ตรวจจับและอ่านรหัสครุภัณฑ์จากภาพ (Pipeline หลัก) |
| โค้ดชื่อฟังก์ชัน (Function Name Code) | [detect_code(img)](file:///d:/gog/AI_ocr/ai_no_pattern.py#513-618) |
| คำอธิบาย (Description) | Pipeline หลักของระบบ ทำงานแบบ Extreme Fast Mode: (1) ใช้ YOLO ตรวจจับตำแหน่งป้าย เอาแค่ 1 กล่อง confident สูงสุด (2) Crop ภาพตาม bounding box + padding 10% (3) ลอง 3 preprocessing เร็ว (CLAHE, Otsu, Adaptive) หยุดทันทีถ้า conf ≥ 0.45 (4) เลือก candidate ดีที่สุดด้วย voting + OCR correction |
| ข้อมูลนำเข้า (Input Data) | img: np.ndarray (ภาพสี BGR) |
| ตัวอย่างข้อมูลนำเข้า (Example of Input Data) | img = cv2.imread("photo.jpg") ได้ np.ndarray shape (1920, 1080, 3) |
| ข้อมูลนำออก (Output Data) | Dict ที่มี key: status, message, code, source, confidence, ocr_confidence, total_candidates, processing_time |
| ตัวอย่างข้อมูลนำออก (Example of Output Data) | {"status": "success", "message": "Detect และ OCR สำเร็จ (Fast Path)", "code": "SSH04622", "source": "easyocr_fast+v1_clahe", "confidence": 0.95, "ocr_confidence": 0.892, "total_candidates": 3, "processing_time": "0.45s"} |

---

### ฟังก์ชันที่ 21: ocr_image (API Endpoint)

| หัวข้อ | รายละเอียด |
|---|---|
| ชื่อฟังก์ชัน (Function Name) | API endpoint สำหรับอ่านรหัสครุภัณฑ์ |
| โค้ดชื่อฟังก์ชัน (Function Name Code) | [ocr_image()](file:///d:/gog/AI_ocr/ai_no_pattern.py#627-641) — route: POST `/ocr` |
| คำอธิบาย (Description) | Flask API endpoint รับไฟล์ภาพผ่าน multipart form-data (field name: "file") ตรวจสอบความถูกต้องของภาพ แล้วส่งเข้า detect_code pipeline คืนผลลัพธ์เป็น JSON |
| ข้อมูลนำเข้า (Input Data) | HTTP POST request พร้อมไฟล์ภาพใน field "file" |
| ตัวอย่างข้อมูลนำเข้า (Example of Input Data) | curl -X POST -F "file=@label.jpg" http://localhost:8000/ocr |
| ข้อมูลนำออก (Output Data) | JSON Response จาก detect_code() หรือ error message |
| ตัวอย่างข้อมูลนำออก (Example of Output Data) | {"status": "success", "code": "SSH04622", "confidence": 0.95, ...} |

---

### ฟังก์ชันที่ 22: debug_image (API Endpoint)

| หัวข้อ | รายละเอียด |
|---|---|
| ชื่อฟังก์ชัน (Function Name) | API endpoint สำหรับ debug ทดสอบทุก strategy |
| โค้ดชื่อฟังก์ชัน (Function Name Code) | [debug_image()](file:///d:/gog/AI_ocr/ai_no_pattern.py#647-680) — route: POST `/debug` |
| คำอธิบาย (Description) | Flask API endpoint สำหรับ debug รับภาพแล้วรัน OCR ด้วยทุก preprocessing strategy (v1-v8) คืนผลละเอียดของแต่ละ strategy เพื่อใช้เปรียบเทียบว่า strategy ไหนอ่านได้ดีที่สุด |
| ข้อมูลนำเข้า (Input Data) | HTTP POST request พร้อมไฟล์ภาพใน field "file" |
| ตัวอย่างข้อมูลนำเข้า (Example of Input Data) | curl -X POST -F "file=@label.jpg" http://localhost:8000/debug |
| ข้อมูลนำออก (Output Data) | JSON Response รายการผลลัพธ์จากทุก strategy พร้อม raw texts และ found codes |
| ตัวอย่างข้อมูลนำออก (Example of Output Data) | {"debug": [{"strategy": "v1_clahe", "raw_texts": [("SSH04622", 0.92)], "found": [{"text": "SSH04622", "score": 1.0}]}, ...]} |
