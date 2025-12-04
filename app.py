from flask import Flask, request, jsonify ,send_file
import africastalking
from flask_cors import CORS
from supabase import create_client
import os
import uuid
import base64
import requests
from datetime import datetime
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
import secrets
import string
from io import BytesIO


app = Flask(__name__)
CORS(app)

username = "Jolofliz"  # use sandbox for testing
api_key = "atsk_5227d4795cfaf1c1a659fb603870ae8e66fd2497abe11f5756b0dd511128e87981a8a748"


MPESA_BASE_URL = os.getenv("MPESA_BASE_URL", "https://sandbox.safaricom.co.ke")
CONSUMER_KEY = os.getenv("MPESA_CONSUMER_KEY")
CONSUMER_SECRET = os.getenv("MPESA_CONSUMER_SECRET")
SHORTCODE = os.getenv("MPESA_SHORTCODE")
PASSKEY = os.getenv("MPESA_PASSKEY")
CALLBACK_URL = os.getenv("MPESA_CALLBACK_URL")

supabase = create_client(
    os.getenv("SUPABASE_URL"),
    os.getenv("SUPABASE_SERVICE_ROLE_KEY")
)


@app.route("/api/create-user", methods=["POST"])
def create_user():
    try:
        data = request.json
        print(f"Request data: {data}")  # Debug log

        # ✅ Validate required fields
        required_fields = ["email", "full_name", "role"]
        if not all(data.get(key) for key in required_fields):
            return jsonify({"error": "Missing required fields: email, full_name, role"}), 400

        email = data.get("email")
        full_name = data.get("full_name")
        role = data.get("role", "").strip().lower()

        if role not in ["parent", "student", "teacher", "admin", "clerk"]:
            return jsonify({"error": "Invalid role specified"}), 400

        # ✅ Role-specific validation
        if role == "parent" and not data.get("phone_number"):
            return jsonify({"error": "phone_number is required for parent role"}), 400

        if role == "student":
            required_student_fields = ["dob", "gender", "admission_number", "class_name", "parent_id"]
            if not all(data.get(key) for key in required_student_fields):
                return jsonify({"error": "dob, gender, admission_number, class_name, and parent_id are required for student role"}), 400

        # ✅ Generate secure password
        password = 'Jomoks!'
        # 1️⃣ Create Supabase Auth user
        user = supabase.auth.admin.create_user({
            "email": email,
            "password": password,
            "email_confirm": True
        })
        print(f"Auth user response: {user}")  # Debug log

        if not user or not getattr(user, "user", None):
            return jsonify({"error": "Failed to create auth user"}), 400

        user_id = user.user.id

        # 2️⃣ Insert into profiles
        profile = {
            "id": user_id,
            "email": email,
            "full_name": full_name,
            "role": role
        }
        res_profile = supabase.table("profiles").insert(profile).execute()
        print(f"Profile insert response: {res_profile}")

        if not res_profile.data:
            supabase.auth.admin.delete_user(user_id)  # cleanup
            return jsonify({"error": "Failed to insert profile"}), 400

        # 3️⃣ If parent → insert into parents table
        if role == "parent":
            parent_data = {
                "id": user_id,
                "phone_number": data.get("phone_number")
            }
            res_parent = supabase.table("parents").insert(parent_data).execute()
            print(f"Parent insert response: {res_parent}")

            if not res_parent.data:
                supabase.table("profiles").delete().eq("id", user_id).execute()
                supabase.auth.admin.delete_user(user_id)
                return jsonify({"error": "Failed to insert parent"}), 400

        # 4️⃣ If student → lookup class_id & parent_id then insert into students table
        if role == "student":
            # 🔍 Get class_id from classes table using class_name
            class_name = data.get("class_name")
            class_res = supabase.table("classes").select("name , category").eq("name", class_name).maybe_single().execute()

            if not class_res.data:
                supabase.table("profiles").delete().eq("id", user_id).execute()
                supabase.auth.admin.delete_user(user_id)
                return jsonify({"error": f"Class '{class_name}' not found"}), 400

            class_name = class_res.data["name"]
            class_category = class_res.data["category"]

            # ✅ Use parent_id directly from request (no lookup needed)
            parent_id = data.get("parent_id")
            class_res = supabase.table("parents").select("phone_number").eq("id", parent_id).maybe_single().execute()
            if not parent_id:
                supabase.table("profiles").delete().eq("id", user_id).execute()
                supabase.auth.admin.delete_user(user_id)
                return jsonify({"error": "parent_id is required"}), 400
            parent_phonenumber = class_res.data.get("phone_number") if class_res.data else None
            # ✅ Insert student
            student_data = {
                "id": user_id,
                "full_name": full_name,
                "dob": data.get("dob"),
                "gender": data.get("gender"),
                "admission_number": data.get("admission_number"),
                "class_name": class_name,
                "class_category": class_category,
                "parent_phonenumber": parent_phonenumber,
            }
            res_student = supabase.table("students").insert(student_data).execute()
            print(f"Student insert response: {res_student}")

            if not res_student.data:
                supabase.table("profiles").delete().eq("id", user_id).execute()
                supabase.auth.admin.delete_user(user_id)
                return jsonify({"error": "Failed to insert student"}), 400

        return jsonify({"message": "User created successfully", "user_id": user_id}), 201

    except Exception as e:
        print(f"Error in create_user: {str(e)}")
        return jsonify({"error": f"Failed to create user: {str(e)}"}), 500


