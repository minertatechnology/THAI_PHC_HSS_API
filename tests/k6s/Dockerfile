FROM grafana/k6:latest

WORKDIR /scripts

COPY scripts/ .
COPY lib/ /lib/

ENTRYPOINT ["k6"]
