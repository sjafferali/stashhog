# Task 02: GitHub Actions CI/CD Setup

## Current State
- Basic project structure exists with backend and frontend directories
- No CI/CD pipeline configured
- No automated testing or linting

## Objective
Set up comprehensive GitHub Actions workflows for continuous integration, including linting, type checking, testing, and Docker image building.

## Requirements

### Workflow Files Structure
Create the following GitHub Actions workflow files:

```
.github/
├── workflows/
│   ├── ci.yml          # Main CI workflow
│   ├── backend.yml     # Backend-specific checks
│   ├── frontend.yml    # Frontend-specific checks
│   └── docker.yml      # Docker build workflow
└── dependabot.yml      # Dependency updates
```

### Main CI Workflow (.github/workflows/ci.yml)
This workflow should:
1. Trigger on:
   - Push to main branch
   - Pull requests
   - Manual dispatch

2. Use a matrix strategy to run jobs in parallel

3. Call reusable workflows for backend and frontend

4. Only build Docker image if all checks pass

### Backend Workflow (.github/workflows/backend.yml)
Should include:

1. **Python Setup**
   - Use Python 3.9, 3.10, 3.11 matrix
   - Cache pip dependencies

2. **Linting and Formatting**
   - Run `ruff check` for linting
   - Run `ruff format --check` for formatting
   - Run `mypy` for type checking

3. **Testing**
   - Run `pytest` with coverage
   - Generate coverage report
   - Upload coverage to artifact

4. **Security Checks**
   - Run `bandit` for security issues
   - Run `safety check` for vulnerable dependencies

### Frontend Workflow (.github/workflows/frontend.yml)
Should include:

1. **Node Setup**
   - Use Node 18.x and 20.x matrix
   - Cache npm dependencies

2. **Linting and Formatting**
   - Run ESLint
   - Check Prettier formatting
   - Run TypeScript compiler checks

3. **Testing**
   - Run Jest tests
   - Generate coverage report
   - Upload coverage to artifact

4. **Build Check**
   - Run production build
   - Check bundle size

### Docker Workflow (.github/workflows/docker.yml)
Should include:

1. **Conditional Execution**
   - Only run on main branch
   - Only if CI passes

2. **Multi-stage Build**
   - Build frontend
   - Build backend
   - Create final image

3. **Image Tagging**
   - Tag with commit SHA
   - Tag with branch name
   - Tag as latest for main branch

4. **Registry Push** (optional)
   - Push to GitHub Container Registry
   - Push to Docker Hub

### Additional Configuration Files

1. **backend/.ruff.toml**
   ```toml
   line-length = 88
   target-version = "py39"
   
   [lint]
   select = ["E", "F", "I", "N", "UP", "S", "B", "A", "C4", "T20"]
   ignore = ["E501"]
   
   [format]
   quote-style = "double"
   ```

2. **backend/pyproject.toml** (for mypy)
   ```toml
   [tool.mypy]
   python_version = "3.9"
   warn_return_any = true
   warn_unused_configs = true
   disallow_untyped_defs = true
   ```

3. **backend/pytest.ini**
   ```ini
   [pytest]
   testpaths = tests
   python_files = test_*.py
   python_classes = Test*
   python_functions = test_*
   addopts = --cov=app --cov-report=html --cov-report=term
   ```

4. **frontend/.eslintrc.json**
   ```json
   {
     "extends": [
       "eslint:recommended",
       "plugin:react/recommended",
       "plugin:@typescript-eslint/recommended",
       "prettier"
     ],
     "rules": {
       "react/react-in-jsx-scope": "off"
     }
   }
   ```

5. **frontend/.prettierrc**
   ```json
   {
     "semi": true,
     "trailingComma": "es5",
     "singleQuote": true,
     "printWidth": 80,
     "tabWidth": 2
   }
   ```

### Dependencies to Add

Backend (add to requirements-dev.txt):
- pytest==7.4.3
- pytest-cov==4.1.0
- pytest-asyncio==0.21.1
- ruff==0.1.7
- mypy==1.7.1
- bandit==1.7.5
- safety==3.0.1

Frontend (add to package.json devDependencies):
- @types/jest
- @testing-library/react
- @testing-library/jest-dom
- eslint
- eslint-config-prettier
- eslint-plugin-react
- @typescript-eslint/eslint-plugin
- prettier
- jest
- ts-jest

## Expected Outcome

After completing this task:
- All pushes and PRs trigger automated checks
- Code quality is enforced through linting
- Type safety is verified
- Tests run automatically
- Docker images build on successful CI
- Developers get immediate feedback on code quality

## Integration Points
- Workflows integrate with GitHub PR checks
- Status badges can be added to README
- Failed checks block PR merging
- Artifacts are available for debugging

## Success Criteria
1. All workflow files are valid YAML
2. Workflows trigger on appropriate events
3. Linting catches style issues
4. Type checking catches type errors
5. Tests run and generate coverage
6. Docker build succeeds
7. All checks pass on a clean codebase
8. Workflows complete in under 5 minutes