# Bank Account Microservice 🏦

A high-performance, asynchronous microservice for managing bank account operations. Built with **Python 3.12** and **FastAPI**, following modern software engineering practices and **Clean Architecture** principles.

## 🚀 Project Overview

This project implements a backend engine for banking operations including account creation, balance management (deposits/withdrawals), and advanced searching. It is designed to be cloud-ready, containerized, and fully testable.

### 🛠 Technology Stack

* **Language:** Python 3.12+ (Modern Typing features)
* **Framework:** FastAPI (Asynchronous Web Framework)
* **ORM:** SQLModel (Combines SQLAlchemy + Pydantic)
* **Database:** SQLite (Async via `aiosqlite` for Dev/Test)
* **Testing:** Pytest, Pytest-Asyncio, Httpx
* **Dependency Manager:** uv (Blazing fast Python package installer)
* **Containerization:** Docker & Docker Compose

---

## 🏗 Architecture & Design Pattern

The project follows a **Layered Architecture** (Separation of Concerns) to ensure maintainability and scalability.

### 1. The Layers
* **📂 Routers (`/api`):** Handles HTTP requests and responses. No business logic here.
* **⚙️ Services (`/services`):** Contains business rules (e.g., preventing overdrafts, calculating balances).
* **💾 Repositories (`/repositories`):** Abstracts direct database access. Handles raw SQL/ORM queries.
* **📦 Models (`/models`):** Defines the data schema and domain entities (`Compte`, `CompteType`).

### 2. Project Structure
```text
bank-account-service/
├── src/
│   ├── api/             # API Routes
│   ├── core/            # Config & Database Setup
│   ├── models/          # Database Tables & Pydantic Schemas
│   ├── repositories/    # CRUD Operations
│   └── services/        # Business Logic
├── tests/               # Test Suite
├── docker-compose.yml   # Container Orchestration
├── Dockerfile           # Multi-stage Build
├── pyproject.toml       # Dependencies
└── README.md
```

---

## ✅ Features & Endpoints

| Method | Endpoint | Function |
| :--- | :--- | :--- |
| `POST` | `/api/v1/comptes/` | Create a new Account |
| `GET` | `/api/v1/comptes/` | List Accounts (Supports Projections) |
| `GET` | `/api/v1/comptes/search` | Search by Type or Balance Range |
| `POST` | `/api/v1/comptes/{id}/deposit` | Credit Account |
| `POST` | `/api/v1/comptes/{id}/withdraw` | Debit Account (Safe) |

---

## 📸 Documentation & Validation

### 1. Interactive API Documentation (Swagger UI)
The project includes auto-generated documentation via OpenAPI specifications.

![API Documentation Screenshot](./screenshots/swagger.png)
*(Screenshot of http://localhost:8000/docs)*

### 2. Testing Suite
The application is validated by a rigorous test suite covering all endpoints and business logic.

* **Framework:** Pytest
* **Coverage:** 100% Pass Rate (32/32 Tests)

![Tests Passing Screenshot](screenshots/tests.png)
*(Screenshot of terminal running `pytest`)*

---

## ⚡ How to Run

### Using Docker (Standard)
This project is containerized to ensure a consistent environment across development and production.

```bash
# 1. Build and Start the Containers
docker-compose up --build -d

# 2. Access the API Documentation
# Open your browser to: http://localhost:8000/docs
```