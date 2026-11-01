FROM python:3.14.4-slim

ENV PYTHONDONTWRITEBYTECODE=1

WORKDIR /mnt/delivery

RUN apt-get update && apt-get install -y --no-install-recommends build-essential git && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

CMD ["bash"]