@app.route("/api/classes", methods=["GET"])
def get_classes():
    try:
        res = supabase.table("classes").select("*").execute()
        return jsonify(res.data), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/parents", methods=["GET"])
def get_parents():
    try:
        res = supabase.table("parents").select("id, phone_number, profiles(full_name)").execute()
        # Join with profiles for parent name
        parents = []
        for row in res.data:
            parents.append({
                "id": row["id"],
                "phone_number": row["phone_number"],
                "full_name": row.get("profiles", {}).get("full_name", "")
            })
        return jsonify(parents), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500



@app.route("/api/announcements", methods=["GET"])
def get_announcements():
    try:
        res = supabase.table("announcements").select("*").order("created_at", desc=True).execute()
        return jsonify(res.data), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
# Create a new announcement
@app.route("/api/announcements", methods=["POST"])
def create_announcement():
    try:
        data = request.json
        required_fields = ["title", "content"]
        if not all(data.get(f) for f in required_fields):
            return jsonify({"error": "Missing required fields"}), 400

        announcement = {
            "title": data.get("title"),
            "content": data.get("content"),
            "category": data.get("category"),
        }
        print(f"Creating announcement: {announcement}")

        # Save to Supabase
        res = supabase.table("announcements").insert(announcement).execute()
        if not res.data:
            return jsonify({"error": "Failed to save announcement"}), 500
        saved_announcement = res.data[0]

        # Initialize Africa's Talking SMS service
        try:
            africastalking.initialize(username, api_key)
            sms = africastalking.SMS
            recipients = ["+254754356019"]  
            # Replace with a valid test number
            # sender_id = "YourApprovedSenderID"  # Replace with your Sender ID

            message = (
                f"{saved_announcement['title']}: "
                f"{saved_announcement['content']} "
                f"(Category: {saved_announcement.get('category', 'GENERAL').upper()})"
            )

            # Send SMS
            sms_response = sms.send(message, recipients)
            print("SMS Response:", sms_response)

            # Check for blacklist or other errors
            if sms_response.get("SMSMessageData", {}).get("Recipients", [{}])[0].get("statusCode") == 406:
                print(f"Recipient blacklisted: {recipients}")
                return jsonify({
                    "message": "Announcement created, but SMS failed due to blacklist",
                    "announcement": saved_announcement,
                    "sms_response": sms_response
                }), 201

        except Exception as sms_error:
            print(f"SMS Error: {sms_error}")
            import traceback
            traceback.print_exc()
            return jsonify({
                "message": "Announcement created, but SMS failed",
                "announcement": saved_announcement,
                "sms_error": str(sms_error)
            }), 201

        return jsonify({
            "message": "Announcement created and SMS sent successfully",
            "announcement": saved_announcement,
            "sms_response": sms_response
        }), 201

    except Exception as e:
        print(f"General Error: {e}")
        return jsonify({"error": str(e)}), 500

# Update an announcement
@app.route("/api/announcements/<uuid:announcement_id>", methods=["PUT"])
def update_announcement(announcement_id):
    try:
        data = request.json
        update_fields = {
            "title": data.get("title"),
            "content": data.get("content"),
            "category": data.get("category"),
        }
        # remove None values
        update_fields = {k: v for k, v in update_fields.items() if v is not None}

        res = (
            supabase.table("announcements")
            .update(update_fields)
            .eq("id", str(announcement_id))
            .execute()
        )

        if not res.data:
            return jsonify({"error": "Announcement not found"}), 404

        return jsonify(res.data[0]), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# Delete an announcement
