# Fintech Service API

![Build and Test API](https://github.com/aluyapeter/fin-doc/actions/workflows/ci.yml/badge.svg)

This is a backend API for a fintech wallet service, built with Python and FastAPI. It provides foundational services for user authentication, product management, and payment processing through Stripe.

The entire application is containerised using Docker and Docker Compose, and it includes a full suite of integration tests run with `pytest`.

## ✨ Features

* **User Authentication:** Secure user registration and login (`/register`, `/login`).
* **JWT Security:** Protected endpoints using JWT (JSON Web Tokens).
* **Payment Processing:** Integration with Stripe to create and manage payment intents (`/payments/initiate`).
* **Stripe Webhooks:** A dedicated endpoint (`/webhooks/stripe`) to handle asynchronous payment success or failure events from Stripe.
* **Product Management:** Basic endpoints to create and list products.
* **Database:** All data (users, products, payments) is stored in a PostgreSQL database.
* **100% Test Coverage:** Includes a full integration test suite using `pytest`, including mocks for external services.

## 🛠️ Tech Stack

* **Backend:** **FastAPI**
* **Database:** **PostgreSQL**
* **Payments:** **Stripe**
* **Containerisation:** **Docker** & **Docker Compose**
* **Testing:** **Pytest** with `pytest-mock`
* **Authentication:** **JWT** (via `passlib` and `python-jose`)
* **Data Validation:** **Pydantic**

## 🚀 Getting Started

Follow these instructions to get the project up and running on your local machine for development and testing.

### Prerequisites

* **Docker**
* **Docker Compose** (V2, i.e., the `docker compose` command)
* A **Stripe Account** to get your API keys.

### 1. Configuration

1.  **Clone the repository:**
    ```bash
    git clone [https://github.com/aluyapeter/fin-doc.git](https://github.com/aluyapeter/fin-doc.git)
    cd fin-doc
    ```

2.  **Create the environment file:**
    This project uses a `.env` file to manage all environment variables. Create a file named `.env` in the root of the project:
    ```bash
    touch .env
    ```

3.  **Add your environment variables:**
    Open the `.env` file and add the following variables.

    ```ini
    # --- Database Container ---
    # These are used by the Postgres container to initialize itself
    POSTGRES_USER=myuser
    POSTGRES_PASSWORD=mypassword
    POSTGRES_DB=findoc_db

    # --- Application ---
    # This is the *full* URL your FastAPI app will use to connect to the DB
    DATABASE_URL=postgresql://myuser:mypassword@db:5432/findoc_db
    
    # --- Test Database ---
    # A separate DB for your integration tests (tests run in the app container)
    TEST_DATABASE_URL=postgresql://myuser:mypassword@db:5432/findoc_test_db

    # --- Authentication ---
    # A strong, random string for signing JWTs
    JWT_SECRET_KEY=your_super_secret_key_here_a_very_long_one
    JWT_ALGORITHM=HS256

    # --- Stripe ---
    # Your Stripe secret key (e.g., sk_test_...)
    STRIPE_SECRET_KEY=sk_test_...
    # Your Stripe webhook secret for local testing (e.g., whsec_...)
    STRIPE_WEBHOOK_SECRET=whsec_...
    ```
    > **Note:** The `DATABASE_URL` uses the hostname `db` because that is the service name of the database container within the Docker network.

### 2. Running the Application

1.  **Build and run the containers:**
    ```bash
    docker compose up --build -d
    ```
    This will build the `app` image, pull the `postgres` image, and start both services in the background.

2.  **Access the API:**
    The API will be running and available at `http://localhost:8000`.

3.  **View the API Docs:**
    FastAPI's automatic documentation is available at:
    * **Swagger UI:** `http://localhost:8000/docs`
    * **ReDoc:** `http://localhost:8000/redoc`

## 🧪 Running Tests

This project is configured to run tests against a separate test database inside the Docker container.

1.  **Ensure the containers are running:**
    ```bash
    docker compose up -d
    ```

2.  **Execute the `pytest` command:**
    This command runs `pytest` *inside* the `app` container.
    ```bash
    docker compose exec app pytest -v
    ```

## 🔌 Testing Stripe Webhooks Locally

The `/webhooks/stripe` endpoint cannot be reached by Stripe when running on `localhost`. You must use a tunneling service. The **Stripe CLI** is the easiest way to do this.

1.  **Install the Stripe CLI:**
    Follow the instructions on the [official Stripe website](https://stripe.com/docs/stripe-cli).

2.  **Log in to Stripe:**
    ```bash
    stripe login
    ```

3.  **Forward webhook events to your local app:**
    ```bash
    stripe listen --forward-to http://localhost:8000/webhooks/stripe
    ```

4.  **Update your `.env` file:**
    The `stripe listen` command will output a new **webhook secret** (it will start with `whsec_...`). You **must** copy this new secret and paste it into your `.env` file for the `STRIPE_WEBOK_SECRET` variable. Restart your containers (`docker compose down && docker compose up -d`) for the change to take effect.

## API Endpoints

Here are the primary endpoints available:

### Authentication
* `POST /register` - Create a new user.
* `POST /login` - Log in a user and receive a JWT access token.

### Users
* `GET /users/me` - (Protected) Get the profile for the currently authenticated user.

### Products
* `POST /products` - Create a new product.

### Payments
* `POST /payments/initiate` - (Protected) Create a new Stripe Payment Intent for a product.
* `POST /webhooks/stripe` - Handles incoming webhook events from Stripe.

### Transactions
* `GET /transactions/{user_id}` - Get a list of transactions for a specific user.
* `POST /transactions` - (Note: This seems to be a placeholder/example) Create a manual transaction.