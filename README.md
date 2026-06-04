# printer_test

ชุดสคริปต์ Python สำหรับมอนิเตอร์ 3 งานหลักในรอบเดียว:

- ตรวจสอบเว็บไซต์
- ทดสอบความเร็วอินเทอร์เน็ต
- ดึงสถิติเครื่องพิมพ์ผ่าน SNMP
- รีล็อกอิน internet authentication gateway แบบ headless

## ไฟล์สำคัญ

- `main.py` - ฟังก์ชันกลางสำหรับดึง `public_ip` และ `private_ip`
- `web_agent.py` - ตรวจสอบสถานะเว็บไซต์และบันทึกลงฐานข้อมูล
- `network_agent.py` - รันทดสอบความเร็วเน็ตและบันทึกผลลงฐานข้อมูล
- `printer_agent_direct.py` - ดึงค่ามิเตอร์เครื่องพิมพ์และบันทึกลงฐานข้อมูล
- `gateway_auth_monitor.py` - ตรวจเช็คอินเทอร์เน็ตและล็อกอิน gateway อัตโนมัติผ่าน Selenium แบบ headless
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

สำหรับ gateway monitor ให้กำหนดเพิ่ม:

```bash
GATEWAY_USER=your_username
GATEWAY_PASS=your_password
# GATEWAY_CHECK_URL=https://www.google.com
# GATEWAY_LOG_FILE=/var/log/printer_test/gateway_auth_monitor.log
```

## การรันแบบ manual

```bash
./run_monitoring.sh
```

## การรัน gateway monitor บน Ubuntu Server 24.04 LTS

ติดตั้งแพ็กเกจระบบที่จำเป็น:

```bash
sudo apt update
sudo apt install -y chromium-driver chromium-browser
```

ติดตั้ง Python dependencies:

```bash
source venv/bin/activate
pip install -r requirements.txt
```

รันสคริปต์:

```bash
source venv/bin/activate
python3 gateway_auth_monitor.py
```

สคริปต์นี้ออกแบบให้ทำงานแบบ CLI ล้วน โดยใช้ Chrome headless และ ChromeDriver ที่ตำแหน่ง `/usr/bin/chromedriver`

## การรัน gateway monitor เป็น systemd service

มีไฟล์ตัวอย่าง service ที่ [deploy/gateway-auth-monitor.service](deploy/gateway-auth-monitor.service)

ตัวอย่างการติดตั้ง:

```bash
sudo mkdir -p /opt/printer_test
sudo cp -r . /opt/printer_test
sudo cp deploy/gateway-auth-monitor.service /etc/systemd/system/gateway-auth-monitor.service
```

ปรับค่าใน service file ให้ตรงกับ user และ path จริง จากนั้นสั่ง:

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now gateway-auth-monitor.service
sudo systemctl status gateway-auth-monitor.service
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
