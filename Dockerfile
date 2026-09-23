FROM python:3.14.4-slim

ENV PYTHONDONTWRITEBYTECODE=1

WORKDIR /mnt/delivery

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

CMD ["bash"]
