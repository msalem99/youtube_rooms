from flask_wtf import FlaskForm
from wtforms.fields import StringField, SubmitField
from wtforms.validators import DataRequired


class create_room(FlaskForm):
    """Accepts a nickname and a room."""
    name = StringField('Name', validators=[DataRequired()])
 #  room = StringField('Room', validators=[DataRequired()])
    submit = SubmitField('Enter room')