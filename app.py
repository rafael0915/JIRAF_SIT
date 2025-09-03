from flask import Flask, render_template, redirect, url_for, flash, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from models import db, User, Project, Issue, BusinessTrip, VesselSchedule, Trip
from forms import RegistrationForm, LoginForm, ProjectForm, IssueForm, UpdateIssueForm, AssignUserForm
from datetime import datetime
from flask_mail import Message, Mail
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
import os
import folium
import uuid


app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'default_secret_key')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///site.db' , 'sqlite: ///trips.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = os.path.join('static', 'uploads')
app.config['WORK_REPORT_FOLDER'] = os.path.join('static', 'work_reports')
app.config['ALLOWED_EXTENSIONS'] = {'pdf'}
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # Limit upload size to 16 MB

# Ensure the upload folder exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['WORK_REPORT_FOLDER'], exist_ok=True)


db.init_app(app)
with app.app_context():
    db.create_all()


# Configure Flask-Mail
app.config['MAIL_SERVER'] = 'smtp.example.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = os.environ.get('MAIL_USERNAME')
app.config['MAIL_PASSWORD'] = os.environ.get('MAIL_PASSWORD')
app.config['MAIL_DEFAULT_SENDER'] = os.environ.get('MAIL_DEFAULT_SENDER')
mail = Mail(app)

login_manager = LoginManager()
login_manager.init_app(app)

trips_by_fleet = {}

@app.route('/map')
def map():
    # Create a map centered at a specific location
    m = folium.Map(location=[1, 0], zoom_start=3)

    # Example markers
    folium.Marker([51.505, -0.09], popup='London').add_to(m)
    folium.Marker([48.8566, 2.3522], popup='Paris').add_to(m)
    folium.Marker([35.6895, 139.6917], popup='Tokyo').add_to(m)
    folium.Marker([-33.8688, 151.2093], popup='Sydney').add_to(m)

    # Save the map to an HTML file
    m.save('templates/map.html')
    return render_template('map.html')

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.route('/', methods=['GET'])
def index():
    return render_template('index.html')  # Your home page

@app.route('/trips', methods=['GET'])
def trips():
    return render_template('trips.html', trips_by_fleet=trips_by_fleet)

@app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegistrationForm()
    if form.validate_on_submit():
        user = User(username=form.username.data, password=generate_password_hash(form.password.data))
        db.session.add(user)
        db.session.commit()
        flash('Account created!', 'success')
        return redirect(url_for('login'))
    return render_template('register.html', form=form)

@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user and check_password_hash(user.password, form.password.data):
            login_user(user)
            return redirect(url_for('projects'))
        else:
            flash('Login Unsuccessful. Please check username and password', 'danger')
    return render_template('login.html', form=form)

@app.route('/projects', methods=['GET', 'POST'])
@login_required
def projects():
    form = ProjectForm()
    if form.validate_on_submit():
        project = Project(name=form.name.data)
        db.session.add(project)
        db.session.commit()
        flash('Project created!', 'success')
        return redirect(url_for('projects'))
    projects = Project.query.all()
    return render_template('projects.html', form=form, projects=projects)

@app.route('/projects/<int:project_id>/issues', methods=['GET', 'POST'])
@login_required
def issues(project_id):
    form = IssueForm()
    if form.validate_on_submit():
        issue = Issue(title=form.title.data, description=form.description.data, status=form.status.data, project_id=project_id)
        db.session.add(issue)
        db.session.commit()
        flash('Issue created!', 'success')
        return redirect(url_for('issues', project_id=project_id))
    issues = Issue.query.filter_by(project_id=project_id).all()
    return render_template('issues.html', form=form, issues=issues)

