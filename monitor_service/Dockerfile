FROM golang:1.22-alpine AS build
WORKDIR /app
COPY go.mod go.sum ./
RUN go mod download
COPY . .
RUN CGO_ENABLED=0 GOOS=linux go build -o /api ./cmd/api \
 && CGO_ENABLED=0 GOOS=linux go build -o /worker ./cmd/worker \
 && CGO_ENABLED=0 GOOS=linux go build -o /dashboard_bridge ./cmd/dashboard_bridge

FROM alpine:3.20
WORKDIR /
COPY --from=build /api /api
COPY --from=build /worker /worker
COPY --from=build /dashboard_bridge /dashboard_bridge
EXPOSE 8000
CMD ["/api"]
