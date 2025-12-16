# Project Status Report: Bank Account Microservice

## 1. Project Overview

**Name:** `bank-account-service`
**Goal:** Create a robust, async microservice for managing bank accounts using modern Python standards.
**Tech Stack:**

- **Language:** Python 3.12+
- **Framework:** FastAPI
- **ORM:** SQLModel (SQLAlchemy + Pydantic)
- **Database:** SQLite (Async via `aiosqlite`) for dev/test
- **Testing:** Pytest, Pytest-Asyncio, Httpx
- **DevOps:** Docker, Docker Compose, uv
- **Cloud Infrastructure:** Azure VM (Ubuntu)
- **CI/CD:** GitHub Actions (In Progress)

---

## 2. Achievements & Implementation Details

### A. Core Architecture

- **Models:** Defined the `Compte` entity with business constraints (enums for `COURANT`/`EPARGNE`).
- **Repository Layer:** Implemented `CompteRepository` to abstract raw database operations.
- **Service Layer:** Implemented `CompteService` to handle business logic (e.g., preventing negative balances).
- **Router Layer:** Implemented `CompteRouter` to handle HTTP requests.

### B. API Endpoints Implemented

| Method   | Endpoint                        | Description                                                                                                     |
| :------- | :------------------------------ | :-------------------------------------------------------------------------------------------------------------- |
| `POST`   | `/api/v1/comptes/`              | Create a new account.                                                                                           |
| `GET`    | `/api/v1/comptes/{id}`          | Retrieve a specific account by ID.                                                                              |
| `GET`    | `/api/v1/comptes/`              | List all accounts. Supports **Projections** (`full`, `summary`, `minimal`) to return different JSON structures. |
| `GET`    | `/api/v1/comptes/search`        | Filter accounts by `type` or balance range (`min_solde`, `max_solde`).                                          |
| `PUT`    | `/api/v1/comptes/{id}`          | Update account details.                                                                                         |
| `DELETE` | `/api/v1/comptes/{id}`          | Delete an account.                                                                                              |
| `POST`   | `/api/v1/comptes/{id}/deposit`  | Credit an account.                                                                                              |
| `POST`   | `/api/v1/comptes/{id}/withdraw` | Debit an account (with balance checks).                                                                         |

### C. Testing & Quality Assurance

We established a rigorous testing environment using `pytest`.

- **Infrastructure:** In-memory SQLite database using `pytest` fixtures.
- **Dependency Injection:** Overrode FastAPI's `get_session` to inject test sessions.
- **Clean Code:** Fixed all `HTTP_422_UNPROCESSABLE_ENTITY` deprecation warnings.
- **Status:** **32/32 Tests Passing** (100% success rate).

### D. DevOps & Production Readiness

- **Dockerization:** Created a multistage `Dockerfile` using `uv` for fast, cached builds.
- **Orchestration:** Implemented `docker-compose.yml` with persistent volume mapping (`./data`) and async database configuration (`sqlite+aiosqlite`).

### E. Manual Deployment to Azure (Proof of Concept)

Successfully performed manual deployment to validate infrastructure before automation:

#### Infrastructure Setup
- **Server Provisioned:** Ubuntu VM on Azure with secured access.
- **Networking Configuration:** Configured Azure Network Security Group (NSG/Firewall) to open port 8000 for external access.
- **Runtime Environment:** Installed Docker and Docker Compose on the server.

#### Manual Verification
- Manually connected to the server via SSH.
- Pulled the application code from the repository.
- Started the application using Docker Compose.
- **Validation:** Successfully tested the deployment using `curl` from local machine to Azure public IP.

**Why This Step Was Critical:**
This manual deployment proved that the infrastructure, networking, and application configuration are correct. If the CI/CD pipeline fails later, we know the issue is in the automation script, not the environment or application.

---

## 3. Current State

The application is functionally complete, fully containerized, and manually deployed to Azure.

1. **Core Logic:** Verified by extensive testing (32/32 tests passing).
2. **Deployment:** Runs successfully in Docker with data persistence.
3. **Code Quality:** Clean, warning-free codebase.
4. **Cloud Infrastructure:** Azure VM properly configured and validated.

