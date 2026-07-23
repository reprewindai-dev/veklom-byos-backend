```markdown
# veklom-byos-backend Development Patterns

> Auto-generated skill from repository analysis

## Overview
This skill provides guidance on contributing to the `veklom-byos-backend` Python codebase. It covers coding conventions, commit patterns, dependency update workflows, and testing strategies observed in the repository. Use this as a reference for maintaining consistency and leveraging automation in your development process.

## Coding Conventions

### File Naming
- Use **camelCase** for file names.
  - Example: `userProfile.py`, `dataFetcher.py`

### Import Style
- Use **relative imports** within the package.
  - Example:
    ```python
    from .utils import parseConfig
    from ..models import User
    ```

### Export Style
- Use **named exports** (i.e., explicitly define what is exported).
  - Example:
    ```python
    __all__ = ['UserService', 'AuthManager']
    ```

### Commit Patterns
- Commit messages are of mixed types, often prefixed with `build`.
- Example commit message:
  ```
  build: update dependencies for user and auth modules
  ```

## Workflows

### Dependency Update Across Multiple Packages

**Trigger:** When dependencies need to be updated across several packages or applications in the monorepo.

**Command:** `/update-dependencies`

1. Identify outdated dependencies in each package.
2. Update the version numbers in `package.json` files.
3. Regenerate `package-lock.json` files to reflect new dependency versions.
4. Commit all changed `package.json` and `package-lock.json` files together.

**Files Involved:**
- `**/package.json`
- `**/package-lock.json`

**Frequency:** Approximately twice per month.

**Example:**
```bash
# Run the update command (if automated)
$ /update-dependencies

# Or manually:
$ cd package1
$ npm update
$ cd ../package2
$ npm update
$ git add package1/package.json package1/package-lock.json package2/package.json package2/package-lock.json
$ git commit -m "build: update dependencies for all packages"
```

## Testing Patterns

- **Framework:** Unknown (not explicitly detected).
- **Test File Pattern:** Files named with `*.test.*` (e.g., `userService.test.py`).
- **Typical Test Example:**
  ```python
  # userService.test.py
  import unittest
  from .userService import getUser

  class TestUserService(unittest.TestCase):
      def test_get_user(self):
          user = getUser(1)
          self.assertEqual(user.id, 1)
  ```

## Commands

| Command              | Purpose                                                         |
|----------------------|-----------------------------------------------------------------|
| /update-dependencies | Update dependencies across all packages in the monorepo         |
```
