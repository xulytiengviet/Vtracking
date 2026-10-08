FROM python:3.12-slim
WORKDIR /app
RUN useradd --uid 10001 --create-home vtracking && mkdir /data && chown vtracking:vtracking /data
COPY --chown=vtracking:vtracking domain.py server.py ./
COPY --chown=vtracking:vtracking static ./static
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 BIND=0.0.0.0 PORT=8090 DATABASE_PATH=/data/logistics.sqlite3
USER vtracking
EXPOSE 8090
CMD ["python", "server.py"]
