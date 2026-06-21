function helper(x) {
  return x * 2;
}

function validateUser(name, password) {
  if (!name) return false;
  if (password.length < 8) return false;
  return helper(password.length) > 0;
}

class Account {
  constructor(owner) {
    this.owner = owner;
  }
  login(password) {
    return validateUser(this.owner, password);
  }
}
