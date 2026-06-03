// 1. ตรวจสอบว่าลิงก์ Base URL ดึงค่าจากตัวแปรที่เราตั้งไว้ใน Vercel/ไฟล์ .env ถูกต้อง
const API_URL = import.meta.env.VITE_API_URL || "http://localhost:7860";

// 2. ปรับตัวพาร์ท (Path) สำหรับ Fetch ข้อมูลทุกตัวให้มี /api/ นำหน้าคำสั่งเดิม
useEffect(() => {
  const loadData = async () => {
    try {
      // 📊 ดึงข้อมูลสรุปภาพรวมด้านบน (จำนวนคำร้องทั้งหมด, รอดำเนินการ, กำลังทำ, เสร็จสิ้น)
      const resSummary = await fetch(`${API_URL}/api/summary`);
      const dataSummary = await resSummary.json();
      setSummaryData(dataSummary);

      // 📈 ดึงข้อมูลสำหรับกราฟประสิทธิภาพ (SLA)
      const resPerformance = await fetch(`${API_URL}/api/performance`);
      const dataPerformance = await resPerformance.json();
      setSlaData(dataPerformance);

      // 🍕 ดึงข้อมูลแยกตามสถานะคำร้อง
      const resStatus = await fetch(`${API_URL}/api/by-status`);
      const dataStatus = await resStatus.json();
      setStatusData(dataStatus);

      // 🗺️ ดึงข้อมูลแยกตามเขต/อำเภอ
      const resDistrict = await fetch(`${API_URL}/api/by-district`);
      const dataDistrict = await resDistrict.json();
      setDistrictData(dataDistrict);

      // 🛠️ ดึงข้อมูลแยกตามประเภทคำร้องเรียน (ถนนพัง, ไฟดับ, ขยะ ฯลฯ)
      const resType = await fetch(`${API_URL}/api/by-type`);
      const dataType = await resType.json();
      setTypeData(dataType);

    } catch (error) {
      console.error("เกิดข้อผิดพลาดในการโหลดข้อมูลคำร้องเรียน:", error);
    }
  };

  loadData();
}, []);
