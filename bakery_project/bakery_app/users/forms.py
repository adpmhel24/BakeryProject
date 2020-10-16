from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed
from flask_login import current_user
from wtforms import StringField, PasswordField, SubmitField, BooleanField, TextAreaField, DateField, SelectField
from wtforms.validators import DataRequired, Length, Email, EqualTo, ValidationError, Optional
from bakery_app.users.models import User
from bakery_app import bcrypt

class UserAddForm(FlaskForm):
    fullname = StringField('Full Name', validators=[DataRequired(),
                            Length(max=100)])
    username = StringField('Username', validators=[DataRequired(),
                            Length(min=2, max=30)])
    password = PasswordField('Password', validators=[DataRequired(), Length(min=6, max=32)])
    confirm_password = PasswordField('Confirm Password', validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Sign Up')

    def validate_username(self, username):
        user = User.query.filter_by(username=username.data).first()
        if user:
            raise ValidationError('Username is already exists. Pleaser choose different one.')
    


class LoginForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    remember = BooleanField('Remember Me')
    submit = SubmitField('Login')

class UpdateAccountForm(FlaskForm):
    fullname = StringField('Full Name', validators=[DataRequired(),
                            Length(max=100)])
    username = StringField('Username', validators=[DataRequired(),
                            Length(min=2, max=30)])
    picture = FileField('Update Profile Picture', validators=[FileAllowed(['jpg', 'png'])])
    submit = SubmitField('Update')

    def validate_username(self, username):
        if username.data != current_user.username:
            user = User.query.filter_by(username=username.data).first()
            if user:
                raise ValidationError("This username is already taken.")
    

class ChangePasswordForm(FlaskForm):
    old_password = PasswordField('Old Password', validators=[DataRequired()])
    password = PasswordField('New Password', validators=[DataRequired(), Length(min=6, max=32)])
    confirm_password = PasswordField('Confirm Password', validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Submit')

    def validate_old_password(self, old_password):
        if not bcrypt.check_password_hash(current_user.password, old_password.data):
            raise ValidationError("Incorrect Old Password!")


class TaskSearchForm(FlaskForm):
    # choices = [(-1, 'All'),
    #             (0, 'In Process'),
    #             (1, 'Completed')]
    # select = SelectField('Status', choices=choices)
    search = StringField('')