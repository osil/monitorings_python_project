import os
import psycopg2
from dotenv import load_dotenv
import speedtest
from main import get_ip_info

# โหลดค่าคอนฟิกจากไฟล์ .env
load_dotenv()

# =====================================================================
# DATABASE CONFIGURATION
# =====================================================================
DB_HOST = os.getenv("DB_HOST")
DB_NAME = os.getenv("DB_NAME")
DB_USER = os.getenv("DB_USER")
DB_PASS = os.getenv("DB_PASS")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_SCHEMA = os.getenv("DB_SCHEMA", "monitoring")

DEPARTMENT_ID = 4 

def run_speedtest(server_ids=None):
    """ฟังก์ชันหลักในการรัน Speedtest และรวบรวมข้อมูล IP"""
    st = speedtest.Speedtest()
    ip_info = get_ip_info()
    
    print("🔍 กำลังค้นหาเซิร์ฟเวอร์ที่ใกล้ที่สุด...")
    st.get_servers(server_ids)
    best_server = st.get_best_server()
    
    print(f"🚀 เริ่มทดสอบกับเซิร์ฟเวอร์: {best_server['sponsor']} ({best_server['name']}, {best_server['country']})")
    
    print("📥 กำลังทดสอบ Download Speed...")
    download_speed = st.download()
    
    print("📤 กำลังทดสอบ Upload Speed...")
    upload_speed = st.upload()
    
    # ดึงค่าผลลัพธ์ดิบ
    results = st.results.dict()
    
    # 1. ดึง Public IP ที่ Speedtest ตรวจจับได้ขากลาง
    public_ip = results.get('client', {}).get('ip', '') or ip_info['public_ip']
    
    # 2. ดึง Private IP ในเครื่อง Local
    private_ip = ip_info['private_ip']
    
    # แปลงหน่วยจาก bps ให้เป็น Mbps
    download_mbps = round(download_speed / 1000000, 2)
    upload_mbps = round(upload_speed / 1000000, 2)
    ping_ms = round(results['ping'], 2)
    jitter_ms = round(results.get('client', {}).get('jitter', 0.0), 2)
    
    return {
        "server_name": f"{best_server['sponsor']} - {best_server['name']}",
        "country": best_server['country'],
        "download_mbps": download_mbps,
        "upload_mbps": upload_mbps,
        "ping_ms": ping_ms,
        "jitter_ms": jitter_ms,
        "public_ip": public_ip,
        "private_ip": private_ip
    }

def build_error_metrics():
    """สร้าง metrics พื้นฐานสำหรับบันทึกกรณีทดสอบล้มเหลว"""
    ip_info = get_ip_info()
    return {
        "server_name": "N/A",
        "download_mbps": 0.0,
        "upload_mbps": 0.0,
        "ping_ms": 0.0,
        "jitter_ms": 0.0,
        "public_ip": ip_info['public_ip'],
        "private_ip": ip_info['private_ip'],
    }


def classify_speedtest_error(err):
    """แปลง exception เป็น error_code มาตรฐานสำหรับบันทึกในฐานข้อมูล"""
    text = str(err).lower()
    if "timeout" in text:
        return "SPEEDTEST_TIMEOUT"
    if "server" in text and ("not found" in text or "cannot" in text or "invalid" in text):
        return "SPEEDTEST_SERVER_ERROR"
    if "network" in text or "connection" in text:
        return "SPEEDTEST_NETWORK_ERROR"
    return "SPEEDTEST_UNKNOWN_ERROR"


