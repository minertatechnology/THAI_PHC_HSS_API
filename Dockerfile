# 1. ใช้ Base Image ของ Python ที่มีขนาดเล็กและเหมาะสม
FROM python:3.11-slim

# 2. ตั้งค่า Working Directory ภายใน Container
WORKDIR /app

# 3. คัดลอกไฟล์ที่บอก Dependencies และติดตั้งก่อน เพื่อใช้ประโยชน์จาก Docker Cache
COPY requirements.txt .
RUN pip install --force-reinstall --no-cache-dir -r requirements.txt

# 4. คัดลอกโค้ดโปรเจกต์ทั้งหมดเข้าไป
COPY . .

# 5. เปิด port 8000
EXPOSE 8000

# 6. คำสั่งสำหรับรันแอปใน Production
# ใช้ Gunicorn เป็นตัวจัดการ Process และให้มันเรียก Uvicorn Worker
# เพื่อให้แอปใช้ประโยชน์จาก CPU หลาย Core ได้เต็มที่
CMD ["gunicorn", "-w", "4", "-k", "uvicorn.workers.UvicornWorker", "app.main:app", "--bind", "0.0.0.0:8000"]