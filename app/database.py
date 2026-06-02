from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from .config import settings
import os

# SQLite configuration details for concurrent access
connect_args = {}
if settings.DATABASE_URL.startswith("sqlite"):
    connect_args["check_same_thread"] = False

engine = create_engine(settings.DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_db():
    from .models import User, District, ComplaintCategory, Complaint, AIPrediction, AnalyticsLog
    import bcrypt
    import random
    from datetime import datetime, timedelta

    Base.metadata.create_all(bind=engine)
    
    db = SessionLocal()
    try:
        # Check if database is already seeded
        if db.query(User).first() is not None:
            return
            
        print("Seeding database...")
        def get_hash(pw: str) -> str:
            salt = bcrypt.gensalt()
            return bcrypt.hashpw(pw.encode('utf-8'), salt).decode('utf-8')
        
        # 1. Create categories
        categories_data = [
            ("Electricity", "Issues regarding streetlights, power lines, blackouts, or electricity infrastructure."),
            ("Water", "Issues regarding water pipe leaks, water quality, hydrants, or low pressure."),
            ("Road Damage", "Issues regarding potholes, cracked asphalt, missing traffic signs, or broken barriers."),
            ("Garbage", "Issues regarding illegal dumping, overflowing bins, missed collections, or littering."),
            ("Flood", "Issues regarding clogged storm drains, standing water, or localized flooding during rain."),
            ("Public Safety", "Issues regarding street hazards, abandoned vehicles, loitering, or dangerous physical conditions.")
        ]
        categories = []
        for name, desc in categories_data:
            cat = ComplaintCategory(name=name, description=desc)
            db.add(cat)
            categories.append(cat)
        db.commit()

        # 2. Create districts
        districts_data = [
            ("Downtown", 85000, 40.7128, -74.0060, 1.2),
            ("North Heights", 62000, 40.7428, -74.0160, 0.8),
            ("West End", 45000, 40.7228, -74.0460, 1.5),
            ("South Haven", 95000, 40.6728, -73.9860, 1.1),
            ("East River", 58000, 40.7328, -73.9560, 0.9),
            ("Waterfront", 32000, 40.6928, -74.0260, 1.4)
        ]
        districts = []
        for name, pop, lat, lng, risk in districts_data:
            dist = District(name=name, population=pop, latitude=lat, longitude=lng, risk_score=risk)
            db.add(dist)
            districts.append(dist)
        db.commit()

        # 3. Create users
        admin_pw = get_hash("admin123")
        officer_pw = get_hash("officer123")
        viewer_pw = get_hash("viewer123")

        
        users_data = [
            ("admin", "admin@smartcity.gov", admin_pw, "Administrator", "Admin"),
            ("officer_alex", "alex@smartcity.gov", officer_pw, "Officer Alex", "Officer"),
            ("officer_sarah", "sarah@smartcity.gov", officer_pw, "Officer Sarah", "Officer"),
            ("viewer_john", "john@citizen.org", viewer_pw, "Viewer John", "Viewer")
        ]
        users = []
        for uname, email, pw, name, role in users_data:
            usr = User(username=uname, email=email, hashed_password=pw, full_name=name, role=role, is_active=True)
            db.add(usr)
            users.append(usr)
        db.commit()

        # Get seeded instances
        db_categories = db.query(ComplaintCategory).all()
        db_districts = db.query(District).all()
        db_users = db.query(User).all()
        
        admin_user = next(u for u in db_users if u.role == "Admin")
        officers = [u for u in db_users if u.role == "Officer"]
        viewer_user = next(u for u in db_users if u.role == "Viewer")

        # 4. Generate realistic historical complaints
        descriptions = {
            "Electricity": [
                "Streetlight is completely out on Main St and 4th Ave. The corner is pitch black and feels unsafe.",
                "High voltage power line is hanging dangerously low after the storm yesterday. Needs urgent repair.",
                "Frequent voltage fluctuations are causing home appliances to reset. Whole block is experiencing this.",
                "Traffic light is dead at the crossing near the elementary school, traffic is absolute chaos.",
                "Park lamps in the central plaza are flickering and making a loud buzzing noise."
            ],
            "Water": [
                "Main water line pipe burst under the sidewalk. Clean drinking water is shooting up and flooding the street.",
                "Low water pressure reported in the entire apartment building since this morning. Barely a trickle.",
                "Tap water from the kitchen sink is coming out brown with a metallic smell. Need testing.",
                "Fire hydrant is leaking slowly, water is pool on the road and causing freezing hazards.",
                "Water is leaking from an underground sewer vent, smells strongly of chlorine."
            ],
            "Road Damage": [
                "Huge, deep pothole in the middle lane of the expressway. Several cars have popped their tires today.",
                "The asphalt on Broad St is severely cracked and buckling. It's dangerous for motorcycles.",
                "Speed bump is falling apart, metal rods are starting to expose and scratch undercarriages.",
                "Road collapse/sinkhole forming near the storm drain on 8th street.",
                "Stop sign is bent and hidden behind tree branches, drivers cannot see it."
            ],
            "Garbage": [
                "Massive pile of construction waste illegally dumped in the alleyway behind the pharmacy.",
                "Public trash cans in the plaza are overflowing. Garbage is blowing onto the streets and attracting rats.",
                "Missed garbage pickup for this entire week on our street. The bins are smell awful in the sun.",
                "Someone dumped several old mattresses and a broken refrigerator on the sidewalk.",
                "Industrial trash bins are leaking greasy liquid onto the street, slipping hazard."
            ],
            "Flood": [
                "Storm drain is completely clogged with leaves and plastic bottles. Water is pooling up to the curb.",
                "Heavy rainfall has flooded the underpass. Two cars are stuck in deep water.",
                "Street is flooded after a moderate rain because the drainage system is too small.",
                "Basement stores are getting flooded due to road runoff not being captured by the sewers.",
                "Retention pond is overflowing into the nearby residential yards."
            ],
            "Public Safety": [
                "An old brick wall of the abandoned warehouse looks like it is about to collapse onto the public sidewalk.",
                "Abandoned rusted vehicle has been parked in the fire lane for over three weeks.",
                "Sidewalk is completely blocked by illegal scaffolding and construction material without a permit.",
                "Broken glass and sharp metal parts are scattered all over the children's playground slide.",
                "Tree branch is cracked and hanging precariously over the busy walkway, ready to fall."
            ]
        }

        urgencies = ["Low", "Medium", "High"]
        statuses = ["Pending", "In Progress", "Completed", "Rejected"]
        departments = {
            "Electricity": "Bureau of Power & Lighting",
            "Water": "Water Resource Authority",
            "Road Damage": "Department of Public Works",
            "Garbage": "Sanitation & Waste Management",
            "Flood": "Stormwater & Drainage Agency",
            "Public Safety": "Department of Inspections & Public Safety"
        }

        start_date = datetime.now() - timedelta(days=90)
        
        # We will create about 65 complaints with timestamps spread over 90 days
        for i in range(65):
            # Choose category
            cat = random.choice(db_categories)
            desc_template = random.choice(descriptions[cat.name])
            
            # Personalize description a bit so it's not identical
            street_names = ["Broadway", "5th Ave", "Lexington St", "Oak Road", "Pine Ave", "Grand St", "Maple Blvd", "River Rd"]
            street = random.choice(street_names)
            desc = desc_template.replace("Main St", street).replace("Broad St", street)
            
            # Choose district
            dist = random.choice(db_districts)
            
            # Coordinate slightly jittered around district center
            lat = dist.latitude + random.uniform(-0.015, 0.015)
            lng = dist.longitude + random.uniform(-0.015, 0.015)
            
            # Created date: spread over the last 90 days
            created_days_ago = random.randint(0, 90)
            created_at = start_date + timedelta(days=created_days_ago, hours=random.randint(0, 23), minutes=random.randint(0, 59))
            
            # Determine status and related fields based on age
            if created_days_ago < 5:
                # Very recent complaints are mostly Pending or In Progress
                status = random.choice(["Pending", "In Progress"])
            elif created_days_ago < 15:
                status = random.choice(["In Progress", "Completed"])
            else:
                # Older complaints are mostly Completed or Rejected
                status = random.choice(["Completed", "Completed", "Completed", "Rejected"])
                
            urgency = random.choice(urgencies)
            # High severity items get High urgency
            if "dangerous" in desc.lower() or "voltage" in desc.lower() or "burst" in desc.lower() or "flood" in desc.lower():
                urgency = "High"
                
            # Assign officer if not pending
            assigned_to = None
            if status != "Pending":
                assigned_to = random.choice(officers)
                
            # Estimated completion days
            est_days = float(random.randint(1, 10))
            if urgency == "High":
                est_days = float(random.randint(1, 3))
                
            # Risk Level
            risk = "Low"
            if urgency == "High":
                risk = "High" if random.random() > 0.3 else "Critical"
            elif urgency == "Medium":
                risk = "Medium"
                
            # Random creator (admin or viewer)
            creator = random.choice([admin_user, viewer_user])
            
            complaint = Complaint(
                title=f"{cat.name} Incident at {street}",
                description=desc,
                district_id=dist.id,
                category_id=cat.id,
                status=status,
                urgency=urgency,
                risk_level=risk,
                recommended_department=departments[cat.name],
                estimated_completion_days=est_days,
                latitude=lat,
                longitude=lng,
                created_by_id=creator.id,
                assigned_to_id=assigned_to.id if assigned_to else None,
                created_at=created_at,
                updated_at=created_at + timedelta(days=random.randint(0, min(5, max(1, 90-created_days_ago)))) if status != "Pending" else created_at
            )
            
            db.add(complaint)
            db.flush()  # to get complaint.id
            
            # Add AIPrediction record
            keywords_list = ["leak", "broken", "danger", "dark", "street", "pipe", "flooding", "trash", "illegal"]
            matched_kws = [kw for kw in keywords_list if kw in desc.lower()]
            if not matched_kws:
                matched_kws = ["incident", street.lower()]
                
            prediction = AIPrediction(
                complaint_id=complaint.id,
                predicted_category=cat.name,
                predicted_urgency=urgency,
                confidence_score=round(random.uniform(0.78, 0.99), 2),
                risk_level=risk,
                completion_days=est_days,
                keywords=",".join(matched_kws),
                created_at=created_at
            )
            db.add(prediction)
            
            # Add some analytics logs for actions
            if status != "Pending":
                log_date = created_at + timedelta(hours=random.randint(1, 24))
                log1 = AnalyticsLog(
                    event_type="Complaint Assigned",
                    description=f"Complaint #{complaint.id} was automatically analyzed by AI and assigned to Officer {assigned_to.username}.",
                    user_id=admin_user.id,
                    timestamp=log_date
                )
                db.add(log1)
                
                if status == "Completed":
                    log2 = AnalyticsLog(
                        event_type="Complaint Resolved",
                        description=f"Complaint #{complaint.id} was marked as Completed by Officer {assigned_to.username}.",
                        user_id=assigned_to.id,
                        timestamp=complaint.updated_at
                    )
                    db.add(log2)

        # 5. Add general audit logs
        db.add(AnalyticsLog(event_type="System Initialized", description="Smart Complaint Analytics Platform was initialized with default configurations.", user_id=admin_user.id))
        db.add(AnalyticsLog(event_type="AI Models Loaded", description="NLP text classification models and Random Forest predictors loaded successfully.", user_id=admin_user.id))
        
        db.commit()
        print("Database seeded successfully with 65 complaints!")
        
    except Exception as e:
        db.rollback()
        print(f"Error seeding database: {e}")
        raise e
    finally:
        db.close()
