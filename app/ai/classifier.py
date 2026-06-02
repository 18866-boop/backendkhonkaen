import os
import joblib
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline

# Seed training data for category and urgency classification
SEED_TRAINING_DATA = [
    # Electricity
    ("street light is out and it's extremely dark here", "Electricity", "Medium"),
    ("the power line has fallen down onto the street", "Electricity", "High"),
    ("transformers blew up and there is no electricity in our street", "Electricity", "High"),
    ("flickering streetlights are buzzing on broadway", "Electricity", "Low"),
    ("electrical wire is sparked and smoking after the rain", "Electricity", "High"),
    ("power outage affecting the whole residential block", "Electricity", "High"),
    ("the traffic lights are not working at the intersection", "Electricity", "High"),
    ("the park lamp posts are broken and dark", "Electricity", "Low"),
    
    # Water
    ("water pipe has burst and is flooding the entire road", "Water", "High"),
    ("we have zero water pressure in the building since morning", "Water", "Medium"),
    ("brown dirty water coming out from tap with bad odor", "Water", "High"),
    ("fire hydrant is broken and leaking clean water onto the street", "Water", "High"),
    ("sewer water is leaking onto the sidewalk and smells awful", "Water", "High"),
    ("there is a slow leak in the underground utility pipeline", "Water", "Low"),
    ("municipal drinking water pipe is dripping heavily", "Water", "Low"),
    
    # Road Damage
    ("massive pothole on main street has damaged several tires", "Road Damage", "High"),
    ("deep asphalt crack in the center of the avenue is dangerous for bikes", "Road Damage", "Medium"),
    ("road is crumbling and collapsing near the storm drain", "Road Damage", "High"),
    ("the speed bump is completely broken and has exposed metal bolts", "Road Damage", "High"),
    ("pavement has shifted and created a major tripping hazard", "Road Damage", "Medium"),
    ("missing stop sign at the crossroad, causing accidents", "Road Damage", "High"),
    ("road markings are faded, traffic is confused", "Road Damage", "Low"),
    
    # Garbage
    ("some contractor dumped construction waste in our back alleyway", "Garbage", "Low"),
    ("overflowing trash bins in the park are spreading litter everywhere", "Garbage", "Low"),
    ("illegal garbage dumping of plastic bags on the sidewalk", "Garbage", "Medium"),
    ("missed trash pickup for two weeks, bins are smelling horrible", "Garbage", "Medium"),
    ("someone left an old mattress and refrigerator on the curb", "Garbage", "Low"),
    ("toxic waste barrels dumped near the river bank", "Garbage", "High"),
    
    # Flood
    ("storm drain is blocked by leaves and street is completely flooded", "Flood", "High"),
    ("heavy rain flooded the highway underpass, cars are trapped", "Flood", "High"),
    ("water is rising in the streets due to poor drainage during storms", "Flood", "High"),
    ("basement businesses are flooding because of curb runoff", "Flood", "High"),
    ("standing water on the road is causing cars to hydroplane", "Flood", "Medium"),
    ("the retention basin is overflowing into nearby gardens", "Flood", "Medium"),
    
    # Public Safety
    ("unsafe scaffolding at construction site has no safety netting", "Public Safety", "High"),
    ("cracked concrete wall of abandoned building is about to collapse", "Public Safety", "High"),
    ("broken glass and sharp metal exposed on playground equipment", "Public Safety", "High"),
    ("abandoned rusted truck is blocking the fire department access lane", "Public Safety", "High"),
    ("massive tree branch is cracked and hanging over the walkway", "Public Safety", "High"),
    ("construction fence has collapsed into the sidewalk, forcing people to walk on road", "Public Safety", "Medium"),
]

MODEL_PATH_CATEGORY = "classifier_category.joblib"
MODEL_PATH_URGENCY = "classifier_urgency.joblib"

