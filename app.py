from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
import numpy as np
import base64
import cv2
import io
from PIL import Image
import os
import random
from datetime import datetime

app = Flask(__name__)
CORS(app)

# Serve the main page
@app.route('/')
def index():
    return render_template('index.html')

# Map facial indicators to numerical scores
def map_facial_indicator_to_score(indicator):
    if indicator in ["Good", "Healthy", "Normal"]:
        return 3
    elif indicator in ["Fair", "Moderate", "Tired"]:
        return 2
    else:
        return 1

# Calculate a comprehensive health score combining both analyses
def calculate_comprehensive_health_score(nutrition_data, facial_data):
    # Base nutrition score (0-100, higher is better)
    nutrition_score = (
        nutrition_data['protein'] * 0.2 +
        nutrition_data['carbs'] * 0.15 +
        nutrition_data['fats'] * 0.15 +
        nutrition_data['vitamins'] * 0.25 +
        nutrition_data['minerals'] * 0.25
    )
    
    # Adjust based on facial analysis if available
    if facial_data and facial_data.get('success') and facial_data.get('face_count', 0) > 0:
        facial_score = facial_data.get('assessment_score', 50)
        indicators = facial_data.get('nutritional_indicators', {})
        
        # Calculate facial indicator score
        facial_indicator_score = 0
        indicator_count = 0
        
        for indicator, value in indicators.items():
            score = map_facial_indicator_to_score(value)
            facial_indicator_score += score
            indicator_count += 1
        
        if indicator_count > 0:
            facial_indicator_score = (facial_indicator_score / indicator_count) * 33.33
            
        # Combine scores (60% nutrition, 40% facial analysis)
        comprehensive_score = (nutrition_score * 0.6) + (facial_score * 0.3) + (facial_indicator_score * 0.1)
    else:
        comprehensive_score = nutrition_score * 0.9  # Reduce weight if no facial analysis
    
    return min(100, comprehensive_score)

