# ShopSphere — Django E-commerce Platform

ShopSphere is a full-stack e-commerce web application built with Python and Django. It provides a customer shopping experience, seller product management, Razorpay payment integration, order tracking, and a sales dashboard for administrators.

**Repository:** https://github.com/princebhuva1234/ShopSphere

> **Payment note:** The Razorpay integration can be tested using Razorpay Test Mode. Do not put live credentials, secret keys, passwords, or real customer data in this public repository.

## Features

### Customer experience
- Customer registration, login, and logout
- Product catalogue and product detail pages
- Product search, category and price filtering, and sorting
- Product images and stock availability indicators
- Shopping cart and quantity management
- Wishlist management, including moving items to the cart
- Checkout with saved delivery addresses
- Razorpay checkout and payment verification
- Order history, order details, and order tracking
- Downloadable order invoices
- Product reviews and ratings
- Coupon application and removal
- Order cancellation and return-related functionality

### Seller features
- Seller product management
- Product creation, editing, and activation/deactivation
- Stock management
- Seller order management with status-transition restrictions

### Administration
- Django Admin integration
- ShopSphere Sales Dashboard inside Django Admin
- Sales and revenue summaries
- Order status overview and recent orders
- Product performance and inventory information

## Technology stack

- **Backend:** Python, Django
- **Database:** PostgreSQL
- **Frontend:** Django Templates, HTML, CSS, JavaScript
- **Payments:** Razorpay
- **API toolkit:** Django REST Framework (included in the project)
- **PDF invoices:** ReportLab (if installed in the project requirements)
- **Version control:** Git and GitHub

## Project applications

The project is organized into Django apps, including:

- `accounts` — accounts and address-related functionality
- `categories` — product categories
- `products` — product catalogue and product management
- `cart` — shopping cart
- `wishlist` — saved products
- `orders` — checkout, orders, tracking, and invoices
- `payments` — payment-related functionality
- `reviews` — product reviews and ratings
- `returns` — return-related functionality
- `coupons` — coupon functionality
- `dashboard` — administrator sales dashboard

The exact app structure may evolve as the project is updated.

## Requirements

Install the following before running the project:

- Python compatible with the project's Django version
- PostgreSQL, with a database and database user configured for the project
- Git
- A Razorpay account for testing the payment flow (optional if you are only exploring non-payment features)

## Run locally on Windows

The commands below assume the project folder is `C:\PROJECT`. Change the path if you keep the project elsewhere.

### 1. Clone the repository

```powershell
git clone https://github.com/princebhuva1234/ShopSphere.git
cd ShopSphere
```

### 2. Create and activate a virtual environment

```powershell
py -m venv venv
.\venv\Scripts\Activate.ps1
```

If PowerShell blocks activation, you can run the project's Python executable directly instead, for example:

```powershell
.\venv\Scripts\python.exe --version
```

### 3. Install dependencies

```powershell
python -m pip install --upgrade pip
pip install -r requirements.txt
```

### 4. Configure environment variables

Create a local `.env` file in the project root. **Never commit this file.** Use the variable names expected by your `config/settings.py` file. The following is an example template; adjust database variable names to match your settings:

```dotenv
SECRET_KEY=replace-with-a-long-random-secret
DEBUG=True
ALLOWED_HOSTS=127.0.0.1,localhost

# Razorpay Test Mode credentials
RAZORPAY_KEY_ID=replace-with-your-test-key-id
RAZORPAY_KEY_SECRET=replace-with-your-test-key-secret

# Database values — use these only if your settings.py reads these names
DB_NAME=shopsphere
DB_USER=your_postgres_user
DB_PASSWORD=your_postgres_password
DB_HOST=localhost
DB_PORT=5432
```

Do not use production credentials in local development. Keep `DEBUG=False` and configure secure production settings when deploying.

### 5. Create/configure the PostgreSQL database

Create a PostgreSQL database and user, then configure the connection values expected by the project. If your local `settings.py` already contains database settings, make sure they match your local PostgreSQL setup.

### 6. Apply migrations

```powershell
python manage.py migrate
```

### 7. Create an administrator account

```powershell
python manage.py createsuperuser
```

Follow the prompts to create the account.

### 8. Check the project and start the server

```powershell
python manage.py check
python manage.py runserver
```

Open the website at:

- Storefront: http://127.0.0.1:8000/
- Django Admin: http://127.0.0.1:8000/admin/

After signing in with an eligible staff/superuser account, open **ShopSphere Sales Dashboard** from the Django Admin interface.

## Razorpay testing

1. Add your Razorpay **Test Mode** key ID and secret to the local `.env` file.
2. Confirm that `config/settings.py` reads those environment variables correctly.
3. Run the Django server and complete a test checkout using Razorpay's supported test credentials and test payment methods.
4. Never put the Razorpay secret in frontend JavaScript, templates, screenshots, README content, or Git commits.
5. Before going live, configure live credentials securely and review payment verification, webhook configuration, HTTPS, and production settings.

Razorpay availability and payment methods can depend on account configuration and the checkout integration.

## Security checklist

Before publishing or deploying ShopSphere:

- Keep `.env` out of Git using `.gitignore`.
- Never commit secret keys, passwords, private keys, or production database URLs.
- Check whether any secret was committed previously; `.gitignore` alone does not remove already tracked files or Git history.
- If credentials were exposed, revoke or rotate them.
- Do not publish database backups or real customer/order data.
- Use `DEBUG=False` in production.
- Configure `ALLOWED_HOSTS`, HTTPS, secure cookies, and other production security settings for the deployment environment.
- Serve uploaded media securely and use an appropriate storage solution for production.
- Use Razorpay Test Mode until the live payment flow has been reviewed.

## Useful commands

```powershell
# Check for Django configuration issues
python manage.py check

# Create migrations after model changes
python manage.py makemigrations

# Apply database migrations
python manage.py migrate

# Run the development server
python manage.py runserver

# Update the dependency list after installing/removing packages
python -m pip freeze > requirements.txt
```

## Screenshots

Add screenshots of the storefront, product details, cart, checkout, order tracking, and Django Admin Sales Dashboard here when ready. Avoid screenshots that show secrets, customer personal information, or real payment details.

## Deployment

ShopSphere is intended to be deployable to a suitable Python/Django hosting environment with PostgreSQL support. Deployment requires production environment variables, `DEBUG=False`, valid host configuration, HTTPS, static/media configuration, and securely configured Razorpay credentials. Follow the hosting provider's Django and PostgreSQL deployment documentation.

## License

No open-source license is specified in this repository yet. Unless a license is added, others do not automatically receive permission to reuse, modify, or distribute the code. Add a license only after choosing the terms you want.
