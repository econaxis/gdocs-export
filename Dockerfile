FROM python:3.8.2-slim AS compile

ENV DOCKERENV 1


COPY ./installation ./installation

RUN ls -a && echo "\n\n" && ls installation

RUN chmod +x installation/install.sh && \
    ./installation/install.sh && \
    echo "Installation done!"

FROM python:3.8.2-slim AS run
COPY --from=compile /root/.local /root/.local
ENV PATH=/root/.local/bin:$PATH

COPY . .


ENTRYPOINT ["./boot.sh"]
