"""Sample module for parser tests."""
import os
from collections import OrderedDict


def helper(x):
    """Double a number."""
    return x * 2


def validate_user(name, password):
    if not name:
        return False
    if len(password) < 8:
        return False
    return helper(len(password)) > 0


class Account:
    def __init__(self, owner):
        self.owner = owner

    def login(self, password):
        return validate_user(self.owner, password)


class AdminAccount(Account):
    def login(self, password):
        return super().login(password) and self.owner == "root"