@app.route('/issues/<int:issue_id>/update', methods=['GET', 'POST'])
@login_required
def update_issue(issue_id):
    issue = Issue.query.get_or_404(issue_id)
    form = UpdateIssueForm()
    assign_form = AssignUserForm()
    
    assign_form.assigned_to.choices = [(user.id, user.username) for user in User.query.all()]

    if form.validate_on_submit():
        issue.status = form.status.data
        db.session.commit()
        flash('Issue status updated!', 'success')
        return redirect(url_for('issues', project_id=issue.project_id))

    if assign_form.validate_on_submit():
        issue.assigned_to_id = assign_form.assigned_to.data
        db.session.commit()
        flash('User  assigned to issue!', 'success')
        return redirect(url_for('issues', project_id=issue.project_id))

    form.status.data = issue.status
    assign_form.assigned_to.data = issue.assigned_to_id
    return render_template('update_issue.html', form=form, assign_form=assign_form, issue=issue)

@app.route('/business_trip', methods=['GET', 'POST'])
def business_trip():
    if request.method == 'POST':
        trip = Trip(
            destination=request.form['destination'],
            start_date=datetime.strptime(request.form['start_date'], '%Y-%m-%d'),
            end_date=datetime.strptime(request.form['end_date'], '%Y-%m-%d'),
            purpose=request.form['purpose'],
            participants=request.form['participants']
        )
        db.session.add(trip)
        db.session.commit()
        return redirect(url_for('business_trip'))

    query = Trip.query
    participant_filter = request.args.get('participant')
    if participant_filter:
        query = query.filter(Trip.participants.contains(participant_filter))
    trips = query.order_by(Trip.start_date).all()
    return render_template('business_trip.html', trips=trips)

@app.route('/remove_trip/<int:trip_id>', methods=['POST'])
def remove_trip(trip_id):
    trip = Trip.query.get_or_404(trip_id)
    db.session.delete(trip)
    db.session.commit()
    return redirect(url_for('business_trip'))

@app.route('/export_trips')
def export_trips():
    trips = Trip.query.all()
    df = pd.DataFrame([{
        'Destination': t.destination,
        'Start Date': t.start_date.strftime('%Y-%m-%d'),
        'End Date': t.end_date.strftime('%Y-%m-%d'),
        'Purpose': t.purpose,
        'Participants': t.participants
    } for t in trips])
    output = io.BytesIO()
    df.to_excel(output, index=False)
    output.seek(0)
    return send_file(output, download_name='business_trips.xlsx', as_attachment=True)


@app.route('/add_trip', methods=['POST'])
def add_trip():
    destination = request.form['destination']
    start_date = request.form['start_date']
    end_date = request.form['end_date']
    purpose = request.form['purpose']
    fleet = request.form['fleet']
    
    # Convert the start_date and end_date from string to datetime
    start_date_dt = datetime.strptime(start_date, '%Y-%m-%d')
    end_date_dt = datetime.strptime(end_date, '%Y-%m-%d')
    
    trip = {
        'destination': destination,
        'start_date': start_date_dt,
        'end_date': end_date_dt,
        'purpose': purpose
    }
    
    # Add trip to the appropriate fleet
    if fleet not in trips_by_fleet:
        trips_by_fleet[fleet] = []
    trips_by_fleet[fleet].append(trip)

    # Redirect back to the trips page after adding the trip
    return redirect(url_for('trips'))

@app.route('/mail-templates', endpoint='mailTemplates2')
def mail_templates():
    return render_template('mailTemplates2.html')

@app.route('/Directories', endpoint='Directories')
def Directories():
    return render_template('Directories.html')

@app.route('/vesselist2', endpoint='vesselist2')
def vesselist():
    return render_template('vesselist2.html')

@app.route('/troubleshooting', endpoint='troubleshooting')
def troubleshooting():
    return render_template('troubleshooting.html')

