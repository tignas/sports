from wtforms import PasswordField
from wtforms import RadioField
from wtforms import TextField
from wtforms import validators
import apex
from apex.models import (AuthGroup,
                         AuthID,
                         AuthUser,
                         DBSession)
                         
from pyramid.i18n import TranslationString as _


from apex.lib.form import ExtendedForm
from bizarro.models import DBSession

class Register(ExtendedForm):
    """ Registration Form
    """
    username = TextField(_('Username'), [validators.Required(),
                         validators.Length(min=4, max=25)])
    display_name = TextField(_('Display'), [validators.Optional()])
    password = PasswordField(_('Password'), [validators.Required(),
                             validators.EqualTo('password2', \
                             message=_('Passwords must match'))])
    password2 = PasswordField(_('Repeat Password'), [validators.Required()])
    email = TextField(_('Email Address'), [validators.Optional(),
                      validators.Email()])

    def validate_login(form, field):
        if AuthUser.get_by_login(field.data) is not None:
            raise validators.ValidationError(_('Sorry that username already exists.'))

    def create_user(self):
        group = self.request.registry.settings.get('apex.default_user_group',
                                                   None)
        if not self.data['display_name']:
            self.data['display_name'] = self.data['username']
        user = apex.lib.libapex.create_user(**self.data)
        return user

    def save(self):
        new_user = self.create_user()
        self.after_signup(user=new_user)

        return new_user

    def after_signup(self, **kwargs):
        """ Function to be overloaded and called after form submission
        to allow you the ability to save additional form data or perform
        extra actions after the form submission.
        """
        
        #profile = ForeignKeyProfile(user_id=user.id)
