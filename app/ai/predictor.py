import os
import joblib
import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
from sqlalchemy.orm import Session

MODEL_PATH_RISK = "predictor_risk.joblib"
MODEL_PATH_DAYS = "predictor_days.joblib"

class ComplaintPredictor:
    def __init__(self):
        self.risk_model = None
        self.days_model = None
        self.is_trained = False
        self.load_models()

    def load_models(self):
        try:
            if os.path.exists(MODEL_PATH_RISK) and os.path.exists(MODEL_PATH_DAYS):
                self.risk_model = joblib.load(MODEL_PATH_RISK)
                self.days_model = joblib.load(MODEL_PATH_DAYS)
                self.is_trained = True
            else:
                self.train_fallback_models()
        except Exception as e:
            print(f"Error loading prediction models: {e}. Training fallback models...")
            self.train_fallback_models()

    def train_fallback_models(self):
        """Train models with static synthetic data so they work even without database records."""
        print("Training fallback predictive ML models (Random Forest)...")
        
        # Synthetic historical training dataset
        # Columns: category_id, district_id, urgency_num, hour, month, completion_days, risk_level_num
        # Urgency: Low=0, Medium=1, High=2
        # Risk: Low=0, Medium=1, High=2, Critical=3
        data = []
        for _ in range(200):
            cat_id = np.random.randint(1, 7) # 1 to 6
            dist_id = np.random.randint(1, 7) # 1 to 6
            urgency = np.random.randint(0, 3) # 0 to 2
            hour = np.random.randint(7, 21)
            month = np.random.randint(1, 13)
            
            # Predict completion days logic
            base_days = 6.0
            if cat_id == 1: base_days = 2.0 # Electricity is faster
            elif cat_id == 3: base_days = 7.0 # Road Damage is slow
            elif cat_id == 4: base_days = 3.0 # Garbage is fast
            elif cat_id == 5: base_days = 8.0 # Flood is slow
            
            # Urgency factor
            days = base_days - (urgency * 1.5) + np.random.normal(0, 0.5)
            days = max(0.5, round(days, 1))
            
            # Risk level logic
            if urgency == 2:
                risk = 2 if np.random.random() > 0.4 else 3 # High or Critical
            elif urgency == 1:
                risk = 1 if np.random.random() > 0.3 else 2 # Medium or High
            else:
                risk = 0 if np.random.random() > 0.2 else 1 # Low or Medium
                
            data.append([cat_id, dist_id, urgency, hour, month, days, risk])

        df = pd.DataFrame(data, columns=["category_id", "district_id", "urgency_num", "hour", "month", "completion_days", "risk_level_num"])
        
        X = df[["category_id", "district_id", "urgency_num", "hour", "month"]]
        y_days = df["completion_days"]
        y_risk = df["risk_level_num"]

        self.days_model = RandomForestRegressor(n_estimators=50, random_state=42)
        self.days_model.fit(X, y_days)

        self.risk_model = RandomForestClassifier(n_estimators=50, random_state=42)
        self.risk_model.fit(X, y_risk)

        joblib.dump(self.days_model, MODEL_PATH_DAYS)
        joblib.dump(self.risk_model, MODEL_PATH_RISK)
        self.is_trained = True
        print("Fallback predictive models trained successfully.")

    def train_on_db_data(self, db: Session):
        """Train ML models using actual database history."""
        from ..models import Complaint
        
        complaints = db.query(Complaint).filter(Complaint.status.in_(["Completed", "Rejected"])).all()
        
        # If we don't have enough completed complaints (need at least 15 for decent fitting), train fallback
        if len(complaints) < 15:
            self.train_fallback_models()
            return True

        print(f"Training predictive models using {len(complaints)} historical database records...")
        
        data = []
        urgency_map = {"Low": 0, "Medium": 1, "High": 2}
        risk_map = {"Low": 0, "Medium": 1, "High": 2, "Critical": 3}
        
        for c in complaints:
            # Calculate actual resolution days
            if c.updated_at and c.created_at:
                delta = c.updated_at - c.created_at
                actual_days = max(0.5, delta.days + (delta.seconds / 86400.0))
            else:
                actual_days = c.estimated_completion_days or 5.0
                
            urgency_num = urgency_map.get(c.urgency, 1)
            risk_num = risk_map.get(c.risk_level, 1)
            
            hour = c.created_at.hour
            month = c.created_at.month
            
            data.append([
                c.category_id, 
                c.district_id, 
                urgency_num, 
                hour, 
                month, 
                actual_days, 
                risk_num
            ])
            
        df = pd.DataFrame(data, columns=["category_id", "district_id", "urgency_num", "hour", "month", "completion_days", "risk_level_num"])
        
        X = df[["category_id", "district_id", "urgency_num", "hour", "month"]]
        y_days = df["completion_days"]
        y_risk = df["risk_level_num"]

        self.days_model = RandomForestRegressor(n_estimators=100, random_state=42)
        self.days_model.fit(X, y_days)

        self.risk_model = RandomForestClassifier(n_estimators=100, random_state=42)
        self.risk_model.fit(X, y_risk)

        joblib.dump(self.days_model, MODEL_PATH_DAYS)
        joblib.dump(self.risk_model, MODEL_PATH_RISK)
        self.is_trained = True
        print("Predictive models retrained on actual database data successfully.")
        return True

    def predict(self, category_id: int, district_id: int, urgency: str):
        if not self.is_trained:
            self.load_models()

        urgency_map = {"Low": 0, "Medium": 1, "High": 2}
        urgency_num = urgency_map.get(urgency, 1)
        
        # We simulate current timestamp features
        import datetime
        now = datetime.datetime.now()
        hour = now.hour
        month = now.month

        # Prepare feature vector
        features = [[category_id, district_id, urgency_num, hour, month]]
        
        # Predict completion days
        pred_days = float(self.days_model.predict(features)[0])
        pred_days = max(0.5, round(pred_days, 1))

        # Predict risk level
        risk_num = int(self.risk_model.predict(features)[0])
        risk_reverse_map = {0: "Low", 1: "Medium", 2: "High", 3: "Critical"}
        risk_level = risk_reverse_map.get(risk_num, "Low")

        # Department recommendation logic based on category ID
        # 1: Electricity, 2: Water, 3: Road Damage, 4: Garbage, 5: Flood, 6: Public Safety
        dept_map = {
            1: "Bureau of Power & Lighting",
            2: "Water Resource Authority",
            3: "Department of Public Works",
            4: "Sanitation & Waste Management",
            5: "Stormwater & Drainage Agency",
            6: "Department of Inspections & Public Safety"
        }
        recommended_dept = dept_map.get(category_id, "City General Administration Office")

        return {
            "estimated_days": pred_days,
            "risk_level": risk_level,
            "recommended_department": recommended_dept
        }

# Singleton instance
predictor = ComplaintPredictor()
