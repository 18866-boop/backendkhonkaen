import pandas as pd
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA
from sqlalchemy.orm import Session
from ..models import Complaint, ComplaintCategory
from collections import Counter
import re

def clean_and_tokenize(text):
    text_lower = text.lower()
    # Remove non-alphabetical characters
    words = re.findall(r'\b[a-z]{4,15}\b', text_lower)
    
    stop_words = {
        "the", "a", "an", "and", "or", "but", "is", "are", "was", "were", "of", "to", "in", "on", "at", 
        "for", "with", "this", "that", "it", "from", "by", "about", "as", "into", "like", "through", 
        "after", "over", "between", "out", "against", "during", "without", "before", "under", "around", 
        "re", "street", "avenue", "road", "block", "near", "house", "building", "please", "there", 
        "been", "have", "has", "had", "will", "would", "should", "could", "report", "reported", "issue", 
        "problem", "complaint", "incident", "needs", "needed", "repair", "broken", "since", "today", 
        "yesterday", "every", "some", "someone", "people"
    }
    
    return [w for w in words if w not in stop_words]

def get_topic_modeling_data(db: Session):
    complaints = db.query(Complaint).all()
    categories = db.query(ComplaintCategory).all()
    category_map = {c.id: c.name for c in categories}
    
    if not complaints:
        return {
            "word_cloud": [],
            "clusters": [],
            "top_keywords": [],
            "trending_topics": []
        }
        
    # 1. Generate Word Cloud Data
    all_tokens = []
    for c in complaints:
        all_tokens.extend(clean_and_tokenize(c.description))
        
    token_counts = Counter(all_tokens)
    # Get top 50 keywords
    word_cloud = [{"text": word, "value": count} for word, count in token_counts.most_common(50)]
    
    # Top keywords list
    top_keywords = [item["text"] for item in word_cloud[:10]]
    
    # 2. Generate Topic Clustering using KMeans and PCA
    clusters_data = []
    descriptions = [c.description for c in complaints]
    
    if len(descriptions) >= 6:
        try:
            # TF-IDF Vectorization
            vectorizer = TfidfVectorizer(stop_words='english', min_df=1)
            tfidf_matrix = vectorizer.fit_transform(descriptions)
            
            # KMeans Clustering
            num_clusters = min(6, len(descriptions))
            kmeans = KMeans(n_clusters=num_clusters, random_state=42, n_init=10)
            cluster_labels = kmeans.fit_predict(tfidf_matrix)
            
            # PCA projection to 2D
            pca = PCA(n_components=2, random_state=42)
            coords2d = pca.fit_transform(tfidf_matrix.toarray())
            
            # Get cluster representative names
            cluster_names = {}
            for i in range(num_clusters):
                # Find indices in this cluster
                indices = np.where(cluster_labels == i)[0]
                # Aggregate words for this cluster
                cluster_words = []
                for idx in indices:
                    cluster_words.extend(clean_and_tokenize(descriptions[idx]))
                cluster_counts = Counter(cluster_words)
                top_word = cluster_counts.most_common(1)
                cluster_names[i] = f"Topic: {top_word[0][0].capitalize()}" if top_word else f"Cluster {i+1}"

            # Build plot points
            for i, c in enumerate(complaints):
                # Scale coordinates slightly for nicer scatter chart bounding boxes
                x_val = float(coords2d[i, 0]) * 10
                y_val = float(coords2d[i, 1]) * 10
                clusters_data.append({
                    "x": round(x_val, 2),
                    "y": round(y_val, 2),
                    "label": cluster_names[cluster_labels[i]],
                    "category": category_map.get(c.category_id, "Unknown"),
                    "complaint_id": c.id,
                    "title": c.title
                })
        except Exception as e:
            print(f"Error during Topic Clustering PCA: {e}")
            # Fallback to simple random coordinates but correct labels
            for i, c in enumerate(complaints):
                clusters_data.append({
                    "x": round(np.random.uniform(-5, 5), 2),
                    "y": round(np.random.uniform(-5, 5), 2),
                    "label": f"Cluster {c.category_id}",
                    "category": category_map.get(c.category_id, "Unknown"),
                    "complaint_id": c.id,
                    "title": c.title
                })
    else:
        # Simple fallback for too few data points
        for i, c in enumerate(complaints):
            clusters_data.append({
                "x": float(i),
                "y": float(i),
                "label": f"Cluster {c.category_id}",
                "category": category_map.get(c.category_id, "Unknown"),
                "complaint_id": c.id,
                "title": c.title
            })

    # 3. Monthly Trends & Trending Topics
    # Group complaints by month and category to see which issues are trending
    df_items = []
    for c in complaints:
        month_str = c.created_at.strftime("%b %Y") # e.g. "Apr 2026"
        month_sort_key = c.created_at.strftime("%Y-%m") # e.g. "2026-04"
        df_items.append({
            "month": month_str,
            "sort_key": month_sort_key,
            "category": category_map.get(c.category_id, "Unknown")
        })
    
    df = pd.DataFrame(df_items)
    trending_topics = []
    
    if not df.empty:
        # Group by month and category
        grouped = df.groupby(["sort_key", "month", "category"]).size().reset_index(name="count")
        grouped = grouped.sort_values("sort_key")
        
        # Format for trending topics chart
        for name, group in grouped.groupby("category"):
            history = []
            for _, row in group.iterrows():
                history.append({
                    "month": row["month"],
                    "count": int(row["count"])
                })
            # Add to list
            trending_topics.append({
                "category": name,
                "history": history,
                "total": int(group["count"].sum())
            })
            
    # Sort categories by total volume
    trending_topics = sorted(trending_topics, key=lambda x: x["total"], reverse=True)

    return {
        "word_cloud": word_cloud,
        "clusters": clusters_data,
        "top_keywords": top_keywords,
        "trending_topics": trending_topics
    }
