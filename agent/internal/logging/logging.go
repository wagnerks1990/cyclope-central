package logging

import (
	"io"
	"log/slog"
	"os"
	"strings"
)

func New(level string) *slog.Logger {
	return NewWithOutput(level, os.Stdout)
}

func NewWithOutput(level string, output io.Writer) *slog.Logger {
	var parsed slog.Level
	switch strings.ToUpper(level) {
	case "DEBUG":
		parsed = slog.LevelDebug
	case "WARN":
		parsed = slog.LevelWarn
	case "ERROR":
		parsed = slog.LevelError
	default:
		parsed = slog.LevelInfo
	}
	return slog.New(slog.NewJSONHandler(output, &slog.HandlerOptions{Level: parsed}))
}
