from flask import (
    Flask,
    render_template,
    jsonify,
    request,
    redirect,
    url_for,
    session,
    send_file
)

import pandas as pd
import os
import sqlite3

from reportlab.platypus import SimpleDocTemplate, Paragraph
from reportlab.lib.styles import getSampleStyleSheet

# AI MODULE
from ai_model import (
    predict_health_risk,
    get_model_accuracy
)


# =========================================================
# FLASK APP
# =========================================================

app = Flask(__name__)

app.secret_key = "community-health-secret-key"


# =========================================================
# PROJECT PATHS
# =========================================================

BASE_DIR = os.path.dirname(
    os.path.abspath(__file__)
)

DATABASE = os.path.join(
    BASE_DIR,
    "users.db"
)

DATA_DIR = os.path.join(
    BASE_DIR,
    "data"
)

DATASET = os.path.join(
    DATA_DIR,
    "community_health_dataset.csv"
)

CONTACT_FILE = os.path.join(
    DATA_DIR,
    "contact_messages.csv"
)


# =========================================================
# DATABASE SETUP
# =========================================================

def init_db():

    conn = sqlite3.connect(DATABASE)

    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT NOT NULL,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL
        )
    """)

    # Default admin account
    cursor.execute(
        "SELECT * FROM users WHERE username = ?",
        ("admin",)
    )

    existing_user = cursor.fetchone()

    if existing_user is None:

        cursor.execute("""
            INSERT INTO users
            (name, email, username, password)
            VALUES (?, ?, ?, ?)
        """, (
            "Administrator",
            "admin@gmail.com",
            "admin",
            "admin123"
        ))

    conn.commit()
    conn.close()

init_db()


# =========================================================
# LOGIN CHECK
# =========================================================

def login_required():

    return "logged_in" in session


# =========================================================
# HOME / LOGIN PAGE
# =========================================================

@app.route("/")
def home():

    if login_required():

        return redirect(
            url_for("index")
        )

    return render_template(
        "login.html"
    )


# =========================================================
# LOGIN
# =========================================================

@app.route(
    "/login",
    methods=["GET", "POST"]
)
def login():

    if request.method == "POST":

        username = request.form.get(
            "username",
            ""
        ).strip()

        password = request.form.get(
            "password",
            ""
        ).strip()

        conn = sqlite3.connect(
            DATABASE
        )

        cursor = conn.cursor()

        cursor.execute("""
            SELECT id, name, username
            FROM users
            WHERE username = ?
            AND password = ?
        """, (
            username,
            password
        ))

        user = cursor.fetchone()

        conn.close()

        if user:

            session["logged_in"] = True
            session["user_id"] = user[0]
            session["name"] = user[1]
            session["username"] = user[2]

            return redirect(
                url_for("index")
            )

        return render_template(
            "login.html",
            error="Invalid username or password."
        )

    return render_template(
        "login.html"
    )


# =========================================================
# REGISTER
# =========================================================

@app.route(
    "/register",
    methods=["GET", "POST"]
)
def register():

    if request.method == "POST":

        name = request.form.get(
            "name",
            ""
        ).strip()

        email = request.form.get(
            "email",
            ""
        ).strip()

        username = request.form.get(
            "username",
            ""
        ).strip()

        password = request.form.get(
            "password",
            ""
        ).strip()

        confirm_password = request.form.get(
            "confirm_password",
            ""
        ).strip()

        if not name or not email or not username or not password:

            return render_template(
                "register.html",
                error="Please fill in all fields."
            )

        if password != confirm_password:

            return render_template(
                "register.html",
                error="Passwords do not match."
            )

        conn = sqlite3.connect(
            DATABASE
        )

        cursor = conn.cursor()

        try:

            cursor.execute("""
                INSERT INTO users
                (name, email, username, password)
                VALUES (?, ?, ?, ?)
            """, (
                name,
                email,
                username,
                password
            ))

            conn.commit()
            conn.close()

            return render_template(
                "register.html",
                success="Account created successfully. You can now sign in."
            )

        except sqlite3.IntegrityError:

            conn.close()

            return render_template(
                "register.html",
                error="Username already exists. Please choose another username."
            )

    return render_template(
        "register.html"
    )


# =========================================================
# LOGOUT
# =========================================================

@app.route("/logout")
def logout():

    session.clear()

    return redirect(
        url_for("home")
    )


# =========================================================
# MAIN INDEX
# =========================================================

@app.route("/index")
def index():

    if not login_required():

        return redirect(
            url_for("home")
        )

    return render_template(
        "index.html"
    )


# =========================================================
# ABOUT
# =========================================================

@app.route("/about")
def about():

    if not login_required():

        return redirect(
            url_for("home")
        )

    return render_template(
        "about.html"
    )


# =========================================================
# CONTACT
# =========================================================

@app.route(
    "/contact",
    methods=["GET", "POST"]
)
def contact():

    if not login_required():

        return redirect(
            url_for("home")
        )

    if request.method == "POST":

        name = request.form.get(
            "name",
            ""
        ).strip()

        email = request.form.get(
            "email",
            ""
        ).strip()

        subject = request.form.get(
            "subject",
            ""
        ).strip()

        message = request.form.get(
            "message",
            ""
        ).strip()

        os.makedirs(
            DATA_DIR,
            exist_ok=True
        )

        if not os.path.exists(
            CONTACT_FILE
        ):

            df = pd.DataFrame(
                columns=[
                    "Name",
                    "Email",
                    "Subject",
                    "Message"
                ]
            )

            df.to_csv(
                CONTACT_FILE,
                index=False
            )

        new_message = pd.DataFrame([{
            "Name": name,
            "Email": email,
            "Subject": subject,
            "Message": message
        }])

        new_message.to_csv(
            CONTACT_FILE,
            mode="a",
            header=False,
            index=False
        )

        return render_template(
            "contact.html",
            success="Your message has been sent successfully."
        )

    return render_template(
        "contact.html"
    )


# =========================================================
# ADMIN PANEL
# =========================================================

@app.route("/admin")
def admin():

    if not login_required():

        return redirect(
            url_for("home")
        )

    conn = sqlite3.connect(
        DATABASE
    )

    cursor = conn.cursor()

    cursor.execute(
        "SELECT COUNT(*) FROM users"
    )

    total_users = cursor.fetchone()[0]

    cursor.execute("""
        SELECT id, name, email, username
        FROM users
        ORDER BY id DESC
    """)

    users_data = cursor.fetchall()

    conn.close()

    users = []

    for user in users_data:

        users.append({
            "id": user[0],
            "name": user[1],
            "email": user[2],
            "username": user[3]
        })

    # Contact messages
    if os.path.exists(
        CONTACT_FILE
    ):

        try:

            data = pd.read_csv(
                CONTACT_FILE
            )

            messages = data.to_dict(
                orient="records"
            )

        except Exception:

            messages = []

    else:

        messages = []

    return render_template(
        "admin.html",
        users=users,
        total_users=total_users,
        messages=messages
    )


# =========================================================
# MESSAGES
# =========================================================

@app.route("/messages")
def messages():

    if not login_required():

        return redirect(
            url_for("home")
        )

    if os.path.exists(
        CONTACT_FILE
    ):

        try:

            data = pd.read_csv(
                CONTACT_FILE
            )

            message_list = data.to_dict(
                orient="records"
            )

        except Exception:

            message_list = []

    else:

        message_list = []

    return render_template(
        "messages.html",
        messages=message_list
    )


# =========================================================
# TRADITIONAL RISK SCORE
# =========================================================

def calculate_risk_score(
    total_cases,
    recovered_cases,
    mental_health,
    risk_level
):

    if total_cases > 0:

        recovery_rate = (
            recovered_cases /
            total_cases
        ) * 100

    else:

        recovery_rate = 0

    score = 0

    # Mental health
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

    score = min(
        score,
        100
    )

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


# =========================================================
# AI ANALYSIS
# =========================================================

def get_ai_analysis(
    total_cases,
    recovered_cases,
    mental_health
):

    try:

        ai_prediction, ai_confidence = (
            predict_health_risk(
                total_cases,
                recovered_cases,
                mental_health
            )
        )

        model_accuracy = get_model_accuracy()

        if ai_prediction.lower() == "high":

            recommendation = (
                "AI analysis indicates a high "
                "health risk. Priority monitoring, "
                "mental health support, disease "
                "surveillance and preventive "
                "health measures are recommended."
            )

        elif ai_prediction.lower() == "medium":

            recommendation = (
                "AI analysis indicates a medium "
                "health risk. Regular monitoring, "
                "preventive healthcare and mental "
                "health awareness are recommended."
            )

        else:

            recommendation = (
                "AI analysis indicates a low "
                "health risk. Continue routine "
                "health monitoring and preventive "
                "health practices."
            )

        return (
            ai_prediction,
            ai_confidence,
            model_accuracy,
            recommendation
        )

    except Exception as e:

        print(
            "AI prediction error:",
            e
        )

        return (
            "Unavailable",
            0,
            0,
            "AI prediction is currently unavailable."
        )


# =========================================================
# DASHBOARD
# =========================================================

@app.route("/dashboard")
def dashboard():

    if not login_required():

        return redirect(
            url_for("home")
        )

    if not os.path.exists(
        DATASET
    ):

        return (
            "Dataset not found: " +
            DATASET
        )

    data = pd.read_csv(
        DATASET
    )

    data.columns = (
        data.columns
        .str.strip()
    )

    data["community"] = (
        data["community"]
        .astype(str)
        .str.strip()
    )

    data["risk_level"] = (
        data["risk_level"]
        .astype(str)
        .str.strip()
    )

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
            .str.lower()
            == "high"
        ]
    )

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
        ).strip()

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

        # AI
        (
            ai_prediction,
            ai_confidence,
            ai_model_accuracy,
            ai_recommendation
        ) = get_ai_analysis(
            total,
            recovered,
            mental_health
        )

        # Traditional warning
        if calculated_risk == "High Risk":

            warning = (
                f"{row['community']} has a HIGH "
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
                f"{row['community']} has a MEDIUM "
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
                f"{row['community']} has a LOW "
                f"community health risk score of "
                f"{risk_score}/100. Continue routine health monitoring."
            )

            recommendation = (
                "Continue routine health monitoring and "
                "preventive health measures. Maintain "
                "community awareness and preparedness."
            )

        communities.append({

            "community":
                row["community"],

            "total_cases":
                total,

            "recovered_cases":
                recovered,

            "mental_health_impact":
                mental_health,

            "risk_level":
                risk_level,

            "recovery_rate":
                recovery_rate,

            "risk_score":
                risk_score,

            "calculated_risk":
                calculated_risk,

            "warning":
                warning,

            "recommendation":
                recommendation,

            "ai_prediction":
                ai_prediction,

            "ai_confidence":
                ai_confidence,

            "model_accuracy":
                ai_model_accuracy,

            "ai_recommendation":
                ai_recommendation
        })

    model_accuracy = get_model_accuracy()

    return render_template(

        "dashboard.html",

        total_cases=total_cases,

        recovered_cases=recovered_cases,

        average_mental_health=average_mental_health,

        high_risk_count=high_risk_count,

        communities=communities,

        model_accuracy=model_accuracy
    )


# =========================================================
# COMMUNITY DETAILS API
# =========================================================

@app.route(
    "/api/community/<community_name>"
)
def community_details(
    community_name
):

    if not login_required():

        return jsonify({
            "error": "Login required"
        }), 401

    if not os.path.exists(
        DATASET
    ):

        return jsonify({
            "error": "Dataset not found"
        }), 500

    data = pd.read_csv(
        DATASET
    )

    data.columns = (
        data.columns
        .str.strip()
    )

    data["community"] = (
        data["community"]
        .astype(str)
        .str.strip()
    )

    selected = data[
        data["community"]
        .str.lower()
        ==
        community_name
        .strip()
        .lower()
    ]

    if selected.empty:

        return jsonify({
            "error": "Community not found"
        }), 404

    community = selected.iloc[0]

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

    (
        ai_prediction,
        ai_confidence,
        model_accuracy,
        ai_recommendation
    ) = get_ai_analysis(
        total_cases,
        recovered_cases,
        mental_health
    )

    if calculated_risk == "High Risk":

        warning = (
            f"{community_name} has a HIGH "
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
            f"{community_name} has a MEDIUM "
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
            f"{community_name} has a LOW "
            f"community health risk score of "
            f"{risk_score}/100. Continue routine health monitoring."
        )

        recommendation = (
            "Continue routine health monitoring and "
            "preventive health measures. Maintain "
            "community awareness and preparedness."
        )

    return jsonify({

        "community":
            community_name,

        "totalCases":
            total_cases,

        "recoveredCases":
            recovered_cases,

        "mentalHealth":
            mental_health,

        "riskLevel":
            risk_level,

        "recoveryRate":
            recovery_rate,

        "riskScore":
            risk_score,

        "calculatedRisk":
            calculated_risk,

        "warning":
            warning,

        "recommendation":
            recommendation,

        "aiPrediction":
            ai_prediction,

        "aiConfidence":
            ai_confidence,

        "modelAccuracy":
            model_accuracy,

        "aiRecommendation":
            ai_recommendation
    })


# =========================================================
# RISK PREDICTION
# =========================================================

@app.route(
    "/prediction",
    methods=["GET", "POST"]
)
def prediction():

    if not login_required():

        return redirect(
            url_for("home")
        )

    if request.method == "GET":

        return render_template(
            "prediction.html"
        )

    try:

        total_cases = int(
            request.form.get(
                "total_cases",
                0
            )
        )

        recovered_cases = int(
            request.form.get(
                "recovered_cases",
                0
            )
        )

        mental_health = float(
            request.form.get(
                "mental_health",
                0
            )
        )

        risk_level = request.form.get(
            "risk_level",
            "Low"
        ).strip()

    except (
        ValueError,
        TypeError
    ):

        return render_template(
            "prediction.html",
            error="Please enter valid numerical values."
        )

    # -----------------------------------------------------
    # VALIDATION
    # -----------------------------------------------------

    if total_cases < 0:

        return render_template(
            "prediction.html",
            error="Total cases cannot be negative."
        )

    if recovered_cases < 0:

        return render_template(
            "prediction.html",
            error="Recovered cases cannot be negative."
        )

    if recovered_cases > total_cases:

        return render_template(
            "prediction.html",
            error="Recovered cases cannot be greater than total cases."
        )

    if mental_health < 0 or mental_health > 100:

        return render_template(
            "prediction.html",
            error="Mental health impact must be between 0 and 100."
        )

    # -----------------------------------------------------
    # RECOVERY RATE
    # -----------------------------------------------------

    if total_cases > 0:

        recovery_rate = round(
            (
                recovered_cases /
                total_cases
            ) * 100,
            2
        )

    else:

        recovery_rate = 0

    # -----------------------------------------------------
    # TRADITIONAL RISK SCORE
    # -----------------------------------------------------

    risk_score = 0

    # Cases
    if total_cases >= 1500:

        risk_score += 30

    elif total_cases >= 1000:

        risk_score += 25

    elif total_cases >= 500:

        risk_score += 15

    else:

        risk_score += 5

    # Mental health
    if mental_health >= 70:

        risk_score += 30

    elif mental_health >= 50:

        risk_score += 25

    elif mental_health >= 30:

        risk_score += 15

    else:

        risk_score += 5

    # Existing risk level
    if risk_level.lower() == "high":

        risk_score += 40

    elif risk_level.lower() == "medium":

        risk_score += 25

    else:

        risk_score += 10

    # Recovery
    if recovery_rate < 70:

        risk_score += 20

    elif recovery_rate < 85:

        risk_score += 15

    elif recovery_rate < 95:

        risk_score += 5

    risk_score = min(
        risk_score,
        100
    )

    # -----------------------------------------------------
    # TRADITIONAL RESULT
    # -----------------------------------------------------

    if risk_score >= 70:

        prediction_result = "High Risk"

        recommendation = (
            "Priority health monitoring is recommended. "
            "Focus on mental health support, regular health "
            "screening, disease surveillance, and preparedness "
            "for possible future outbreaks."
        )

    elif risk_score >= 40:

        prediction_result = "Medium Risk"

        recommendation = (
            "Regular health monitoring is recommended. "
            "Focus on preventive health measures, mental "
            "health awareness, and community-level disease monitoring."
        )

    else:

        prediction_result = "Low Risk"

        recommendation = (
            "The community currently has a relatively low "
            "risk level. Continue regular health monitoring "
            "and preventive health practices."
        )

    # -----------------------------------------------------
    # AI PREDICTION
    # -----------------------------------------------------

    (
        ai_prediction,
        ai_confidence,
        model_accuracy,
        ai_recommendation
    ) = get_ai_analysis(
        total_cases,
        recovered_cases,
        mental_health
    )

    # -----------------------------------------------------
    # SEND RESULTS TO HTML
    # -----------------------------------------------------

    return render_template(

        "prediction.html",

        prediction=prediction_result,

        recovery_rate=recovery_rate,

        risk_score=risk_score,

        recommendation=recommendation,

        total_cases=total_cases,

        recovered_cases=recovered_cases,

        mental_health=mental_health,

        risk_level=risk_level,

        ai_prediction=ai_prediction,

        ai_confidence=ai_confidence,

        model_accuracy=model_accuracy,

        ai_recommendation=ai_recommendation
    )


# =========================================================
# DOWNLOAD CSV
# =========================================================

@app.route("/download_csv")
def download_csv():

    if not login_required():

        return redirect(
            url_for("home")
        )

    if not os.path.exists(
        DATASET
    ):

        return "Dataset not found"

    return send_file(
        DATASET,
        as_attachment=True
    )


# =========================================================
# DOWNLOAD PDF
# =========================================================

@app.route("/download_pdf")
def download_pdf():

    if not login_required():

        return redirect(
            url_for("home")
        )

    if not os.path.exists(
        DATASET
    ):

        return "Dataset not found"

    data = pd.read_csv(
        DATASET
    )

    pdf_path = os.path.join(
        BASE_DIR,
        "Community_Health_Report.pdf"
    )

    pdf = SimpleDocTemplate(
        pdf_path
    )

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
            "<br/>Total Communities: {}".format(
                len(data)
            ),
            styles["Normal"]
        )
    )

    story.append(
        Paragraph(
            "Total COVID Cases: {}".format(
                data["total_cases"].sum()
            ),
            styles["Normal"]
        )
    )

    story.append(
        Paragraph(
            "Recovered Cases: {}".format(
                data["recovered_cases"].sum()
            ),
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

    story.append(
        Paragraph(
            "AI Model Accuracy: {}%".format(
                get_model_accuracy()
            ),
            styles["Normal"]
        )
    )

    pdf.build(
        story
    )

    return send_file(
        pdf_path,
        as_attachment=True
    )


# =========================================================
# RUN APPLICATION
# =========================================================

if __name__ == "__main__":

    app.run(
        debug=True
    )