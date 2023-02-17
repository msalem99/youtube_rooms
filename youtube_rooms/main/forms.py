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
        regex = re.compile('[@_!#$%^&*()<>?/\|}{~:-]')
        if not regex.search(self.name.data) == None:
            raise ValidationError(self.myParam+" can not contain special characters.")
        if self.name.data.lower().strip() == "room":
            raise ValidationError("Room is a reserved word.")
        if " " in self.name.data.lower().strip():
            raise ValidationError("Name can not contain spaces.")
class csrf(FlaskForm):
    pass


