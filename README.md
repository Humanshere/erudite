# University Management System

## Project Overview
The University Management System is a comprehensive platform designed to streamline academic operations, encompassing role-based access control, academic structuring, and attendance tracking. It provides a cohesive environment where administrators, faculty, and students can interact with and manage academic data efficiently. The system is designed to support both web and mobile interfaces.

## Tech Stack Used
### Backend
- **Framework:** Django, Django REST Framework
- **Database:** MariaDB / MySQL
- **Authentication:** JWT (JSON Web Tokens)
- **Language:** Python 3

### Frontend (Web)
- **Framework:** React
- **Build Tool:** Vite
- **Language:** JavaScript (JSX)

### Mobile Application
- **Platform:** Android
- **Language:** Kotlin
- **Build Tool:** Gradle

## Features and Functionality
- **Role-Based Authentication:** Dedicated portals and access levels tailored for Administrators, Faculty, and Students.
- **Academic Structure Management:** Administration interfaces for managing Departments, Semesters, Courses, and Enrollments.
- **Attendance Management System:**
  - Bulk attendance marking capabilities for faculty.
  - QR Code or location-based attendance sessions.
  - Individual student attendance tracking and reporting.
  - Facial recognition and selfie benchmarks for attendance validation.
- **Integrated Chatbot:** Support module built into the platform to handle general queries and assistance.
- **Profile Management:** Profile-aware dashboard rendering specific insights according to the logged-in user role.
- **Cross-Platform Accessibility:** REST API infrastructure enabling interaction across web frontends and Android mobile applications.

## Steps to Run the Project

### Database Requirements
1. Ensure MariaDB or MySQL is installed and running on your local machine.
2. Create a writable database (e.g., `test` or `ums_db`).

### Backend Setup
1. Open a terminal and navigate to the backend directory:
   ```bash
   cd backend
   ```
2. Create and activate a Python virtual environment:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```
3. Install backend dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Configure environment variables:
   - Create a `.env` file from the `.env.example` file (if available) or set the required variables.
   - Example Database configuration for a local socket-based setup:
     ```
     MYSQL_HOST=localhost
     MYSQL_PORT=
     MYSQL_DB=test
     MYSQL_USER=<your_user>
     MYSQL_PASSWORD=<your_password_or_empty>
     ```
5. Apply database migrations:
   ```bash
   python manage.py makemigrations
   python manage.py migrate
   ```
6. Create an application administrator account:
   ```bash
   python manage.py createsuperuser
   ```
7. Start the backend server:
   ```bash
   python manage.py runserver
   ```
   *Note: For accessibility from an Android emulator or mobile device, bind to `0.0.0.0:8000` (`DJANGO_RUNSERVER_ADDR=0.0.0.0:8000`) and add the machine's IP to `DJANGO_ALLOWED_HOSTS` in your configuration.*

   **Backend API URL:** `http://127.0.0.1:8000`

### Frontend Setup
1. Open a new terminal window and navigate to the frontend directory:
   ```bash
   cd frontend
   ```
2. Install node dependencies:
   ```bash
   npm install
   ```
3. Start the local frontend development server:
   ```bash
   npm run dev
   ```

   **Frontend Web Application URL:** `http://127.0.0.1:5173`

### Android Mobile Setup
1. Open the `android/` directory using Android Studio.
2. Allow Gradle to synchronize and download necessary dependencies.
3. Configure the backend API base URL in your Android app configuration to direct to your local machine's IP address (not `localhost` nor `127.0.0.1`).
4. Build and run the application on an emulator or physical device.

## Seeded Demo Data (If configured locally)
- Administrator: `admin@ums.local` (Password: `Admin@12345`)
- Faculty: `faculty@ums.local` (Password: `Faculty@12345`)
- Student: `student@ums.local` (Password: `Student@12345`)
