from flask import send_file
from reportlab.platypus import SimpleDocTemplate, Paragraph
from reportlab.lib.styles import getSampleStyleSheet
from flask import Flask, render_template, jsonify, request, flash
import pandas as pd
import os

app = Flask(__name__)

app.secret_key = "community_health_secret_key"

# ==========================================
# HOME PAGE
# ==========================================

import pandas as pd

@app.route("/messages")
def messages():
    data = pd.read_csv("data/contact_messages.csv")
    return render_template("messages.html", messages=data.to_dict(orient="records"))
@app.route("/admin")
def admin():

    data = pd.read_csv("data/contact_messages.csv")

    messages = data.to_dict(orient="records")

    return render_template(
        "admin.html",
        messages=messages
    )
@app.route("/")
def home():
    return render_template("index.html")

@app.route("/about")
def about():
    return render_template("about.html")

@app.route("/contact", methods=["GET", "POST"])
def contact():

    if request.method == "POST":

        name = request.form.get("name")
        email = request.form.get("email")
        subject = request.form.get("subject")
        message = request.form.get("message")

        file_path = "data/contact_messages.csv"

        if not os.path.exists(file_path):
            df = pd.DataFrame(columns=[
                "Name",
                "Email",
                "Subject",
                "Message"
            ])
            df.to_csv(file_path, index=False)

        new_message = pd.DataFrame([{
            "Name": name,
            "Email": email,
            "Subject": subject,
            "Message": message
        }])

        new_message.to_csv(
            file_path,
            mode="a",
            header=False,
            index=False
        )

        return render_template(
            "contact.html",
            success="✅ Your message has been sent successfully!"
        )

    return render_template("contact.html")

# ==========================================
# CALCULATE COMMUNITY RISK SCORE
# ==========================================

def calculate_risk_score(
    total_cases,
    recovered_cases,
    mental_health,
    risk_level
):

    # Calculate recovery rate
    if total_cases > 0:
        recovery_rate = (
            recovered_cases / total_cases
        ) * 100
    else:
        recovery_rate = 0

    # Start risk score
    score = 0

    # Mental health impact
    if mental_health >= 70:
        score += 40
    elif mental_health >= 50:
        score += 30
    elif mental_health >= 30:
        score += 20
    else:
        score += 10

    # Existing risk level
    if risk_level.lower() == "high":
        score += 40
    elif risk_level.lower() == "medium":
        score += 25
    else:
        score += 10

    # Recovery rate
    if recovery_rate < 70:
        score += 20
    elif recovery_rate < 85:
        score += 15
    elif recovery_rate < 95:
        score += 5

    # Maximum score = 100
    score = min(score, 100)

    # Final risk
    if score >= 61:
        calculated_risk = "High Risk"
    elif score >= 31:
        calculated_risk = "Medium Risk"
    else:
        calculated_risk = "Low Risk"

    return (
        round(score),
        calculated_risk,
        round(recovery_rate, 2)
    )


# ==========================================
# DASHBOARD PAGE
# ==========================================