---

## 4. Roadmap: CI/CD Automation with GitHub Actions

### Goal
Automate the entire deployment pipeline so that pushing code to a specific branch triggers automatic testing and deployment to Azure.

### Pipeline Architecture

The CI/CD pipeline will consist of three stages:

#### Stage 1: Continuous Integration (Quality Gate)
**Trigger:** Push to `main` branch
**Purpose:** Ensure code quality before deployment

**Actions:**
- Spin up a temporary GitHub Actions runner.
- Install Python 3.12+ and project dependencies.
- Run the full test suite (`pytest`).
- **Quality Gate:** If any test fails, stop the pipeline immediately and prevent deployment.

**Why:** This protects the production server from broken code.

#### Stage 2: Continuous Delivery (Packaging)
**Purpose:** Build the application artifact on powerful GitHub servers instead of the resource-constrained Azure VM.

**Actions:**
- Build the Docker image from the `Dockerfile`.
- Tag the image with the commit SHA and `latest`.
- Push the image to Docker Hub registry.

**Why:** Building on GitHub's infrastructure is faster and doesn't consume Azure VM resources.

#### Stage 3: Continuous Deployment (Release)
**Purpose:** Deploy the new version to the Azure VM automatically.

**Actions:**
- Connect to Azure VM via SSH (using secure GitHub Secrets for credentials).
- Pull the latest Docker image from Docker Hub.
- Stop the old container gracefully.
- Start the new container with the updated image.
- Verify the deployment (health check).

**Why:** Eliminates manual deployment steps entirely.

### Implementation Checklist

- [ ] Create `.github/workflows/deploy.yml` workflow file
- [ ] Configure GitHub Secrets:
  - `DOCKER_USERNAME` - Docker Hub username
  - `DOCKER_PASSWORD` - Docker Hub access token
  - `AZURE_SSH_KEY` - Private SSH key for Azure VM
  - `AZURE_VM_IP` - Azure VM public IP address
  - `AZURE_VM_USER` - Azure VM username
- [ ] Test the pipeline on a feature branch first
- [ ] Configure branch protection rules for `main`
- [ ] Document the deployment process for the team

### Expected Outcome

Once implemented:
1. Developer pushes code to `main` branch.
2. GitHub Actions automatically runs tests (2-3 minutes).
3. If tests pass, builds and pushes Docker image (1-2 minutes).
4. Deploys to Azure VM automatically (1 minute).
5. Application is live with zero manual intervention.

**Total Time:** ~5 minutes from code push to production deployment.

---

## 5. Future Enhancements

### After CI/CD Implementation

1. **Monitoring & Observability:**
   - Add health check endpoints.
   - Integrate with monitoring tools (Prometheus/Grafana).
   - Set up alerting for deployment failures.

2. **Advanced Deployment Strategies:**
   - Implement blue-green deployment.
   - Add rollback mechanism.
   - Configure deployment notifications (Slack/Email).

3. **Security Enhancements:**
   - Scan Docker images for vulnerabilities.
   - Implement secrets management (Azure Key Vault).
   - Add SSL/TLS certificates for HTTPS.

4. **Performance Optimization:**
   - Add test coverage reporting (`pytest-cov`).
   - Implement caching strategies.
   - Optimize Docker image size.

5. **GraphQL Integration:**
   - Implement GraphQL layer (using Strawberry).
   - Provide flexible data fetching capabilities.

---

## 6. Deployment History

| Date       | Version | Environment | Status  | Notes                           |
| :--------- | :------ | :---------- | :------ | :------------------------------ |
| 2025-12-16 | v1.0    | Azure VM    | Success | Manual deployment (Proof of Concept) |

---

## 7. Known Issues & Limitations

- No automated deployment pipeline yet (manual deployment required).
- No monitoring or alerting configured.
- Single server deployment (no redundancy).

---

## 8. Team Notes

**Current Focus:** Implementing CI/CD pipeline with GitHub Actions to automate testing and deployment.

**Success Criteria:**
- All tests pass in CI environment.
- Docker image builds successfully.
- Automated deployment to Azure VM works reliably.
- Zero-downtime deployments.
