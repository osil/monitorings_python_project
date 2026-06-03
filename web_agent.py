import asyncio
import os
import time
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv
import requests
from main import get_ip_info

# 📦 ปิดการแสดงผลคำเตือนเรื่อง SSL
from requests.packages import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# โหลดค่าคอนฟิกจากไฟล์ .env
load_dotenv()

DB_HOST = os.getenv("DB_HOST")
DB_NAME = os.getenv("DB_NAME")
DB_USER = os.getenv("DB_USER")
DB_PASS = os.getenv("DB_PASS")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_SCHEMA = os.getenv("DB_SCHEMA", "monitoring")


def classify_web_exception(err):
    """แปลง exception จาก requests เป็น error_code มาตรฐาน"""
    text = str(err).lower()
    if "timeout" in text:
        return "WEB_TIMEOUT"
    if "connection" in text or "name or service not known" in text:
        return "WEB_CONNECTION_ERROR"
    return "WEB_REQUEST_ERROR"

def check_website_status(url):
    headers = {'User-Agent': 'RMU-UOMS Uptime Monitor Agent/1.0'}
    start_time = time.time()
    try:
        response = requests.get(url, headers=headers, timeout=10.0, verify=False)
        end_time = time.time()
        response_time_ms = int((end_time - start_time) * 1000)
        is_online = 200 <= response.status_code < 400
        if is_online:
            return response.status_code, response_time_ms, True, None, None

        error_log = f"HTTP {response.status_code} from {url}"
        return response.status_code, response_time_ms, False, error_log, "WEB_HTTP_ERROR"
    except requests.exceptions.Timeout as err:
        return 504, 10000, False, str(err), classify_web_exception(err)
    except requests.exceptions.ConnectionError as err:
        return 0, 0, False, str(err), classify_web_exception(err)
    except Exception as err:
        return 500, 0, False, str(err), classify_web_exception(err)

def save_web_log(db_conn, website_id, status_code, response_time_ms, is_online, public_ip, private_ip, error_log=None, error_code=None):
    try:
        cursor = db_conn.cursor()
        insert_query = f"""
            INSERT INTO {DB_SCHEMA}.website_logs (
                website_id, status_code, response_time_ms, is_online,
                public_ip, private_ip, error_log, error_code, checked_at
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, NOW());
        """
        cursor.execute(
            insert_query,
            (website_id, status_code, response_time_ms, is_online, public_ip, private_ip, error_log, error_code),
        )
        db_conn.commit()
        cursor.close()
        return True
    except Exception as e:
        db_conn.rollback()
        print(f"   ❌ [INSERT ERROR] (DB_INSERT_ERROR) ไม่สามารถบันทึก Log ได้: {e}")
        return False

def main():
    print(f"--- [RMU-UOMS Web Agent] ตรวจสอบสถานะเว็บไซต์แยกตามสังกัดหน่วยงาน ---")
    ip_info = get_ip_info()
    print(f"🌐 [IP: {ip_info['private_ip']} -> {ip_info['public_ip']}]")
    
    try:
        conn = psycopg2.connect(
            host=DB_HOST, database=DB_NAME, user=DB_USER, password=DB_PASS, port=DB_PORT
        )
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        # 🔍 อัปเดตคำสั่ง SQL ให้ดึง department_id ขึ้นมาด้วย
        cursor.execute(f"SELECT website_id, department_id, website_name, website_url FROM {DB_SCHEMA}.websites WHERE is_active = true;")
        active_sites = cursor.fetchall()
        cursor.close()
        
        print(f"📊 พบเว็บไซต์ระบบงานที่เปิดมอนิเตอร์: {len(active_sites)} เว็บไซต์")
        print("-" * 70)
        
        for site in active_sites:
            web_id = site['website_id']
            dept_id = site['department_id']  # ดึงไอดีกอง/คณะมาใช้งาน
            web_name = site['website_name']
            url = site['website_url']
            
            print(f"🔍 [หน่วยงาน ID: {dept_id}] ตรวจสอบเว็บ -> {web_name} ({url})")
            
            status_code, resp_time, is_online, error_log, error_code = check_website_status(url)
            status_text = "🟢 ONLINE" if is_online else "🔴 OFFLINE"
            print(f"   📊 ผลลัพธ์: {status_text} | Response: {resp_time} ms")
            
            # บันทึกข้อมูลประวัติ
            if save_web_log(
                conn,
                web_id,
                status_code,
                resp_time,
                is_online,
                ip_info['public_ip'],
                ip_info['private_ip'],
                error_log,
                error_code,
            ):
                print(f"   📥 บันทึกสถิติลง {DB_SCHEMA}.website_logs เรียบร้อย")
                
        conn.close()
        
    except Exception as db_err:
        print(f"❌ [DATABASE ERROR] (DB_CONNECTION_ERROR) เชื่อมต่อระบบฐานข้อมูลขัดข้อง: {db_err}")
        
    print("\n--- [สิ้นสุดกระบวนการตรวจสอบเว็บไซต์] ---")

if __name__ == "__main__":
    main()