@app.route("/dashboard")
def dashboard():

    # Read CSV
    data = pd.read_csv("data/community_health_dataset.csv")

    # Clean column names
    data.columns = data.columns.str.strip()

    # Clean community names
    data["community"] = (
        data["community"]
        .astype(str)
        .str.strip()
    )

    # Clean risk levels
    data["risk_level"] = (
        data["risk_level"]
        .astype(str)
        .str.strip()
    )

    # Overall statistics
    total_cases = int(
        data["total_cases"].sum()
    )

    recovered_cases = int(
        data["recovered_cases"].sum()
    )

    average_mental_health = round(
        data["mental_health_impact"].mean(),
        2
    )

    high_risk_count = len(
        data[
            data["risk_level"]
            .str.lower() == "high"
        ]
    )

    # Community data
    communities = []

    for _, row in data.iterrows():

        total = int(
            row["total_cases"]
        )

        recovered = int(
            row["recovered_cases"]
        )

        mental_health = float(
            row["mental_health_impact"]
        )

        risk_level = str(
            row["risk_level"]
        )

        # Calculate risk
        (
            risk_score,
            calculated_risk,
            recovery_rate
        ) = calculate_risk_score(
            total,
            recovered,
            mental_health,
            risk_level
        )

        # Warning and recommendation
        if calculated_risk == "High Risk":

            warning = (
                f"⚠️ {row['community']} has a HIGH "
                f"community health risk score of "
                f"{risk_score}/100. Priority monitoring "
                f"and early intervention are recommended."
            )

            recommendation = (
                "Priority health monitoring is recommended. "
                "Focus on mental health support, regular "
                "health screening, disease surveillance, "
                "and preparedness for possible future outbreaks."
            )

        elif calculated_risk == "Medium Risk":

            warning = (
                f"⚠️ {row['community']} has a MEDIUM "
                f"community health risk score of "
                f"{risk_score}/100. Regular monitoring "
                f"and preventive health measures are recommended."
            )

            recommendation = (
                "Regular health monitoring is recommended. "
                "Focus on preventive health measures, mental "
                "health awareness, and community-level disease monitoring."
            )

        else:

            warning = (
                f"✅ {row['community']} has a LOW "
                f"community health risk score of "
                f"{risk_score}/100. Continue routine health monitoring."
            )

            recommendation = (
                "Continue routine health monitoring and "
                "preventive health measures. Maintain "
                "community awareness and preparedness."
            )

        # Add community information
        communities.append({

            "community": row["community"],

            "total_cases": total,

            "recovered_cases": recovered,

            "mental_health_impact": mental_health,

            "risk_level": risk_level,

            "recovery_rate": recovery_rate,

            "risk_score": risk_score,

            "calculated_risk": calculated_risk,

            "warning": warning,

            "recommendation": recommendation

        })

    # Send data to dashboard
    return render_template(

        "dashboard.html",

        total_cases=total_cases,

        recovered_cases=recovered_cases,

        average_mental_health=average_mental_health,

        high_risk_count=high_risk_count,

        communities=communities

    )


# ==========================================
# COMMUNITY DETAILS API
# ==========================================

@app.route(
    "/api/community/<community_name>"
)
def community_details(community_name):

    data =pd.read_csv("data/community_health_dataset.csv")

    # Clean columns
    data.columns = (
        data.columns
        .str.strip()
    )

    # Clean community
    data["community"] = (
        data["community"]
        .astype(str)
        .str.strip()
    )

    # Find selected community
    selected = data[
        data["community"]
        .str.lower()
        ==
        community_name
        .strip()
        .lower()
    ]

    # Not found
    if selected.empty:

        return jsonify({

            "error":
                "Community not found"

        }), 404

    # Get community
    community = selected.iloc[0]

    # Get values
    total_cases = int(
        community["total_cases"]
    )

    recovered_cases = int(
        community["recovered_cases"]
    )

    mental_health = float(
        community["mental_health_impact"]
    )

    risk_level = str(
        community["risk_level"]
    ).strip()

    # Calculate risk
    (
        risk_score,
        calculated_risk,
        recovery_rate
    ) = calculate_risk_score(

        total_cases,

        recovered_cases,

        mental_health,

        risk_level

    )

    # Warning
    if calculated_risk == "High Risk":

        warning = (
            f"⚠️ {community_name} has a HIGH "
            f"community health risk score of "
            f"{risk_score}/100. Priority monitoring "
            f"is recommended."
        )

        recommendation = (
            "Priority health monitoring is recommended. "
            "Focus on mental health support, health screening, "
            "disease surveillance, and preparedness."
        )

    elif calculated_risk == "Medium Risk":

        warning = (
            f"⚠️ {community_name} has a MEDIUM "
            f"community health risk score of "
            f"{risk_score}/100. Regular monitoring "
            f"is recommended."
        )

        recommendation = (
            "Regular health monitoring and preventive "
            "health measures are recommended."
        )

    else:

        warning = (
            f"✅ {community_name} has a LOW "
            f"community health risk score of "
            f"{risk_score}/100."
        )

        recommendation = (
            "Continue routine health monitoring and "
            "preventive health measures."
        )

    # Return JSON
    return jsonify({

        "community": community_name,

        "totalCases": total_cases,

        "recoveredCases": recovered_cases,

        "mentalHealth": mental_health,

        "riskLevel": risk_level,

        "recoveryRate": recovery_rate,

        "riskScore": risk_score,

        "calculatedRisk": calculated_risk,

        "warning": warning,

        "recommendation": recommendation

    })


