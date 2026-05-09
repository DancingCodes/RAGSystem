FROM golang:1.25-alpine AS builder
WORKDIR /app
COPY go.mod go.sum ./
RUN --mount=type=cache,target=/go/pkg/mod go mod download
COPY . .
RUN CGO_ENABLED=0 GOOS=linux go build -o backend ./cmd/server/main.go

FROM alpine:latest
WORKDIR /app
COPY --from=builder /app/backend .
EXPOSE 10005
CMD ["./backend"]