@app.route('/send_email', methods=['POST'])
def send_email():
    recipient_email = request.form['recipient_email']
    subject = "REMINDER: EMAIL AWARENESS (CYBERSECURITY RELATED)"
    
    msg = Message(subject, recipients=[recipient_email])
    msg.body = render_template('email_template.txt')
    msg.html = render_template('email_template.html')

    try:
        mail.send(msg)
        flash('Email sent successfully!', 'success')
    except Exception as e:
        flash(f'Failed to send email: {str(e)}', 'error')


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']


@app.route('/network_diagram', methods=['GET', 'POST'])
def network_diagram():
    if request.method == 'POST':
        if 'pdfFiles' not in request.files:
            flash('No file part in the request')
            return redirect(request.url)

        files = request.files.getlist('pdfFiles')
        pdfLabels = request.form.get('pdfLabels', '')
        if not pdfLabels:
            flash('No labels provided')
            return redirect(request.url)

        labels = [label.strip() for label in pdfLabels.split(',') if label.strip()]
        try:
            for i, file in enumerate(files):
                if file and '.' in file.filename and file.filename.rsplit('.', 1)[1].lower() == 'pdf':
                    original_filename = secure_filename(file.filename)
                    unique_filename = f"{uuid.uuid4().hex}_{original_filename}"
                    file.save(os.path.join(app.config['UPLOAD_FOLDER'], unique_filename))
                else:
                    flash(f'File {file.filename} has invalid extension and was skipped.')
            flash('Files successfully uploaded')
        except Exception as e:
            flash(f'An error occurred while uploading files: {str(e)}')
        return redirect(url_for('network_diagram'))
    return render_template('network_diagram.html')


@app.route('/list_files', methods=['GET'])
def list_files():
    files = os.listdir(app.config['UPLOAD_FOLDER'])
    return render_template('list_files.html', files=files)


history = []

@app.route('/finalbriefing2', methods=['GET', 'POST'])
def finalbriefing2():
    name = ''
    date = ''
    vesselName = ''
    personInCharge = ''
    status = ''
    submitted = False

    if request.method == 'POST':
        name = request.form.get('name', '')
        date = request.form.get('date', '')
        vesselName = request.form.get('vesselName', '')
        personInCharge = request.form.get('personInCharge', '')
        status = request.form.get('status', '')
        submitted = True
        
        # Append the new entry to the history
        history.append({
            'name': name,
            'date': date,
            'vesselName': vesselName,
            'personInCharge': personInCharge,
            'status': status
        })

    # Always return a rendered template
    return render_template('finalbriefing2.html',
                           name=name,
                           date=date,
                           vesselName=vesselName,
                           personInCharge=personInCharge,
                           status=status,
                           submitted=submitted,
                           history=history)

@app.route('/add_schedule', methods=['GET', 'POST'])
def add_schedule():
    if request.method == 'POST':
        data = request.get_json()
        # process and store the schedule
        return jsonify({'status': 'success'})
    else:
        # For GET requests, return a simple page or redirect
        return render_template('add_schedule.html')  # or any valid response


@app.route('/work_reports')
def work_reports():
    return render_template('work_reports.html')

# Route to handle uploads
@app.route('/upload_work_report', methods=['POST'])
def upload_work_report():
    files = request.files.getlist('workReports')
    labels = request.form.get('workLabels', '').split(',')

    for i, file in enumerate(files):
        if file.filename.endswith('.pdf'):
            label = labels[i].strip() if i < len(labels) else f"Report_{i+1}"
            filename = f"{label.replace(' ', '_')}_{file.filename}"
            file.save(os.path.join(app.config['WORK_REPORT_FOLDER'], filename))

    return redirect(url_for('list_work_reports'))

# Route to list uploaded reports
@app.route('/list_work_reports')
def list_work_reports():
    files = os.listdir(app.config['WORK_REPORT_FOLDER'])
    return render_template('list_work_reports.html', files=files)

# Optional: serve the uploaded PDFs
@app.route('/work_reports/<filename>')
def serve_work_report(filename):
    return send_from_directory(app.config['WORK_REPORT_FOLDER'], filename)



@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