@app.route("/api/announcements/<uuid:announcement_id>", methods=["DELETE"])
def delete_announcement(announcement_id):
    try:
        res = (
            supabase.table("announcements")
            .delete()
            .eq("id", str(announcement_id))
            .execute()
        )

        if not res.data:
            return jsonify({"error": "Announcement not found"}), 404

        return jsonify({"message": "Announcement deleted"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    
@app.route("/api/pay", methods=["POST"])
def pay_fee():
    try:
        data = request.get_json()
        student_id = data.get("student_id")
        amount = float(data.get("amount", 0))
        phone = data.get("phone")

        if not student_id or amount <= 0 or not phone:
            return jsonify({"error": "Missing student_id, amount, or phone"}), 400

        payment_id = str(uuid.uuid4())

        # Record new payment as awaiting manual payment
        supabase.table("payments").insert({
            "id": payment_id,
            "student_id": student_id,
            "amount": amount,
            "method": "mpesa",
            "phone": phone,
            "status": "pending",
            "created_at": datetime.now().isoformat(),
        }).execute()

        # Response message to show user payment instructions
        return jsonify({
            "message": "Payment initialized",
            "instructions": {
                "till_number": "5412431",  # Replace with your client’s Buy Goods Till
                "amount": amount,
                "steps": [
                    "Go to M-PESA > Lipa na M-PESA > Buy Goods and Services",
                    "Enter Till Number: 5412431",
                    f"Enter Amount: {amount}",
                    "Enter your M-PESA PIN and press OK",
                    "After payment, click 'I’ve Paid' to confirm."
                ]
            }
        }), 200

    except Exception as e:
        print("Error:", e)
        return jsonify({"error": "Internal server error"}), 500


@app.route("/api/confirm_payment", methods=["POST"])
def confirm_payment():
    """Called when user clicks 'I’ve Paid'"""
    try:
        data = request.get_json()
        student_id = data.get("student_id")

        res = supabase.table("payments").select("*").eq("student_id", student_id).order("created_at", desc=True).limit(1).execute()
        if not res.data:
            return jsonify({"error": "No recent payment found"}), 404

        payment = res.data[0]
        supabase.table("payments").update({"status": "pending"}).eq("id", payment["id"]).execute()

        return jsonify({"message": "Payment marked for verification"}), 200
    except Exception as e:
        print("Error:", e)
        return jsonify({"error": "Internal server error"}), 500


@app.route("/api/admin/payments", methods=["GET"])
def admin_payments():
    """Simple admin view of all payments"""
    try:
        res = supabase.table("payments").select("*").order("created_at", desc=True).execute()
        return jsonify(res.data), 200
    except Exception as e:
        print("Error:", e)
        return jsonify({"error": "Internal server error"}), 500


@app.route("/api/payments/<student_id>", methods=["GET"])
def get_student_payments(student_id):
    """Return all payments for a specific student"""
    try:
        res = supabase.table("payments") \
            .select("*") \
            .eq("student_id", student_id) \
            .order("created_at", desc=True) \
            .execute()

        return jsonify({"payments": res.data}), 200
    except Exception as e:
        print("Error:", e)
        return jsonify({"error": "Failed to fetch payments"}), 500
    

@app.route("/api/invoice/<payment_id>", methods=["GET"])
def download_invoice(payment_id):
    """Generate a simple PDF invoice for a specific payment"""
    try:
        res = supabase.table("payments").select("*").eq("id", payment_id).execute()
        if not res.data:
            return jsonify({"error": "Payment not found"}), 404

        payment = res.data[0]

        buffer = BytesIO()
        c = canvas.Canvas(buffer, pagesize=A4)
        c.setFont("Helvetica-Bold", 16)
        c.drawString(150, 800, "ST. PETER’S ACADEMY - PAYMENT INVOICE")
        c.setFont("Helvetica", 12)
        c.drawString(100, 760, f"Payment ID: {payment['id']}")
        c.drawString(100, 740, f"Student ID: {payment['student_id']}")
        c.drawString(100, 720, f"Phone: {payment['phone']}")
        c.drawString(100, 700, f"Amount: KES {payment['amount']}")
        c.drawString(100, 680, f"Status: {payment['status']}")
        c.drawString(100, 660, f"Date: {payment['created_at']}")
        c.showPage()
        c.save()

        buffer.seek(0)
        return send_file(buffer, as_attachment=True, download_name=f"invoice_{payment['id']}.pdf", mimetype="application/pdf")

    except Exception as e:
        print("Error generating invoice:", e)
        return jsonify({"error": "Failed to generate invoice"}), 500


@app.route("/api/fees", methods=["POST"])
def set_fee():
    """Admin adds or updates a fee structure"""
    try:
        data = request.get_json()
        class_level = data.get("class_level")
        term = data.get("term")
        year = data.get("year")
        amount = data.get("amount")

        if not all([class_level, term, year, amount]):
            return jsonify({"error": "All fields are required"}), 400

        supabase.table("fees").insert({
            "class_level": class_level,
            "term": term,
            "year": year,
            "amount": amount,
            "created_at": datetime.now().isoformat(),
        }).execute()

        return jsonify({"message": "Fee structure saved successfully"}), 200

    except Exception as e:
        print("Error:", e)
        return jsonify({"error": "Internal server error"}), 500


@app.route("/api/fees", methods=["GET"])
def get_fees():
    """Get all fee structures"""
    try:
        res = supabase.table("fees").select("*").order("created_at", desc=True).execute()
        return jsonify(res.data), 200
    except Exception as e:
        print("Error:", e)
        return jsonify({"error": "Internal server error"}), 500








    

# # -------------------------
# # HELPER: M-PESA TOKEN
# # -------------------------
# def get_access_token():
#     url = f"{MPESA_BASE_URL}/oauth/v1/generate?grant_type=client_credentials"
#     response = requests.get(url, auth=(CONSUMER_KEY, CONSUMER_SECRET))
#     response.raise_for_status()
#     return response.json()["access_token"]


# # -------------------------
# # HELPER: STK PUSH
# # -------------------------
# def stk_push(phone, amount, account_reference, description="School Fees"):
#     token = get_access_token()
#     timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
#     password = base64.b64encode((SHORTCODE + PASSKEY + timestamp).encode()).decode()

#     payload = {
#         "BusinessShortCode": SHORTCODE,
#         "Password": password,
#         "Timestamp": timestamp,
#         "TransactionType": "CustomerPayBillOnline",
#         "Amount": amount,
#         "PartyA": phone,
#         "PartyB": SHORTCODE,
#         "PhoneNumber": phone,
#         "CallBackURL": CALLBACK_URL,
#         "AccountReference": account_reference,
#         "TransactionDesc": description,
#     }

#     headers = {
#         "Authorization": f"Bearer {token}",
#         "Content-Type": "application/json",
#     }

#     url = f"{MPESA_BASE_URL}/mpesa/stkpush/v1/processrequest"
#     res = requests.post(url, json=payload, headers=headers)
#     return res.json()


# # -------------------------
# # ENDPOINT: INITIATE PAYMENT
# # -------------------------
# @app.route("/api/pay", methods=["POST"])
# def pay_fee():
#     try:
#         data = request.get_json()
#         student_id = data.get("student_id")
#         amount = float(data.get("amount", 0))
#         phone = data.get("phone")
#         method = data.get("method", "mpesa")

#         if not student_id or amount <= 0 or not phone:
#             return jsonify({"error": "Missing student_id, amount, or phone"}), 400

#         payment_id = str(uuid.uuid4())

#         # Save pending payment record
#         supabase.table("payments").insert({
#             "id": payment_id,
#             "student_id": student_id,
#             "amount": amount,
#             "method": method,
#             "status": "pending",
#         }).execute()

#         # Initiate STK Push
#         account_ref = "STUDENT-" + student_id[:6]
#         response = stk_push(phone, amount, account_ref)

#         return jsonify({
#             "message": "STK Push initiated",
#             "mpesa_response": response,
#         }), 200

#     except Exception as e:
#         print("Error:", e)
#         return jsonify({"error": "Internal server error"}), 500


# # -------------------------
# # ENDPOINT: CALLBACK
# # -------------------------
# @app.route("/api/mpesa/callback", methods=["POST"])
# def mpesa_callback():
#     data = request.get_json()
#     print("Callback received:", data)

#     body = data.get("Body", {})
#     stk = body.get("stkCallback", {})
#     result_code = stk.get("ResultCode")
#     metadata = stk.get("CallbackMetadata", {}).get("Item", [])

#     if result_code == 0:
#         # Payment successful
#         amount = next((x["Value"] for x in metadata if x["Name"] == "Amount"), None)
#         receipt = next((x["Value"] for x in metadata if x["Name"] == "MpesaReceiptNumber"), None)
#         phone = next((x["Value"] for x in metadata if x["Name"] == "PhoneNumber"), None)

#         supabase.table("payments").update({
#             "transaction_code": receipt,
#             "status": "successful",
#         }).eq("method", "mpesa").eq("status", "pending").execute()
#     else:
#         supabase.table("payments").update({
#             "status": "failed",
#         }).eq("status", "pending").execute()

#     return jsonify({"ResultCode": 0, "ResultDesc": "Accepted"}), 200