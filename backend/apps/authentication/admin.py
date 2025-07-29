from django.contrib import admin
from .models import User,Address # Import your models here
from rest_framework.authtoken.models import Token
# Register your models here.
admin.site.register(User)  # Register your models here if any
admin.site.register(Address)  # Register the Token model from DRF
admin.site.register(Token)

admin.site.site_header = "Authentication Admin"
admin.site.site_title = "Authentication Admin Portal"
admin.site.index_title = "Welcome to the Authentication Admin Portal"