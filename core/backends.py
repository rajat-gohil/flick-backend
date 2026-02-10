from django.contrib.auth.backends import ModelBackend
from django.contrib.auth import get_user_model

User = get_user_model()

class EmailOrUsernameModelBackend(ModelBackend):
    """
    Custom authentication backend that allows login with either email or username.
    """
    
    def authenticate(self, request, username=None, password=None, **kwargs):
        if username is None:
            username = kwargs.get(User.USERNAME_FIELD)
        
        if username is None or password is None:
            return None
            
        try:
            # Try to find user by username first
            user = User.objects.get(username=username)
            print(f"Found user by username: {username}")
        except User.DoesNotExist:
            try:
                # If not found, try to find by email
                user = User.objects.get(email=username)
                print(f"Found user by email: {username}")
            except User.DoesNotExist:
                print(f"No user found with username/email: {username}")
                return None
        
        if user.check_password(password) and self.user_can_authenticate(user):
            print(f"Authentication successful for user: {user.username}")
            return user
            
        print(f"Authentication failed for user: {username}")
        return None