# Enhanced nutrition analysis function that includes facial analysis
def analyze_nutrition(data, facial_data=None):
    age = int(data['age'])
    gender = data['gender']
    height = int(data['height'])
    weight = int(data['weight'])
    fruits = int(data['fruits'])
    vegetables = int(data['vegetables'])
    proteins = int(data['proteins'])
    fatigue = int(data['fatigue'])
    skin = int(data['skin'])
    sickness = int(data['sickness'])
    
    # Calculate BMI
    height_in_meters = height / 100
    bmi = weight / (height_in_meters * height_in_meters)
    
    # Calculate base nutrient scores
    protein_score = min(100, proteins * 30 + (10 if proteins == 3 else 0) + (5 if age > 15 else 0))
    carbs_score = min(100, 70 + (fruits + vegetables) * 7 + (fruits == 3 and vegetables == 3) * 10)
    fats_score = min(100, 60 + (proteins * 12) - (10 if fatigue == 3 else 0))
    vitamins_score = min(100, (fruits + vegetables) * 28 - (sickness * 8) - (skin * 5))
    minerals_score = min(100, (fruits + vegetables) * 22 + (proteins * 8) - (fatigue * 7) - (sickness * 5))
    
    # Calculate base risk score
    risk_score = (100 - protein_score) * 0.25 + \
                (100 - vitamins_score) * 0.3 + \
                (100 - minerals_score) * 0.25 + \
                (fatigue * 8) + (skin * 7) + (sickness * 5)
    
    # Adjust scores based on facial analysis if available
    facial_adjustment = 0
    facial_feedback = []
    facial_impact = {}
    
    if facial_data and facial_data.get('success') and facial_data.get('face_count', 0) > 0:
        indicators = facial_data.get('nutritional_indicators', {})
        
        # Adjust scores based on facial indicators
        skin_score = map_facial_indicator_to_score(indicators.get('skin_health', 'Normal'))
        eye_score = map_facial_indicator_to_score(indicators.get('eye_vitality', 'Normal'))
        lip_score = map_facial_indicator_to_score(indicators.get('lip_condition', 'Normal'))
        
        # Apply adjustments with detailed tracking
        if skin_score < 2:
            vit_adjust = -15
            vitamins_score = max(0, vitamins_score + vit_adjust)
            facial_feedback.append("Facial skin analysis suggests potential vitamin deficiencies")
            facial_impact['skin_health'] = vit_adjust
        
        if eye_score < 2:
            vit_adjust = -10
            min_adjust = -5
            vitamins_score = max(0, vitamins_score + vit_adjust)
            minerals_score = max(0, minerals_score + min_adjust)
            facial_feedback.append("Eye vitality analysis suggests potential nutrient deficiencies")
            facial_impact['eye_vitality'] = {'vitamins': vit_adjust, 'minerals': min_adjust}
        
        if lip_score < 2:
            vit_adjust = -8
            vitamins_score = max(0, vitamins_score + vit_adjust)
            facial_feedback.append("Lip condition analysis suggests potential B-vitamin deficiencies")
            facial_impact['lip_condition'] = vit_adjust
        
        # Calculate facial adjustment to risk score
        facial_adjustment = (3 - skin_score) * 5 + (3 - eye_score) * 4 + (3 - lip_score) * 3
        
        # Add facial assessment score to risk calculation
        facial_risk_adjustment = (100 - facial_data.get('assessment_score', 50)) * 0.2
        risk_score += facial_risk_adjustment + facial_adjustment
    
    risk_score = min(100, risk_score)
    
    # Determine risk level based on comprehensive assessment
    comprehensive_score = calculate_comprehensive_health_score({
        'protein': protein_score,
        'carbs': carbs_score,
        'fats': fats_score,
        'vitamins': vitamins_score,
        'minerals': minerals_score
    }, facial_data)
    
    if comprehensive_score >= 70:
        risk_level = 'Low Risk'
        overall_assessment = 'Good nutritional status'
    elif comprehensive_score >= 50:
        risk_level = 'Medium Risk'
        overall_assessment = 'Moderate nutritional concerns'
    else:
        risk_level = 'High Risk'
        overall_assessment = 'Significant nutritional deficiencies detected'
    
    # Generate timestamp for report
    analysis_timestamp = datetime.now().isoformat()
    
    return {
        'protein': protein_score,
        'carbs': carbs_score,
        'fats': fats_score,
        'vitamins': vitamins_score,
        'minerals': minerals_score,
        'risk_score': risk_score,
        'comprehensive_score': comprehensive_score,
        'risk_level': risk_level,
        'overall_assessment': overall_assessment,
        'bmi': round(bmi, 1),
        'facial_feedback': facial_feedback,
        'facial_adjustment': facial_adjustment,
        'facial_impact': facial_impact,
        'analysis_timestamp': analysis_timestamp
    }

