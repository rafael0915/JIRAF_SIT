from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime



db = SQLAlchemy()

class User(db.Model, UserMixin):  # Inherit from UserMixin
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(150), nullable=False)

    # Implementing the required properties
    def is_active(self):
        return True  # You can implement your own logic here

    def is_authenticated(self):
        return True  # This is handled by UserMixin

    def is_anonymous(self):
        return False  # This is handled by UserMixin

    def get_id(self):
        return str(self.id)  # Return the user ID as a string

class Project(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    # Define the relationship to issues
    issues = db.relationship('Issue', backref='project', lazy=True)

class Issue(db.Model):
    __tablename__ = 'issue'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(150), nullable=False)
    description = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(50), default='To Do')
    project_id = db.Column(db.Integer, db.ForeignKey('project.id'), nullable=False)
    assigned_to_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)

class VesselSchedule(db.Model):
    __tablename__ = 'VesselSchedule'
    
    id = db.Column(db.Integer, primary_key=True)
    destination = db.Column(db.String(150), nullable=False)
    start_date = db.Column(db.DateTime, nullable=False)
    end_date = db.Column(db.DateTime, nullable=False)
    purpose = db.Column(db.Text, nullable=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)  # Assuming you have a User model

    def __repr__(self):
        return f'<VesselSchedule {self.destination}>'
    
class BusinessTrip(db.Model):
    __tablename__ = 'BusinessTrip'
    
    id = db.Column(db.Integer, primary_key=True)
    destination = db.Column(db.String(150), nullable=False)
    start_date = db.Column(db.DateTime, nullable=False)
    end_date = db.Column(db.DateTime, nullable=False)
    purpose = db.Column(db.Text, nullable=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)  # Assuming you have a User model

    def __repr__(self):
        return f'<BusinessTrip {self.destination}>'