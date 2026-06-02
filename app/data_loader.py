import os
import pandas as pd
import numpy as np
import collections

# Attempt pythainlp imports
try:
    from pythainlp.tokenize import word_tokenize
    from pythainlp.corpus.common import thai_stopwords
    THAI_STOPWORDS = thai_stopwords()
except ImportError:
    def word_tokenize(text, **kwargs):
        return text.split()
    THAI_STOPWORDS = set()

# Excel file path
EXCEL_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "ข้อมูลคำร้อง_sampled.xlsx")

def parse_thai_date(date_str):
    if pd.isna(date_str) or not isinstance(date_str, str):
        return pd.NaT
    date_str = date_str.strip()
    try:
        parts = date_str.split('/')
        if len(parts) == 3:
            day = int(parts[0])
            month = int(parts[1])
            year = int(parts[2]) - 543  # Convert Buddhist Era to Gregorian (A.D.)
            return pd.Timestamp(year=year, month=month, day=day)
    except Exception:
        pass
    return pd.NaT

def map_status(status_str):
    if pd.isna(status_str):
        return "ค้างอยู่"
    status_str = str(status_str).strip()
    if status_str == "ประเมินผลเสร็จสิ้น":
        return "เสร็จสิ้น"
    elif status_str in ["กำลังดำเนินการ", "อยู่ระหว่างการติดตาม", "แก้ไขคำร้อง"]:
        return "กำลังดำเนินการ"
    else:
        return "ค้างอยู่"