# Enhanced face analysis function with nutritional assessment
def analyze_face(image_data):
    try:
        # Decode base64 image
        if ',' in image_data:
            image_data = base64.b64decode(image_data.split(',')[1])
        else:
            image_data = base64.b64decode(image_data)
            
        image = Image.open(io.BytesIO(image_data))
        image = np.array(image)
        
        # Convert to BGR if needed
        if len(image.shape) == 3:
            if image.shape[2] == 4:  # RGBA
                image = cv2.cvtColor(image, cv2.COLOR_RGBA2BGR)
            else:  # RGB
                image = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)
        else:  # Grayscale
            image = cv2.cvtColor(image, cv2.COLOR_GRAY2BGR)
        
        # Load classifiers
        face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
        eye_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_eye.xml')
        
        # Detect faces
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        faces = face_cascade.detectMultiScale(gray, 1.1, 4)
        
        # Initialize analysis results
        face_count = len(faces)
        skin_health = "Good"
        eye_vitality = "Normal"
        lip_condition = "Healthy"
        face_symmetry = "Good"
        complexion = "Normal"
        facial_structure = "Normal"
        
        # Analyze each face for nutritional indicators
        for (x, y, w, h) in faces:
            # Draw rectangle around face
            cv2.rectangle(image, (x, y), (x+w, y+h), (255, 0, 0), 2)
            
            # Region of Interest for face analysis
            roi_gray = gray[y:y+h, x:x+w]
            roi_color = image[y:y+h, x:x+w]
            
            # Detect eyes
            eyes = eye_cascade.detectMultiScale(roi_gray)
            
            # Simple analysis based on face properties (simulated)
            # In a real application, this would use more advanced computer vision techniques
            
            # Simulate analysis based on face size and properties
            face_area = w * h
            if face_area < 15000:  # Small face area
                skin_health = "Fair"
                eye_vitality = "Tired"
                facial_structure = "Thin"
            elif face_area > 30000:  # Large face area
                lip_condition = "Dry"
                facial_structure = "Full"
            
            # Check for eye bags (simulated)
            if len(eyes) > 0:
                for (ex, ey, ew, eh) in eyes:
                    if eh > 20:  # Larger eyes might indicate fatigue
                        eye_vitality = "Tired"
            
            # Add more "analysis" markers to the image
            font = cv2.FONT_HERSHEY_SIMPLEX
            cv2.putText(image, "Analysis: Nutritional Screening", (10, 30), font, 0.7, (0, 0, 255), 2)
            
            # Add eye markers if eyes detected
            for (ex, ey, ew, eh) in eyes:
                cv2.rectangle(roi_color, (ex, ey), (ex+ew, ey+eh), (0, 255, 0), 2)
                cv2.putText(image, "Eye", (x+ex, y+ey-10), font, 0.5, (0, 255, 0), 1)
        
        # Simulate nutritional deficiency detection based on random factors
        # In a real application, this would use actual facial analysis algorithms
        nutritional_indicators = {
            "skin_health": skin_health,
            "eye_vitality": eye_vitality,
            "lip_condition": lip_condition,
            "face_symmetry": face_symmetry,
            "complexion": complexion,
            "facial_structure": facial_structure
        }
        
        # Generate a nutritional assessment score based on the "analysis"
        if face_count > 0:
            # Calculate score based on facial indicators
            base_score = 70
            adjustments = 0
            
            if skin_health != "Good":
                adjustments -= 10
            if eye_vitality != "Normal":
                adjustments -= 8
            if lip_condition != "Healthy":
                adjustments -= 7
            if facial_structure != "Normal":
                adjustments -= 5
                
            assessment_score = max(0, min(100, base_score + adjustments))
            
            if assessment_score >= 70:
                nutritional_assessment = "Good nutritional indicators"
            elif assessment_score >= 50:
                nutritional_assessment = "Moderate nutritional indicators"
            else:
                nutritional_assessment = "Possible nutritional deficiencies"
        else:
            assessment_score = 0
            nutritional_assessment = "No face detected for analysis"
        
        # Convert back to base64
        _, buffer = cv2.imencode('.jpg', image)
        image_base64 = base64.b64encode(buffer).decode('utf-8')
        
        return {
            'success': True,
            'face_count': face_count,
            'processed_image': f'data:image/jpeg;base64,{image_base64}',
            'nutritional_indicators': nutritional_indicators,
            'assessment_score': assessment_score,
            'nutritional_assessment': nutritional_assessment
        }
    except Exception as e:
        return {
            'success': False,
            'error': str(e)
        }

@app.route('/analyze', methods=['POST'])
def analyze():
    try:
        data = request.json
        # Check if facial data is included in the request
        facial_data = data.get('facial_analysis')
        result = analyze_nutrition(data, facial_data)
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@app.route('/detect-face', methods=['POST'])
def face_detection():
    try:
        data = request.json
        image_data = data['image']
        result = analyze_face(image_data)
        return jsonify(result)
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400
    

if __name__ == '__main__':
    app.run(debug=True, port=5000)