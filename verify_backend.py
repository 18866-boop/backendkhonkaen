import sys
import os

# Add parent directory to path so we can run directly
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    print("1. Testing config and database connection...")
    from app.config import settings
    print(f"   Project Name: {settings.PROJECT_NAME}")
    print(f"   Database URL: {settings.DATABASE_URL}")

    from app.database import init_db, SessionLocal
    from app.models import User, Complaint, District, ComplaintCategory
    
    print("2. Initializing and Seeding Database...")
    init_db()
    
    db = SessionLocal()
    users_cnt = db.query(User).count()
    complaints_cnt = db.query(Complaint).count()
    districts_cnt = db.query(District).count()
    categories_cnt = db.query(ComplaintCategory).count()
    
    print(f"   Database Loaded successfully:")
    print(f"   - Users: {users_cnt}")
    print(f"   - Districts: {districts_cnt}")
    print(f"   - Categories: {categories_cnt}")
    print(f"   - Complaints: {complaints_cnt}")
    
    print("3. Checking AI Classifier prediction...")
    from app.ai.classifier import classifier
    test_text = "There is a huge pothole in the road near broadway. Several cars damaged their tires."
    res = classifier.predict(test_text)
    print(f"   Input text: '{test_text}'")
    print(f"   AI classified: {res}")
    
    assert res["category"] == "Road Damage", "Category prediction mismatch"
    print("   AI classification validation: PASSED!")
    
    print("4. Checking ML Predictor prediction...")
    from app.ai.predictor import predictor
    pred_res = predictor.predict(category_id=3, district_id=1, urgency="High")
    print(f"   Predictive AI results (Category=3, District=1, Urgency=High):")
    print(f"   - Estimated completion days: {pred_res['estimated_days']}")
    print(f"   - Risk level: {pred_res['risk_level']}")
    print(f"   - Recommended department: {pred_res['recommended_department']}")
    
    db.close()
    print("\nVerification successful! All systems operational.")
    sys.exit(0)

except Exception as e:
    print(f"\nVerification failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
