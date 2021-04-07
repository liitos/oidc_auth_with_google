from flask_login import UserMixin

class User(UserMixin):
    def __init__(self, id_, given_name, family_name, email, picture, email_verified, locale):
        self.id = id_
        self.given_name = given_name
        self.family_name = family_name
        self.email = email
        self.picture = picture
        self.email_verified = email_verified
        self.locale = locale
        