def save_to_db(metrics, test_location, error_log=None, error_code=None):
    """ฟังก์ชันบันทึกข้อมูลพร้อม Public IP, Private IP, Error Log และ Error Code ลงตาราง"""
    try:
        conn = psycopg2.connect(
            host=DB_HOST, database=DB_NAME, user=DB_USER, password=DB_PASS, port=DB_PORT
        )
        cursor = conn.cursor()
        
        # 🔍 อัปเดต SQL ให้เพิ่มคอลัมน์ public_ip และ private_ip
        insert_query = f"""
            INSERT INTO {DB_SCHEMA}.internet_speed_logs (
                department_id, test_location, server_name, 
                download_mbps, upload_mbps, ping_ms, jitter_ms, 
                public_ip, private_ip, error_log, error_code, tested_at
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW());
        """
        
        cursor.execute(insert_query, (
            DEPARTMENT_ID,
            test_location,
            metrics['server_name'],
            metrics['download_mbps'],
            metrics['upload_mbps'],
            metrics['ping_ms'],
            metrics['jitter_ms'],
            metrics['public_ip'],        # ส่งค่าขารับ Public ไปบันทึก
            metrics['private_ip'],       # ส่งค่าวงภายใน LAN ไปบันทึก
            error_log,
            error_code
        ))
        
        conn.commit()
        cursor.close()
        conn.close()
        print(f"📥 [SUCCESS] บันทึกสถิติเน็ตพร้อมข้อมูล IP ({test_location}) สำเร็จ!")
        
    except Exception as db_err:
        db_error_code = "DB_CONNECTION_ERROR" if isinstance(db_err, psycopg2.OperationalError) else "DB_INSERT_ERROR"
        print(f"❌ [DATABASE ERROR] ({db_error_code}) ไม่สามารถบันทึกข้อมูลได้: {db_err}")

if __name__ == "__main__":
    print("--- [RMU-UOMS Network Agent] เริ่มต้นระบบทดสอบอินเทอร์เน็ตพร้อมจัดเก็บ IP ---")
    
    # -----------------------------------------------------------------
    # 1. ทดสอบอินเทอร์เน็ตภายในประเทศ (Domestic)
    # -----------------------------------------------------------------
    print("\n--- [เฟสที่ 1: ทดสอบในประเทศ] ---")
    try:
        domestic_results = run_speedtest()
        print(f"📈 [IP: {domestic_results['private_ip']} -> {domestic_results['public_ip']}]")
        print(f"   Download: {domestic_results['download_mbps']} Mbps | Upload: {domestic_results['upload_mbps']} Mbps")
        save_to_db(domestic_results, 'domestic')
    except Exception as e:
        print(f"❌ เกิดข้อผิดพลาดในการทดสอบในประเทศ: {e}")
        save_to_db(
            build_error_metrics(),
            'domestic',
            error_log=str(e),
            error_code=classify_speedtest_error(e),
        )

    # -----------------------------------------------------------------
    # 2. ทดสอบอินเทอร์เน็ตต่างประเทศ (International)
    # -----------------------------------------------------------------
    print("\n--- [เฟสที่ 2: ทดสอบต่างประเทศ] ---")
    try:
        inter_servers = [18451, 41426] 
        inter_results = run_speedtest(server_ids=inter_servers)
        print(f"📈 [IP: {inter_results['private_ip']} -> {inter_results['public_ip']}]")
        print(f"   Download: {inter_results['download_mbps']} Mbps | Upload: {inter_results['upload_mbps']} Mbps")
        save_to_db(inter_results, 'international')
    except Exception as e:
        print("⚠️ ขัดข้องในการระบุเซิร์ฟเวอร์สิงคโปร์ กำลังสลับไปโหมดอัตโนมัติ...")
        try:
            inter_results = run_speedtest()
            save_to_db(inter_results, 'international')
        except Exception as auto_err:
            print(f"❌ เกิดข้อผิดพลาดในโหมดต่างประเทศอัตโนมัติ: {auto_err}")
            save_to_db(
                build_error_metrics(),
                'international',
                error_log=str(auto_err),
                error_code=classify_speedtest_error(auto_err),
            )
            
    print("\n--- [สิ้นสุดการทดสอบอินเทอร์เน็ตแบบผูก IP] ---")