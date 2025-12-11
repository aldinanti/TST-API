# Tugas Besar II3160 Teknologi Sistem Terintegrasi

Leticia Aldina Trulykinanti/18223108
Pada tugas besar ini, saya mengimplementasikan "EV Charging Management API", API ini merupakan sistem backend berbasis FastAPI yang mengelola proses pengisian daya kendaraan listrik yang mencakup:
1. User & Vehicle Management
2. Station & Asset Management
3. Charging Session Management
4. Billing & Invoice Management

API ini dirancang menggunakan pendekatan DDD dengan arsitektur context-based agar mudah dikembangkan serta terintegrasi dengan aplikasi mobile/web.

# Tech Stack
1. FastAPI
2. SQLModel (SQLAlchemy + Pydantic)
3. SQLite / PostgreSQL (opsional)
4. Uvicorn
5. JWT Authentication (Autentikasi)


# How to Run

1. Buat virtual environment

python -m venv myenv
source myenv/bin/activate   # Mac / Linux
myenv\Scripts\activate      # Windows


2. Install dependencies

pip install -r requirements.txt


3. Run server

uvicorn main:app --reload


3. Buka Swagger UI: http://localhost:8000/docs

4. Gunakan endpoint Register & Login untuk mendapatkan JWT Token