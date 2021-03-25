FROM python:3.8.2-slim AS compile

COPY ./installation ./installation

RUN chmod +x installation/install.sh && \
    ./installation/install.sh && \
    echo "Installation done!"

FROM python:3.8.2-slim AS run
COPY --from=compile /root/.local /root/.local
COPY --from=compile /usr /usr
COPY --from=compile /var /var
COPY --from=compile /lib /lib

WORKDIR /app/
ENV PATH=/root/.local/bin:$PATH

COPY . .

ENTRYPOINT ["./boot.sh"]
