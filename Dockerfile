FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .

# DB_PATH must point here, and /data must be a mounted volume — otherwise
# every user loses their saved Pollinations key on redeploy.
ENV DB_PATH=/data/bot.db
VOLUME /data

CMD ["python", "bot.py"]
