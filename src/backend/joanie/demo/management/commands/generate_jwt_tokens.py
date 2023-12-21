"""Management command to generate user JWT tokens"""
import json
from datetime import datetime, timedelta

from django.core.management.base import BaseCommand

from joanie.core.models import User
from joanie.core.utils.jwt_tokens import generate_jwt_token_from_user


class Command(BaseCommand):
    """Generate user JWT tokens"""

    help = "Display existing tokens"

    def handle(self, *args, **options):
        """Generate user tokens"""
        self.stdout.write("\nTokens:")
        expires_at = datetime.utcnow() + timedelta(days=365)
        tokens = {}
        for user in User.objects.all():
            token = generate_jwt_token_from_user(user, expires_at=expires_at)
            tokens[user.username] = str(token)
            self.stdout.write(f"jwt: {token}")
            for key, value in token.payload.items():
                self.stdout.write(f"  {key}: {value}")
            self.stdout.write("")

        self.stdout.write("Copy the following into your dummy.ts file in Richie:")
        self.stdout.write(json.dumps(tokens, indent=2))
