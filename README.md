# printer_test

ชุดสคริปต์ Python สำหรับมอนิเตอร์ 3 งานหลักในรอบเดียว:

- ตรวจสอบเว็บไซต์
- ทดสอบความเร็วอินเทอร์เน็ต
- ดึงสถิติเครื่องพิมพ์ผ่าน SNMP

## ไฟล์สำคัญ

- `main.py` - ฟังก์ชันกลางสำหรับดึง `public_ip` และ `private_ip`
- `web_agent.py` - ตรวจสอบสถานะเว็บไซต์และบันทึกลงฐานข้อมูล
- `network_agent.py` - รันทดสอบความเร็วเน็ตและบันทึกผลลงฐานข้อมูล
- `printer_agent_direct.py` - ดึงค่ามิเตอร์เครื่องพิมพ์และบันทึกลงฐานข้อมูล
- `run_monitoring.sh` - สคริปต์สำหรับรันทั้ง 3 งานแบบรอบอัตโนมัติ
- `requirements.txt` - รายการแพ็กเกจ Python แบบ pinned version
- `.env.example` - ตัวอย่างค่า environment

## การติดตั้ง

1. สร้าง virtual environment

```bash
python3 -m venv venv
source venv/bin/activate
```

2. ติดตั้ง dependencies

```bash
pip install -r requirements.txt
```

3. เตรียมไฟล์ `.env`

```bash
cp .env.example .env
```

แล้วแก้ค่าให้ตรงกับระบบจริง

## การรันแบบ manual

```bash
./run_monitoring.sh
```

## การรันอัตโนมัติทุก 10 นาที

เปิด crontab:

```bash
crontab -e
```

เพิ่มบรรทัดนี้:

```cron
*/10 * * * * PHASE_TIMEOUT_SECONDS=180 LOG_RETENTION_DAYS=30 /Users/tinnakorn/My-Dev/PYTHON/printer_test/run_monitoring.sh
```

## Log files

สคริปต์จะเก็บ log แยกรายวันไว้ในโฟลเดอร์ `logs/` เช่น:

- `logs/monitoring_2026-06-03.log`

## หมายเหตุ

- ต้องมี PostgreSQL schema และตารางที่รองรับคอลัมน์ที่สคริปต์บันทึกไว้แล้ว
- ถ้าใช้บนเครื่องอื่น ควรปรับ path ใน cron ให้เป็น path จริงของเครื่องนั้น
