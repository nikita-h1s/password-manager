from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, BooleanField
from wtforms.validators import DataRequired, Email, Length, EqualTo


class LoginForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    master_password = PasswordField('Password', validators=[DataRequired()])
    remember_me = BooleanField('Remember Me')
    totp_code = StringField('2FA Code')
    submit = SubmitField('Log In')


class RegistrationForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    username = StringField('Username', validators=[DataRequired(),
                                                   Length(min=2, max=50,
                                                          message="Username length must be "
                                                                  "between 2 and 50 characters")])
    master_password = PasswordField('Password', validators=[DataRequired(), Length(min=6)])
    confirm_password = PasswordField('Confirm Password',
                                     validators=[DataRequired(),
                                                 EqualTo('master_password',
                                                         message="Passwords must match")])
    submit = SubmitField('Register')
