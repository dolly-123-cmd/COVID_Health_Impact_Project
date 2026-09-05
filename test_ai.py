from ai_model import (
    predict_health_risk,
    get_model_accuracy
)


risk, confidence = predict_health_risk(
    total_cases=1200,
    recovered_cases=1100,
    mental_health=65
)


print("--------------------------------")
print("AI COMMUNITY HEALTH ANALYSIS")
print("--------------------------------")

print("AI Prediction:", risk)

print("AI Confidence:", confidence, "%")

print("Model Accuracy:", get_model_accuracy(), "%")

print("--------------------------------")