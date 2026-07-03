import os
import io
import certifi
from flask import Flask, render_template, request, redirect, url_for, session, flash, send_file
from werkzeug.security import generate_password_hash, check_password_hash
from pymongo import MongoClient
from datetime import datetime
import pandas as pd
from bson.objectid import ObjectId
from functools import wraps
from fpdf import FPDF

base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
frontend_dir = os.path.join(base_dir, 'frontend')
template_dir = os.path.join(frontend_dir, 'templates')
static_dir = os.path.join(frontend_dir, 'static')

app = Flask(__name__, template_folder=template_dir, static_folder=static_dir)
app.secret_key = os.environ.get("SECRET_KEY", "super_secret_key_change_in_prod")

# MongoDB connection with SSL certificate verification for Render deployment
MONGO_URI = os.environ.get("MONGO_URI", "mongodb+srv://zadafiyadhruv_db_user:Dhruv6147@cluster0.h1togyr.mongodb.net/stockdb?appName=Cluster0")
client = MongoClient(
    MONGO_URI,
    tlsCAFile=certifi.where(),
    serverSelectionTimeoutMS=5000,
    connectTimeoutMS=10000,
    socketTimeoutMS=10000
)
db = client['member_management_db']
users_collection = db['users']
members_collection = db['members']

# Initialize admin user if none exists
if users_collection.count_documents({}) == 0:
    users_collection.insert_one({
        "name": "admin",
        "username": "admin",
        "password": generate_password_hash("admin"),
        "role": "admin"
    })
else:
    # Ensure existing admin has role 'admin'
    users_collection.update_one({"username": "admin"}, {"$set": {"role": "admin"}})