# ==========================================
# PREDICTION PAGE
# ==========================================

# ==========================================
# EARLY WARNING PREDICTION PAGE
# ==========================================

@app.route(
    "/prediction",
    methods=["GET", "POST"]
)
def prediction():

    # ======================================
    # OPEN PREDICTION PAGE
    # ======================================

    if request.method == "GET":

        return render_template(
            "prediction.html"
        )


    # ======================================
    # GET FORM VALUES
    # ======================================

    total_cases = int(
        request.form["total_cases"]
    )

    recovered_cases = int(
        request.form["recovered_cases"]
    )

    mental_health = float(
        request.form["mental_health"]
    )

    risk_level = request.form[
        "risk_level"
    ]


    # ======================================
    # CALCULATE RECOVERY RATE
    # ======================================

    if total_cases > 0:

        recovery_rate = round(
            (
                recovered_cases
                /
                total_cases
            ) * 100,
            2
        )

    else:

        recovery_rate = 0


    # ======================================
    # START RISK SCORE
    # ======================================

    risk_score = 0


    # ======================================
    # COVID CASES FACTOR
    # ======================================

    if total_cases >= 1500:

        risk_score += 30

    elif total_cases >= 1000:

        risk_score += 25

    elif total_cases >= 500:

        risk_score += 15

    else:

        risk_score += 5


    # ======================================
    # MENTAL HEALTH FACTOR
    # ======================================

    if mental_health >= 70:

        risk_score += 30

    elif mental_health >= 50:

        risk_score += 25

    elif mental_health >= 30:

        risk_score += 15

    else:

        risk_score += 5


    # ======================================
    # EXISTING RISK LEVEL FACTOR
    # ======================================

    if risk_level.lower() == "high":

        risk_score += 40

    elif risk_level.lower() == "medium":

        risk_score += 25

    else:

        risk_score += 10


    # ======================================
    # MAXIMUM SCORE = 100
    # ======================================

    risk_score = min(
        risk_score,
        100
    )


    # ======================================
    # DETERMINE FINAL PREDICTION
    # ======================================

    if risk_score >= 70:

        prediction_result = "High Risk"

        recommendation = (

            "Priority health monitoring is "
            "recommended. The community should "
            "focus on mental health support, "
            "regular health screening, disease "
            "surveillance, and preparedness for "
            "possible future outbreaks."

        )


    elif risk_score >= 40:

        prediction_result = "Medium Risk"

        recommendation = (

            "Regular health monitoring is "
            "recommended. The community should "
            "improve preventive health measures, "
            "mental health awareness, and "
            "community-level disease monitoring."

        )


    else:

        prediction_result = "Low Risk"

        recommendation = (

            "The community currently has a "
            "relatively low risk level. Continue "
            "regular health monitoring and "
            "preventive health practices."

        )


    # ======================================
    # DISPLAY RESULT
    # ======================================

    return render_template(

        "prediction.html",

        prediction=prediction_result,

        recovery_rate=recovery_rate,

        risk_score=risk_score,

        recommendation=recommendation

    )

    # ======================================
    # OPEN PREDICTION PAGE
    # ======================================

    if request.method == "GET":

        return render_template(
            "prediction.html"
        )


    # ======================================
    # GET FORM VALUES
    # ======================================

    try:

        total_cases = int(
            request.form["total_cases"]
        )

        recovered_cases = int(
            request.form["recovered_cases"]
        )

        mental_health = float(
            request.form["mental_health"]
        )

    except (ValueError, KeyError):

        return render_template(
            "prediction.html",
            error="Please enter valid values."
        )


    # ======================================
    # VALIDATE VALUES
    # ======================================

    if recovered_cases > total_cases:

        return render_template(

            "prediction.html",

            error="Recovered cases cannot be greater than total cases."

        )


    # ======================================
    # CALCULATE RECOVERY RATE
    # ======================================

    if total_cases > 0:

        recovery_rate = round(

            (
                recovered_cases
                /
                total_cases
            ) * 100,

            2

        )

    else:

        recovery_rate = 0


    # ======================================
    # START RISK SCORE
    # ======================================

    risk_score = 0


    # ======================================
    # COVID CASES FACTOR
    # ======================================

    if total_cases >= 1500:

        risk_score += 30

    elif total_cases >= 1000:

        risk_score += 25

    elif total_cases >= 500:

        risk_score += 15

    else:

        risk_score += 5


    # ======================================
    # MENTAL HEALTH FACTOR
    # ======================================

    if mental_health >= 70:

        risk_score += 30

    elif mental_health >= 50:

        risk_score += 25

    elif mental_health >= 30:

        risk_score += 15

    else:

        risk_score += 5


    # ======================================
    # RECOVERY RATE FACTOR
    # Lower recovery = Higher risk
    # ======================================

    if recovery_rate < 70:

        risk_score += 30

    elif recovery_rate < 85:

        risk_score += 20

    elif recovery_rate < 95:

        risk_score += 10

    else:

        risk_score += 0


    # ======================================
    # MAXIMUM SCORE = 100
    # ======================================

    risk_score = min(
        risk_score,
        100
    )


    # ======================================
    # DETERMINE FINAL RISK
    # ======================================

    if risk_score >= 70:

        prediction_result = "High Risk"

        recommendation = (

            "Priority health monitoring is recommended. "
            "The community should focus on mental health "
            "support, regular health screening, disease "
            "surveillance, and preparedness for possible "
            "future outbreaks."

        )


    elif risk_score >= 40:

        prediction_result = "Medium Risk"

        recommendation = (

            "Regular health monitoring is recommended. "
            "The community should improve preventive health "
            "measures, mental health awareness, and "
            "community-level disease monitoring."

        )


    else:

        prediction_result = "Low Risk"

        recommendation = (

            "The community currently has a relatively low "
            "risk level. Continue regular health monitoring "
            "and preventive health practices."

        )


    # ======================================
    # SEND RESULT TO prediction.html
    # ======================================

    return render_template(

        "prediction.html",

        prediction=prediction_result,

        recovery_rate=recovery_rate,

        risk_score=risk_score,

        recommendation=recommendation

    )

