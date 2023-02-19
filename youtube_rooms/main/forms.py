from flask_wtf import FlaskForm
from wtforms.fields import StringField, SubmitField
from wtforms.validators import DataRequired,Length,ValidationError
import re





        
        
        
class my_form(FlaskForm):
  
    name = StringField('Name', validators=[DataRequired(),
        Length(min=4, max=20)])
    submit = SubmitField('Submit')
    
    def __init__(self, myParam: str, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.myParam = myParam
   
        
    def validate_name(self,form):
        regex = re.compile(r'[^A-Za-z0-9]')
        if regex.search(self.name.data):
            raise ValidationError(self.myParam+" can not contain spaces or special characters.")
        if self.name.data.lower().strip() == "room":
            raise ValidationError("Room is a reserved word.")