class ComplaintDataLoader:
    def __init__(self):
        self.df = None
        self.load_data()
        
    def load_data(self):
        if not os.path.exists(EXCEL_PATH):
            raise FileNotFoundError(f"Excel file not found at {EXCEL_PATH}")
            
        df = pd.read_excel(EXCEL_PATH)
        df.columns = [c.strip() for c in df.columns]
        
        # Parse Dates
        df['dt_received'] = df['วันที่รับเรื่อง'].apply(parse_thai_date)
        df['dt_completed'] = df['วันที่เสร็จ'].apply(parse_thai_date)
        
        # Calculate days difference (avg_days)
        df['calculated_avg_days'] = (df['dt_completed'] - df['dt_received']).dt.days
        df.loc[df['calculated_avg_days'] < 0, 'calculated_avg_days'] = 0
        
        # Map statuses
        df['mapped_status'] = df['สถานะ'].apply(map_status)
        
        # Normalize fields
        string_cols = ['ส่วนงาน', 'ฝ่าย', 'เลขคำร้อง', 'เรื่องร้องทุกข์', 'ประเภทคำร้อง', 'เขต', 'ชุมชน']
        for col in string_cols:
            if col in df.columns:
                df[col] = df[col].fillna("ไม่ระบุ").astype(str).str.strip()
                
        self.df = df
        
    def get_summary(self):
        total = len(self.df)
        status_counts = self.df['mapped_status'].value_counts().to_dict()
        completed = status_counts.get("เสร็จสิ้น", 0)
        in_progress = status_counts.get("กำลังดำเนินการ", 0)
        pending = status_counts.get("ค้างอยู่", 0)
        
        # Top Type
        type_counts = self.df['ประเภทคำร้อง'].value_counts()
        top_type = type_counts.index[0] if not type_counts.empty else "N/A"
        
        # Overall Avg Days (only for completed/valid avg_days)
        completed_df = self.df[self.df['calculated_avg_days'].notna()]
        overall_avg = float(completed_df['calculated_avg_days'].mean()) if not completed_df.empty else 0.0
        
        return {
            "total": total,
            "completed": completed,
            "in_progress": in_progress,
            "pending": pending,
            "top_type": top_type,
            "avg_days": round(overall_avg, 1)
        }
        
    def get_by_type(self):
        total = len(self.df)
        if total == 0:
            return []
        grouped = self.df['ประเภทคำร้อง'].value_counts().reset_index()
        grouped.columns = ['type', 'count']
        grouped['percent'] = ((grouped['count'] / total) * 100).round(1)
        return grouped.to_dict(orient="records")
        
    def get_by_department(self):
        # group by ส่วนงาน
        grouped = self.df.groupby('ส่วนงาน')
        res = []
        for name, group in grouped:
            count = len(group)
            completed_group = group[group['calculated_avg_days'].notna()]
            avg_days = float(completed_group['calculated_avg_days'].mean()) if not completed_group.empty else 0.0
            res.append({
                "dept": name,
                "count": count,
                "avg_days": round(avg_days, 1)
            })
        # Sort by count desc
        res = sorted(res, key=lambda x: x['count'], reverse=True)
        return res
        
    def get_performance(self):
        # group by ฝ่าย
        grouped = self.df.groupby('ฝ่าย')
        res = []
        for name, group in grouped:
            total = len(group)
            completed_group = group[group['calculated_avg_days'].notna()]
            
            if not completed_group.empty:
                avg_days = float(completed_group['calculated_avg_days'].mean())
                min_days = int(completed_group['calculated_avg_days'].min())
                max_days = int(completed_group['calculated_avg_days'].max())
            else:
                avg_days = 0.0
                min_days = 0
                max_days = 0
                
            res.append({
                "dept": name,  # key is dept in api contract but grouped by ฝ่าย
                "avg_days": round(avg_days, 1),
                "min": min_days,
                "max": max_days,
                "total": total
            })
        # Sort by total count descending
        res = sorted(res, key=lambda x: x['total'], reverse=True)
        return res
        
    def get_by_district(self):
        grouped = self.df['เขต'].value_counts().reset_index()
        grouped.columns = ['district', 'count']
        return grouped.to_dict(orient="records")
        
    def get_by_status(self):
        # Mapped statuses: เสร็จสิ้น, กำลังดำเนินการ, ค้างอยู่
        grouped = self.df['mapped_status'].value_counts().reset_index()
        grouped.columns = ['status', 'count']
        return grouped.to_dict(orient="records")
        
    def get_monthly_trend(self):
        # Get YYYY-MM
        df_valid = self.df[self.df['dt_received'].notna()].copy()
        df_valid['month'] = df_valid['dt_received'].dt.strftime('%Y-%m')
        
        grouped = df_valid.groupby('month').size().reset_index(name='count')
        grouped = grouped.sort_values('month')
        
        # Return last 12 months in the dataset
        records = grouped.tail(12).to_dict(orient="records")
        return records
        
    def get_records(self, page=1, per_page=10, search="", complaint_type="", district=""):
        temp_df = self.df.copy()
        
        # Apply search on title and complaint id
        if search:
            search_lower = search.lower()
            mask = (
                temp_df['เรื่องร้องทุกข์'].str.lower().str.contains(search_lower) |
                temp_df['เลขคำร้อง'].str.lower().str.contains(search_lower) |
                temp_df['ส่วนงาน'].str.lower().str.contains(search_lower) |
                temp_df['ฝ่าย'].str.lower().str.contains(search_lower)
            )
            temp_df = temp_df[mask]
            
        # Apply filters
        if complaint_type:
            temp_df = temp_df[temp_df['ประเภทคำร้อง'] == complaint_type]
            
        if district:
            temp_df = temp_df[temp_df['เขต'] == district]
            
        # Calculate pagination
        total_records = len(temp_df)
        total_pages = int(np.ceil(total_records / per_page)) if total_records > 0 else 1
        
        # Slice for pagination
        start_idx = (page - 1) * per_page
        end_idx = start_idx + per_page
        sliced_df = temp_df.iloc[start_idx:end_idx]
        
        data = []
        for _, row in sliced_df.iterrows():
            data.append({
                "id": str(row['เลขคำร้อง']),
                "department": str(row['ส่วนงาน']),
                "sub_department": str(row['ฝ่าย']),
                "title": str(row['เรื่องร้องทุกข์']),
                "type": str(row['ประเภทคำร้อง']),
                "district": str(row['เขต']),
                "community": str(row['ชุมชน']),
                "date_received": row['วันที่รับเรื่อง'],
                "date_completed": row['วันที่เสร็จ'] if pd.notna(row['วันที่เสร็จ']) else "-",
                "status": str(row['mapped_status']),
                "avg_days": int(row['calculated_avg_days']) if pd.notna(row['calculated_avg_days']) else 0
            })
            
        return {
            "total": total_records,
            "page": page,
            "per_page": per_page,
            "pages": total_pages,
            "data": data
        }
        
    def get_keywords(self, limit=20):
        text_data = " ".join(self.df['เรื่องร้องทุกข์'].astype(str).tolist())
        words = word_tokenize(text_data, keep_whitespace=False)
        cleaned_words = []
        for w in words:
            w = w.strip()
            if len(w) > 1 and w not in THAI_STOPWORDS and not w.isdigit():
                # Avoid punctuation characters
                if not any(char in '!"#$%&\'()*+,-./:;<=>?@[\\]^_`{|}~' for char in w):
                    cleaned_words.append(w)
        counter = collections.Counter(cleaned_words)
        return [{"word": word, "count": count} for word, count in counter.most_common(limit)]

    def add_complaint(self, title: str, complaint_type: str, department: str, sub_department: str, district: str, community: str):
        df_excel = pd.read_excel(EXCEL_PATH)
        
        current_year_be = 2569
        be_suffix = f"/{str(current_year_be)[-2:]}"
        
        seq_num = 1
        year_69_complaints = df_excel[df_excel['เลขคำร้อง'].astype(str).str.endswith(be_suffix)]
        if not year_69_complaints.empty:
            ids = []
            for item in year_69_complaints['เลขคำร้อง']:
                try:
                    parts = str(item).split('/')
                    ids.append(int(parts[0]))
                except ValueError:
                    pass
            if ids:
                seq_num = max(ids) + 1
                
        new_id = f"{seq_num}/69"
        
        import datetime
        now = datetime.datetime.now()
        day_str = f"{now.day:02d}"
        month_str = f"{now.month:02d}"
        year_str = f"{now.year + 543}"
        date_received_be = f"{day_str}/{month_str}/{year_str}"
        
        new_row = {
            'ส่วนงาน': department.strip(),
            'ฝ่าย': sub_department.strip(),
            'เลขคำร้อง': new_id,
            'เรื่องร้องทุกข์': title.strip(),
            'ประเภทคำร้อง': complaint_type.strip(),
            'เขต': district.strip(),
            'ชุมชน': community.strip(),
            'วันที่รับเรื่อง': date_received_be,
            'วันที่เสร็จ': np.nan,
            'สถานะ': 'รอช่างรับเรื่อง'
        }
        
        new_row_df = pd.DataFrame([new_row])
        df_excel = pd.concat([df_excel, new_row_df], ignore_index=True)
        df_excel.to_excel(EXCEL_PATH, index=False)
        
        self.load_data()
        return new_id

    def resolve_complaint(self, complaint_id: str):
        df_excel = pd.read_excel(EXCEL_PATH)
        
        df_excel['เลขคำร้อง'] = df_excel['เลขคำร้อง'].astype(str).str.strip()
        complaint_id_str = str(complaint_id).strip()
        
        mask = df_excel['เลขคำร้อง'] == complaint_id_str
        if not mask.any():
            raise KeyError(f"Complaint ID {complaint_id_str} not found")
            
        import datetime
        now = datetime.datetime.now()
        day_str = f"{now.day:02d}"
        month_str = f"{now.month:02d}"
        year_str = f"{now.year + 543}"
        date_completed_be = f"{day_str}/{month_str}/{year_str}"
        
        df_excel.loc[mask, 'สถานะ'] = 'ประเมินผลเสร็จสิ้น'
        df_excel.loc[mask, 'วันที่เสร็จ'] = date_completed_be
        
        df_excel.to_excel(EXCEL_PATH, index=False)
        self.load_data()
        return True

# Singleton instance
data_loader = ComplaintDataLoader()
