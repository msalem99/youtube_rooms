from flask_wtf import FlaskForm
from wtforms.fields import StringField, SubmitField
from wtforms.validators import DataRequired,Length,ValidationError
import re

class create_room(FlaskForm):
    """Accepts a nickname and a room."""
    name = StringField('Name', validators=[DataRequired(),
        Length(min=2, max=20)])
    submit = SubmitField('Enter room')
   
    def validate_name(self,form):
        regex = re.compile('[@_!#$%^&*()<>?/\|}{~:]')
        if not regex.search(self.name.data) == None:
            raise ValidationError("Room name can not contain special characters.")

