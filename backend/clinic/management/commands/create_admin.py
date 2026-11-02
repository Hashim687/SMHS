from getpass import getpass

from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError

from accounts.models import User


class Command(BaseCommand):
    help = "Create an administrator, or reset the password and two-factor setup of an existing user."

    def add_arguments(self, p):
        p.add_argument("username")

    def handle(self, *a, **o):
        name = o["username"].strip()
        if not name:
            raise CommandError("username is empty")
        user = User.objects.filter(username=name).first()
        if user:
            self.stdout.write(f"User '{name}' already exists.")
            if input("Reset its password and two-factor setup and make it an admin? (y/n): ").strip().lower() != "y":
                self.stdout.write("Nothing changed.")
                return
        while True:
            pw = getpass("Password: ")
            if pw != getpass("Repeat: "):
                self.stdout.write(self.style.ERROR("Passwords do not match, try again."))
                continue
            try:
                validate_password(pw)
            except ValidationError as e:
                self.stdout.write(self.style.ERROR("Weak password: " + " ".join(e.messages)))
                continue
            break
        if user:
            user.set_password(pw)
            user.role = "admin"
            user.is_active = True
            user.totp_secret, user.totp_enabled = "", False
            user.failed_attempts, user.locked_until = 0, None
            user.save()
            self.stdout.write(self.style.SUCCESS("admin updated; two-factor setup is required at next login"))
        else:
            User.objects.create_user(name, password=pw, role="admin")
            self.stdout.write(self.style.SUCCESS("admin created; two-factor setup is required at first login"))