# Auth Guard Decorator
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'username' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# Admin Guard Decorator
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'username' not in session or session.get('role') != 'admin':
            flash("You do not have permission to access this page.", "danger")
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/')
def index():
    return redirect(url_for('dashboard'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        user = users_collection.find_one({"username": username})
        if user and check_password_hash(user['password'], password):
            session['username'] = user['username']
            session['name'] = user['name']
            session['role'] = user.get('role', 'user')
            
            if session['role'] == 'admin':
                flash(f"Login successful! Welcome back, {session['name']}.", "success")
                return redirect(url_for('admin_portal'))
            flash(f"Login successful! Welcome back, {session['name']}.", "success")
            return redirect(url_for('dashboard'))
        else:
            flash("Invalid username or password", "danger")
            
    return render_template('login.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        name = request.form.get('name')
        username = request.form.get('username')
        password = request.form.get('password')
        
        if users_collection.find_one({"username": username}):
            flash("Username already exists. Please choose another.", "warning")
        elif name and username and password:
            users_collection.insert_one({
                "name": name,
                "username": username,
                "password": generate_password_hash(password),
                "role": "user"
            })
            flash("Account created successfully! You can now log in.", "success")
            return redirect(url_for('login'))
        else:
            flash("All fields are required.", "danger")
            
    return render_template('signup.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/dashboard')
@login_required
def dashboard():
    today_str = datetime.now().strftime("%Y-%m-%d")
    username = session.get('username')
    
    user_filter = {"created_by": username}
    
    total_members = members_collection.count_documents(user_filter)
    today_entries = members_collection.count_documents({"date": today_str, "created_by": username})
    boy_entries = members_collection.count_documents({"grain_type": "દીકરા ના", "created_by": username})
    girl_entries = members_collection.count_documents({"grain_type": "દીકરી ના", "created_by": username})
    
    members = list(members_collection.find(user_filter).sort([("_id", -1)]))
        
    return render_template('dashboard.html', 
                           total_members=total_members,
                           today_entries=today_entries,
                           boy_entries=boy_entries,
                           girl_entries=girl_entries,
                           members=members,
                           datetime=datetime)

@app.route('/add_member', methods=['POST'])
@login_required
def add_member():
    member_name = request.form.get('member_name')
    mobile_number = request.form.get('mobile_number')
    if mobile_number and not mobile_number.startswith('+91'):
        mobile_number = f"+91 {mobile_number}"
    date_str = request.form.get('date')
    grain_type = request.form.get('grain_type')
    hastak = request.form.get('hastak')
    
    if member_name and date_str and grain_type and hastak:
        try:
            members_collection.insert_one({
                "member_name": member_name,
                "mobile_number": mobile_number,
                "date": date_str,
                "grain_type": grain_type,
                "hastak": hastak,
                "created_by": session.get('username')
            })
            flash("Member added successfully", "success")
        except Exception as e:
            flash(f"Error saving to database: {str(e)}", "danger")
    else:
        flash("All fields are required", "danger")
        
    return redirect(url_for('dashboard'))

@app.route('/edit_member/<member_id>', methods=['POST'])
@login_required
def edit_member(member_id):
    query = {"_id": ObjectId(member_id)}
    if session.get('role') != 'admin':
        query["created_by"] = session.get('username')
        
    member = members_collection.find_one(query)
    if not member:
        flash("You don't have permission to edit this member or it doesn't exist.", "danger")
        return redirect(request.referrer or url_for('dashboard'))
        
    member_name = request.form.get('member_name')
    mobile_number = request.form.get('mobile_number')
    # Clean mobile number if they submitted with +91 already or didn't
    if mobile_number:
        mobile_number = mobile_number.replace("+91", "").strip()
        mobile_number = f"+91 {mobile_number}"
        
    date_str = request.form.get('date')
    grain_type = request.form.get('grain_type')
    hastak = request.form.get('hastak')
    
    if member_name and date_str and grain_type and hastak:
        update_data = {
            "member_name": member_name,
            "mobile_number": mobile_number,
            "date": date_str,
            "grain_type": grain_type,
            "hastak": hastak
        }
        members_collection.update_one(query, {"$set": update_data})
        flash("Member updated successfully!", "success")
    else:
        flash("All fields are required.", "danger")
        
    return redirect(request.referrer or url_for('dashboard'))

@app.route('/delete_member/<member_id>', methods=['POST'])
@login_required
def delete_member(member_id):
    query = {"_id": ObjectId(member_id)}
    if session.get('role') != 'admin':
        query["created_by"] = session.get('username')
        
    result = members_collection.delete_one(query)
    
    if result.deleted_count > 0:
        flash("Member deleted successfully", "success")
    else:
        flash("You don't have permission to delete this member.", "danger")
        
    return redirect(request.referrer or url_for('dashboard'))

@app.route('/admin')
@login_required
@admin_required
def admin_portal():
    total_members = members_collection.count_documents({})
    total_users = users_collection.count_documents({})
    
    pipeline = [
        {"$group": {"_id": "$created_by", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}}
    ]
    user_stats_raw = list(members_collection.aggregate(pipeline))
    user_stats = []
    for stat in user_stats_raw:
        username = stat['_id']
        if username:
            user = users_collection.find_one({"username": username})
            name = user['name'] if user else username
            user_stats.append({"username": username, "name": name, "count": stat['count']})
        
    members_raw = list(members_collection.find().sort([("_id", -1)]))
    members = []
    
    username_to_name = {stat['username']: stat['name'] for stat in user_stats}
    
    for member in members_raw:
        creator_username = member.get('created_by')
        if creator_username:
            if creator_username not in username_to_name:
                user = users_collection.find_one({"username": creator_username})
                username_to_name[creator_username] = user['name'] if user else creator_username
            member['creator_name'] = username_to_name[creator_username]
        else:
            member['creator_name'] = 'System'
        members.append(member)
    
    return render_template('admin.html', 
                           total_members=total_members,
                           total_users=total_users,
                           user_stats=user_stats,
                           members=members)

@app.route('/reports')
@login_required
def reports():
    return render_template('reports.html')

@app.route('/export/excel')
@login_required
def export_excel():
    members = list(members_collection.find({}, {"_id": 0}))
    if not members:
        flash("No data to export", "warning")
        return redirect(url_for('reports'))
        
    df = pd.DataFrame(members)
    df.rename(columns={
        "member_name": "નામ (Name)",
        "mobile_number": "મોબાઈલ (Mobile)",
        "date": "તારીખ (Date)",
        "grain_type": "દાણા (Grain)",
        "hastak": "હસ્તક (Hastak)",
        "created_by": "Created By"
    }, inplace=True)
    
    # Use in-memory buffer instead of filesystem (Render has ephemeral filesystem)
    output = io.BytesIO()
    df.to_excel(output, index=False, engine='openpyxl')
    output.seek(0)
    
    return send_file(
        output,
        as_attachment=True,
        download_name='members.xlsx',
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )

@app.route('/export/pdf')
@login_required
def export_pdf():
    members = list(members_collection.find({}, {"_id": 0}))
    if not members:
        flash("No data to export", "warning")
        return redirect(url_for('reports'))
    
    # Create PDF with fpdf2 (pure Python, no system binary needed)
    pdf = FPDF(orientation='L', unit='mm', format='A4')
    pdf.set_auto_page_break(auto=True, margin=15)
    
    # Load fonts - NotoSans for English/numbers, NotoSansGujarati for Gujarati text
    base_dir = os.path.dirname(os.path.abspath(__file__))
    latin_font_path = os.path.join(base_dir, 'static', 'fonts', 'NotoSans-Regular.ttf')
    gujarati_font_path = os.path.join(base_dir, 'static', 'fonts', 'NotoSansGujarati-Regular.ttf')
    
    if not os.path.exists(latin_font_path) or not os.path.exists(gujarati_font_path):
        flash("PDF font files not found. Please run the build script first.", "danger")
        return redirect(url_for('reports'))
    
    try:
        pdf.add_font('NotoSans', '', latin_font_path)
        pdf.add_font('NotoGujarati', '', gujarati_font_path)
        # Set Gujarati as fallback - fpdf2 auto-switches when it finds Gujarati characters
        pdf.set_fallback_fonts(['NotoGujarati'])
    except Exception as e:
        flash(f"Error loading PDF fonts: {str(e)}", "danger")
        return redirect(url_for('reports'))
    
    pdf.add_page()
    
    # Title
    pdf.set_font('NotoSans', '', 18)
    pdf.set_text_color(41, 98, 255)
    pdf.cell(0, 12, 'Member Management - Report', ln=True, align='C')
    
    # Subtitle with date
    pdf.set_font('NotoSans', '', 10)
    pdf.set_text_color(120, 120, 120)
    pdf.cell(0, 8, f'Generated on: {datetime.now().strftime("%d-%m-%Y %H:%M")} | Total Records: {len(members)}', ln=True, align='C')
    pdf.ln(5)
    
    # Table header
    headers = ['Name', 'Mobile', 'Date', 'Grain Type', 'Hastak', 'Created By']
    col_widths = [60, 38, 30, 38, 56, 55]
    
    # Header row
    pdf.set_font('NotoSans', '', 10)
    pdf.set_fill_color(41, 98, 255)
    pdf.set_text_color(255, 255, 255)
    for i, header in enumerate(headers):
        pdf.cell(col_widths[i], 10, header, border=1, fill=True, align='C')
    pdf.ln()
    
    # Data rows
    pdf.set_font('NotoSans', '', 9)
    pdf.set_text_color(50, 50, 50)
    
    for idx, member in enumerate(members):
        # Alternate row colors
        if idx % 2 == 0:
            pdf.set_fill_color(245, 247, 250)
        else:
            pdf.set_fill_color(255, 255, 255)
        
        row_data = [
            str(member.get('member_name', '')),
            str(member.get('mobile_number', '')),
            str(member.get('date', '')),
            str(member.get('grain_type', '')),
            str(member.get('hastak', '')),
            str(member.get('created_by', ''))
        ]
        
        for i, data in enumerate(row_data):
            pdf.cell(col_widths[i], 8, data, border=1, fill=True, align='C')
        pdf.ln()
    
    # Footer
    pdf.ln(5)
    pdf.set_font('NotoSans', '', 8)
    pdf.set_text_color(150, 150, 150)
    pdf.cell(0, 8, 'Member Management System - Confidential Report', ln=True, align='C')
    
    # Output to in-memory buffer
    output = io.BytesIO()
    pdf.output(output)
    output.seek(0)
    
    return send_file(
        output,
        as_attachment=True,
        download_name=f'members_report_{datetime.now().strftime("%Y%m%d")}.pdf',
        mimetype='application/pdf'
    )

@app.route('/export_member_pdf/<member_id>')
@login_required
def export_member_pdf(member_id):
    query = {"_id": ObjectId(member_id)}
    if session.get('role') != 'admin':
        query["created_by"] = session.get('username')
        
    member = members_collection.find_one(query)
    if not member:
        flash("You don't have permission to view this member or it doesn't exist.", "danger")
        return redirect(request.referrer or url_for('dashboard'))
    
    pdf = FPDF(orientation='P', unit='mm', format='A4')
    pdf.set_auto_page_break(auto=True, margin=15)
    
    base_dir = os.path.dirname(os.path.abspath(__file__))
    # Adjust paths if we moved app.py to backend, assuming it runs from same place for now
    if os.path.basename(base_dir) == 'backend':
        static_dir = os.path.join(os.path.dirname(base_dir), 'frontend', 'static')
    else:
        static_dir = os.path.join(base_dir, 'static')
        
    latin_font_path = os.path.join(static_dir, 'fonts', 'NotoSans-Regular.ttf')
    gujarati_font_path = os.path.join(static_dir, 'fonts', 'NotoSansGujarati-Regular.ttf')
    
    if os.path.exists(latin_font_path) and os.path.exists(gujarati_font_path):
        pdf.add_font('NotoSans', '', latin_font_path)
        pdf.add_font('NotoGujarati', '', gujarati_font_path)
        pdf.set_fallback_fonts(['NotoGujarati'])
    else:
        pdf.set_font('helvetica', '', 12)
        
    pdf.add_page()
    
    pdf.set_font('NotoSans' if os.path.exists(latin_font_path) else 'helvetica', '', 20)
    pdf.set_text_color(41, 98, 255)
    pdf.cell(0, 15, 'Member Profile Receipt', ln=True, align='C')
    
    pdf.set_font('NotoSans' if os.path.exists(latin_font_path) else 'helvetica', '', 10)
    pdf.set_text_color(120, 120, 120)
    pdf.cell(0, 5, f'Generated on: {datetime.now().strftime("%d-%m-%Y %H:%M")}', ln=True, align='C')
    pdf.ln(10)
    
    pdf.set_font('NotoSans' if os.path.exists(latin_font_path) else 'helvetica', '', 12)
    pdf.set_text_color(50, 50, 50)
    
    details = [
        ('Name (નામ):', str(member.get('member_name', ''))),
        ('Mobile (મોબાઈલ):', str(member.get('mobile_number', ''))),
        ('Date (તારીખ):', str(member.get('date', ''))),
        ('Grain Type (દાણા):', str(member.get('grain_type', ''))),
        ('Hastak (હસ્તક):', str(member.get('hastak', ''))),
        ('Added By:', str(member.get('created_by', '')))
    ]
    
    for label, value in details:
        pdf.set_fill_color(245, 247, 250)
        pdf.cell(60, 12, label, border=1, fill=True)
        pdf.set_fill_color(255, 255, 255)
        pdf.cell(130, 12, value, border=1, fill=True)
        pdf.ln()
    
    pdf.ln(20)
    pdf.set_font('NotoSans' if os.path.exists(latin_font_path) else 'helvetica', '', 10)
    pdf.set_text_color(150, 150, 150)
    pdf.cell(0, 8, 'Member Management System', ln=True, align='C')
    
    output = io.BytesIO()
    pdf.output(output)
    output.seek(0)
    
    return send_file(
        output,
        as_attachment=True,
        download_name=f'member_{member.get("member_name", "profile")}_{member_id}.pdf',
        mimetype='application/pdf'
    )

@app.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    if request.method == 'POST':
        new_name = request.form.get('name')
        new_password = request.form.get('password')
        
        update_data = {}
        if new_name and new_name.strip():
            update_data['name'] = new_name.strip()
            session['name'] = new_name.strip()
            
        if new_password and new_password.strip():
            update_data['password'] = generate_password_hash(new_password)
            
        if update_data:
            users_collection.update_one({"username": session['username']}, {"$set": update_data})
            flash("Profile updated successfully!", "success")
            
        return redirect(url_for('profile'))
        
    user = users_collection.find_one({"username": session['username']})
    return render_template('profile.html', user=user)

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(debug=False, host='0.0.0.0', port=port)