class ComplaintClassifier:
    def __init__(self):
        self.category_pipeline = None
        self.urgency_pipeline = None
        self.load_or_train_models()

    def train_models(self):
        print("Training AI Text Classifier models...")
        texts = [x[0] for x in SEED_TRAINING_DATA]
        categories = [x[1] for x in SEED_TRAINING_DATA]
        urgencies = [x[2] for x in SEED_TRAINING_DATA]

        # 1. Category Classifier (using TF-IDF + Logistic Regression)
        cat_vect = TfidfVectorizer(stop_words='english', min_df=1, ngram_range=(1, 2))
        cat_clf = LogisticRegression(C=1.0, max_iter=200, random_state=42)
        self.category_pipeline = Pipeline([
            ('tfidf', cat_vect),
            ('clf', cat_clf)
        ])
        self.category_pipeline.fit(texts, categories)

        # 2. Urgency Classifier
        urg_vect = TfidfVectorizer(stop_words='english', min_df=1, ngram_range=(1, 2))
        urg_clf = LogisticRegression(C=1.0, max_iter=200, random_state=42)
        self.urgency_pipeline = Pipeline([
            ('tfidf', urg_vect),
            ('clf', urg_clf)
        ])
        self.urgency_pipeline.fit(texts, urgencies)

        # Save models
        joblib.dump(self.category_pipeline, MODEL_PATH_CATEGORY)
        joblib.dump(self.urgency_pipeline, MODEL_PATH_URGENCY)
        print("AI models trained and saved successfully.")

    def load_or_train_models(self):
        try:
            if os.path.exists(MODEL_PATH_CATEGORY) and os.path.exists(MODEL_PATH_URGENCY):
                self.category_pipeline = joblib.load(MODEL_PATH_CATEGORY)
                self.urgency_pipeline = joblib.load(MODEL_PATH_URGENCY)
            else:
                self.train_models()
        except Exception as e:
            print(f"Error loading models: {e}. Retraining...")
            self.train_models()

    def predict(self, text: str):
        if not text or len(text.strip()) < 3:
            return {
                "category": "Public Safety",
                "urgency": "Low",
                "confidence": 0.5,
                "keywords": []
            }
            
        # Pred category and confidence
        cat_probs = self.category_pipeline.predict_proba([text])[0]
        cat_classes = self.category_pipeline.classes_
        max_idx = np.argmax(cat_probs)
        predicted_category = cat_classes[max_idx]
        confidence = float(cat_probs[max_idx])

        # Pred urgency
        predicted_urgency = self.urgency_pipeline.predict([text])[0]
        
        # Boost urgency if explicit dangerous keywords are found
        high_urg_words = ["danger", "collapse", "burst", "fire", "explosion", "spark", "die", "injury", "trapped", "broken glass", "high voltage", "accident"]
        text_lower = text.lower()
        if any(w in text_lower for w in high_urg_words):
            predicted_urgency = "High"

        # Extract keywords
        keywords = self.extract_keywords(text)

        return {
            "category": predicted_category,
            "urgency": predicted_urgency,
            "confidence": round(confidence, 2),
            "keywords": keywords
        }

    def extract_keywords(self, text: str, top_n=5):
        try:
            # We use the tfidf vectorizer from the pipeline to find top words in the input text
            vectorizer = self.category_pipeline.named_steps['tfidf']
            feature_names = np.array(vectorizer.get_feature_names_out())
            
            # Vectorize the single text
            tfidf_matrix = vectorizer.transform([text])
            if tfidf_matrix.nnz == 0:
                # Fallback simple keyword filter
                words = [w.strip(".,!?\"'") for w in text.lower().split()]
                stop_words = {"the", "a", "an", "and", "or", "but", "is", "are", "was", "were", "of", "to", "in", "on", "at", "for", "with", "this", "that", "it"}
                words = [w for w in words if w and w not in stop_words and len(w) > 3]
                return list(set(words))[:top_n]

            # Get tfidf weights for non-zero entries
            row = tfidf_matrix.tocoo()
            sorted_indices = np.argsort(row.data)[::-1]
            top_words = [feature_names[row.col[idx]] for idx in sorted_indices]
            
            # Avoid single character and boring word tokens
            clean_words = []
            for w in top_words:
                if len(w) > 3 and w not in ["street", "avenue", "road", "block", "near", "house", "building"]:
                    clean_words.append(w)
            
            # If we don't have enough, fill in with any top words
            if len(clean_words) < top_n:
                for w in top_words:
                    if w not in clean_words:
                        clean_words.append(w)
            
            return list(dict.fromkeys(clean_words))[:top_n]
        except Exception:
            # Simple fallback split
            words = [w.strip(".,!?\"'") for w in text.lower().split()]
            return [w for w in words if len(w) > 4][:top_n]

# Singleton instance
classifier = ComplaintClassifier()