# ==========================================
# RUN APPLICATION
# ==========================================
from flask import send_file

@app.route("/download_csv")
def download_csv():
    return send_file(
        "data/community_health_dataset.csv",
        as_attachment=True
    )

@app.route("/download_pdf")
def download_pdf():

    data = pd.read_csv("data/community_health_dataset.csv")

    pdf = SimpleDocTemplate("Community_Health_Report.pdf")

    styles = getSampleStyleSheet()

    story = []

    story.append(
        Paragraph(
            "<b>Community Health Analysis Report</b>",
            styles["Title"]
        )
    )

    story.append(
        Paragraph(
            "<br/>Total Communities: {}".format(len(data)),
            styles["Normal"]
        )
    )

    story.append(
        Paragraph(
            "Total COVID Cases: {}".format(data["total_cases"].sum()),
            styles["Normal"]
        )
    )

    story.append(
        Paragraph(
            "Recovered Cases: {}".format(data["recovered_cases"].sum()),
            styles["Normal"]
        )
    )

    story.append(
        Paragraph(
            "Average Mental Health Impact: {:.2f}".format(
                data["mental_health_impact"].mean()
            ),
            styles["Normal"]
        )
    )

    pdf.build(story)

    return send_file(
        "Community_Health_Report.pdf",
        as_attachment=True
    )

if __name__ == "__main__":

    app.run(
        debug=True
    )