FROM python:3.8.5

RUN mkdir -p /usr/scr/gateway/
WORKDIR /usr/scr/gateway/

COPY gateway/ /usr/scr/gateway/
RUN pip install --no-cache-dir -r requirements.txt

EXPOSE 8080 47808 47809 47810 47811 47812 47813 47814 47815 47816 47817 47818 47819 47820 47821 47822 47823

CMD ["python", "run.py"]