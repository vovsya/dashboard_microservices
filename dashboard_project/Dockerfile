FROM python:3.12

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

EXPOSE 8080
CMD ["uvicorn", "dashboard_app.main:dashboard_app", "--host", "0.0.0.0", "--port", "8080"]